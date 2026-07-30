import streamlit as st

from datetime import (
    date,
    datetime,
    time,
    timedelta,
)

from db import add_tasks_bulk


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
# 時間表示
# =====================================

def format_estimated_time(
    minutes,
):
    if minutes <= 0:
        return "未設定"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours == 0:
        return f"{remaining_minutes}分"

    if remaining_minutes == 0:
        return f"{hours}時間"

    return (
        f"{hours}時間"
        f"{remaining_minutes}分"
    )


# =====================================
# 入力欄の管理
# =====================================

def initialize_task_cards(
    form_version,
):
    ids_key = (
        f"add_task_ids_{form_version}"
    )

    next_id_key = (
        f"add_task_next_id_{form_version}"
    )

    if ids_key not in st.session_state:
        st.session_state[
            ids_key
        ] = [0]

    if next_id_key not in st.session_state:
        st.session_state[
            next_id_key
        ] = 1

    return (
        ids_key,
        next_id_key,
    )


def render_task_input_card(
    form_version,
    task_id,
    display_index,
    can_remove,
):
    key_prefix = (
        f"task_form_"
        f"{form_version}_"
        f"{task_id}"
    )

    with st.container(
        border=True
    ):
        if display_index == 1:
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

        else:
            st.markdown(
                f"#### 課題 {display_index}"
            )

        # =====================================
        # 課題名
        # =====================================

        title = st.text_input(
            "課題名",
            placeholder=(
                "例：推薦システム最終課題"
            ),
            key=f"{key_prefix}_title",
        )

        # =====================================
        # 締切日
        # =====================================

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
                key=(
                    f"{key_prefix}_"
                    "deadline_quick"
                ),
                label_visibility="collapsed",
            )
        )

        today = date.today()

        if deadline_quick == "今日":
            deadline_date = today

        elif deadline_quick == "明日":
            deadline_date = (
                today
                + timedelta(days=1)
            )

        elif deadline_quick == "3日後":
            deadline_date = (
                today
                + timedelta(days=3)
            )

        elif deadline_quick == "1週間後":
            deadline_date = (
                today
                + timedelta(days=7)
            )

        else:
            deadline_date = st.date_input(
                "締切日",
                value=(
                    today
                    + timedelta(days=1)
                ),
                min_value=today,
                key=(
                    f"{key_prefix}_"
                    "deadline_date"
                ),
            )

        st.caption(
            "締切日："
            f"{deadline_date.strftime('%m/%d')}"
        )

        # =====================================
        # 締切時刻
        # =====================================

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
                key=(
                    f"{key_prefix}_"
                    "time_setting"
                ),
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
                        key=(
                            f"{key_prefix}_"
                            "deadline_hour"
                        ),
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
                        key=(
                            f"{key_prefix}_"
                            "deadline_minute"
                        ),
                    )
                )

        else:
            deadline_hour = 23
            deadline_minute = 59

            st.caption(
                "指定しない場合は"
                "23:59になります。"
            )

        # =====================================
        # 予想所要時間
        # =====================================

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
                key=(
                    f"{key_prefix}_"
                    "estimated_time"
                ),
                label_visibility="collapsed",
            )
        )

        estimated_minutes = (
            TIME_OPTIONS[
                selected_time
            ]
        )

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
                        key=(
                            f"{key_prefix}_"
                            "custom_hours"
                        ),
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
                        key=(
                            f"{key_prefix}_"
                            "custom_minutes"
                        ),
                    )
                )

            estimated_minutes = (
                custom_hours * 60
                + custom_minutes
            )

        if estimated_minutes is None:
            estimated_minutes = 0

        deadline_dt = datetime.combine(
            deadline_date,
            time(
                deadline_hour,
                deadline_minute,
            ),
        )

        # =====================================
        # 入力欄の削除
        # =====================================

        remove_clicked = False

        if can_remove:
            st.write("")

            remove_clicked = st.button(
                "この入力欄を削除",
                key=(
                    f"{key_prefix}_remove"
                ),
                use_container_width=True,
            )

    # このreturnはwithの外・関数の中に置く
    return {
        "task_id": task_id,
        "title": title.strip(),
        "deadline": deadline_dt.isoformat(),
        "deadline_dt": deadline_dt,
        "estimated_minutes": int(
            estimated_minutes
        ),
        "remove_clicked": remove_clicked,
    }



# =====================================
# 入力内容の確認
# =====================================

def validate_task(
    task_data,
    display_index,
):
    errors = []

    if (
        task_data[
            "estimated_minutes"
        ]
        <= 0
    ):
        errors.append(
            f"課題{display_index}："
            "所要時間を1分以上にしてください。"
        )

    if (
        task_data[
            "deadline_dt"
        ]
        <= datetime.now()
    ):
        errors.append(
            f"課題{display_index}："
            "締切は現在より後にしてください。"
        )

    return errors

def render_add_task():
    st.subheader(
        "＋ 課題を追加"
    )

    st.caption(
        "複数登録したい場合は、"
        "入力欄を追加できます。"
    )

    form_version = st.session_state.get(
        "add_task_form_version",
        0,
    )

    (
        ids_key,
        next_id_key,
    ) = initialize_task_cards(
        form_version
    )

    task_ids = list(
        st.session_state[
            ids_key
        ]
    )

    task_data_list = []

    # =====================================
    # 入力カード
    # =====================================

    for (
        display_index,
        task_id,
    ) in enumerate(
        task_ids,
        start=1,
    ):
        task_data = (
            render_task_input_card(
                form_version=form_version,
                task_id=task_id,
                display_index=display_index,
                can_remove=(
                    len(task_ids) > 1
                ),
            )
        )

        if task_data[
            "remove_clicked"
        ]:
            st.session_state[
                ids_key
            ] = [
                current_id
                for current_id
                in task_ids
                if current_id != task_id
            ]

            st.rerun()

        task_data_list.append(
            task_data
        )

        st.write("")

    # =====================================
    # 入力欄を追加
    # =====================================

    if st.button(
        "＋ 課題入力欄を追加",
        key=(
            f"add_task_card_"
            f"{form_version}"
        ),
        use_container_width=True,
    ):
        new_task_id = (
            st.session_state[
                next_id_key
            ]
        )

        st.session_state[
            ids_key
        ].append(
            new_task_id
        )

        st.session_state[
            next_id_key
        ] = (
            new_task_id + 1
        )

        st.rerun()

    st.write("")

    # =====================================
    # 追加前の確認
    # =====================================

    with st.container(
        border=True
    ):
        st.markdown(
            "### 📋 追加する内容"
        )

        st.caption(
            "登録する課題の内容を"
            "確認してください。"
        )

        for (
            display_index,
            task_data,
        ) in enumerate(
            task_data_list,
            start=1,
        ):
            title = (
                task_data["title"]
                if task_data["title"]
                else "課題名未入力"
            )

            if len(task_data_list) == 1:
                st.markdown(
                    f"**📝 {title}**"
                )

            else:
                st.markdown(
                    f"**課題{display_index}　📝 {title}**"
                )

            st.caption(
                "📅 "
                f"{task_data['deadline_dt'].strftime('%m/%d %H:%M')}"
                "　・　"
                "⏱️ "
                f"{format_estimated_time(task_data['estimated_minutes'])}"
            )

            if (
                display_index
                < len(task_data_list)
            ):
                st.divider()

    st.write("")

    # 課題名が入力されているものだけ登録対象
    entered_tasks = [
        task_data
        for task_data
        in task_data_list
        if task_data["title"]
    ]

    if len(entered_tasks) <= 1:
        submit_label = (
            "✅ この課題を追加する"
        )

    else:
        submit_label = (
            f"✅ {len(entered_tasks)}件の課題を"
            "まとめて追加する"
        )

    st.caption(
        "入力内容を確認して、"
        "下のボタンを押すと課題が登録されます。"
    )

    # =====================================
    # 登録
    # =====================================

    if st.button(
        submit_label,
        key=(
            f"submit_tasks_"
            f"{form_version}"
        ),
        use_container_width=True,
        type="primary",
    ):
        if not entered_tasks:
            st.error(
                "課題名を1件以上"
                "入力してください。"
            )
            return

        errors = []

        for (
            display_index,
            task_data,
        ) in enumerate(
            entered_tasks,
            start=1,
        ):
            errors.extend(
                validate_task(
                    task_data,
                    display_index,
                )
            )

        if errors:
            for error in errors:
                st.error(
                    error
                )

            return

        tasks_to_add = []

        for task_data in entered_tasks:
            tasks_to_add.append(
                {
                    "title": (
                        task_data[
                            "title"
                        ]
                    ),
                    "deadline": (
                        task_data[
                            "deadline"
                        ]
                    ),
                    "estimated_minutes": (
                        task_data[
                            "estimated_minutes"
                        ]
                    ),
                }
            )

        add_tasks_bulk(
            tasks_to_add
        )

        task_count = len(
            tasks_to_add
        )

        if task_count == 1:
            message = (
                f"「{tasks_to_add[0]['title']}」を"
                "追加しました ☕"
            )

        else:
            message = (
                f"{task_count}件の課題を"
                "まとめて追加しました ☕"
            )

        st.session_state[
            "message"
        ] = message

        # 古い入力欄の管理情報を削除
        st.session_state.pop(
            ids_key,
            None,
        )

        st.session_state.pop(
            next_id_key,
            None,
        )

        # 新しいキーに切り替えて入力内容を初期化
        st.session_state[
            "add_task_form_version"
        ] = (
            form_version + 1
        )

        st.rerun()