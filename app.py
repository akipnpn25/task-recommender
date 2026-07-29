import streamlit as st

from db import (
    init_db,
    get_tasks,
    get_weekly_settings,
    get_date_overrides,
)

from sidebar import render_sidebar

from views.today import render_today
from views.tasks import render_tasks
from views.add_task import render_add_task


# =====================================
# ページ設定
# =====================================

st.set_page_config(
    page_title="今やる課題推薦",
    page_icon="☕",
)


# =====================================
# 背景
# =====================================

st.markdown(
    """
    <style>
    .stApp {
        background:
            linear-gradient(
                180deg,
                #FBF9F5 0%,
                #F4EEE6 100%
            );
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================
# 初期化
# =====================================

init_db()


# =====================================
# タイトル
# =====================================

st.title(
    "☕ 今やる課題推薦"
)

st.caption(
    "今日やることを、迷わず決める。"
)

st.write(
    "締切・残り作業量・空き時間から、"
    "今取り組む課題をおすすめします。"
)


# =====================================
# メッセージ
# =====================================

if "message" in st.session_state:
    st.success(
        st.session_state.pop(
            "message"
        )
    )


# =====================================
# 完了のお祝い
# =====================================

if "celebrate_task" in st.session_state:
    completed_title = (
        st.session_state.pop(
            "celebrate_task"
        )
    )

    st.balloons()

    st.toast(
        f"「{completed_title}」完了！"
        " ひとつ片づいたね ☕",
        icon="🎉",
        duration="long",
    )


# =====================================
# データ
# =====================================

tasks = get_tasks()

saved_weekly_settings = (
    get_weekly_settings()
)

date_overrides = (
    get_date_overrides()
)


# =====================================
# サイドバー
# =====================================

weekly_available_minutes = (
    render_sidebar(
        saved_weekly_settings,
        date_overrides,
    )
)


# =====================================
# ナビゲーション
# =====================================

page = st.segmented_control(
    "ページ",
    options=[
        "☕ 今日",
        "📚 課題一覧",
        "＋ 課題を追加",
    ],
    default="☕ 今日",
    selection_mode="single",
    label_visibility="collapsed",
)


# =====================================
# ページ表示
# =====================================

if page == "☕ 今日":
    render_today(
        tasks,
        weekly_available_minutes,
        date_overrides,
    )


elif page == "📚 課題一覧":
    render_tasks(
        tasks
    )


elif page == "＋ 課題を追加":
    render_add_task()