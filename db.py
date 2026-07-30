from datetime import (
    datetime,
    timedelta,
)

import streamlit as st

from auth import (
    get_authenticated_client,
)


# =====================================
# 共通
# =====================================

def init_db():
    """
    SQLite時代との互換用。

    Supabaseではテーブル作成は
    Dashboard / SQL Editor側で行っているため、
    ここでは何もしない。
    """
    return


def get_current_user_id():
    user_id = st.session_state.get(
        "user_id"
    )

    if not user_id:
        raise RuntimeError(
            "ログイン情報がありません。"
        )

    return user_id


def get_db_client():
    client = (
        get_authenticated_client()
    )

    if client is None:
        raise RuntimeError(
            "Supabaseに接続できません。"
            "もう一度ログインしてください。"
        )

    return client


# =====================================
# 課題
# =====================================

def add_task(
    title,
    deadline,
    estimated_minutes,
):
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "tasks"
        )
        .insert(
            {
                "user_id": user_id,
                "title": title,
                "deadline": deadline,
                "estimated_minutes": int(
                    estimated_minutes
                ),
                "progress": 0,
            }
        )
        .execute()
    )


def add_tasks_bulk(
    tasks,
):
    """
    複数の課題を一度に追加する。
    """

    if not tasks:
        return

    client = get_db_client()
    user_id = get_current_user_id()

    rows = []

    for task in tasks:
        rows.append(
            {
                "user_id": user_id,
                "title": task["title"],
                "deadline": task["deadline"],
                "estimated_minutes": int(
                    task["estimated_minutes"]
                ),
                "progress": 0,
            }
        )

    (
        client.table(
            "tasks"
        )
        .insert(
            rows
        )
        .execute()
    )


def get_tasks():
    client = get_db_client()
    user_id = get_current_user_id()

    response = (
        client.table(
            "tasks"
        )
        .select(
            "id,title,deadline,"
            "estimated_minutes,progress"
        )
        .eq(
            "user_id",
            user_id,
        )
        .lt(
            "progress",
            100,
        )
        .order(
            "deadline",
        )
        .execute()
    )

    tasks = []

    for row in response.data:
        tasks.append(
            (
                row["id"],
                row["title"],
                row["deadline"],
                row["estimated_minutes"],
                row["progress"],
            )
        )

    return tasks


def get_completed_tasks():
    client = get_db_client()
    user_id = get_current_user_id()

    response = (
        client.table(
            "tasks"
        )
        .select(
            "id,title,deadline,"
            "estimated_minutes,progress"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "progress",
            100,
        )
        .order(
            "deadline",
            desc=True,
        )
        .execute()
    )

    completed_tasks = []

    for row in response.data:
        completed_tasks.append(
            (
                row["id"],
                row["title"],
                row["deadline"],
                row["estimated_minutes"],
                row["progress"],
            )
        )

    return completed_tasks


def update_task(
    task_id,
    title,
    deadline,
    estimated_minutes,
):
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "tasks"
        )
        .update(
            {
                "title": title,
                "deadline": deadline,
                "estimated_minutes": int(
                    estimated_minutes
                ),
            }
        )
        .eq(
            "id",
            task_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )


def update_progress(
    task_id,
    progress,
):
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "tasks"
        )
        .update(
            {
                "progress": int(
                    progress
                ),
            }
        )
        .eq(
            "id",
            task_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )


def complete_task(
    task_id,
):
    update_progress(
        task_id,
        100,
    )


def restore_task(
    task_id,
):
    """
    完了済み課題を未完了へ戻す。

    90%へ戻して、
    再び通常の課題として扱う。
    """

    update_progress(
        task_id,
        90,
    )


def delete_task(
    task_id,
):
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "tasks"
        )
        .delete()
        .eq(
            "id",
            task_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )


def delete_all_completed_tasks():
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "tasks"
        )
        .delete()
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "progress",
            100,
        )
        .execute()
    )


# =====================================
# 毎週の空き時間
# =====================================

def get_weekly_settings():
    client = get_db_client()
    user_id = get_current_user_id()

    response = (
        client.table(
            "weekly_settings"
        )
        .select(
            "weekday,available_minutes"
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    settings = {}

    for row in response.data:
        settings[
            int(
                row["weekday"]
            )
        ] = int(
            row["available_minutes"]
        )

    return settings


def save_weekly_settings(
    weekly_available_minutes,
):
    client = get_db_client()
    user_id = get_current_user_id()

    rows = []

    for (
        weekday,
        minutes,
    ) in weekly_available_minutes.items():
        rows.append(
            {
                "user_id": user_id,
                "weekday": int(
                    weekday
                ),
                "available_minutes": int(
                    minutes
                ),
            }
        )

    if not rows:
        return

    (
        client.table(
            "weekly_settings"
        )
        .upsert(
            rows,
            on_conflict=(
                "user_id,weekday"
            ),
        )
        .execute()
    )


# =====================================
# 日付ごとの空き時間変更
# =====================================

def get_date_overrides():
    client = get_db_client()
    user_id = get_current_user_id()

    response = (
        client.table(
            "date_overrides"
        )
        .select(
            "override_date,"
            "available_minutes"
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    overrides = {}

    for row in response.data:
        overrides[
            row["override_date"]
        ] = int(
            row["available_minutes"]
        )

    return overrides


def save_date_override(
    date_string,
    available_minutes,
):
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "date_overrides"
        )
        .upsert(
            {
                "user_id": user_id,
                "override_date": date_string,
                "available_minutes": int(
                    available_minutes
                ),
            },
            on_conflict=(
                "user_id,override_date"
            ),
        )
        .execute()
    )


def delete_date_override(
    date_string,
):
    client = get_db_client()
    user_id = get_current_user_id()

    (
        client.table(
            "date_overrides"
        )
        .delete()
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "override_date",
            date_string,
        )
        .execute()
    )


# =====================================
# 集中履歴
# =====================================

def add_focus_session(
    task_id,
    task_title,
    started_at,
    ended_at,
    focused_minutes,
):
    client = get_db_client()
    user_id = get_current_user_id()

    if isinstance(
        started_at,
        datetime,
    ):
        started_at = (
            started_at.isoformat()
        )

    if isinstance(
        ended_at,
        datetime,
    ):
        ended_at = (
            ended_at.isoformat()
        )

    (
        client.table(
            "focus_sessions"
        )
        .insert(
            {
                "user_id": user_id,
                "task_id": task_id,
                "task_title": task_title,
                "started_at": started_at,
                "ended_at": ended_at,
                "focused_minutes": int(
                    focused_minutes
                ),
            }
        )
        .execute()
    )


def get_today_focus_summary():
    client = get_db_client()
    user_id = get_current_user_id()

    today = (
        datetime.now()
        .date()
    )

    tomorrow = (
        today
        + timedelta(
            days=1
        )
    )

    response = (
        client.table(
            "focus_sessions"
        )
        .select(
            "focused_minutes"
        )
        .eq(
            "user_id",
            user_id,
        )
        .gte(
            "started_at",
            today.isoformat(),
        )
        .lt(
            "started_at",
            tomorrow.isoformat(),
        )
        .execute()
    )

    total_minutes = sum(
        int(
            row[
                "focused_minutes"
            ]
        )
        for row in response.data
    )

    session_count = len(
        response.data
    )

    return {
        "total_minutes": total_minutes,
        "session_count": session_count,
    }