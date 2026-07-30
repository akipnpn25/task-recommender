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
from views.outlook import render_outlook


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
                #FAF7F2 0%,
                #F3ECE3 100%
            );
        color: #342F2B;
    }

    .block-container {
        max-width: 980px;
        padding-top: 2rem;
        padding-bottom: 5rem;
    }


    /* =====================================
       見出し
    ===================================== */

    h1, h2, h3 {
        color: #342F2B;
        letter-spacing: -0.02em;
    }

    .section-kicker {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.14em;
        color: #8B7563;
        margin-bottom: 4px;
    }

    .section-heading {
        font-size: 20px;
        font-weight: 700;
        color: #3E3732;
        margin-bottom: 6px;
    }

    .section-description {
        font-size: 13px;
        color: #7A7068;
        margin-bottom: 14px;
        line-height: 1.7;
    }


    /* =====================================
       border=True のカード
    ===================================== */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 253, 250, 0.97);
        border: 1px solid #DCCFC2 !important;
        border-radius: 20px !important;

        box-shadow:
            0 6px 20px
            rgba(67, 52, 40, 0.07);

        padding: 6px;
    }


    /* =====================================
       1位カード
    ===================================== */

    .today-pick-label {
        display: inline-block;

        background: #EAE2D8;
        color: #725D4D;

        border-radius: 999px;

        padding: 5px 11px;

        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.07em;

        margin-bottom: 7px;
    }

    .today-pick-title {
        font-size: 26px;
        font-weight: 750;
        color: #302B27;

        margin-top: 3px;
        margin-bottom: 5px;

        line-height: 1.45;
    }

    .today-pick-meta {
        color: #756A62;
        font-size: 14px;
        margin-bottom: 4px;
    }


    /* =====================================
       状態バッジ
    ===================================== */

    .status-pill {
        display: inline-block;

        border-radius: 999px;

        padding: 7px 13px;

        font-size: 13px;
        font-weight: 700;

        margin-top: 10px;
        margin-bottom: 6px;
    }

    .status-safe {
        background: #E5EEE1;
        color: #506047;
    }

    .status-warning {
        background: #F4E7C8;
        color: #755F35;
    }

    .status-urgent {
        background: #F1DDD2;
        color: #7D4E3D;
    }

    .status-danger {
        background: #EBCFCB;
        color: #873C36;
    }


    /* =====================================
       Metric
    ===================================== */

    div[data-testid="stMetric"] {
        background: #F8F4EF;

        border: 1px solid #E3D8CC;

        border-radius: 15px;

        padding: 14px 15px;

        min-height: 100px;
    }

    div[data-testid="stMetricLabel"] {
        color: #766B62;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #352F2B;
        font-weight: 750;
    }


    /* =====================================
       おすすめ理由
    ===================================== */

    .reason-box {
        background: #EEF2E9;

        border: 1px solid #CDD6C5;
        border-left: 5px solid #7F9073;

        border-radius: 16px;

        padding: 17px 19px;

        margin-top: 14px;
        margin-bottom: 14px;
    }

    .reason-title {
        color: #495440;
        font-size: 15px;
        font-weight: 750;
        margin-bottom: 8px;
    }

    .reason-item {
        color: #45423D;
        font-size: 14px;
        line-height: 1.7;
        margin-top: 5px;
    }


    /* =====================================
       今週の見通し
    ===================================== */

    .week-outlook-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;

        margin-top: 12px;
        margin-bottom: 12px;
    }

    .outlook-card {
        border-radius: 14px;

        padding: 11px 5px;

        text-align: center;

        border: 1px solid
            rgba(90, 70, 55, 0.10);
    }

    .outlook-safe {
        background: #E7EFE3;
    }

    .outlook-warning {
        background: #F3E4BF;
    }

    .outlook-shortage {
        background: #EED3CE;
    }

    .outlook-date {
        font-size: 12px;
        font-weight: 650;
        color: #5D544D;
    }

    .outlook-weekday {
        font-size: 11px;
        color: #897C72;
        margin-top: 2px;
    }

    .outlook-symbol {
        font-size: 26px;
        font-weight: 750;
        color: #38322E;
        line-height: 1.3;
        margin-top: 3px;
    }

    .outlook-label {
        font-size: 10px;
        color: #615952;
    }


    /* =====================================
       Expander
    ===================================== */

    div[data-testid="stExpander"] {
        background: #FBF8F4;

        border: 1px solid #DED2C7;

        border-radius: 15px;
    }


    /* =====================================
       ボタン
    ===================================== */

    .stButton > button {
        background: #FFFDF9;

        color: #493E36;

        border: 1px solid #CBB7A5;

        border-radius: 14px;

        min-height: 43px;

        font-weight: 600;

        transition: 0.15s ease;
    }

    .stButton > button:hover {
        background: #EDE3D8;

        color: #332B26;

        border-color: #9A7B64;

        transform: translateY(-1px);
    }


    /* =====================================
       スマホ
    ===================================== */

    @media (max-width: 700px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .week-outlook-grid {
            grid-template-columns:
                repeat(4, 1fr);
        }

        .today-pick-title {
            font-size: 22px;
        }
    }
    /* =====================================
   1位の締切・残り時間カード
===================================== */

.task-info-card {
    background: #FFFDF9;
    border: 1px solid #D8C8B8;
    border-radius: 16px;
    padding: 18px 20px;
    min-height: 125px;

    box-shadow:
        0 3px 10px
        rgba(67, 52, 40, 0.05);
}

.task-info-label {
    font-size: 14px;
    font-weight: 700;
    color: #76675C;
    margin-bottom: 12px;
}

.task-info-value {
    font-size: 25px;
    font-weight: 700;
    color: #352F2B;
    line-height: 1.3;
}

.task-info-sub {
    font-size: 13px;
    color: #91857B;
    margin-top: 10px;
}
/* =====================================
   集中モード
===================================== */

.focus-screen {
    max-width: 650px;

    margin:
        50px auto 25px auto;

    padding:
        55px 35px;

    text-align: center;

    background:
        linear-gradient(
            145deg,
            #FFFDF9 0%,
            #EEE5DA 100%
        );

    border:
        1px solid #D3C1B0;

    border-radius:
        28px;

    box-shadow:
        0 12px 35px
        rgba(
            67,
            52,
            40,
            0.10
        );
}


.focus-screen-label {
    display: inline-block;

    padding:
        6px 13px;

    background:
        #E5D8CB;

    border-radius:
        999px;

    color:
        #755F4F;

    font-size:
        12px;

    font-weight:
        700;

    letter-spacing:
        0.13em;

    margin-bottom:
        24px;
}


.focus-screen-title {
    font-size:
        30px;

    font-weight:
        750;

    color:
        #342E2A;

    margin-bottom:
        25px;
}


.focus-screen-time {
    font-size:
        34px;

    font-weight:
        700;

    color:
        #493D35;

    margin-bottom:
        8px;
}


.focus-screen-duration {
    font-size:
        15px;

    font-weight:
        600;

    color:
        #826E5F;

    margin-bottom:
        30px;
}


.focus-screen-message {
    font-size:
        15px;

    color:
        #766B63;
}
/* =====================================
   集中モード カウントダウン
===================================== */

.focus-countdown {
    font-size: 64px;
    font-weight: 750;

    letter-spacing: 0.05em;

    color: #3F352E;

    line-height: 1.2;

    margin-top: 12px;
    margin-bottom: 14px;
}

.focus-finished {
    font-size: 34px;
    font-weight: 750;

    color: #56634E;

    margin-top: 18px;
    margin-bottom: 14px;
}

@media (max-width: 700px) {

    .focus-countdown {
        font-size: 48px;
    }

    .focus-finished {
        font-size: 28px;
    }
}
/* =====================================
   集中終了後
===================================== */

.focus-result-card {
    max-width: 650px;

    margin:
        35px auto 25px auto;

    padding:
        42px 35px;

    text-align: center;

    background:
        linear-gradient(
            145deg,
            #FFFDF9 0%,
            #EDF1E8 100%
        );

    border:
        1px solid #CCD4C4;

    border-radius:
        26px;

    box-shadow:
        0 10px 30px
        rgba(67, 52, 40, 0.08);
}

.focus-result-icon {
    font-size: 42px;

    margin-bottom: 8px;
}

.focus-result-title {
    font-size: 28px;

    font-weight: 750;

    color: #384033;

    margin-bottom: 10px;
}

.focus-result-task {
    font-size: 19px;

    font-weight: 700;

    color: #463D36;

    margin-bottom: 18px;
}

.focus-result-message {
    font-size: 14px;

    color: #756C65;

    line-height: 1.8;
}
/* =====================================
   スマホ表示
===================================== */

@media (max-width: 700px) {

    /* ページ全体の余白を小さくする */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1.5rem !important;
    }

    /* タイトルを少し小さく */
    h1 {
        font-size: 1.8rem !important;
    }

    h2 {
        font-size: 1.5rem !important;
    }

    h3 {
        font-size: 1.2rem !important;
    }

    /* TODAY'S PICK */
    .today-pick-title {
        font-size: 1.35rem !important;
        line-height: 1.5 !important;
    }

    /* カード内の文字 */
    .task-info-value {
        font-size: 1rem !important;
    }

    /* 集中モード */
    .focus-countdown {
        font-size: 3.2rem !important;
    }

    /* 理由欄 */
    .reason-box {
        padding: 0.9rem !important;
    }
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
# 集中中・振り返り中
# =====================================

is_focus_mode = st.session_state.get(
    "focus_mode",
    False,
)

is_focus_result_mode = st.session_state.get(
    "focus_result_mode",
    False,
)


if (
    is_focus_mode
    or is_focus_result_mode
):
    
    if (
    is_focus_mode
    or is_focus_result_mode
):
        st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }

        [data-testid="stSidebarCollapsedControl"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_today(
        tasks,
        weekly_available_minutes,
        date_overrides,
    )


else:

    # =====================================
    # 通常ナビゲーション
    # =====================================

    page = st.segmented_control(
    "ページ",
    options=[
        "☕ 今日",
        "📅 見通し",
        "📚 課題",
        "＋ 追加",
    ],
    default="☕ 今日",
    selection_mode="single",
    label_visibility="collapsed",
)
    if page == "☕ 今日":
        render_today(
        tasks,
        weekly_available_minutes,
        date_overrides,
    )
    elif page == "📅 見通し":
        render_outlook(
        tasks,
        weekly_available_minutes,
        date_overrides,
    )
    elif page == "📚 課題":
        render_tasks(
        tasks
    )
    elif page == "＋ 追加":
        render_add_task()