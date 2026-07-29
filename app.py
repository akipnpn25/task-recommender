import streamlit as st

from datetime import datetime, time

from db import (
    init_db,
    add_task,
    get_tasks,
    delete_task,
)


st.set_page_config(
    page_title="今やる課題推薦",
    page_icon="📚",
)


# =========================
# 初期設定
# =========================

init_db()

st.title("📚 今やる課題推薦")

st.write(
    "課題を登録すると、今取り組むべき課題をおすすめします。"
)


# =========================
# 課題登録
# =========================

st.subheader("＋ 課題を追加")

time_options = {
    "15分": 15,
    "30分": 30,
    "1時間": 60,
    "2時間": 120,
    "3時間": 180,
    "4時間以上": 240,
}


with st.form(
    "task_form",
    clear_on_submit=True,
):

    title = st.text_input(
        "課題名",
        placeholder="例：推薦システム最終課題",
    )

    deadline_date = st.date_input(
        "締切日",
    )

    estimated_label = st.selectbox(
        "だいたい何分かかりそう？",
        list(time_options.keys()),
        index=2,
    )

    submitted = st.form_submit_button(
        "追加する",
        use_container_width=True,
    )


if submitted:

    if not title.strip():

        st.error(
            "課題名を入力してください。"
        )

    else:

        # 締切時刻は自動的に23:59
        deadline = datetime.combine(
            deadline_date,
            time(23, 59),
        )

        estimated_minutes = time_options[
            estimated_label
        ]

        add_task(
            title=title.strip(),
            deadline=deadline.isoformat(),
            estimated_minutes=estimated_minutes,
        )

        st.success(
            f"「{title}」を追加しました！"
        )


# =========================
# 課題一覧
# =========================

st.divider()

st.subheader("📋 課題一覧")

tasks = get_tasks()


if len(tasks) == 0:

    st.info(
        "まだ課題がありません。"
    )

else:

    for task in tasks:

        (
            task_id,
            title,
            deadline,
            estimated_minutes,
        ) = task

        deadline_dt = datetime.fromisoformat(
            deadline
        )

        with st.container(border=True):

            st.markdown(
                f"### {title}"
            )

            col1, col2 = st.columns(2)

            with col1:

                st.write(
                    f"📅 {deadline_dt.strftime('%m/%d')} まで"
                )

            with col2:

                if estimated_minutes < 60:

                    time_text = (
                        f"{estimated_minutes}分"
                    )

                else:

                    hours = (
                        estimated_minutes / 60
                    )

                    if hours.is_integer():
                        time_text = (
                            f"{int(hours)}時間"
                        )
                    else:
                        time_text = (
                            f"{hours:.1f}時間"
                        )

                st.write(
                    f"⏱️ 約{time_text}"
                )

            if st.button(
                "削除",
                key=f"delete_{task_id}",
            ):

                delete_task(task_id)

                st.rerun()