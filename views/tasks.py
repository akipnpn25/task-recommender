import streamlit as st
from datetime import datetime, time

from components import (
    format_minutes,
    TASK_TIME_OPTIONS,
)

from db import (
    get_completed_tasks,
    update_task,
    complete_task,
    restore_task,
    delete_task,
)


def render_tasks(tasks):
    st.subheader(
        f"未完了の課題"
        f"（{len(tasks)}件）"
    )

    # =====================================
    # 未完了
    # =====================================

    if not tasks:
        st.info(
            "未完了の課題はありません。"
        )

    else:
        for task in tasks:
            (
                task_id,
                title,
                deadline,
                estimated_minutes,
                progress,
            ) = task

            deadline_dt = (
                datetime.fromisoformat(
                    deadline
                )
            )

            remaining_minutes = round(
                estimated_minutes
                * (
                    100
                    - progress
                )
                / 100
            )

            with st.container(
                border=True
            ):
                st.markdown(
                    f"### {title}"
                )

                col1, col2 = (
                    st.columns(2)
                )

                with col1:
                    st.write(
                        "📅 "
                        f"{deadline_dt.strftime('%m/%d %H:%M')}"
                        "まで"
                    )

                with col2:
                    st.write(
                        "⏱️ 残り約"
                        f"{format_minutes(remaining_minutes)}"
                    )

                st.write(
                    f"進捗：{progress}%"
                )

                st.progress(
                    progress / 100
                )

                # =====================================
                # 完了
                # =====================================

                if st.button(
                    "✓ 終わった！",
                    key=(
                        f"complete_"
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
                # 編集
                # =====================================

                with st.expander(
                    "✏️ 編集"
                ):
                    edited_title = (
                        st.text_input(
                            "課題名",
                            value=title,
                            key=(
                                f"title_"
                                f"{task_id}"
                            ),
                        )
                    )

                    # -------------------------
                    # 締切日
                    # -------------------------

                    edited_date = (
                        st.date_input(
                            "締切日",
                            value=(
                                deadline_dt.date()
                            ),
                            key=(
                                f"date_"
                                f"{task_id}"
                            ),
                        )
                    )

                    # -------------------------
                    # 締切時刻
                    # -------------------------

                    current_time = (
                        deadline_dt.time().replace(
                            second=0,
                            microsecond=0,
                        )
                    )

                    has_custom_time = (
                        current_time
                        != time(
                            23,
                            59,
                        )
                    )

                    specify_edit_time = (
                        st.checkbox(
                            "⏰ 締切時刻を指定する",
                            value=(
                                has_custom_time
                            ),
                            key=(
                                "specify_time_"
                                f"{task_id}"
                            ),
                        )
                    )

                    if specify_edit_time:
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
                                    index=(
                                        current_time.hour
                                    ),
                                    key=(
                                        "deadline_hour_"
                                        f"{task_id}"
                                    ),
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

                            if (
                                current_time.minute
                                not in minute_options
                            ):
                                minute_options.append(
                                    current_time.minute
                                )

                                minute_options.sort()

                            minute_index = (
                                minute_options.index(
                                    current_time.minute
                                )
                            )

                            deadline_minute = (
                                st.selectbox(
                                    "分",
                                    options=(
                                        minute_options
                                    ),
                                    index=(
                                        minute_index
                                    ),
                                    key=(
                                        "deadline_minute_"
                                        f"{task_id}"
                                    ),
                                    format_func=(
                                        lambda x:
                                        f"{x:02d}分"
                                    ),
                                )
                            )

                        edited_deadline_time = (
                            time(
                                deadline_hour,
                                deadline_minute,
                            )
                        )

                    else:
                        edited_deadline_time = (
                            time(
                                23,
                                59,
                            )
                        )

                    # =====================================
                    # 予想所要時間
                    # =====================================

                    matching_label = (
                        "その他"
                    )

                    for (
                        label,
                        minutes,
                    ) in (
                        TASK_TIME_OPTIONS.items()
                    ):
                        if (
                            minutes
                            == estimated_minutes
                        ):
                            matching_label = (
                                label
                            )
                            break

                    option_labels = list(
                        TASK_TIME_OPTIONS.keys()
                    )

                    default_time_index = (
                        option_labels.index(
                            matching_label
                        )
                    )

                    edited_time_label = (
                        st.selectbox(
                            "だいたいどれくらい"
                            "かかりそう？",
                            option_labels,
                            index=(
                                default_time_index
                            ),
                            key=(
                                f"time_"
                                f"{task_id}"
                            ),
                        )
                    )

                    # -------------------------
                    # その他
                    # -------------------------

                    if (
                        edited_time_label
                        == "その他"
                    ):
                        st.write(
                            "予想所要時間"
                        )

                        (
                            duration_hour_col,
                            duration_minute_col,
                        ) = st.columns(2)

                        default_hours = (
                            estimated_minutes
                            // 60
                        )

                        default_minutes = (
                            estimated_minutes
                            % 60
                        )

                        hour_options = list(
                            range(
                                0,
                                max(
                                    25,
                                    default_hours + 1,
                                ),
                            )
                        )

                        with duration_hour_col:
                            edited_hours = (
                                st.selectbox(
                                    "時間",
                                    options=(
                                        hour_options
                                    ),
                                    index=(
                                        hour_options.index(
                                            default_hours
                                        )
                                    ),
                                    key=(
                                        "duration_hour_"
                                        f"{task_id}"
                                    ),
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

                            if (
                                default_minutes
                                not in
                                duration_minute_options
                            ):
                                duration_minute_options.append(
                                    default_minutes
                                )

                                duration_minute_options.sort()

                            minute_index = (
                                duration_minute_options.index(
                                    default_minutes
                                )
                            )

                            edited_minutes = (
                                st.selectbox(
                                    "分",
                                    options=(
                                        duration_minute_options
                                    ),
                                    index=minute_index,
                                    key=(
                                        "duration_minute_"
                                        f"{task_id}"
                                    ),
                                    format_func=(
                                        lambda x:
                                        f"{x}分"
                                    ),
                                )
                            )

                        edited_estimated_minutes = (
                            edited_hours * 60
                            + edited_minutes
                        )

                    else:
                        edited_estimated_minutes = (
                            TASK_TIME_OPTIONS[
                                edited_time_label
                            ]
                        )

                    # =====================================
                    # 保存
                    # =====================================

                    if st.button(
                        "変更を保存",
                        key=(
                            f"save_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):
                        if (
                            not edited_title.strip()
                        ):
                            st.error(
                                "課題名を入力してください。"
                            )

                        elif (
                            edited_estimated_minutes
                            <= 0
                        ):
                            st.error(
                                "予想所要時間を"
                                "設定してください。"
                            )

                        else:
                            new_deadline = (
                                datetime.combine(
                                    edited_date,
                                    edited_deadline_time,
                                )
                            )

                            update_task(
                                task_id=task_id,
                                title=(
                                    edited_title.strip()
                                ),
                                deadline=(
                                    new_deadline.isoformat()
                                ),
                                estimated_minutes=(
                                    edited_estimated_minutes
                                ),
                            )

                            st.session_state[
                                "message"
                            ] = (
                                "課題を更新しました。"
                            )

                            st.rerun()

                    # =====================================
                    # 削除
                    # =====================================

                    if st.button(
                        "🗑 削除",
                        key=(
                            f"delete_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):
                        delete_task(
                            task_id
                        )

                        st.session_state[
                            "message"
                        ] = (
                            f"「{title}」を"
                            "削除しました。"
                        )

                        st.rerun()

    # =====================================
    # 完了済み
    # =====================================

    completed_tasks = (
        get_completed_tasks()
    )

    if completed_tasks:
        st.divider()

        with st.expander(
            "✅ 完了済み"
            f"（{len(completed_tasks)}件）"
        ):
            for task in (
                completed_tasks
            ):
                (
                    task_id,
                    title,
                    deadline,
                    estimated_minutes,
                    progress,
                ) = task

                st.write(
                    f"**{title}**"
                )

                col1, col2 = (
                    st.columns(2)
                )

                with col1:
                    if st.button(
                        "↩️ 元に戻す",
                        key=(
                            f"restore_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):
                        restore_task(
                            task_id
                        )

                        st.rerun()

                with col2:
                    if st.button(
                        "🗑 削除",
                        key=(
                            "delete_completed_"
                            f"{task_id}"
                        ),
                        use_container_width=True,
                    ):
                        delete_task(
                            task_id
                        )

                        st.rerun()