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
    with st.popover(
        "📈 進捗を更新",
        use_container_width=True,
    ):
        st.caption(
            f"現在の進捗：{progress}%"
        )

        options = (
            get_forward_progress_options(
                progress
            )
        )

        selected = (
            st.segmented_control(
                "どこまで進みましたか？",
                options=list(
                    options.keys()
                ),
                selection_mode="single",
                key=(
                    f"{key_prefix}_progress_"
                    f"{task_id}"
                ),
            )
        )

        if (
            selected is not None
            and selected != "変わらない"
        ):
            new_progress = (
                options[
                    selected
                ]
            )

            if st.button(
                "進捗を保存",
                key=(
                    f"{key_prefix}_save_"
                    f"{task_id}"
                ),
                use_container_width=True,
                type="primary",
            ):
                update_progress(
                    task_id,
                    new_progress,
                )

                st.session_state[
                    "message"
                ] = (
                    f"「{title}」の進捗を"
                    f"{new_progress}%に更新しました。"
                )

                st.rerun()

        st.divider()

        if st.button(
            "✓ 完了した",
            key=(
                f"{key_prefix}_finish_"
                f"{task_id}"
            ),
            use_container_width=True,
        ):
            complete_task(
                task_id
            )

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
# =====================================
# 締切を分かりやすく表示
# =====================================

def format_deadline_friendly(
    deadline,
):
    deadline_dt = (
        datetime.fromisoformat(
            deadline
        )
    )

    now = datetime.now()

    if deadline_dt <= now:
        return (
            "🚨 締切超過"
        )

    day_difference = (
        deadline_dt.date()
        - now.date()
    ).days

    time_text = (
        deadline_dt.strftime(
            "%H:%M"
        )
    )

    if day_difference == 0:
        return (
            f"今日 {time_text}"
        )

    if day_difference == 1:
        return (
            f"明日 {time_text}"
        )

    if day_difference <= 6:
        return (
            f"あと{day_difference}日"
            f"・{deadline_dt.strftime('%m/%d')}"
        )

    return (
        deadline_dt.strftime(
            "%m/%d %H:%M"
        )
    )


# =====================================
# 現在より先の進捗だけ表示
# =====================================

def get_forward_progress_options(
    current_progress,
):
    options = {
        "変わらない": current_progress,
    }

    for progress in range(
        10,
        100,
        10,
    ):
        if progress > current_progress:
            options[
                f"{progress}%"
            ] = progress

    return options