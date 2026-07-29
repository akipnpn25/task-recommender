import streamlit as st

from datetime import datetime, time, timedelta

from recommender import recommend_tasks

from db import (
    init_db,
    add_task,
    get_tasks,
    get_completed_tasks,
    update_task,
    update_progress,
    complete_task,
    restore_task,
    delete_task,
    get_weekly_settings,
    save_weekly_settings,
    get_date_overrides,
    save_date_override,
    delete_date_override,
)


# =====================================
# 便利関数
# =====================================

def format_minutes(minutes):
    minutes = max(
        0,
        round(minutes),
    )

    hours = (
        minutes // 60
    )

    remaining_minutes = (
        minutes % 60
    )

    if hours == 0:
        return (
            f"{remaining_minutes}分"
        )

    if remaining_minutes == 0:
        return (
            f"{hours}時間"
        )

    return (
        f"{hours}時間"
        f"{remaining_minutes}分"
    )


def get_recommendation_status(
    recommendation
):
    metrics = (
        recommendation[
            "metrics"
        ]
    )

    remaining_hours = (
        metrics[
            "remaining_hours"
        ]
    )

    slack_minutes = (
        metrics[
            "slack_minutes"
        ]
    )

    # -------------------------
    # 締切超過
    # -------------------------

    if remaining_hours <= 0:

        return (
            "🚨 締切超過",
            "締切を過ぎています。"
            "優先して取り組みましょう。",
        )

    # -------------------------
    # 最初の時間不足に関係する課題
    # -------------------------

    schedule_summary = (
        recommendation.get(
            "schedule_summary",
            {},
        )
    )

    first_shortage = (
        schedule_summary.get(
            "first_shortage"
        )
    )

    if (
        first_shortage is not None
        and recommendation.get(
            "contributes_to_first_shortage",
            False,
        )
    ):

        shortage_dt = (
            datetime.fromisoformat(
                first_shortage[
                    "deadline"
                ]
            )
        )

        return (
            "🔥 今から進めたい",
            (
                f"{shortage_dt.strftime('%m/%d')}の"
                "締切までに、"
                f"約{format_minutes(abs(first_shortage['slack_minutes']))}"
                "不足する見込みです。"
            ),
        )

    # -------------------------
    # その他
    # -------------------------

    if slack_minutes < 0:

        return (
            "🔥 今すぐやる",
            (
                "この締切までに約"
                f"{format_minutes(abs(slack_minutes))}"
                "不足する見込みです。"
            ),
        )

    if (
        slack_minutes <= 60
        or recommendation[
            "score"
        ] >= 75
    ):

        return (
            "⚠️ そろそろやる",
            "締切までの余裕が"
            "少なくなっています。",
        )

    return (
        "🙂 まだ余裕あり",
        "現時点では比較的余裕があります。",
    )


# =====================================
# 2位・3位用進捗ポップアップ
# =====================================

def render_progress_popover(
    task_id,
    title,
    progress,
    key_prefix,
):
    progress_options = {
        "1割": 10,
        "2割": 20,
        "3割": 30,
        "4割": 40,
        "5割": 50,
        "6割": 60,
        "7割": 70,
        "8割": 80,
        "9割": 90,
    }

    with st.popover(
        "📈 進捗を更新",
        use_container_width=True,
    ):

        selected_label = (
            st.segmented_control(
                "どのくらい進みましたか？",
                options=list(
                    progress_options.keys()
                ),
                selection_mode="single",
                key=(
                    f"{key_prefix}_"
                    f"progress_{task_id}"
                ),
            )
        )

        if (
            selected_label
            is not None
        ):

            new_progress = (
                progress_options[
                    selected_label
                ]
            )

            if (
                new_progress
                != progress
            ):

                update_progress(
                    task_id,
                    new_progress,
                )

                st.session_state[
                    "message"
                ] = (
                    f"「{title}」の進捗を"
                    f"{selected_label}に更新しました。"
                )

                st.rerun()

        if st.button(
            "✅ 終わった！",
            key=(
                f"{key_prefix}_"
                f"finish_{task_id}"
            ),
            use_container_width=True,
        ):

            complete_task(
                task_id
            )

            st.session_state[
                "message"
            ] = (
                f"「{title}」完了！🎉"
            )

            st.rerun()


# =====================================
# 初期設定
# =====================================

st.set_page_config(
    page_title="今やる課題推薦",
    page_icon="📚",
)

init_db()

st.title(
    "📚 今やる課題推薦"
)

st.caption(
    "空き時間・締切・残り作業量から、"
    "今取り組むべき課題をおすすめします。"
)


# =====================================
# 操作後メッセージ
# =====================================

if "message" in st.session_state:

    st.success(
        st.session_state.pop(
            "message"
        )
    )


# =====================================
# 設定読み込み
# =====================================

saved_weekly_settings = (
    get_weekly_settings()
)

date_overrides = (
    get_date_overrides()
)

weekday_names = [
    "月曜日",
    "火曜日",
    "水曜日",
    "木曜日",
    "金曜日",
    "土曜日",
    "日曜日",
]

weekly_time_values = [
    0,
    30,
    60,
    120,
    180,
    240,
    300,
]

weekly_available_minutes = {}


# =====================================
# サイドバー
# =====================================

with st.sidebar:

    st.header(
        "⚙️ 設定"
    )

    # -------------------------
    # 普段の空き時間
    # -------------------------

    with st.expander(
        "普段の空き時間"
    ):

        st.caption(
            "各曜日に普段どれくらい"
            "課題へ使えるか設定します。"
        )

        for (
            weekday_index,
            weekday_name,
        ) in enumerate(
            weekday_names
        ):

            saved_minutes = (
                saved_weekly_settings.get(
                    weekday_index,
                    120,
                )
            )

            try:

                default_index = (
                    weekly_time_values.index(
                        saved_minutes
                    )
                )

            except ValueError:

                default_index = 3

            selected_minutes = (
                st.selectbox(
                    weekday_name,
                    weekly_time_values,
                    index=default_index,
                    format_func=(
                        format_minutes
                    ),
                    key=(
                        f"weekday_"
                        f"{weekday_index}"
                    ),
                )
            )

            weekly_available_minutes[
                weekday_index
            ] = selected_minutes

        if st.button(
            "普段の設定を保存",
            use_container_width=True,
        ):

            save_weekly_settings(
                weekly_available_minutes
            )

            st.session_state[
                "message"
            ] = (
                "普段の空き時間を保存しました。"
            )

            st.rerun()

    # -------------------------
    # 今週だけ変更
    # -------------------------

    with st.expander(
        "📅 今週だけ変更"
    ):

        st.caption(
            "試験・バイトなどで"
            "普段と違う日だけ変更できます。"
        )

        tomorrow = (
            datetime.now().date()
            + timedelta(days=1)
        )

        override_date = (
            st.date_input(
                "変更する日",
                value=tomorrow,
                min_value=tomorrow,
                max_value=(
                    datetime.now().date()
                    + timedelta(
                        days=7
                    )
                ),
                key="override_date",
            )
        )

        override_minutes = (
            st.selectbox(
                "その日に使える時間",
                weekly_time_values,
                index=3,
                format_func=(
                    format_minutes
                ),
                key="override_minutes",
            )
        )

        if st.button(
            "この日を変更",
            key="save_override",
            use_container_width=True,
        ):

            save_date_override(
                override_date.isoformat(),
                override_minutes,
            )

            st.session_state[
                "message"
            ] = (
                f"{override_date.strftime('%m/%d')}の"
                "空き時間を変更しました。"
            )

            st.rerun()

        future_overrides = []

        for (
            date_string,
            minutes,
        ) in sorted(
            date_overrides.items()
        ):

            date_object = (
                datetime.fromisoformat(
                    date_string
                ).date()
            )

            if (
                date_object
                >= datetime.now().date()
            ):

                future_overrides.append(
                    (
                        date_string,
                        date_object,
                        minutes,
                    )
                )

        if future_overrides:

            st.divider()

            st.caption(
                "変更済み"
            )

            for (
                date_string,
                date_object,
                minutes,
            ) in future_overrides:

                col1, col2 = (
                    st.columns(
                        [3, 1]
                    )
                )

                with col1:

                    st.write(
                        f"{date_object.strftime('%m/%d')} "
                        f"→ {format_minutes(minutes)}"
                    )

                with col2:

                    if st.button(
                        "戻す",
                        key=(
                            "remove_override_"
                            f"{date_string}"
                        ),
                    ):

                        delete_date_override(
                            date_string
                        )

                        st.rerun()


# =====================================
# 共通データ
# =====================================

tasks = get_tasks()

task_time_options = {
    "15分": 15,
    "30分": 30,
    "45分": 45,
    "1時間": 60,
    "1時間30分": 90,
    "2時間": 120,
    "3時間": 180,
    "4時間": 240,
    "5時間": 300,
    "6時間以上": 360,
}


# =====================================
# タブ
# =====================================

recommend_tab, tasks_tab, add_tab = (
    st.tabs(
        [
            "🔥 おすすめ",
            "📋 課題一覧",
            "➕ 課題追加",
        ]
    )
)


# =====================================
# おすすめタブ
# =====================================

with recommend_tab:

    st.subheader(
        "今やるなら？"
    )

    available_options = {
        "15分": 15,
        "30分": 30,
        "45分": 45,
        "1時間": 60,
        "1時間30分": 90,
        "2時間": 120,
        "3時間": 180,
    }

    available_label = (
        st.radio(
            "今どれくらい時間がありますか？",
            list(
                available_options.keys()
            ),
            index=3,
            horizontal=True,
            key="available_time",
        )
    )

    available_minutes = (
        available_options[
            available_label
        ]
    )

    if not tasks:

        st.info(
            "課題を登録すると、"
            "おすすめが表示されます。"
        )

    else:

        recommendations = (
            recommend_tasks(
                tasks,
                available_minutes,
                weekly_available_minutes,
                date_overrides,
            )
        )

        top_recommendations = (
            recommendations[:3]
        )

        # -------------------------
        # 全体の時間不足
        # -------------------------

        schedule_summary = (
            recommendations[
                0
            ][
                "schedule_summary"
            ]
        )

        first_shortage = (
            schedule_summary[
                "first_shortage"
            ]
        )

        if first_shortage is not None:

            shortage_dt = (
                datetime.fromisoformat(
                    first_shortage[
                        "deadline"
                    ]
                )
            )

            st.warning(
                "📉 現在の予定では、"
                f"{shortage_dt.strftime('%m/%d')}の"
                "締切時点で"
                f"約{format_minutes(abs(first_shortage['slack_minutes']))}"
                "不足する見込みです。"
            )

        else:

            st.info(
                "✅ 現在登録されている予定では、"
                "締切までの作業時間を"
                "確保できる見込みです。"
            )

        # =========================
        # 1位
        # =========================

        best = (
            top_recommendations[
                0
            ]
        )

        (
            best_task_id,
            best_title,
            best_deadline,
            best_estimated_minutes,
            best_progress,
        ) = best["task"]

        best_deadline_dt = (
            datetime.fromisoformat(
                best_deadline
            )
        )

        status_title, status_message = (
            get_recommendation_status(
                best
            )
        )

        metrics = (
            best[
                "metrics"
            ]
        )

        remaining_hours = (
            metrics[
                "remaining_hours"
            ]
        )

        available_until_deadline = (
            metrics[
                "available_minutes"
            ]
        )

        required_until_deadline = (
            metrics[
                "required_minutes"
            ]
        )

        slack_minutes = (
            metrics[
                "slack_minutes"
            ]
        )

        remaining_minutes = (
            metrics[
                "task_remaining_minutes"
            ]
        )

        st.markdown(
            f"## 🥇 {status_title}"
        )

        st.success(
            f"### {best_title}"
        )

        st.caption(
            "📅 締切："
            f"{best_deadline_dt.strftime('%m/%d %H:%M')}"
        )

        if remaining_hours > 0:

            if remaining_hours < 24:

                st.caption(
                    "⏰ 締切まで約"
                    f"{max(1, round(remaining_hours))}時間"
                )

            else:

                st.caption(
                    "📅 締切まで約"
                    f"{round(remaining_hours / 24, 1)}日"
                )

        st.write(
            status_message
        )

        # -------------------------
        # 進捗
        # -------------------------

        st.write(
            f"**現在の進捗："
            f"{best_progress}%**"
        )

        st.progress(
            best_progress / 100
        )

        st.caption(
            "この課題の残り："
            f"約{format_minutes(remaining_minutes)}"
        )

        # -------------------------
        # 締切までの見通し
        # -------------------------

        st.write(
            "**締切までの見通し**"
        )

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:

            st.metric(
                "使える時間",
                format_minutes(
                    available_until_deadline
                ),
            )

        with col2:

            st.metric(
                "必要時間",
                format_minutes(
                    required_until_deadline
                ),
            )

        with col3:

            if slack_minutes < 0:

                st.metric(
                    "不足",
                    format_minutes(
                        abs(
                            slack_minutes
                        )
                    ),
                )

            else:

                st.metric(
                    "余裕",
                    format_minutes(
                        slack_minutes
                    ),
                )

        st.caption(
            "※必要時間は、この課題と"
            "それ以前が締切の課題の"
            "残り作業時間の合計です。"
        )

        # -------------------------
        # 推薦理由
        # -------------------------

        st.write(
            "**おすすめ理由**"
        )

        for reason in (
            best[
                "reasons"
            ]
        ):

            st.write(
                f"・{reason}"
            )

        # -------------------------
        # 推薦スコア
        # -------------------------

        with st.expander(
            "💡 なぜこの課題が1位？"
        ):

            score_details = (
                best[
                    "score_details"
                ]
            )

            st.write(
                "**総合おすすめ度："
                f"{best['score']} / 100**"
            )

            st.write(
                "締切の近さ"
            )

            st.progress(
                score_details[
                    "urgency"
                ] / 30
            )

            st.caption(
                f"{score_details['urgency']} / 30点"
            )

            st.write(
                "時間不足のリスク"
            )

            st.progress(
                score_details[
                    "risk"
                ] / 50
            )

            st.caption(
                f"{score_details['risk']} / 50点"
            )

            st.write(
                "今の空き時間との相性"
            )

            st.progress(
                score_details[
                    "fit"
                ] / 20
            )

            st.caption(
                f"{score_details['fit']} / 20点"
            )

        # -------------------------
        # 1位の進捗更新
        # -------------------------

        st.divider()

        st.write(
            "**どのくらい進みましたか？**"
        )

        progress_options = {
            "1割": 10,
            "2割": 20,
            "3割": 30,
            "4割": 40,
            "5割": 50,
            "6割": 60,
            "7割": 70,
            "8割": 80,
            "9割": 90,
        }

        selected_label = (
            st.segmented_control(
                "進捗",
                options=list(
                    progress_options.keys()
                ),
                selection_mode="single",
                key=(
                    "recommend_progress_"
                    f"{best_task_id}"
                ),
                width="stretch",
                label_visibility=(
                    "collapsed"
                ),
            )
        )

        if (
            selected_label
            is not None
        ):

            new_progress = (
                progress_options[
                    selected_label
                ]
            )

            if (
                new_progress
                != best_progress
            ):

                update_progress(
                    best_task_id,
                    new_progress,
                )

                st.session_state[
                    "message"
                ] = (
                    f"「{best_title}」の進捗を"
                    f"{selected_label}に更新しました。"
                )

                st.rerun()

        if st.button(
            "✅ 終わった！",
            key=(
                "recommend_finish_"
                f"{best_task_id}"
            ),
            use_container_width=True,
        ):

            complete_task(
                best_task_id
            )

            st.session_state[
                "message"
            ] = (
                f"「{best_title}」完了！🎉"
            )

            st.rerun()

        # =========================
        # 2位・3位
        # =========================

        if (
            len(
                top_recommendations
            )
            >= 2
        ):

            st.divider()

            st.subheader(
                "他のおすすめ"
            )

            for (
                rank,
                recommendation,
            ) in enumerate(
                top_recommendations[
                    1:
                ],
                start=2,
            ):

                (
                    task_id,
                    title,
                    deadline,
                    estimated_minutes,
                    progress,
                ) = (
                    recommendation[
                        "task"
                    ]
                )

                deadline_dt = (
                    datetime.fromisoformat(
                        deadline
                    )
                )

                task_metrics = (
                    recommendation[
                        "metrics"
                    ]
                )

                task_remaining = (
                    task_metrics[
                        "task_remaining_minutes"
                    ]
                )

                task_slack = (
                    task_metrics[
                        "slack_minutes"
                    ]
                )

                medal = (
                    "🥈"
                    if rank == 2
                    else "🥉"
                )

                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"#### {medal} "
                        f"{rank}位　{title}"
                    )

                    col1, col2, col3 = (
                        st.columns(3)
                    )

                    with col1:

                        st.write(
                            "📅 "
                            f"{deadline_dt.strftime('%m/%d')}"
                        )

                    with col2:

                        st.write(
                            "⏱️ "
                            f"{format_minutes(task_remaining)}"
                        )

                    with col3:

                        st.write(
                            f"📈 {progress}%"
                        )

                    if task_slack < 0:

                        st.warning(
                            "締切までに約"
                            f"{format_minutes(abs(task_slack))}"
                            "不足する見込みです。"
                        )

                    # -----------------
                    # コンパクトな進捗更新
                    # -----------------

                    render_progress_popover(
                        task_id,
                        title,
                        progress,
                        key_prefix=(
                            f"rank_{rank}"
                        ),
                    )

                    # -----------------
                    # 理由
                    # -----------------

                    with st.expander(
                        "おすすめ理由"
                    ):

                        st.write(
                            "おすすめ度："
                            f"{recommendation['score']}"
                            " / 100"
                        )

                        for reason in (
                            recommendation[
                                "reasons"
                            ]
                        ):

                            st.write(
                                f"・{reason}"
                            )


# =====================================
# 課題一覧
# =====================================

with tasks_tab:

    st.subheader(
        f"未完了の課題"
        f"（{len(tasks)}件）"
    )

    if not tasks:

        st.info(
            "未完了の課題はありません。"
        )

    else:

        for task in tasks:

            (
                task_id,
                title,
                deadline,
                estimated_minutes,
                progress,
            ) = task

            deadline_dt = (
                datetime.fromisoformat(
                    deadline
                )
            )

            remaining_minutes = (
                round(
                    estimated_minutes
                    * (
                        100
                        - progress
                    )
                    / 100
                )
            )

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### {title}"
                )

                col1, col2 = (
                    st.columns(2)
                )

                with col1:

                    st.write(
                        "📅 "
                        f"{deadline_dt.strftime('%m/%d')}まで"
                    )

                with col2:

                    st.write(
                        "⏱️ 残り約"
                        f"{format_minutes(remaining_minutes)}"
                    )

                st.write(
                    f"進捗：{progress}%"
                )

                st.progress(
                    progress / 100
                )

                if st.button(
                    "✅ 完了",
                    key=(
                        f"complete_"
                        f"{task_id}"
                    ),
                    use_container_width=True,
                ):

                    complete_task(
                        task_id
                    )

                    st.session_state[
                        "message"
                    ] = (
                        f"「{title}」を"
                        "完了にしました！"
                    )

                    st.rerun()

                with st.expander(
                    "✏️ 編集"
                ):

                    edited_title = (
                        st.text_input(
                            "課題名",
                            value=title,
                            key=(
                                f"title_"
                                f"{task_id}"
                            ),
                        )
                    )

                    edited_date = (
                        st.date_input(
                            "締切日",
                            value=(
                                deadline_dt.date()
                            ),
                            key=(
                                f"date_"
                                f"{task_id}"
                            ),
                        )
                    )
                    
                    # ---------------------
                    # 締切時刻
                    # ---------------------

                    has_custom_time = (
                        deadline_dt.time().replace(
                            second=0,
                            microsecond=0,
                        )
                        != time(
                            23,
                            59,
                        )
                    )

                    specify_edit_time = (
                        st.checkbox(
                            "締切時刻を指定する",
                            value=has_custom_time,
                            key=(
                                "specify_time_"
                                f"{task_id}"
                            ),
                        )
                    )

                    if specify_edit_time:

                        edited_deadline_time = (
                            st.time_input(
                                "締切時刻",
                                value=(
                                    deadline_dt.time()
                                ),
                                key=(
                                    "deadline_time_"
                                    f"{task_id}"
                                ),
                            )
                        )

                    else:

                        edited_deadline_time = (
                            time(
                                23,
                                59,
                            )
                        )

                    time_values = list(
                        task_time_options.values()
                    )

                    nearest_minutes = min(
                        time_values,
                        key=lambda value: abs(
                            value
                            - estimated_minutes
                        ),
                    )

                    default_index = (
                        time_values.index(
                            nearest_minutes
                        )
                    )

                    edited_time = (
                        st.selectbox(
                            "予想所要時間",
                            list(
                                task_time_options.keys()
                            ),
                            index=(
                                default_index
                            ),
                            key=(
                                f"time_"
                                f"{task_id}"
                            ),
                        )
                    )

                    if st.button(
                        "変更を保存",
                        key=(
                            f"save_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):

                        new_deadline = (
    datetime.combine(
        edited_date,
        edited_deadline_time,
    )
)

                        update_task(
                            task_id,
                            edited_title.strip(),
                            new_deadline.isoformat(),
                            task_time_options[
                                edited_time
                            ],
                        )

                        st.session_state[
                            "message"
                        ] = (
                            "課題を更新しました。"
                        )

                        st.rerun()

                    if st.button(
                        "🗑 削除",
                        key=(
                            f"delete_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):

                        delete_task(
                            task_id
                        )

                        st.rerun()

    # -------------------------
    # 完了済み
    # -------------------------

    completed_tasks = (
        get_completed_tasks()
    )

    if completed_tasks:

        st.divider()

        with st.expander(
            "✅ 完了済み"
            f"（{len(completed_tasks)}件）"
        ):

            for task in completed_tasks:

                (
                    task_id,
                    title,
                    deadline,
                    estimated_minutes,
                    progress,
                ) = task

                st.write(
                    f"**{title}**"
                )

                col1, col2 = (
                    st.columns(2)
                )

                with col1:

                    if st.button(
                        "↩️ 元に戻す",
                        key=(
                            f"restore_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):

                        restore_task(
                            task_id
                        )

                        st.rerun()

                with col2:

                    if st.button(
                        "🗑 削除",
                        key=(
                            "delete_completed_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):

                        delete_task(
                            task_id
                        )

                        st.rerun()


# =====================================
# 課題追加
# =====================================

with add_tab:

    st.subheader(
        "新しい課題を追加"
    )

    # -------------------------
    # 1. 課題名
    # -------------------------

    new_title = st.text_input(
        "課題名",
        placeholder=(
            "例：英語レポート"
        ),
        key="new_task_title",
    )

    # -------------------------
    # 2. 締切日
    # -------------------------

    new_deadline_date = st.date_input(
        "締切日",
        value=(
            datetime.now().date()
            + timedelta(days=1)
        ),
        key="new_deadline_date",
    )

    # -------------------------
    # 3. 締切時刻
    # -------------------------

    specify_deadline_time = st.checkbox(
        "⏰ 締切時刻を指定する",
        key="specify_deadline_time",
    )

    if specify_deadline_time:

        new_deadline_time = st.time_input(
            "締切時刻",
            value=time(
                23,
                59,
            ),
            key="new_deadline_time",
        )

    else:

        # 指定しなければ23:59
        new_deadline_time = time(
            23,
            59,
        )

    # -------------------------
    # 4. 予想所要時間
    # -------------------------

    new_estimated_label = st.selectbox(
        "だいたいどれくらいかかりそう？",
        list(
            task_time_options.keys()
        ),
        index=3,
        key="new_estimated_time",
    )

    # -------------------------
    # 追加ボタン
    # -------------------------

    if st.button(
        "課題を追加する",
        use_container_width=True,
        key="add_task_button",
    ):

        if not new_title.strip():

            st.error(
                "課題名を入力してください。"
            )

        else:

            deadline = datetime.combine(
                new_deadline_date,
                new_deadline_time,
            )

            add_task(
                new_title.strip(),
                deadline.isoformat(),
                task_time_options[
                    new_estimated_label
                ],
            )

            st.session_state[
                "message"
            ] = (
                f"「{new_title}」を"
                "追加しました！"
            )

            st.rerun()