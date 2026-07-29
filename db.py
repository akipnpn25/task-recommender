import sqlite3
from pathlib import Path

DB_PATH = Path("data/tasks.db")


def get_connection():
    """SQLiteへの接続を返す"""
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """課題テーブルを作成する。旧形式なら自動で移行する"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='tasks'
        """
    )

    table_exists = cursor.fetchone()

    # 初回起動
    if not table_exists:
        cursor.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                deadline TEXT NOT NULL,
                estimated_minutes INTEGER NOT NULL
            )
            """
        )

    else:
        # 以前のDB構成を確認
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]

        expected_columns = [
            "id",
            "title",
            "deadline",
            "estimated_minutes",
        ]

        # 古い形式なら必要なデータだけ残して作り直す
        if columns != expected_columns:
            cursor.execute(
                """
                CREATE TABLE tasks_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    estimated_minutes INTEGER NOT NULL
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO tasks_new (
                    id,
                    title,
                    deadline,
                    estimated_minutes
                )
                SELECT
                    id,
                    title,
                    deadline,
                    estimated_minutes
                FROM tasks
                """
            )

            cursor.execute("DROP TABLE tasks")
            cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

    conn.commit()
    conn.close()


def add_task(title, deadline, estimated_minutes):
    """課題を追加する"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tasks (
            title,
            deadline,
            estimated_minutes
        )
        VALUES (?, ?, ?)
        """,
        (
            title,
            deadline,
            estimated_minutes,
        ),
    )

    conn.commit()
    conn.close()


def get_tasks():
    """課題を締切が近い順に取得する"""
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
        ORDER BY deadline ASC
        """
    )

    tasks = cursor.fetchall()

    conn.close()

    return tasks


def delete_task(task_id):
    """課題を削除する"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,),
    )

    conn.commit()
    conn.close()