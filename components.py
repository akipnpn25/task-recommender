import streamlit as st
from datetime import datetime

from db import (
    update_progress,
    complete_task,
)


# =====================================
# 課題時間の選択肢
# =====================================

TASK_TIME_OPTIONS = {
    "15分": 15,
    "30分": 30,
    "45分": 45,
    "1時間": 60,
    "1時間30分": 90,
    "2時間": 120,
    "3時間": 180,
    "4時間": 240,
    "5時間": 300,
    "6時間": 360,
    "その他": None,
}


# =====================================
# 時間表示
# =====================================

def format_minutes(minutes):
    """分を「○時間○分」に変換する"""

    minutes = max(0, round(minutes))
    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours == 0:
        return f"{remaining_minutes}分"

    if remaining_minutes == 0:
        return f"{hours}時間"

    return f"{hours}時間{remaining_minutes}分"


# =====================================
# おすすめ状態
# =====================================

def get_recommendation_status(recommendation):
    """推薦結果を分かりやすい状態に変換する"""

    metrics = recommendation["metrics"]

    remaining_hours = metrics["remaining_hours"]
    slack_minutes = metrics["slack_minutes"]

    if remaining_hours <= 0:
        return (
            "🚨 締切超過",
            "締切を過ぎています。優先して取り組みましょう。",
        )

    schedule_summary = recommendation.get(
        "schedule_summary",
        {},
    )

    first_shortage = schedule_summary.get(
        "first_shortage"
    )

    if (
        first_shortage is not None
        and recommendation.get(
            "contributes_to_first_shortage",
            False,
        )
    ):
        shortage_dt = datetime.fromisoformat(
            first_shortage["deadline"]
        )

        shortage_minutes = abs(
            first_shortage["slack_minutes"]
        )

        return (
            "🔥 今から進めたい",
            (
                f"{shortage_dt.strftime('%m/%d')}の締切までに、"
                f"約{format_minutes(shortage_minutes)}"
                "不足する見込みです。"
            ),
        )

    if slack_minutes < 0:
        return (
            "🔥 今すぐやる",
            (
                "この締切までに約"
                f"{format_minutes(abs(slack_minutes))}"
                "不足する見込みです。"
            ),
        )

    if (
        slack_minutes <= 60
        or recommendation["score"] >= 75
    ):
        return (
            "⚠️ そろそろやる",
            "締切までの余裕が少なくなっています。",
        )

    return (
        "🌿 まだ余裕あり",
        "現時点では比較的余裕があります。",
    )


# =====================================
# 2位・3位の進捗更新
# =====================================

def render_progress_popover(
    task_id,
    title,
    progress,
    key_prefix,
):
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

    with st.popover(
        "📈 進捗を更新",
        use_container_width=True,
    ):
        selected_label = st.segmented_control(
            "どのくらい進みましたか？",
            options=list(
                progress_options.keys()
            ),
            selection_mode="single",
            key=(
                f"{key_prefix}_"
                f"progress_{task_id}"
            ),
        )

        if selected_label is not None:
            new_progress = progress_options[
                selected_label
            ]

            if new_progress != progress:
                update_progress(
                    task_id,
                    new_progress,
                )

                st.session_state["message"] = (
                    f"「{title}」の進捗を"
                    f"{selected_label}に更新しました。"
                )

                st.rerun()

        if st.button(
            "✓ 終わった！",
            key=f"{key_prefix}_finish_{task_id}",
            use_container_width=True,
        ):
            complete_task(task_id)

            st.session_state[
                "celebrate_task"
            ] = title

            st.rerun()
            
# =====================================
# 今使える時間
# =====================================

AVAILABLE_TIME_OPTIONS = {
    "15分": 15,
    "30分": 30,
    "45分": 45,
    "1時間": 60,
    "1時間30分": 90,
    "2時間": 120,
    "3時間": 180,
}


def render_available_time_selector(
    key,
):
    labels = list(
        AVAILABLE_TIME_OPTIONS.keys()
    )

    saved_label = st.session_state.get(
        "selected_available_label",
        "1時間",
    )

    if saved_label not in labels:
        saved_label = "1時間"

    selected_label = st.radio(
        "今使える時間",
        labels,
        index=labels.index(
            saved_label
        ),
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )

    st.session_state[
        "selected_available_label"
    ] = selected_label

    return AVAILABLE_TIME_OPTIONS[
        selected_label
    ]