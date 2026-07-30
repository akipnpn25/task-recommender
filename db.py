import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path("data/tasks.db")

DEFAULT_WEEKLY_SETTINGS = {
    0: 120,  # 月曜日
    1: 120,  # 火曜日
    2: 120,  # 水曜日
    3: 120,  # 木曜日
    4: 120,  # 金曜日
    5: 180,  # 土曜日
    6: 180,  # 日曜日
}


# =====================================
# DB接続
# =====================================

def get_connection():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sqlite3.connect(DB_PATH)


# =====================================
# DB初期化
# =====================================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS focus_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        task_title TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT NOT NULL,
        focused_minutes INTEGER NOT NULL
    )
""")

    # -------------------------
    # 課題
    # -------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            estimated_minutes INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # 古いDBにも対応
    cursor.execute(
        "PRAGMA table_info(tasks)"
    )

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "progress" not in columns:
        cursor.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN progress
            INTEGER NOT NULL DEFAULT 0
            """
        )

    if "completed" not in columns:
        cursor.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN completed
            INTEGER NOT NULL DEFAULT 0
            """
        )

    # -------------------------
    # 曜日ごとの空き時間
    # -------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_settings (
            weekday INTEGER PRIMARY KEY,
            available_minutes INTEGER NOT NULL
        )
        """
    )

    for weekday, minutes in (
        DEFAULT_WEEKLY_SETTINGS.items()
    ):
        cursor.execute(
            """
            INSERT OR IGNORE INTO weekly_settings (
                weekday,
                available_minutes
            )
            VALUES (?, ?)
            """,
            (
                weekday,
                minutes,
            ),
        )

    # -------------------------
    # 特定日の空き時間
    # -------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS date_overrides (
            date TEXT PRIMARY KEY,
            available_minutes INTEGER NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# =====================================
# 課題追加
# =====================================

def add_task(
    title,
    deadline,
    estimated_minutes,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tasks (
            title,
            deadline,
            estimated_minutes,
            progress,
            completed
        )
        VALUES (?, ?, ?, 0, 0)
        """,
        (
            title,
            deadline,
            estimated_minutes,
        ),
    )

    conn.commit()
    conn.close()


# =====================================
# 未完了課題
# =====================================

def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            deadline,
            estimated_minutes,
            progress
        FROM tasks
        WHERE completed = 0
        ORDER BY deadline ASC
        """
    )

    tasks = cursor.fetchall()

    conn.close()

    return tasks


# =====================================
# 完了済み課題
# =====================================

def get_completed_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            deadline,
            estimated_minutes,
            progress
        FROM tasks
        WHERE completed = 1
        ORDER BY deadline DESC
        """
    )

    tasks = cursor.fetchall()

    conn.close()

    return tasks


# =====================================
# 課題編集
# =====================================

def update_task(
    task_id,
    title,
    deadline,
    estimated_minutes,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET
            title = ?,
            deadline = ?,
            estimated_minutes = ?
        WHERE id = ?
        """,
        (
            title,
            deadline,
            estimated_minutes,
            task_id,
        ),
    )

    conn.commit()
    conn.close()


# =====================================
# 進捗更新
# =====================================

def update_progress(
    task_id,
    progress,
):
    progress = max(
        0,
        min(100, progress),
    )

    completed = (
        1 if progress >= 100 else 0
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET
            progress = ?,
            completed = ?
        WHERE id = ?
        """,
        (
            progress,
            completed,
            task_id,
        ),
    )

    conn.commit()
    conn.close()


# =====================================
# 完了
# =====================================

def complete_task(task_id):
    update_progress(
        task_id,
        100,
    )


# =====================================
# 完了を取り消す
# =====================================

def restore_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET
            completed = 0,
            progress =
                CASE
                    WHEN progress >= 100 THEN 90
                    ELSE progress
                END
        WHERE id = ?
        """,
        (task_id,),
    )

    conn.commit()
    conn.close()


# =====================================
# 削除
# =====================================

def delete_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (task_id,),
    )

    conn.commit()
    conn.close()


# =====================================
# 曜日ごとの空き時間
# =====================================

def get_weekly_settings():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            weekday,
            available_minutes
        FROM weekly_settings
        ORDER BY weekday
        """
    )

    settings = dict(
        cursor.fetchall()
    )

    conn.close()

    return settings


def save_weekly_settings(settings):
    conn = get_connection()
    cursor = conn.cursor()

    for weekday, minutes in (
        settings.items()
    ):
        cursor.execute(
            """
            INSERT INTO weekly_settings (
                weekday,
                available_minutes
            )
            VALUES (?, ?)

            ON CONFLICT(weekday)
            DO UPDATE SET
                available_minutes =
                excluded.available_minutes
            """,
            (
                weekday,
                minutes,
            ),
        )

    conn.commit()
    conn.close()


# =====================================
# 特定日の空き時間
# =====================================

def get_date_overrides():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            date,
            available_minutes
        FROM date_overrides
        ORDER BY date
        """
    )

    overrides = dict(
        cursor.fetchall()
    )

    conn.close()

    return overrides


def save_date_override(
    date,
    available_minutes,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO date_overrides (
            date,
            available_minutes
        )
        VALUES (?, ?)

        ON CONFLICT(date)
        DO UPDATE SET
            available_minutes =
            excluded.available_minutes
        """,
        (
            date,
            available_minutes,
        ),
    )

    conn.commit()
    conn.close()


def delete_date_override(date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM date_overrides
        WHERE date = ?
        """,
        (date,),
    )

    conn.commit()
    conn.close()
    
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO focus_sessions (
            task_id,
            task_title,
            started_at,
            ended_at,
            focused_minutes
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            task_id,
            task_title,
            started_at,
            ended_at,
            focused_minutes,
        ),
    )

    conn.commit()
    conn.close()


def get_today_focus_summary():
    today = datetime.now().date().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(focused_minutes), 0),
            COUNT(*)
        FROM focus_sessions
        WHERE started_at LIKE ?
        """,
        (
            f"{today}%",
        ),
    )

    total_minutes, session_count = (
        cursor.fetchone()
    )

    conn.close()

    return {
        "total_minutes": total_minutes,
        "session_count": session_count,
    }