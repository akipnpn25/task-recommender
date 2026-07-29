import streamlit as st
from datetime import datetime

from recommender import recommend_tasks

from db import (
    update_progress,
    complete_task,
)

from components import (
    format_minutes,
    get_recommendation_status,
    render_progress_popover,
)


def render_today(
    tasks,
    weekly_available_minutes,
    date_overrides,
):
    st.subheader(
        "今やるなら？"
    )

    # =====================================
    # 今使える時間
    # =====================================

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
        list(
            available_options.keys()
        ),
        index=3,
        horizontal=True,
        key="available_time",
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

    # =====================================
    # 推薦
    # =====================================

    recommendations = recommend_tasks(
        tasks,
        available_minutes,
        weekly_available_minutes,
        date_overrides,
    )

    top_recommendations = (
        recommendations[:3]
    )

    # =====================================
    # 全体の時間不足
    # =====================================

    schedule_summary = (
        recommendations[0][
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

        shortage_minutes = abs(
            first_shortage[
                "slack_minutes"
            ]
        )

        st.warning(
            "📉 現在の予定では、"
            f"{shortage_dt.strftime('%m/%d')}の"
            "締切時点で"
            f"約{format_minutes(shortage_minutes)}"
            "不足する見込みです。"
        )

    else:
        st.info(
            "🌿 現在登録されている予定では、"
            "締切までの作業時間を"
            "確保できる見込みです。"
        )

    # =====================================
    # 1位
    # =====================================

    best = (
        top_recommendations[0]
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

    (
        status_title,
        status_message,
    ) = get_recommendation_status(
        best
    )

    metrics = best[
        "metrics"
    ]

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

    # =====================================
    # 進捗
    # =====================================

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

    # =====================================
    # 締切までの見通し
    # =====================================

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
        "※必要時間は、この課題と"
        "それ以前が締切の課題の"
        "残り作業時間の合計です。"
    )

    # =====================================
    # おすすめ理由
    # =====================================

    st.write(
        "**おすすめ理由**"
    )

    for reason in best[
        "reasons"
    ]:
        st.write(
            f"・{reason}"
        )

    # =====================================
    # 推薦スコア
    # =====================================

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

    # =====================================
    # 1位の進捗更新
    # =====================================

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

    # =====================================
    # 1位を完了
    # =====================================

    if st.button(
        "✓ 終わった！",
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

    if len(
        top_recommendations
    ) >= 2:
        st.divider()

        st.subheader(
            "他のおすすめ"
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
                        f"{deadline_dt.strftime('%m/%d %H:%M')}"
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