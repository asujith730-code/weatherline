import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "attendance.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection_scope():
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with connection_scope() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_code TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                attended_at TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                UNIQUE(student_id, attendance_date)
            );
            CREATE INDEX IF NOT EXISTS attendance_date_idx
                ON attendance(attendance_date, attended_at);
            """
        )


def add_student(name, student_code):
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with connection_scope() as connection:
        cursor = connection.execute(
            "INSERT INTO students (name, student_code, created_at) VALUES (?, ?, ?)",
            (name, student_code, created_at),
        )
        return cursor.lastrowid


def delete_student(student_id):
    with connection_scope() as connection:
        connection.execute("DELETE FROM students WHERE id = ?", (student_id,))


def get_students():
    with connection_scope() as connection:
        return connection.execute(
            """
            SELECT s.id, s.name, s.student_code, s.created_at,
                   COUNT(a.id) AS attendance_count
            FROM students AS s
            LEFT JOIN attendance AS a ON a.student_id = s.id
            GROUP BY s.id
            ORDER BY s.name COLLATE NOCASE
            """
        ).fetchall()


def student_count():
    with connection_scope() as connection:
        return connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def mark_attendance(student_id):
    now = datetime.now().astimezone()
    with connection_scope() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO attendance (student_id, attended_at, attendance_date)
            VALUES (?, ?, ?)
            """,
            (student_id, now.isoformat(timespec="seconds"), now.date().isoformat()),
        )
        return cursor.rowcount == 1


def attendance_count_for_date(day=None):
    day = day or datetime.now().astimezone().date().isoformat()
    with connection_scope() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date = ?", (day,)
        ).fetchone()[0]


def get_student_ids_for_date(day=None):
    day = day or datetime.now().astimezone().date().isoformat()
    with connection_scope() as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT student_id FROM attendance WHERE attendance_date = ?", (day,)
            )
        }


def get_attendance(start_date=None, end_date=None, limit=500):
    conditions = []
    parameters = []
    if start_date:
        conditions.append("a.attendance_date >= ?")
        parameters.append(start_date)
    if end_date:
        conditions.append("a.attendance_date <= ?")
        parameters.append(end_date)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connection_scope() as connection:
        return connection.execute(
            f"""
            SELECT a.attendance_date, a.attended_at, s.name, s.student_code
            FROM attendance AS a
            JOIN students AS s ON s.id = a.student_id
            {where_clause}
            ORDER BY a.attended_at DESC
            LIMIT ?
            """,
            (*parameters, limit),
        ).fetchall()