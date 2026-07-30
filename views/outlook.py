import streamlit as st
from datetime import datetime

from recommender import (
    get_weekly_outlook,
    calculate_remaining_minutes,
    recommend_tasks,
)
from components import (
    format_minutes,
    render_available_time_selector,
)

# =====================================
# 時間不足の原因となる課題
# =====================================

def render_shortage_tasks(
    tasks,
    first_shortage,
    available_minutes,
    weekly_available_minutes,
    date_overrides,
):
    if first_shortage is None:
        return

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

    # =====================================
    # 不足する日までに締切の課題
    # =====================================

    related_tasks = []

    for task in tasks:

        deadline = (
            datetime.fromisoformat(
                task[2]
            )
        )

        if (
            deadline.date()
            <= shortage_date
        ):
            related_tasks.append(
                task
            )

    related_tasks.sort(
        key=lambda task: task[2]
    )

    # =====================================
    # 表示
    # =====================================

    st.write("")

    with st.container(
        border=True
    ):
        st.markdown(
            (
                '<div class="section-kicker">'
                'BOTTLENECK'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                '⚠️ 時間不足に関係する課題'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            f"{shortage_date.strftime('%m/%d')}"
            "までに締切を迎える課題を"
            "確認してみましょう。"
        )

        st.warning(
            "この時点では約"
            f"{format_minutes(shortage_minutes)}"
            "不足する見込みです。"
        )

        # =================================
        # 各課題
        # =================================

        for task in related_tasks:

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
                calculate_remaining_minutes(
                    task
                )
            )

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**{title}**"
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
                            remaining_minutes
                        )
                    )

                with col3:

                    st.caption(
                        "進捗"
                    )

                    st.write(
                        f"{progress}%"
                    )

        # =================================
        # 今やるべき課題
        # =================================

        recommendations = (
            recommend_tasks(
                tasks,
                available_minutes,
                weekly_available_minutes,
                date_overrides,
            )
        )

        if recommendations:

            best_title = (
                recommendations[0][
                    "task"
                ][1]
            )

            st.info(
                "💡 時間不足を防ぐためにも、"
                f"今は「{best_title}」から"
                "進めるのがおすすめです。"
            )


def render_outlook(
    tasks,
    weekly_available_minutes,
    date_overrides,
):
    st.subheader(
        "📅 課題の見通し"
    )

    st.caption(
        "今後の空き時間と課題量を比べて、"
        "このままで間に合うかを確認できます。"
    )

    # =====================================
    # 今日使える時間
    # =====================================

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
                '今日あとどれくらい使えますか？'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            "今日の残り時間も含めて、"
            "今後の見通しを計算します。"
        )

        available_minutes = (
            render_available_time_selector(
                key="outlook_available_time"
            )
        )

    if not tasks:
        st.info(
            "課題を登録すると、"
            "見通しが表示されます。"
        )
        return

    st.write("")

    # =====================================
    # 7日間の見通し
    # =====================================

    outlook_summary = (
        get_weekly_outlook(
            tasks,
            available_minutes,
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

    with st.container(
        border=True
    ):
        st.markdown(
            (
                '<div class="section-kicker">'
                'OUTLOOK'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                'これから7日間の課題全体'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            "○ 余裕あり　"
            "△ 少し注意　"
            "× 時間不足"
        )

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
                    '</div>'
                    '<div class="outlook-weekday">'
                    f'{weekday}'
                    '</div>'
                    '<div class="outlook-symbol">'
                    f'{symbol}'
                    '</div>'
                    '<div class="outlook-label">'
                    f'{label}'
                    '</div>'
                    '</div>'
                )
            )

        st.markdown(
            (
                '<div class="week-outlook-grid">'
                + "".join(
                    cards
                )
                + '</div>'
            ),
            unsafe_allow_html=True,
        )

        # =====================================
        # 7日後までの全体量
        # =====================================

        final_day = (
            outlook_days[-1]
        )

        available_total = (
            final_day[
                "available_minutes"
            ]
        )

        required_total = (
            final_day[
                "required_minutes"
            ]
        )

        slack_total = (
            final_day[
                "slack_minutes"
            ]
        )

        st.write("")

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:
            st.metric(
                "使える時間",
                format_minutes(
                    available_total
                ),
            )

        with col2:
            st.metric(
                "必要な時間",
                format_minutes(
                    required_total
                ),
            )

        with col3:
            if slack_total < 0:
                st.metric(
                    "不足",
                    format_minutes(
                        abs(
                            slack_total
                        )
                    ),
                )
            else:
                st.metric(
                    "余裕",
                    format_minutes(
                        slack_total
                    ),
                )

        st.caption(
            "必要な時間は、7日後までに"
            "締切を迎える課題の残り時間です。"
        )

        # =====================================
        # 最初に不足する日
        # =====================================

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
                "⚠️ "
                f"{shortage_date.strftime('%m/%d')}"
                "時点から、"
                f"約{format_minutes(shortage_minutes)}"
                "不足する見込みです。"
            )

        else:
            st.success(
                "🌿 これから7日間は、"
                "今の予定で間に合う見込みです。"
            )
            
    # =====================================
    # 時間不足の原因
    # =====================================

    render_shortage_tasks(
        tasks,
        first_shortage,
        available_minutes,
        weekly_available_minutes,
        date_overrides,
    )