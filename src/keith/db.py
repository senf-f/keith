import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from keith.models import Book, Chapter


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_dir = Path.home() / ".keith"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "keith.db"
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chapters USING fts5(
                book_title,
                chapter_title,
                content,
                content_rowid=id
            );
        """)
        self._create_triggers()
        self.conn.commit()

    def _create_triggers(self):
        existing = {row[0] for row in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()}

        if "fts_chapters_insert" not in existing:
            self.conn.execute("""
                CREATE TRIGGER fts_chapters_insert AFTER INSERT ON chapters
                BEGIN
                    INSERT INTO fts_chapters(rowid, book_title, chapter_title, content)
                    SELECT NEW.id,
                           (SELECT title FROM books WHERE id = NEW.book_id),
                           NEW.title,
                           NEW.content;
                END;
            """)

        if "fts_chapters_update" not in existing:
            self.conn.execute("""
                CREATE TRIGGER fts_chapters_update AFTER UPDATE ON chapters
                BEGIN
                    DELETE FROM fts_chapters WHERE rowid = OLD.id;
                    INSERT INTO fts_chapters(rowid, book_title, chapter_title, content)
                    SELECT NEW.id,
                           (SELECT title FROM books WHERE id = NEW.book_id),
                           NEW.title,
                           NEW.content;
                END;
            """)

        if "fts_chapters_delete" not in existing:
            self.conn.execute("""
                CREATE TRIGGER fts_chapters_delete AFTER DELETE ON chapters
                BEGIN
                    DELETE FROM fts_chapters WHERE rowid = OLD.id;
                END;
            """)

    def close(self):
        self.conn.close()

    # -- Book CRUD --

    def create_book(self, title: str) -> Book:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO books (title, created_at, updated_at) VALUES (?, ?, ?)",
            (title, now, now),
        )
        self.conn.commit()
        return Book(id=cursor.lastrowid, title=title, created_at=now, updated_at=now)

    def list_books(self) -> list[Book]:
        rows = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM books ORDER BY id"
        ).fetchall()
        return [Book(id=r[0], title=r[1], created_at=r[2], updated_at=r[3]) for r in rows]

    def get_book(self, book_id: int) -> Book | None:
        row = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        if row is None:
            return None
        return Book(id=row[0], title=row[1], created_at=row[2], updated_at=row[3])

    def delete_book(self, book_id: int) -> None:
        self.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()
