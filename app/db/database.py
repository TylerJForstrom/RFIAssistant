import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path("data/processed/rfi_assistant.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(cur, table: str, column: str, definition: str):
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
        confidence_score REAL,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workflow_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        question_text TEXT NOT NULL,
        generated_draft TEXT NOT NULL,
        final_draft TEXT,
        trade TEXT,
        spec_section TEXT,
        project_name TEXT,
        overall_confidence TEXT,
        confidence_score REAL,
        duplicate_warning TEXT,
        status TEXT NOT NULL DEFAULT 'draft_generated',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    _ensure_column(cur, "feedback", "confidence_score", "REAL")

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
    confidence_score: Optional[float] = None,
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
            duplicate_warning,
            confidence_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        subject,
        question_text,
        generated_draft,
        final_draft,
        action,
        overall_confidence,
        duplicate_warning,
        confidence_score,
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


def create_workflow_item(
    subject: str,
    question_text: str,
    generated_draft: str,
    final_draft: Optional[str] = None,
    trade: Optional[str] = None,
    spec_section: Optional[str] = None,
    project_name: Optional[str] = None,
    overall_confidence: Optional[str] = None,
    confidence_score: Optional[float] = None,
    duplicate_warning: Optional[str] = None,
    status: str = "draft_generated",
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workflow_items (
            subject,
            question_text,
            generated_draft,
            final_draft,
            trade,
            spec_section,
            project_name,
            overall_confidence,
            confidence_score,
            duplicate_warning,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        subject,
        question_text,
        generated_draft,
        final_draft,
        trade,
        spec_section,
        project_name,
        overall_confidence,
        confidence_score,
        duplicate_warning,
        status,
    ))
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return item_id


def update_workflow_status(item_id: int, status: str, final_draft: Optional[str] = None) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    if final_draft is not None:
        cur.execute("""
            UPDATE workflow_items
            SET status = ?, final_draft = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, final_draft, item_id))
    else:
        cur.execute("""
            UPDATE workflow_items
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, item_id))

    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def list_workflow_items(status: Optional[str] = None, limit: int = 200) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    if status:
        cur.execute("""
            SELECT *
            FROM workflow_items
            WHERE status = ?
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
        """, (status, limit))
    else:
        cur.execute("""
            SELECT *
            FROM workflow_items
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
        """, (limit,))

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_workflow_summary() -> Dict:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT status, COUNT(*) AS count
        FROM workflow_items
        GROUP BY status
        ORDER BY count DESC
    """)
    status_counts = [{"status": row["status"], "count": row["count"]} for row in cur.fetchall()]

    cur.execute("SELECT COUNT(*) AS count FROM workflow_items")
    total = cur.fetchone()["count"]

    cur.execute("SELECT AVG(confidence_score) AS avg_conf FROM workflow_items WHERE confidence_score IS NOT NULL")
    avg_conf = cur.fetchone()["avg_conf"]

    conn.close()

    return {
        "total_workflow_items": total,
        "status_counts": status_counts,
        "avg_confidence_score": round(float(avg_conf), 2) if avg_conf is not None else None,
    }


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

    cur.execute("SELECT AVG(confidence_score) AS avg_conf FROM feedback WHERE confidence_score IS NOT NULL")
    avg_conf = cur.fetchone()["avg_conf"]

    conn.close()

    return {
        "total_feedback": total_feedback,
        "action_counts": action_counts,
        "reviewed_rfis_count": reviewed_count,
        "avg_feedback_confidence_score": round(float(avg_conf), 2) if avg_conf is not None else None,
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
