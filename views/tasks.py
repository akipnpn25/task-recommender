import streamlit as st
from datetime import datetime

from db import (
    get_completed_tasks,
    update_task,
    complete_task,
    restore_task,
    delete_task,
    delete_all_completed_tasks,
)

from components import (
    format_minutes,
    format_deadline_friendly,
    render_progress_popover,
)


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
    "5時間": 300,
    "6時間": 360,
    "その他": None,
}


# =====================================
# 残り作業時間
# =====================================

def calculate_remaining_minutes(
    estimated_minutes,
    progress,
):
    return round(
        estimated_minutes
        * (
            (100 - progress)
            / 100
        )
    )


# =====================================
# 編集
# =====================================

def render_task_edit(
    task_id,
    title,
    deadline,
    estimated_minutes,
):
    deadline_dt = (
        datetime.fromisoformat(
            deadline
        )
    )

    with st.popover(
        "✏️ 編集",
        use_container_width=True,
    ):
        new_title = st.text_input(
            "課題名",
            value=title,
            key=f"edit_title_{task_id}",
        )

        new_date = st.date_input(
            "締切日",
            value=deadline_dt.date(),
            key=f"edit_date_{task_id}",
        )

        st.markdown(
            "**🕒 締切時刻**"
        )

        time_col1, time_col2 = (
            st.columns(2)
        )

        with time_col1:
            new_hour = st.selectbox(
                "時",
                options=list(
                    range(24)
                ),
                index=deadline_dt.hour,
                key=f"edit_hour_{task_id}",
            )

        minute_options = [
            0,
            15,
            30,
            45,
            59,
        ]

        if (
            deadline_dt.minute
            not in minute_options
        ):
            minute_options.append(
                deadline_dt.minute
            )

            minute_options.sort()

        with time_col2:
            new_minute = st.selectbox(
                "分",
                options=minute_options,
                index=minute_options.index(
                    deadline_dt.minute
                ),
                key=f"edit_minute_{task_id}",
            )

        st.write("")

        st.markdown(
            "**⏱️ 予想所要時間**"
        )

        current_label = "その他"

        for (
            label,
            minutes,
        ) in TIME_OPTIONS.items():
            if (
                minutes
                == estimated_minutes
            ):
                current_label = label
                break

        labels = list(
            TIME_OPTIONS.keys()
        )

        selected_time = (
            st.selectbox(
                "所要時間",
                options=labels,
                index=labels.index(
                    current_label
                ),
                key=f"edit_time_{task_id}",
                label_visibility="collapsed",
            )
        )

        new_estimated_minutes = (
            TIME_OPTIONS[
                selected_time
            ]
        )

        if selected_time == "その他":
            custom_col1, custom_col2 = (
                st.columns(2)
            )

            with custom_col1:
                hours = st.number_input(
                    "時間",
                    min_value=0,
                    max_value=24,
                    value=(
                        estimated_minutes
                        // 60
                    ),
                    step=1,
                    key=(
                        f"edit_custom_hour_"
                        f"{task_id}"
                    ),
                )

            with custom_col2:
                minutes = st.number_input(
                    "分",
                    min_value=0,
                    max_value=59,
                    value=(
                        estimated_minutes
                        % 60
                    ),
                    step=5,
                    key=(
                        f"edit_custom_minute_"
                        f"{task_id}"
                    ),
                )

            new_estimated_minutes = (
                hours * 60
                + minutes
            )

        st.write("")

        if st.button(
            "変更を保存",
            key=f"save_edit_{task_id}",
            use_container_width=True,
            type="primary",
        ):
            if not new_title.strip():
                st.error(
                    "課題名を入力してください。"
                )
                return

            if (
                new_estimated_minutes
                is None
                or new_estimated_minutes <= 0
            ):
                st.error(
                    "所要時間を1分以上にしてください。"
                )
                return

            new_deadline_dt = (
                datetime.combine(
                    new_date,
                    datetime.min.time(),
                ).replace(
                    hour=new_hour,
                    minute=new_minute,
                )
            )

            update_task(
                task_id,
                new_title.strip(),
                new_deadline_dt.isoformat(),
                new_estimated_minutes,
            )

            st.session_state[
                "message"
            ] = (
                f"「{new_title.strip()}」を"
                "更新しました。"
            )

            st.rerun()

        st.divider()

        if st.button(
            "🗑️ この課題を削除",
            key=f"delete_task_{task_id}",
            use_container_width=True,
        ):
            delete_task(
                task_id
            )

            st.session_state[
                "message"
            ] = (
                f"「{title}」を削除しました。"
            )

            st.rerun()


# =====================================
# 未完了
# =====================================

def render_active_tasks(
    tasks,
):
    if not tasks:
        st.success(
            "🎉 未完了の課題はありません。"
        )
        return

    for task in tasks:
        (
            task_id,
            title,
            deadline,
            estimated_minutes,
            progress,
        ) = task

        remaining_minutes = (
            calculate_remaining_minutes(
                estimated_minutes,
                progress,
            )
        )

        deadline_text = (
            format_deadline_friendly(
                deadline
            )
        )

        with st.container(
            border=True
        ):
            # -------------------------
            # タイトル
            # -------------------------

            st.markdown(
                f"### {title}"
            )

            st.caption(
                f"📅 {deadline_text}"
                "　・　"
                "⏱️ 残り "
                f"{format_minutes(remaining_minutes)}"
            )

            # -------------------------
            # 進捗
            # -------------------------

            st.progress(
                progress / 100
            )

            st.caption(
                f"進捗 {progress}%"
            )

            # -------------------------
            # 操作
            # -------------------------

            col1, col2, col3 = (
                st.columns(3)
            )

            with col1:
                render_progress_popover(
                    task_id,
                    title,
                    progress,
                    key_prefix="task_list",
                )

            with col2:
                if st.button(
                    "✓ 完了",
                    key=(
                        f"complete_task_"
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

            with col3:
                render_task_edit(
                    task_id,
                    title,
                    deadline,
                    estimated_minutes,
                )


# =====================================
# 完了済み
# =====================================
def render_completed_tasks(
    completed_tasks,
):
    if not completed_tasks:
        st.info(
            "完了した課題はまだありません。"
        )
        return

    # =====================================
    # 完了済み課題を整理
    # =====================================

    with st.expander(
        "🧹 完了済み課題を整理"
    ):
        st.caption(
            f"現在、完了済みの課題が"
            f"{len(completed_tasks)}件あります。"
        )

        st.write(
            "不要になった完了済み課題を"
            "まとめて削除できます。"
        )

        st.warning(
            "削除した課題は元に戻せません。"
        )

        confirm_delete = st.checkbox(
            "すべて削除しても大丈夫です",
            key="confirm_delete_all_completed",
        )

        if st.button(
            "🗑️ 完了済みをすべて削除",
            use_container_width=True,
            disabled=not confirm_delete,
            key="delete_all_completed_tasks_button",
        ):
            delete_all_completed_tasks()

            st.session_state[
                "message"
            ] = (
                "完了済みの課題を整理しました。"
            )

            st.rerun()

    st.write("")

    # =====================================
    # 完了済み課題一覧
    # =====================================

    for task in completed_tasks:
        (
            task_id,
            title,
            deadline,
            estimated_minutes,
            progress,
        ) = task

        with st.container(
            border=True
        ):
            st.markdown(
                f"### ✅ {title}"
            )

            st.caption(
                "📅 締切 "
                f"{format_deadline_friendly(deadline)}"
                "　・　"
                f"⏱️ {format_minutes(estimated_minutes)}"
            )

            col1, col2 = (
                st.columns(2)
            )

            with col1:
                if st.button(
                    "↩️ 未完了に戻す",
                    key=f"restore_task_{task_id}",
                    use_container_width=True,
                ):
                    restore_task(
                        task_id
                    )

                    st.session_state[
                        "message"
                    ] = (
                        f"「{title}」を"
                        "未完了に戻しました。"
                    )

                    st.rerun()

            with col2:
                if st.button(
                    "🗑️ 削除",
                    key=f"delete_completed_{task_id}",
                    use_container_width=True,
                ):
                    delete_task(
                        task_id
                    )

                    st.session_state[
                        "message"
                    ] = (
                        f"「{title}」を削除しました。"
                    )

                    st.rerun()

# =====================================
# 課題一覧
# =====================================

def render_tasks(
    tasks,
):
    st.subheader(
        "📚 課題一覧"
    )

    completed_tasks = (
        get_completed_tasks()
    )

    # =====================================
    # 概要
    # =====================================

    now = datetime.now()

    urgent_count = 0

    for task in tasks:
        deadline_dt = (
            datetime.fromisoformat(
                task[2]
            )
        )

        remaining_hours = (
            deadline_dt
            - now
        ).total_seconds() / 3600

        if (
            0
            <= remaining_hours
            <= 48
        ):
            urgent_count += 1

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:
        st.metric(
            "残り",
            f"{len(tasks)}件",
        )

    with col2:
        st.metric(
            "48時間以内",
            f"{urgent_count}件",
        )

    with col3:
        st.metric(
            "完了",
            f"{len(completed_tasks)}件",
        )

    st.write("")

    # =====================================
    # 未完了 / 完了
    # =====================================

    view = st.segmented_control(
        "表示",
        options=[
            "📝 未完了",
            "✅ 完了",
        ],
        default="📝 未完了",
        selection_mode="single",
        key="task_list_view",
        label_visibility="collapsed",
    )

    st.write("")

    if view == "📝 未完了":
        render_active_tasks(
            tasks
        )

    else:
        render_completed_tasks(
            completed_tasks
        )