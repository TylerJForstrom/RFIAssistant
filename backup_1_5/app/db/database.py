import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path("data/processed/rfi_assistant.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        question_text TEXT NOT NULL,
        generated_draft TEXT NOT NULL,
        final_draft TEXT,
        action TEXT NOT NULL,
        overall_confidence TEXT,
        duplicate_warning TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviewed_rfis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        question_text TEXT NOT NULL,
        final_response_text TEXT NOT NULL,
        trade TEXT,
        spec_section TEXT,
        project_name TEXT,
        source_type TEXT DEFAULT 'feedback',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_feedback(
    subject: str,
    question_text: str,
    generated_draft: str,
    final_draft: Optional[str],
    action: str,
    overall_confidence: Optional[str],
    duplicate_warning: Optional[str],
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback (
            subject,
            question_text,
            generated_draft,
            final_draft,
            action,
            overall_confidence,
            duplicate_warning
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        subject,
        question_text,
        generated_draft,
        final_draft,
        action,
        overall_confidence,
        duplicate_warning,
    ))
    conn.commit()
    conn.close()


def save_reviewed_rfi(
    subject: str,
    question_text: str,
    final_response_text: str,
    trade: Optional[str],
    spec_section: Optional[str],
    project_name: Optional[str],
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reviewed_rfis (
            subject,
            question_text,
            final_response_text,
            trade,
            spec_section,
            project_name
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        subject,
        question_text,
        final_response_text,
        trade,
        spec_section,
        project_name,
    ))
    conn.commit()
    conn.close()


def get_feedback_summary() -> Dict:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM feedback")
    total_feedback = cur.fetchone()["count"]

    cur.execute("""
        SELECT action, COUNT(*) AS count
        FROM feedback
        GROUP BY action
        ORDER BY count DESC
    """)
    action_counts = [{"action": row["action"], "count": row["count"]} for row in cur.fetchall()]

    cur.execute("SELECT COUNT(*) AS count FROM reviewed_rfis")
    reviewed_count = cur.fetchone()["count"]

    conn.close()

    return {
        "total_feedback": total_feedback,
        "action_counts": action_counts,
        "reviewed_rfis_count": reviewed_count,
        "db_path": str(DB_PATH),
    }


def list_recent_feedback(limit: int = 20) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM feedback
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def list_reviewed_rfis(limit: int = 5000) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM reviewed_rfis
        ORDER BY created_at ASC
        LIMIT ?
    """, (limit,))

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
