import streamlit as st
from datetime import datetime, timedelta

from components import format_minutes

from db import (
    save_weekly_settings,
    save_date_override,
    delete_date_override,
)


def render_sidebar(
    saved_weekly_settings,
    date_overrides,
):
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

        # =====================================
        # 普段の空き時間
        # =====================================

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

                selected_minutes = st.selectbox(
                    weekday_name,
                    weekly_time_values,
                    index=default_index,
                    format_func=format_minutes,
                    key=(
                        f"weekday_"
                        f"{weekday_index}"
                    ),
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

        # =====================================
        # 今週だけ変更
        # =====================================

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

            override_date = st.date_input(
                "変更する日",
                value=tomorrow,
                min_value=tomorrow,
                max_value=(
                    datetime.now().date()
                    + timedelta(days=7)
                ),
                key="override_date",
            )

            override_minutes = st.selectbox(
                "その日に使える時間",
                weekly_time_values,
                index=3,
                format_func=format_minutes,
                key="override_minutes",
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

            # -------------------------
            # 変更済みの日
            # -------------------------

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
                    col1, col2 = st.columns(
                        [3, 1]
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

    return weekly_available_minutes