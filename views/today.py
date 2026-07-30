import streamlit as st
from datetime import datetime

from recommender import (
    recommend_tasks,
)

from db import (
    get_today_focus_summary,
)

from components import (
    format_minutes,
    format_deadline_friendly,
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
        task_id,
        title,
        deadline,
        _estimated_minutes,
        progress,
    ) = best["task"]

    metrics = (
        best[
            "metrics"
        ]
    )

    remaining_minutes = (
        metrics[
            "task_remaining_minutes"
        ]
    )

    deadline_text = (
        format_deadline_friendly(
            deadline
        )
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
    # 1位カード
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
                f'🥇 {title}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        # -------------------------
        # 一番大事な情報だけ
        # -------------------------

        col1, col2 = (
            st.columns(2)
        )

        with col1:
            st.caption(
                "📅 締切"
            )

            st.markdown(
                f"**{deadline_text}**"
            )

        with col2:
            st.caption(
                "⏱️ 残り"
            )

            st.markdown(
                "**"
                f"{format_minutes(remaining_minutes)}"
                "**"
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

        # -------------------------
        # 進捗
        # -------------------------

        st.progress(
            progress / 100
        )

        st.caption(
            f"進捗 {progress}%"
        )

        # -------------------------
        # 今から始める
        # -------------------------

        if st.button(
            (
                "☕ "
                f"{format_minutes(available_minutes)}"
                "だけ始める"
            ),
            key=(
                "start_focus_"
                f"{task_id}"
            ),
            use_container_width=True,
            type="primary",
        ):
            start_focus_session(
                task_id,
                title,
                available_minutes,
            )

            st.rerun()

        # -------------------------
        # 進捗更新
        # -------------------------

        render_progress_popover(
            task_id,
            title,
            progress,
            key_prefix="best",
        )

        # -------------------------
        # 詳細は閉じる
        # -------------------------

        with st.expander(
            "💡 なぜこの課題がおすすめ？"
        ):
            for reason in (
                best[
                    "reasons"
                ]
            ):
                st.write(
                    f"・{reason}"
                )

            st.divider()

            st.caption(
                "おすすめ度"
            )

            st.markdown(
                f"### {best['score']} / 100"
            )

            score_details = (
                best[
                    "score_details"
                ]
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

    st.markdown(
        "### 次にやるなら"
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

        metrics = (
            recommendation[
                "metrics"
            ]
        )

        remaining_minutes = (
            metrics[
                "task_remaining_minutes"
            ]
        )

        deadline_text = (
            format_deadline_friendly(
                deadline
            )
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
                f"#### {medal} {title}"
            )

            st.caption(
                f"📅 {deadline_text}"
                "　・　"
                "⏱️ "
                f"{format_minutes(remaining_minutes)}"
                "　・　"
                f"📈 {progress}%"
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
                "おすすめ理由"
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
    # 振り返り画面
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
    # 集中モード
    # =====================================

    if st.session_state.get(
        "focus_mode",
        False,
    ):
        render_focus_mode()
        return

    # =====================================
    # 通常画面
    # =====================================

    st.subheader(
        "☕ 今日"
    )

    st.caption(
        "今使える時間を選ぶだけで、"
        "最初にやる課題を決めます。"
    )

    # =====================================
    # 今使える時間
    # =====================================

    with st.container(
        border=True
    ):
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

    # =====================================
    # 今日の集中実績
    # =====================================

    focus_summary = (
        get_today_focus_summary()
    )

    total_minutes = (
        focus_summary[
            "total_minutes"
        ]
    )

    session_count = (
        focus_summary[
            "session_count"
        ]
    )

    st.caption(
        "☕ 今日の集中　"
        f"**{format_minutes(total_minutes)}**"
        "　・　"
        f"**{session_count}回**"
    )

    # =====================================
    # 課題なし
    # =====================================

    if not tasks:
        st.info(
            "課題を登録すると、"
            "ここにおすすめが表示されます。"
        )
        return

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

    if not recommendations:
        st.info(
            "おすすめできる課題がありません。"
        )
        return

    top_recommendations = (
        recommendations[:3]
    )

    render_best_task(
        top_recommendations[0],
        available_minutes,
    )

    render_other_recommendations(
        top_recommendations
    )
    
        # =====================================
    # 課題がない場合
    # =====================================

    if not tasks:

        st.subheader(
            "☕ 今日"
        )

        st.caption(
            "空き時間と締切から、"
            "今取り組む課題を決めます。"
        )

        st.write("")

        with st.container(
            border=True
        ):
            st.markdown(
                "### 🌱 まずは課題を登録してみましょう"
            )

            st.write(
                "課題を登録すると、"
                "締切・残り作業時間・空き時間をもとに"
                "「今やる課題」をおすすめします。"
            )

            st.markdown(
                """
**1.** 「＋ 課題を追加」から課題を登録  
**2.** サイドバーで普段の空き時間を設定  
**3.** 「☕ 今日」で今使える時間を選択
                """
            )

            st.info(
                "登録が終わったら、"
                "この画面におすすめ課題が表示されます ☕"
            )

        return