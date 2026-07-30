import streamlit as st
from datetime import datetime, date, time, timedelta

from db import add_task


# =====================================
# 所要時間
# =====================================

TIME_OPTIONS = {
    "30分": 30,
    "1時間": 60,
    "1時間30分": 90,
    "2時間": 120,
    "3時間": 180,
    "4時間": 240,
    "その他": None,
}


# =====================================
# 課題追加画面
# =====================================

def render_add_task():
    st.subheader(
        "＋ 課題を追加"
    )

    st.caption(
        "まずは最低限だけ入力。"
        "細かい設定は必要なときだけ変更できます。"
    )

    # =====================================
    # 基本情報
    # =====================================

    with st.container(
        border=True
    ):
        st.markdown(
            (
                '<div class="section-kicker">'
                'NEW TASK'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            (
                '<div class="section-heading">'
                '課題について教えてください'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        # -------------------------
        # 課題名
        # -------------------------

        title = st.text_input(
            "課題名",
            placeholder=(
                "例：推薦システム最終課題"
            ),
            key="add_task_title",
        )

        # -------------------------
        # 締切
        # -------------------------

        st.write("")

        st.markdown(
            "**📅 締切**"
        )

        deadline_quick = (
            st.segmented_control(
                "締切の選択",
                options=[
                    "今日",
                    "明日",
                    "3日後",
                    "1週間後",
                    "日付を選ぶ",
                ],
                default="明日",
                selection_mode="single",
                key="add_deadline_quick",
                label_visibility="collapsed",
            )
        )

        today = date.today()

        if deadline_quick == "今日":
            deadline_date = today

        elif deadline_quick == "明日":
            deadline_date = (
                today
                + timedelta(
                    days=1
                )
            )

        elif deadline_quick == "3日後":
            deadline_date = (
                today
                + timedelta(
                    days=3
                )
            )

        elif deadline_quick == "1週間後":
            deadline_date = (
                today
                + timedelta(
                    days=7
                )
            )

        else:
            deadline_date = (
                st.date_input(
                    "締切日",
                    value=(
                        today
                        + timedelta(
                            days=1
                        )
                    ),
                    min_value=today,
                    key="add_deadline_date",
                )
            )

        st.caption(
            "締切日："
            f"{deadline_date.strftime('%m/%d')}"
        )
        
        # -------------------------
        # 締切時刻
        # -------------------------

        st.write("")

        st.markdown(
            "**🕒 締切時刻**"
        )

        time_setting = (
            st.segmented_control(
                "締切時刻",
                options=[
                    "指定しない",
                    "指定する",
                ],
                default="指定しない",
                selection_mode="single",
                key="add_time_setting",
                label_visibility="collapsed",
            )
        )

        if time_setting == "指定する":

            time_col1, time_col2 = (
                st.columns(2)
            )

            with time_col1:

                deadline_hour = (
                    st.selectbox(
                        "時",
                        options=list(
                            range(24)
                        ),
                        index=23,
                        key="add_deadline_hour",
                    )
                )

            with time_col2:

                deadline_minute = (
                    st.selectbox(
                        "分",
                        options=[
                            0,
                            15,
                            30,
                            45,
                            59,
                        ],
                        index=4,
                        key="add_deadline_minute",
                    )
                )

        else:

            deadline_hour = 23
            deadline_minute = 59

            st.caption(
                "指定しない場合は23:59になります。"
            )

        # -------------------------
        # 予想所要時間
        # -------------------------

        st.write("")

        st.markdown(
            "**⏱️ だいたい何時間かかりそう？**"
        )

        selected_time = (
            st.segmented_control(
                "予想所要時間",
                options=list(
                    TIME_OPTIONS.keys()
                ),
                default="1時間",
                selection_mode="single",
                key="add_estimated_time",
                label_visibility="collapsed",
            )
        )

        estimated_minutes = (
            TIME_OPTIONS[
                selected_time
            ]
        )

        # =====================================
        # その他の時間
        # =====================================

        if selected_time == "その他":
            custom_col1, custom_col2 = (
                st.columns(2)
            )

            with custom_col1:
                custom_hours = (
                    st.number_input(
                        "時間",
                        min_value=0,
                        max_value=24,
                        value=1,
                        step=1,
                        key="add_custom_hours",
                    )
                )

            with custom_col2:
                custom_minutes = (
                    st.selectbox(
                        "分",
                        options=[
                            0,
                            15,
                            30,
                            45,
                        ],
                        key="add_custom_minutes",
                    )
                )

            estimated_minutes = (
                custom_hours
                * 60
                + custom_minutes
            )

    # =====================================
    # 入力内容の確認
    # =====================================

    st.write("")

    deadline_dt = datetime.combine(
        deadline_date,
        time(
            deadline_hour,
            deadline_minute,
        ),
    )

    if estimated_minutes is None:
        estimated_minutes = 0

    summary_title = (
        title.strip()
        if title.strip()
        else "課題名未入力"
    )

    with st.container(
        border=True
    ):
        st.markdown(
            "**追加する内容**"
        )

        st.write(
            f"📝 {summary_title}"
        )

        st.caption(
            "📅 "
            f"{deadline_dt.strftime('%m/%d %H:%M')}"
            "　・　"
            "⏱️ "
            f"{format_estimated_time(estimated_minutes)}"
        )

        # =====================================
        # 追加
        # =====================================

        if st.button(
            "＋ この課題を追加",
            use_container_width=True,
            type="primary",
            key="add_task_submit",
        ):
            if not title.strip():
                st.error(
                    "課題名を入力してください。"
                )
                return

            if estimated_minutes <= 0:
                st.error(
                    "所要時間を1分以上にしてください。"
                )
                return

            if deadline_dt <= datetime.now():
                st.error(
                    "締切は現在より後の日時を"
                    "設定してください。"
                )
                return

            add_task(
                title.strip(),
                deadline_dt.isoformat(),
                estimated_minutes,
            )

            st.session_state[
                "message"
            ] = (
                f"「{title.strip()}」を追加しました ☕"
            )

            st.rerun()


# =====================================
# 時間表示
# =====================================

def format_estimated_time(
    minutes,
):
    if minutes <= 0:
        return "未設定"

    hours = (
        minutes
        // 60
    )

    remaining_minutes = (
        minutes
        % 60
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