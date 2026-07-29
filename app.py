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
with st.container(
    border=True
):
    st.markdown(
    """
    <style>

    /* =====================================
       全体
    ===================================== */

    .stApp {
        background:
            linear-gradient(
                180deg,
                #FBF8F3 0%,
                #F4EEE5 100%
            );
    }

    /* 横幅を少し整える */
    .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }


    /* =====================================
       Streamlitのborder付きコンテナ
    ===================================== */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(
            255,
            253,
            249,
            0.92
        );

        border: 1px solid #D9C9B9 !important;

        border-radius: 18px !important;

        box-shadow:
            0 4px 14px
            rgba(
                83,
                64,
                48,
                0.07
            );

        padding: 4px;
    }


    /* =====================================
       Metric
    ===================================== */

    div[data-testid="stMetric"] {
        background: #FFFDF9;

        border: 1px solid #DDD0C3;

        border-radius: 14px;

        padding: 14px 16px;

        box-shadow:
            0 2px 8px
            rgba(
                83,
                64,
                48,
                0.05
            );
    }

    div[data-testid="stMetricLabel"] {
        color: #76685D;
        font-weight: 500;
    }

    div[data-testid="stMetricValue"] {
        color: #3F3833;
        font-weight: 700;
    }


    /* =====================================
       Expander
    ===================================== */

    div[data-testid="stExpander"] {
        background: #FFFDF9;

        border: 1px solid #D9C9B9;

        border-radius: 14px;
    }


    /* =====================================
       ボタン
    ===================================== */

    .stButton > button {
        background: #FFFDF9;

        border: 1px solid #CDB9A7;

        color: #453C35;

        border-radius: 14px;

        min-height: 42px;

        transition:
            all 0.15s ease;
    }

    .stButton > button:hover {
        background: #EEE4D9;

        border-color: #9D806A;

        color: #342D28;
    }


    /* =====================================
       進捗バー
    ===================================== */

    div[data-testid="stProgress"] > div > div {
        border-radius: 999px;
    }


    /* =====================================
       自作セクション
    ===================================== */

    .section-title {
        font-size: 18px;
        font-weight: 700;
        color: #453C35;
        margin-bottom: 8px;
    }

    .reason-box {
        background: #F0F3EB;

        border: 1px solid #C9D2BF;

        border-left:
            5px solid #829176;

        border-radius: 16px;

        padding: 18px 20px;

        margin-top: 10px;
        margin-bottom: 18px;
    }

    .reason-title {
        font-size: 16px;
        font-weight: 700;
        color: #48513F;
        margin-bottom: 12px;
    }

    .reason-item {
        color: #48433E;
        margin: 8px 0;
        line-height: 1.7;
    }

    .progress-box-title {
        font-size: 18px;
        font-weight: 700;
        color: #453C35;
        margin-bottom: 4px;
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