import streamlit as st
from datetime import datetime, timedelta

from db import (
    add_focus_session,
    update_progress,
    complete_task,
)

from components import (
    format_minutes,
)


# =====================================
# 集中状態を削除
# =====================================

def clear_focus_state():
    keys = [
        "focus_mode",
        "focus_task_id",
        "focus_task_title",
        "focus_started_at",
        "focus_minutes",
    ]

    for key in keys:
        st.session_state.pop(
            key,
            None,
        )


# =====================================
# 振り返り状態を削除
# =====================================

def clear_focus_result_state():
    keys = [
        "focus_result_mode",
        "focus_result_task_id",
        "focus_result_task_title",
        "focus_result_minutes",
    ]

    for key in keys:
        st.session_state.pop(
            key,
            None,
        )


# =====================================
# 集中開始
# =====================================

def start_focus_session(
    task_id,
    task_title,
    focus_minutes,
):
    clear_focus_result_state()

    st.session_state[
        "focus_mode"
    ] = True

    st.session_state[
        "focus_task_id"
    ] = task_id

    st.session_state[
        "focus_task_title"
    ] = task_title

    st.session_state[
        "focus_started_at"
    ] = datetime.now().isoformat()

    st.session_state[
        "focus_minutes"
    ] = focus_minutes


# =====================================
# 集中履歴を保存
# =====================================

def save_focus_session(
    task_id,
    task_title,
    focused_minutes,
):
    started_at = st.session_state.get(
        "focus_started_at"
    )

    if started_at is None:
        return

    ended_at = (
        datetime.now().isoformat()
    )

    add_focus_session(
        task_id,
        task_title,
        started_at,
        ended_at,
        focused_minutes,
    )


# =====================================
# 振り返り開始
# =====================================

def start_focus_result(
    task_id,
    task_title,
    focused_minutes,
):
    save_focus_session(
        task_id,
        task_title,
        focused_minutes,
    )

    st.session_state[
        "focus_result_mode"
    ] = True

    st.session_state[
        "focus_result_task_id"
    ] = task_id

    st.session_state[
        "focus_result_task_title"
    ] = task_title

    st.session_state[
        "focus_result_minutes"
    ] = focused_minutes

    clear_focus_state()


# =====================================
# 集中モード
# =====================================

def render_focus_mode():
    task_id = st.session_state.get(
        "focus_task_id"
    )

    task_title = st.session_state.get(
        "focus_task_title",
        "課題",
    )

    started_at_text = st.session_state.get(
        "focus_started_at"
    )

    focus_minutes = st.session_state.get(
        "focus_minutes",
        30,
    )

    if (
        task_id is None
        or started_at_text is None
    ):
        clear_focus_state()
        st.rerun()

    started_at = datetime.fromisoformat(
        started_at_text
    )

    finish_at = (
        started_at
        + timedelta(
            minutes=focus_minutes
        )
    )

    st.markdown(
        (
            '<div class="section-kicker">'
            'FOCUS MODE'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "今はこの課題だけに集中しよう。"
    )

    st.write("")

    # =====================================
    # カウントダウン
    # =====================================

    @st.fragment(
        run_every=1
    )
    def render_countdown():
        now = datetime.now()

        remaining_seconds = int(
            (
                finish_at
                - now
            ).total_seconds()
        )

        total_seconds = (
            focus_minutes
            * 60
        )

        # -------------------------
        # 時間終了
        # -------------------------

        if remaining_seconds <= 0:
            st.markdown(
                (
                    '<div class="focus-screen">'
                    '<div class="focus-screen-label">'
                    '☕ FOCUS TIME'
                    '</div>'
                    '<div class="focus-screen-title">'
                    f'{task_title}'
                    '</div>'
                    '<div class="focus-finished">'
                    'おつかれさま！'
                    '</div>'
                    '<div class="focus-screen-message">'
                    '集中時間が終了しました。'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

            st.progress(
                1.0
            )

            if st.button(
                "✓ 進捗を記録する",
                key="finish_focus_time",
                use_container_width=True,
                type="primary",
            ):
                start_focus_result(
                    task_id,
                    task_title,
                    focus_minutes,
                )

                st.rerun()

            if st.button(
                "進捗を記録せず戻る",
                key="finish_without_result",
                use_container_width=True,
            ):
                save_focus_session(
                    task_id,
                    task_title,
                    focus_minutes,
                )

                clear_focus_state()

                st.rerun()

            return

        # -------------------------
        # 残り時間
        # -------------------------

        remaining_minutes = (
            remaining_seconds
            // 60
        )

        remaining_sec = (
            remaining_seconds
            % 60
        )

        timer_text = (
            f"{remaining_minutes:02d}:"
            f"{remaining_sec:02d}"
        )

        elapsed_seconds = (
            total_seconds
            - remaining_seconds
        )

        progress = (
            elapsed_seconds
            / total_seconds
        )

        progress = max(
            0.0,
            min(
                1.0,
                progress,
            ),
        )

        st.markdown(
            (
                '<div class="focus-screen">'
                '<div class="focus-screen-label">'
                '☕ FOCUS TIME'
                '</div>'
                '<div class="focus-screen-title">'
                f'{task_title}'
                '</div>'
                '<div class="focus-countdown">'
                f'{timer_text}'
                '</div>'
                '<div class="focus-screen-duration">'
                f'{format_minutes(focus_minutes)} 集中'
                '</div>'
                '<div class="focus-screen-message">'
                f'{started_at.strftime("%H:%M")}'
                ' 〜 '
                f'{finish_at.strftime("%H:%M")}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.progress(
            progress
        )

        st.caption(
            "☕ 焦らず、この課題だけに集中。"
        )

        st.write("")

        # -------------------------
        # 途中終了
        # -------------------------

        if st.button(
            "✓ ここで集中を終える",
            key="finish_focus_early",
            use_container_width=True,
            type="primary",
        ):
            elapsed_seconds = (
                datetime.now()
                - started_at
            ).total_seconds()

            focused_minutes = max(
                1,
                round(
                    elapsed_seconds
                    / 60
                ),
            )

            focused_minutes = min(
                focus_minutes,
                focused_minutes,
            )

            start_focus_result(
                task_id,
                task_title,
                focused_minutes,
            )

            st.rerun()

        # -------------------------
        # 中断
        # -------------------------

        if st.button(
            "← 中断しておすすめ画面に戻る",
            key="cancel_focus",
            use_container_width=True,
        ):
            clear_focus_state()

            st.rerun()

    render_countdown()


# =====================================
# 集中終了後の振り返り
# =====================================

def render_focus_result(
    tasks,
):
    task_id = st.session_state.get(
        "focus_result_task_id"
    )

    task_title = st.session_state.get(
        "focus_result_task_title",
        "課題",
    )

    focused_minutes = st.session_state.get(
        "focus_result_minutes",
        0,
    )

    target_task = next(
        (
            task
            for task in tasks
            if task[0] == task_id
        ),
        None,
    )

    if target_task is None:
        clear_focus_result_state()
        st.rerun()

    current_progress = (
        target_task[4]
    )

    st.markdown(
        (
            '<div class="focus-result-card">'
            '<div class="focus-result-icon">'
            '☕'
            '</div>'
            '<div class="focus-result-title">'
            'おつかれさま！'
            '</div>'
            '<div class="focus-result-task">'
            f'{task_title}'
            '</div>'
            '<div class="focus-result-message">'
            f'今回は{format_minutes(focused_minutes)}'
            '集中しました。'
            '<br>'
            '今の進み具合を記録しておこう。'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.write("")

    st.markdown(
        "### 📈 どこまで進みましたか？"
    )

    st.caption(
        f"集中前の進捗：{current_progress}%"
    )

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

    selected_label = (
        st.segmented_control(
            "進捗",
            options=list(
                progress_options.keys()
            ),
            selection_mode="single",
            key="focus_result_progress",
            width="stretch",
            label_visibility="collapsed",
        )
    )

    st.write("")

    if selected_label is not None:
        new_progress = (
            progress_options[
                selected_label
            ]
        )

        if st.button(
            "進捗を保存しておすすめを見る",
            key="save_focus_result",
            use_container_width=True,
            type="primary",
        ):
            update_progress(
                task_id,
                new_progress,
            )

            clear_focus_result_state()

            st.session_state[
                "message"
            ] = (
                f"「{task_title}」の進捗を"
                f"{selected_label}に更新しました ☕"
            )

            st.rerun()

    if st.button(
        "✓ この課題は完了した！",
        key="complete_focus_result",
        use_container_width=True,
    ):
        complete_task(
            task_id
        )

        clear_focus_result_state()

        st.session_state[
            "celebrate_task"
        ] = task_title

        st.rerun()

    if st.button(
        "今回は進捗を変えない",
        key="skip_focus_result",
        use_container_width=True,
    ):
        clear_focus_result_state()

        st.rerun()