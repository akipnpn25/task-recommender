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
)


# =====================================
# 便利関数
# =====================================

def format_minutes(minutes):
    """分を「○時間○分」に変換する"""

    minutes = max(0, round(minutes))

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours == 0:
        return f"{remaining_minutes}分"

    if remaining_minutes == 0:
        return f"{hours}時間"

    return f"{hours}時間{remaining_minutes}分"


def get_recommendation_status(recommendation):
    """推薦結果を分かりやすい状態に変換する"""

    metrics = recommendation["metrics"]

    remaining_hours = metrics["remaining_hours"]
    slack_minutes = metrics["slack_minutes"]
    score = recommendation["score"]

    if remaining_hours <= 0:
        return (
            "🚨 締切超過",
            "締切を過ぎています。優先して取り組みましょう。",
        )

    if slack_minutes < 0:
        return (
            "🔥 今すぐやる",
            (
                f"このままだと約"
                f"{format_minutes(abs(slack_minutes))}"
                f"不足する見込みです。"
            ),
        )

    if slack_minutes <= 60 or score >= 75:
        return (
            "⚠️ そろそろやる",
            "締切までの余裕が少なくなっています。",
        )

    return (
        "🙂 まだ余裕あり",
        "現時点では比較的余裕があります。",
    )


# =====================================
# ページ設定
# =====================================

st.set_page_config(
    page_title="今やる課題推薦",
    page_icon="📚",
)

init_db()

st.title("📚 今やる課題推薦")

st.caption(
    "空き時間・締切・残り作業量から、"
    "今取り組むべき課題をおすすめします。"
)


# =====================================
# 操作後メッセージ
# =====================================

if "message" in st.session_state:
    st.success(
        st.session_state.pop("message")
    )


# =====================================
# 曜日別空き時間設定
# =====================================

saved_weekly_settings = get_weekly_settings()

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


with st.sidebar:

    st.header("⚙️ 設定")

    with st.expander(
        "普段の空き時間を変更"
    ):

        st.caption(
            "各曜日に普段どれくらい"
            "課題へ使えるか設定します。"
        )

        for weekday_index, weekday_name in enumerate(
            weekday_names
        ):

            saved_minutes = saved_weekly_settings.get(
                weekday_index,
                120,
            )

            try:
                default_index = weekly_time_values.index(
                    saved_minutes
                )

            except ValueError:
                default_index = 3

            selected_minutes = st.selectbox(
                weekday_name,
                weekly_time_values,
                index=default_index,
                format_func=format_minutes,
                key=f"weekday_{weekday_index}",
            )

            weekly_available_minutes[
                weekday_index
            ] = selected_minutes

        if st.button(
            "設定を保存",
            use_container_width=True,
        ):

            save_weekly_settings(
                weekly_available_minutes
            )

            st.session_state["message"] = (
                "空き時間の設定を保存しました。"
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
    "4時間以上": 240,
}


# =====================================
# タブ
# =====================================

recommend_tab, tasks_tab, add_tab = st.tabs(
    [
        "🔥 おすすめ",
        "📋 課題一覧",
        "➕ 課題追加",
    ]
)


# =====================================
# おすすめタブ
# =====================================

with recommend_tab:

    st.subheader("今やるなら？")

    available_options = {
        "15分": 15,
        "30分": 30,
        "45分": 45,
        "1時間": 60,
        "1時間30分": 90,
        "2時間": 120,
        "3時間": 180,
    }

    available_label = st.radio(
        "今どれくらい時間がありますか？",
        list(available_options.keys()),
        index=3,
        horizontal=True,
        key="available_time",
    )

    available_minutes = available_options[
        available_label
    ]

    # ---------------------------------
    # 課題がない場合
    # ---------------------------------

    if len(tasks) == 0:

        st.info(
            "課題を登録すると、"
            "ここにおすすめが表示されます。"
        )

    # ---------------------------------
    # 推薦
    # ---------------------------------

    else:

        recommendations = recommend_tasks(
            tasks,
            available_minutes,
            weekly_available_minutes,
        )

        top_recommendations = (
            recommendations[:3]
        )

        # =============================
        # 1位
        # =============================

        best = top_recommendations[0]

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
            get_recommendation_status(best)
        )

        metrics = best["metrics"]

        available_until_deadline = (
            metrics["available_minutes"]
        )

        required_until_deadline = (
            metrics["required_minutes"]
        )

        slack_minutes = (
            metrics["slack_minutes"]
        )

        remaining_minutes = (
            metrics[
                "task_remaining_minutes"
            ]
        )

        remaining_hours = (
            metrics["remaining_hours"]
        )

        # -----------------------------
        # メイン推薦
        # -----------------------------

        st.markdown(
            f"## 🥇 {status_title}"
        )

        st.success(
            f"### {best_title}"
        )

        st.caption(
            f"📅 締切："
            f"{best_deadline_dt.strftime('%m/%d %H:%M')}"
        )

        if remaining_hours > 0:

            if remaining_hours < 24:
                st.caption(
                    f"⏰ 締切まで約"
                    f"{max(1, round(remaining_hours))}時間"
                )

            else:
                st.caption(
                    f"📅 締切まで約"
                    f"{round(remaining_hours / 24, 1)}日"
                )

        st.write(
            status_message
        )

        # -----------------------------
        # 進捗
        # -----------------------------

        st.write(
            f"**現在の進捗："
            f"{best_progress}%**"
        )

        st.progress(
            best_progress / 100
        )

        st.caption(
            f"この課題の残り作業時間："
            f"約{format_minutes(remaining_minutes)}"
        )

        # -----------------------------
        # 締切までの見通し
        # -----------------------------

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
                        abs(slack_minutes)
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
            "※「必要時間」は、この課題と"
            "それ以前に締切を迎える課題の"
            "残り作業時間の合計です。"
        )

        # -----------------------------
        # 推薦理由
        # -----------------------------

        st.write(
            "**この課題をおすすめする理由**"
        )

        for reason in best["reasons"]:
            st.write(
                f"・{reason}"
            )

        # -----------------------------
        # なぜ1位？
        # -----------------------------

        with st.expander(
            "💡 なぜこの課題が1位？"
        ):

            st.write(
                f"**総合おすすめ度："
                f"{best['score']} / 100**"
            )

            score_details = best.get(
                "score_details"
            )

            if score_details:

                st.write(
                    "締切の近さ"
                )

                st.progress(
                    score_details[
                        "urgency"
                    ] / 30
                )

                st.caption(
                    f"{score_details['urgency']}"
                    f" / 30点"
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
                    f"{score_details['risk']}"
                    f" / 50点"
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
                    f"{score_details['fit']}"
                    f" / 20点"
                )

            else:

                st.caption(
                    "現在のrecommender.pyでは"
                    "スコア内訳が返されていません。"
                )

        # -----------------------------
        # 進捗更新
        # -----------------------------

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
                label_visibility="collapsed",
            )
        )

        if selected_label is not None:

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

            update_progress(
                best_task_id,
                100,
            )

            st.session_state[
                "message"
            ] = (
                f"「{best_title}」完了！🎉"
            )

            st.rerun()

        # =============================
        # 2位・3位
        # =============================

        if len(
            top_recommendations
        ) >= 2:

            st.divider()

            st.markdown(
                "### 他のおすすめ"
            )

            for (
                rank,
                recommendation,
            ) in enumerate(
                top_recommendations[1:],
                start=2,
            ):

                (
                    task_id,
                    title,
                    deadline,
                    estimated_minutes,
                    progress,
                ) = recommendation[
                    "task"
                ]

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

                with st.container(
                    border=True
                ):

                    medal = (
                        "🥈"
                        if rank == 2
                        else "🥉"
                    )

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
                            "⏱️ 残り "
                            f"{format_minutes(task_remaining)}"
                        )

                    with col3:

                        st.write(
                            f"📈 {progress}%"
                        )

                    if task_slack < 0:

                        st.warning(
                            "この締切までに約"
                            f"{format_minutes(abs(task_slack))}"
                            "不足する見込みです。"
                        )

                    with st.expander(
                        "おすすめ理由を見る"
                    ):

                        st.write(
                            f"おすすめ度："
                            f"{recommendation['score']}"
                            f" / 100"
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
# 課題一覧タブ
# =====================================

with tasks_tab:

    st.subheader(
        f"未完了の課題（{len(tasks)}件）"
    )

    if len(tasks) == 0:

        st.info(
            "現在、未完了の課題はありません。"
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

            remaining_minutes = round(
                estimated_minutes
                * (100 - progress)
                / 100
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
                        f"{deadline_dt.strftime('%m/%d')}"
                        "まで"
                    )

                with col2:

                    st.write(
                        "⏱️ 残り約"
                        f"{format_minutes(remaining_minutes)}"
                    )

                # ---------------------
                # 進捗
                # ---------------------

                st.write(
                    f"進捗：{progress}%"
                )

                st.progress(
                    progress / 100
                )

                # ---------------------
                # 完了
                # ---------------------

                if st.button(
                    "✅ 完了にする",
                    key=f"complete_{task_id}",
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

                # ---------------------
                # 編集
                # ---------------------

                with st.expander(
                    "✏️ 編集"
                ):

                    edited_title = (
                        st.text_input(
                            "課題名",
                            value=title,
                            key=(
                                f"title_{task_id}"
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
                                f"date_{task_id}"
                            ),
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

                    default_time_index = (
                        time_values.index(
                            nearest_minutes
                        )
                    )

                    edited_time_label = (
                        st.selectbox(
                            "予想所要時間",
                            list(
                                task_time_options.keys()
                            ),
                            index=(
                                default_time_index
                            ),
                            key=(
                                f"time_{task_id}"
                            ),
                        )
                    )

                    if st.button(
                        "変更を保存",
                        key=(
                            f"save_{task_id}"
                        ),
                        use_container_width=True,
                    ):

                        new_deadline = (
                            datetime.combine(
                                edited_date,
                                time(23, 59),
                            )
                        )

                        update_task(
                            task_id=task_id,
                            title=(
                                edited_title.strip()
                            ),
                            deadline=(
                                new_deadline.isoformat()
                            ),
                            estimated_minutes=(
                                task_time_options[
                                    edited_time_label
                                ]
                            ),
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
                            f"delete_{task_id}"
                        ),
                        use_container_width=True,
                    ):

                        delete_task(
                            task_id
                        )

                        st.session_state[
                            "message"
                        ] = (
                            f"「{title}」を"
                            "削除しました。"
                        )

                        st.rerun()

    # ---------------------------------
    # 完了済み
    # ---------------------------------

    completed_tasks = (
        get_completed_tasks()
    )

    if completed_tasks:

        st.divider()

        with st.expander(
            f"✅ 完了済み"
            f"（{len(completed_tasks)}件）"
        ):

            for task in completed_tasks:

                (
                    task_id,
                    title,
                    deadline,
                    estimated_minutes,
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
                            f"restore_{task_id}"
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

                st.divider()


# =====================================
# 課題追加タブ
# =====================================

with add_tab:

    st.subheader(
        "新しい課題を追加"
    )

    st.caption(
        "3項目だけで登録できます。"
    )

    with st.form(
        "task_form",
        clear_on_submit=True,
    ):

        new_title = st.text_input(
            "課題名",
            placeholder=(
                "例：推薦システム最終課題"
            ),
        )

        new_deadline_date = (
            st.date_input(
                "締切日",
                value=(
                    datetime.now().date()
                    + timedelta(days=1)
                ),
            )
        )

        new_estimated_label = (
            st.selectbox(
                "だいたいどれくらいかかりそう？",
                list(
                    task_time_options.keys()
                ),
                index=3,
            )
        )

        submitted = (
            st.form_submit_button(
                "課題を追加する",
                use_container_width=True,
            )
        )

    if submitted:

        if not new_title.strip():

            st.error(
                "課題名を入力してください。"
            )

        else:

            new_deadline = (
                datetime.combine(
                    new_deadline_date,
                    time(23, 59),
                )
            )

            add_task(
                title=new_title.strip(),
                deadline=(
                    new_deadline.isoformat()
                ),
                estimated_minutes=(
                    task_time_options[
                        new_estimated_label
                    ]
                ),
            )

            st.session_state[
                "message"
            ] = (
                f"「{new_title}」を"
                "追加しました！"
            )

            st.rerun()