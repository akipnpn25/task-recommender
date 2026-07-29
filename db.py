import sqlite3
from pathlib import Path


# =====================================
# DB設定
# =====================================

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
    """SQLiteへの接続を返す"""

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sqlite3.connect(DB_PATH)


# =====================================
# DB初期化
# =====================================

def init_db():
    """必要なテーブル・カラムを作成する"""

    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------
    # 課題テーブル
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

    # 既存DBを使っている場合のために
    # カラムが存在するか確認する
    cursor.execute(
        "PRAGMA table_info(tasks)"
    )

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    # progressがない古いDBなら追加
    if "progress" not in columns:

        cursor.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN progress
            INTEGER NOT NULL DEFAULT 0
            """
        )

    # completedがない古いDBなら追加
    if "completed" not in columns:

        cursor.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN completed
            INTEGER NOT NULL DEFAULT 0
            """
        )

    # -------------------------
    # 曜日別空き時間テーブル
    # -------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_settings (
            weekday INTEGER PRIMARY KEY,
            available_minutes INTEGER NOT NULL
        )
        """
    )

    # 初回のみデフォルト設定を登録
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM weekly_settings
        """
    )

    count = cursor.fetchone()[0]

    if count == 0:

        for (
            weekday,
            minutes,
        ) in DEFAULT_WEEKLY_SETTINGS.items():

            cursor.execute(
                """
                INSERT INTO weekly_settings (
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
    """新しい課題を登録する"""

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
# 未完了課題取得
# =====================================

def get_tasks():
    """未完了の課題を締切順に取得する"""

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
# 完了済み課題取得
# =====================================

def get_completed_tasks():
    """完了済みの課題を取得する"""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            deadline,
            estimated_minutes
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
    """課題名・締切・予想時間を変更する"""

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
    """課題の進捗率を更新する"""

    # 0〜100%に制限
    progress = max(
        0,
        min(100, progress),
    )

    conn = get_connection()
    cursor = conn.cursor()

    # 100%なら自動で完了
    if progress >= 100:

        cursor.execute(
            """
            UPDATE tasks
            SET
                progress = 100,
                completed = 1
            WHERE id = ?
            """,
            (task_id,),
        )

    else:

        cursor.execute(
            """
            UPDATE tasks
            SET
                progress = ?,
                completed = 0
            WHERE id = ?
            """,
            (
                progress,
                task_id,
            ),
        )

    conn.commit()
    conn.close()


# =====================================
# 完了
# =====================================

def complete_task(task_id):
    """課題を100%・完了状態にする"""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET
            progress = 100,
            completed = 1
        WHERE id = ?
        """,
        (task_id,),
    )

    conn.commit()
    conn.close()


# =====================================
# 完了を取り消す
# =====================================

def restore_task(task_id):
    """完了済み課題を未完了に戻す"""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET
            completed = 0,
            progress = 0
        WHERE id = ?
        """,
        (task_id,),
    )

    conn.commit()
    conn.close()


# =====================================
# 課題削除
# =====================================

def delete_task(task_id):
    """課題を完全に削除する"""

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
# 曜日別空き時間取得
# =====================================

def get_weekly_settings():
    """曜日ごとの空き時間設定を取得する"""

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


# =====================================
# 曜日別空き時間保存
# =====================================

def save_weekly_settings(settings):
    """曜日ごとの空き時間を保存する"""

    conn = get_connection()
    cursor = conn.cursor()

    for (
        weekday,
        minutes,
    ) in settings.items():

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