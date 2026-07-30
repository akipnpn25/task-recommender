import streamlit as st
from datetime import datetime, timedelta

from recommender import (
    recommend_tasks,
    get_weekly_outlook,
)

from db import (
    update_progress,
    complete_task,
)

from components import (
    format_minutes,
    get_recommendation_status,
    render_progress_popover,
)
# =====================================
# 集中モードの状態を削除
# =====================================

def clear_focus_state():
    keys = [
        "focus_mode",
        "focus_task_id",
        "focus_task_title",
        "focus_started_at",
        "focus_minutes",
    ]

    for key in keys:
        st.session_state.pop(
            key,
            None,
        )


# =====================================
# 集中モード
# =====================================

def render_focus_mode():
    """課題に取り組んでいる間の集中画面"""

    task_title = st.session_state.get(
        "focus_task_title",
        "課題",
    )

    started_at_text = st.session_state.get(
        "focus_started_at"
    )

    focus_minutes = st.session_state.get(
        "focus_minutes",
        30,
    )

    # 開始時刻がなければ通常画面へ戻す
    if started_at_text is None:
        clear_focus_state()
        st.rerun()

    started_at = datetime.fromisoformat(
        started_at_text
    )

    finish_at = (
        started_at
        + timedelta(
            minutes=focus_minutes
        )
    )

    # =====================================
    # 上部
    # =====================================

    st.markdown(
        (
            '<div class="section-kicker">'
            'FOCUS MODE'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "今はこの課題だけに集中しよう。"
    )

    st.write("")

    # =====================================
    # 1秒ごとに更新するタイマー
    # =====================================

    @st.fragment(
        run_every=1
    )
    def render_countdown():

        now = datetime.now()

        remaining_seconds = int(
            (
                finish_at
                - now
            ).total_seconds()
        )

        total_seconds = (
            focus_minutes
            * 60
        )

        # =================================
        # 時間終了
        # =================================

        if remaining_seconds <= 0:

            st.markdown(
                (
                    '<div class="focus-screen">'
                    '<div class="focus-screen-label">'
                    '☕ FOCUS TIME'
                    '</div>'
                    '<div class="focus-screen-title">'
                    f'{task_title}'
                    '</div>'
                    '<div class="focus-finished">'
                    'おつかれさま！'
                    '</div>'
                    '<div class="focus-screen-message">'
                    '集中時間が終了しました。'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

            st.progress(
                1.0
            )

            st.success(
                "☕ 集中時間終了！"
                "どのくらい進んだか確認してみよう。"
            )

            if st.button(
                "✓ 集中を終えて進捗を更新",
                key="finish_focus_time",
                use_container_width=True,
                type="primary",
            ):

                clear_focus_state()

                st.session_state[
                    "message"
                ] = (
                    "おつかれさま ☕ "
                    "進捗を更新してみよう。"
                )

                st.rerun()

            return

        # =================================
        # 残り時間
        # =================================

        remaining_minutes = (
            remaining_seconds
            // 60
        )

        remaining_sec = (
            remaining_seconds
            % 60
        )

        timer_text = (
            f"{remaining_minutes:02d}:"
            f"{remaining_sec:02d}"
        )

        # =================================
        # 進捗率
        # =================================

        elapsed_seconds = (
            total_seconds
            - remaining_seconds
        )

        progress = (
            elapsed_seconds
            / total_seconds
        )

        progress = max(
            0.0,
            min(
                1.0,
                progress,
            ),
        )

        # =================================
        # 集中カード
        # =================================

        st.markdown(
            (
                '<div class="focus-screen">'
                '<div class="focus-screen-label">'
                '☕ FOCUS TIME'
                '</div>'
                '<div class="focus-screen-title">'
                f'{task_title}'
                '</div>'
                '<div class="focus-countdown">'
                f'{timer_text}'
                '</div>'
                '<div class="focus-screen-duration">'
                f'{format_minutes(focus_minutes)} 集中'
                '</div>'
                '<div class="focus-screen-message">'
                f'{started_at.strftime("%H:%M")}'
                ' 〜 '
                f'{finish_at.strftime("%H:%M")}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.progress(
            progress
        )

        st.caption(
            "☕ 焦らず、この課題だけに集中。"
        )

        st.write("")

        # =================================
        # 途中で終了
        # =================================

        if st.button(
            "✓ ここで集中を終える",
            key="finish_focus_early",
            use_container_width=True,
            type="primary",
        ):

            clear_focus_state()

            st.session_state[
                "message"
            ] = (
                "おつかれさま ☕ "
                "どのくらい進んだか更新してみよう。"
            )

            st.rerun()

        if st.button(
            "中断しておすすめ画面に戻る",
            key="cancel_focus",
            use_container_width=True,
        ):

            clear_focus_state()

            st.rerun()

    render_countdown()

# =====================================
# 今週の課題全体の見通し
# =====================================

def render_week_outlook(
    tasks,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides,
):
    outlook_summary = (
        get_weekly_outlook(
            tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
            days=7,
        )
    )

    outlook_days = (
        outlook_summary[
            "days"
        ]
    )

    first_shortage = (
        outlook_summary[
            "first_shortage"
        ]
    )

    weekday_names = [
        "月",
        "火",
        "水",
        "木",
        "金",
        "土",
        "日",
    ]

    st.markdown(
        "### 📅 今週の課題全体の見通し"
    )

    st.caption(
        "登録している課題すべてをもとに、"
        "その日までの作業時間に"
        "余裕があるかを表示しています。"
    )

    st.caption(
        "○ 余裕あり　"
        "△ 少し注意　"
        "× 時間不足"
    )

    # -------------------------
    # 見通しカードCSS
    # -------------------------

    st.markdown(
        """
        <style>

        .week-outlook-grid {
            display: grid;
            grid-template-columns:
                repeat(7, 1fr);
            gap: 8px;
            margin-top: 12px;
            margin-bottom: 16px;
        }

        .outlook-card {
            border-radius: 14px;
            padding: 12px 6px;
            text-align: center;
            border: 1px solid
                rgba(90, 70, 55, 0.08);
        }

        .outlook-safe {
            background: #E8EFE5;
        }

        .outlook-warning {
            background: #F4E8CC;
        }

        .outlook-shortage {
            background: #F0D8D2;
        }

        .outlook-date {
            font-size: 13px;
            color: #6D625A;
        }

        .outlook-weekday {
            font-size: 12px;
            color: #8A7D73;
        }

        .outlook-symbol {
            font-size: 26px;
            font-weight: 600;
            color: #3D3834;
            line-height: 1.4;
        }

        .outlook-label {
            font-size: 11px;
            color: #5F5751;
        }

        @media (
            max-width: 700px
        ) {
            .week-outlook-grid {
                grid-template-columns:
                    repeat(4, 1fr);
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 各日のカード
    # -------------------------

    cards = []

    for day in outlook_days:

        date_object = (
            datetime.fromisoformat(
                day["date"]
            ).date()
        )

        status = (
            day["status"]
        )

        if status == "shortage":

            symbol = "×"
            label = "時間不足"
            css_class = (
                "outlook-shortage"
            )

        elif status == "warning":

            symbol = "△"
            label = "少し注意"
            css_class = (
                "outlook-warning"
            )

        else:

            symbol = "○"
            label = "余裕あり"
            css_class = (
                "outlook-safe"
            )

        weekday = (
            weekday_names[
                date_object.weekday()
            ]
        )

        cards.append(
            (
                f'<div class="outlook-card {css_class}">'
                f'<div class="outlook-date">'
                f'{date_object.strftime("%m/%d")}'
                f'</div>'
                f'<div class="outlook-weekday">'
                f'{weekday}'
                f'</div>'
                f'<div class="outlook-symbol">'
                f'{symbol}'
                f'</div>'
                f'<div class="outlook-label">'
                f'{label}'
                f'</div>'
                f'</div>'
            )
        )

    cards_html = (
        '<div class="week-outlook-grid">'
        + "".join(
            cards
        )
        + "</div>"
    )

    st.markdown(
        cards_html,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 時間不足メッセージ
    # -------------------------

    if first_shortage is not None:

        shortage_date = (
            datetime.fromisoformat(
                first_shortage[
                    "date"
                ]
            ).date()
        )

        shortage_minutes = abs(
            first_shortage[
                "slack_minutes"
            ]
        )

        st.warning(
            "⚠️ 課題全体では、"
            f"{shortage_date.strftime('%m/%d')}時点から"
            f"約{format_minutes(shortage_minutes)}"
            "不足する見込みです。"
        )

    else:

        st.success(
            "🌿 課題全体では、"
            "今週は今の予定で"
            "間に合う見込みです。"
        )


# =====================================
# 1位の課題
# =====================================

def render_best_task(
    best,
    available_minutes,
):
    (
        best_task_id,
        best_title,
        best_deadline,
        _best_estimated_minutes,
        best_progress,
    ) = best["task"]

    best_deadline_dt = (
        datetime.fromisoformat(
            best_deadline
        )
    )

    (
        status_title,
        status_message,
    ) = get_recommendation_status(
        best
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

    # -------------------------
    # 状態の色
    # -------------------------

    if "締切超過" in status_title:

        status_class = (
            "status-danger"
        )

    elif (
        "今すぐ" in status_title
        or "今から" in status_title
    ):

        status_class = (
            "status-urgent"
        )

    elif "そろそろ" in status_title:

        status_class = (
            "status-warning"
        )

    else:

        status_class = (
            "status-safe"
        )

    # -------------------------
    # 1位カード
    # -------------------------

    with st.container(
        border=True
    ):

        st.markdown(
            (
                '<div class="today-pick-label">'
                "TODAY'S PICK"
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="today-pick-title">'
                f'🥇 1位　{best_title}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        # -------------------------
        # 締切まで
        # -------------------------

        if remaining_hours > 0:

            if remaining_hours < 24:

                deadline_text = (
                    "あと約"
                    f"{max(1, round(remaining_hours))}"
                    "時間"
                )

            else:

                deadline_text = (
                    "あと約"
                    f"{round(remaining_hours / 24, 1)}"
                    "日"
                )

        else:

            deadline_text = (
                "締切を過ぎています"
            )

        # -------------------------
        # 締切 / 残り時間
        # -------------------------

        info_col1, info_col2 = (
            st.columns(
                2,
                gap="medium",
            )
        )

        with info_col1:

            st.markdown(
                (
                    '<div class="task-info-card">'
                    '<div class="task-info-label">'
                    '📅 締切'
                    '</div>'
                    '<div class="task-info-value">'
                    f'{best_deadline_dt.strftime("%m/%d %H:%M")}'
                    '</div>'
                    '<div class="task-info-sub">'
                    f'{deadline_text}'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

        with info_col2:

            st.markdown(
                (
                    '<div class="task-info-card">'
                    '<div class="task-info-label">'
                    '⏱️ この課題の残り'
                    '</div>'
                    '<div class="task-info-value">'
                    f'{format_minutes(remaining_minutes)}'
                    '</div>'
                    '<div class="task-info-sub">'
                    f'進捗 {best_progress}%'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

        # -------------------------
        # 状態
        # -------------------------

        st.markdown(
            (
                f'<div class="status-pill '
                f'{status_class}">'
                f'{status_title}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            status_message
        )

        st.write("")

        # -------------------------
        # 進捗
        # -------------------------

        st.markdown(
            f"**現在の進捗　"
            f"{best_progress}%**"
        )

        st.progress(
            best_progress / 100
        )

        st.write("")

        # -------------------------
        # 締切までの見通し
        # -------------------------

        st.markdown(
            (
                '<div class="section-kicker">'
                'SCHEDULE'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                '締切までの見通し'
                '</div>'
            ),
            unsafe_allow_html=True,
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
            "必要時間は、この課題と"
            "それ以前に締切がある課題の"
            "残り作業時間の合計です。"
        )

        # -------------------------
        # おすすめ理由
        # -------------------------

        reason_html = "".join(
            (
                '<div class="reason-item">'
                f'・{reason}'
                '</div>'
            )
            for reason in best[
                "reasons"
            ]
        )

        st.markdown(
            (
                '<div class="reason-box">'
                '<div class="reason-title">'
                '🌿 おすすめ理由'
                '</div>'
                f'{reason_html}'
                '</div>'
            ),
            unsafe_allow_html=True,
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

            st.markdown(
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
        # 今から始める
        # -------------------------

        st.write("")

        if st.button(
            (
                "☕ 今から"
                f"{format_minutes(available_minutes)}"
                "始める"
            ),
            key=(
                "start_focus_"
                f"{best_task_id}"
            ),
            use_container_width=True,
            type="primary",
        ):

            st.session_state[
                "focus_mode"
            ] = True

            st.session_state[
                "focus_task_id"
            ] = best_task_id

            st.session_state[
                "focus_task_title"
            ] = best_title

            st.session_state[
                "focus_started_at"
            ] = (
                datetime.now().isoformat()
            )

            st.session_state[
                "focus_minutes"
            ] = available_minutes

            st.rerun()

    return (
        best_task_id,
        best_title,
        best_progress,
    )


# =====================================
# 1位の進捗更新
# =====================================

def render_best_progress(
    best_task_id,
    best_title,
    best_progress,
):
    st.write("")

    with st.container(
        border=True
    ):

        st.markdown(
            (
                '<div class="section-kicker">'
                'PROGRESS'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                '☕ 今日どのくらい進んだ？'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            "進んだ割合を選ぶと、"
            "残り作業時間と"
            "おすすめ順位を更新します。"
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
            "✓ この課題を完了する",
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
                "celebrate_task"
            ] = best_title

            st.rerun()


# =====================================
# 2位・3位
# =====================================

def render_other_recommendations(
    top_recommendations,
):
    if (
        len(
            top_recommendations
        )
        < 2
    ):
        return

    st.write("")
    st.write("")

    st.markdown(
        (
            '<div class="section-kicker">'
            'NEXT'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div class="section-heading">'
            '他のおすすめ'
            '</div>'
        ),
        unsafe_allow_html=True,
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
            _estimated_minutes,
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

        medal = (
            "🥈"
            if rank == 2
            else "🥉"
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {medal} "
                f"{rank}位　{title}"
            )

            col1, col2, col3 = (
                st.columns(3)
            )

            with col1:

                st.caption(
                    "締切"
                )

                st.write(
                    deadline_dt.strftime(
                        "%m/%d %H:%M"
                    )
                )

            with col2:

                st.caption(
                    "残り"
                )

                st.write(
                    format_minutes(
                        task_remaining
                    )
                )

            with col3:

                st.caption(
                    "進捗"
                )

                st.write(
                    f"{progress}%"
                )

            if task_slack < 0:

                st.warning(
                    "締切までに約"
                    f"{format_minutes(abs(task_slack))}"
                    "不足する見込みです。"
                )

            render_progress_popover(
                task_id,
                title,
                progress,
                key_prefix=(
                    f"rank_{rank}"
                ),
            )

            with st.expander(
                "おすすめ理由を見る"
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
# 今日画面
# =====================================

def render_today(
    tasks,
    weekly_available_minutes,
    date_overrides,
):

    # =====================================
    # 集中モード
    # =====================================

    if st.session_state.get(
        "focus_mode",
        False,
    ):

        render_focus_mode()

        return

    # =====================================
    # 今使える時間
    # =====================================

    with st.container(
        border=True
    ):

        st.markdown(
            (
                '<div class="section-kicker">'
                'NOW'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                '☕ 今どれくらい時間がありますか？'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-description">'
                '今使える時間に合わせて、'
                '取り組みやすい課題をおすすめします。'
                '</div>'
            ),
            unsafe_allow_html=True,
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
                "今使える時間",
                list(
                    available_options.keys()
                ),
                index=3,
                horizontal=True,
                key="available_time",
                label_visibility=(
                    "collapsed"
                ),
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

        return

    st.write("")

    # =====================================
    # 今週の課題全体
    # =====================================

    with st.container(
        border=True
    ):

        render_week_outlook(
            tasks,
            available_minutes,
            weekly_available_minutes,
            date_overrides,
        )

    st.write("")

    # =====================================
    # 推薦
    # =====================================

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

    # =====================================
    # 1位
    # =====================================

    (
        best_task_id,
        best_title,
        best_progress,
    ) = render_best_task(
        top_recommendations[0],
        available_minutes,
    )

    # =====================================
    # 進捗
    # =====================================

    render_best_progress(
        best_task_id,
        best_title,
        best_progress,
    )

    # =====================================
    # 2位・3位
    # =====================================

    render_other_recommendations(
        top_recommendations
    )