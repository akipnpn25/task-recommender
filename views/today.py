import streamlit as st
from datetime import datetime

from recommender import (
    recommend_tasks,
)

from db import (
    update_progress,
    complete_task,
    get_today_focus_summary,
)

from components import (
    format_minutes,
    get_recommendation_status,
    render_progress_popover,
    render_available_time_selector,
)
from views.focus import (
    render_focus_mode,
    render_focus_result,
    start_focus_session,
)


# =====================================
# 1位
# =====================================

def render_best_task(
    best,
    available_minutes,
):
    (
        best_task_id,
        best_title,
        best_deadline,
        _estimated_minutes,
        best_progress,
    ) = best["task"]

    deadline_dt = (
        datetime.fromisoformat(
            best_deadline
        )
    )

    metrics = best[
        "metrics"
    ]

    remaining_minutes = (
        metrics[
            "task_remaining_minutes"
        ]
    )

    remaining_hours = (
        metrics[
            "remaining_hours"
        ]
    )

    (
        status_title,
        status_message,
    ) = get_recommendation_status(
        best
    )

    # =====================================
    # 状態の色
    # =====================================

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

    # =====================================
    # 締切まで
    # =====================================

    if remaining_hours <= 0:
        deadline_text = (
            "締切を過ぎています"
        )

    elif remaining_hours < 24:
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

    # =====================================
    # カード
    # =====================================

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

        col1, col2 = (
            st.columns(
                2,
                gap="medium",
            )
        )

        with col1:
            st.markdown(
                (
                    '<div class="task-info-card">'
                    '<div class="task-info-label">'
                    '📅 締切'
                    '</div>'
                    '<div class="task-info-value">'
                    f'{deadline_dt.strftime("%m/%d %H:%M")}'
                    '</div>'
                    '<div class="task-info-sub">'
                    f'{deadline_text}'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

        with col2:
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

        # -------------------------
        # 進捗
        # -------------------------

        st.markdown(
            f"**現在の進捗　{best_progress}%**"
        )

        st.progress(
            best_progress / 100
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
        # 詳細スコア
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

        st.write("")

        # -------------------------
        # 今から始める
        # -------------------------

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
            start_focus_session(
                best_task_id,
                best_title,
                available_minutes,
            )

            st.rerun()

    return (
        best_task_id,
        best_title,
        best_progress,
    )


# =====================================
# 進捗更新
# =====================================

def render_best_progress(
    task_id,
    task_title,
    progress,
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
                    f"{task_id}"
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

            if new_progress != progress:
                update_progress(
                    task_id,
                    new_progress,
                )

                st.session_state[
                    "message"
                ] = (
                    f"「{task_title}」の進捗を"
                    f"{selected_label}に更新しました。"
                )

                st.rerun()

        if st.button(
            "✓ この課題を完了する",
            key=(
                "recommend_finish_"
                f"{task_id}"
            ),
            use_container_width=True,
        ):
            complete_task(
                task_id
            )

            st.session_state[
                "celebrate_task"
            ] = task_title

            st.rerun()


# =====================================
# 2位・3位
# =====================================

def render_other_recommendations(
    top_recommendations,
):
    if len(
        top_recommendations
    ) < 2:
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

        task_remaining = (
            recommendation[
                "metrics"
            ][
                "task_remaining_minutes"
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
                for reason in (
                    recommendation[
                        "reasons"
                    ]
                ):
                    st.write(
                        f"・{reason}"
                    )


# =====================================
# 今日
# =====================================

def render_today(
    tasks,
    weekly_available_minutes,
    date_overrides,
):
    # =====================================
    # 振り返り
    # =====================================

    if st.session_state.get(
        "focus_result_mode",
        False,
    ):
        render_focus_result(
            tasks
        )
        return

    # =====================================
    # 集中中
    # =====================================

    if st.session_state.get(
        "focus_mode",
        False,
    ):
        render_focus_mode()
        return

    # =====================================
    # 通常の今日画面
    # =====================================

    st.subheader(
        "☕ 今日"
    )

    st.caption(
        "今の空き時間から、"
        "最初に取り組む課題を決めます。"
    )

    # -------------------------
    # 今使える時間
    # -------------------------

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
                '今どれくらい時間がありますか？'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        available_minutes = (
            render_available_time_selector(
                key="today_available_time"
            )
        )

    st.write("")

    # -------------------------
    # 今日の集中実績
    # -------------------------

    focus_summary = (
        get_today_focus_summary()
    )

    with st.container(
        border=True
    ):
        st.markdown(
            (
                '<div class="section-kicker">'
                'TODAY'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                '☕ 今日の集中'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        col1, col2 = (
            st.columns(2)
        )

        with col1:
            st.metric(
                "集中時間",
                format_minutes(
                    focus_summary[
                        "total_minutes"
                    ]
                ),
            )

        with col2:
            st.metric(
                "セッション",
                (
                    f"{focus_summary['session_count']}"
                    "回"
                ),
            )

    if not tasks:
        st.info(
            "課題を登録すると、"
            "おすすめが表示されます。"
        )
        return

    st.write("")

    # -------------------------
    # 推薦
    # -------------------------

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

    (
        task_id,
        task_title,
        progress,
    ) = render_best_task(
        top_recommendations[0],
        available_minutes,
    )

    render_best_progress(
        task_id,
        task_title,
        progress,
    )

    render_other_recommendations(
        top_recommendations
    )