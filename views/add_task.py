import streamlit as st
from datetime import datetime, time, timedelta

from db import add_task

from components import (
    TASK_TIME_OPTIONS,
)


def render_add_task():
    st.subheader(
        "新しい課題を追加"
    )

    st.caption(
        "必要最低限の項目だけで登録できます。"
    )

    # =====================================
    # 1. 課題名
    # =====================================

    new_title = (
        st.text_input(
            "課題名",
            placeholder=(
                "例：推薦システム最終課題"
            ),
            key="new_task_title",
        )
    )

    # =====================================
    # 2. 締切日
    # =====================================

    new_deadline_date = (
        st.date_input(
            "締切日",
            value=(
                datetime.now().date()
                + timedelta(days=1)
            ),
            key="new_deadline_date",
        )
    )

    # =====================================
    # 3. 締切時刻
    # =====================================

    specify_deadline_time = (
        st.checkbox(
            "⏰ 締切時刻を指定する",
            key="specify_deadline_time",
        )
    )

    if specify_deadline_time:
        st.write(
            "締切時刻"
        )

        (
            hour_col,
            minute_col,
        ) = st.columns(2)

        with hour_col:
            deadline_hour = (
                st.selectbox(
                    "時",
                    options=list(
                        range(24)
                    ),
                    index=23,
                    key="new_deadline_hour",
                    format_func=(
                        lambda x:
                        f"{x:02d}時"
                    ),
                )
            )

        with minute_col:
            minute_options = [
                0,
                5,
                10,
                15,
                20,
                25,
                30,
                35,
                40,
                45,
                50,
                55,
                59,
            ]

            deadline_minute = (
                st.selectbox(
                    "分",
                    options=(
                        minute_options
                    ),
                    index=12,
                    key="new_deadline_minute",
                    format_func=(
                        lambda x:
                        f"{x:02d}分"
                    ),
                )
            )

        new_deadline_time = (
            time(
                deadline_hour,
                deadline_minute,
            )
        )

    else:
        new_deadline_time = (
            time(
                23,
                59,
            )
        )

    # =====================================
    # 4. 予想所要時間
    # =====================================

    new_estimated_label = (
        st.selectbox(
            "だいたいどれくらい"
            "かかりそう？",
            list(
                TASK_TIME_OPTIONS.keys()
            ),
            index=3,
            key="new_estimated_time",
        )
    )

    if (
        new_estimated_label
        == "その他"
    ):
        st.write(
            "予想所要時間"
        )

        (
            duration_hour_col,
            duration_minute_col,
        ) = st.columns(2)

        with duration_hour_col:
            custom_hours = (
                st.selectbox(
                    "時間",
                    options=list(
                        range(0, 25)
                    ),
                    index=6,
                    key="new_custom_hours",
                    format_func=(
                        lambda x:
                        f"{x}時間"
                    ),
                )
            )

        with duration_minute_col:
            duration_minute_options = [
                0,
                15,
                30,
                45,
            ]

            custom_minutes = (
                st.selectbox(
                    "分",
                    options=(
                        duration_minute_options
                    ),
                    index=0,
                    key="new_custom_minutes",
                    format_func=(
                        lambda x:
                        f"{x}分"
                    ),
                )
            )

        new_estimated_minutes = (
            custom_hours * 60
            + custom_minutes
        )

    else:
        new_estimated_minutes = (
            TASK_TIME_OPTIONS[
                new_estimated_label
            ]
        )

    # =====================================
    # 5. 追加
    # =====================================

    if st.button(
        "課題を追加する",
        use_container_width=True,
        key="add_task_button",
    ):
        if not new_title.strip():
            st.error(
                "課題名を入力してください。"
            )

        elif new_estimated_minutes <= 0:
            st.error(
                "予想所要時間を設定してください。"
            )

        else:
            deadline = (
                datetime.combine(
                    new_deadline_date,
                    new_deadline_time,
                )
            )

            add_task(
                new_title.strip(),
                deadline.isoformat(),
                new_estimated_minutes,
            )

            st.session_state[
                "message"
            ] = (
                f"「{new_title}」を"
                "追加しました！"
            )

            st.rerun()