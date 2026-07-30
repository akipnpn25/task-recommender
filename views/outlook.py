import streamlit as st
from datetime import datetime

from recommender import (
    get_weekly_outlook,
)

from components import (
    format_minutes,
    render_available_time_selector,
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