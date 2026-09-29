"""
OfflineMind - SQLite Note Index & Search Database
Maintains an index of all processed voice notes, meetings, and lectures for instant local search.
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("OfflineMind.Database")

DEFAULT_DB_PATH = Path("storage/notes_data/offlinemind.db")


class NotesDatabase:
    """
    Local SQLite database index for fast full-text searching and filtering.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    from contextlib import contextmanager

    @contextmanager
    def _get_connection(self):
        """Returns SQLite connection context with row factory enabled, closing connection on exit."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    duration_seconds REAL DEFAULT 0.0,
                    backend TEXT DEFAULT 'CPU',
                    word_count INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)")
            conn.commit()
            logger.info(f"Initialized SQLite database at {self.db_path}")

    def insert_note(self, note: Dict[str, Any]) -> str:
        """Inserts a new note record into the SQLite index."""
        now = datetime.now().isoformat()
        tags_str = ",".join(note.get("tags", [])) if isinstance(note.get("tags"), list) else str(note.get("tags", ""))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO notes (
                    id, title, summary, tags, created_at, updated_at,
                    file_path, duration_seconds, backend, word_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note["id"],
                note.get("title", "Untitled Note"),
                note.get("summary", ""),
                tags_str,
                note.get("created_at", now),
                now,
                str(note.get("file_path", "")),
                float(note.get("duration_seconds", 0.0)),
                note.get("backend", "CPU"),
                int(note.get("word_count", 0)),
            ))
            conn.commit()
            logger.info(f"Indexed note '{note['id']}' in SQLite.")
            return note["id"]

    def update_note(self, note_id: str, updates: Dict[str, Any]) -> bool:
        """Updates metadata for an existing note."""
        now = datetime.now().isoformat()
        tags_str = ",".join(updates.get("tags", [])) if isinstance(updates.get("tags"), list) else updates.get("tags")

        fields = ["updated_at = ?"]
        values = [now]

        if "title" in updates:
            fields.append("title = ?")
            values.append(updates["title"])
        if "summary" in updates:
            fields.append("summary = ?")
            values.append(updates["summary"])
        if tags_str is not None:
            fields.append("tags = ?")
            values.append(tags_str)
        if "file_path" in updates:
            fields.append("file_path = ?")
            values.append(str(updates["file_path"]))
        if "word_count" in updates:
            fields.append("word_count = ?")
            values.append(int(updates["word_count"]))

        values.append(note_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves note metadata by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()] if d.get("tags") else []
                return d
            return None

    def list_notes(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Returns list of notes ordered chronologically descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()] if d.get("tags") else []
                results.append(d)
            return results

    def search_notes(self, query: str, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Searches notes matching text query in title or summary, with optional tag filter.
        """
        query_pattern = f"%{query.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if tag:
                tag_pattern = f"%{tag.strip()}%"
                cursor.execute("""
                    SELECT * FROM notes
                    WHERE (title LIKE ? OR summary LIKE ?)
                    AND tags LIKE ?
                    ORDER BY created_at DESC
                """, (query_pattern, query_pattern, tag_pattern))
            else:
                cursor.execute("""
                    SELECT * FROM notes
                    WHERE title LIKE ? OR summary LIKE ?
                    ORDER BY created_at DESC
                """, (query_pattern, query_pattern))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()] if d.get("tags") else []
                results.append(d)
            return results

    def delete_note(self, note_id: str) -> bool:
        """Deletes note from the SQLite index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0
