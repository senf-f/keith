import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from keith.models import Book, Chapter


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


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

    # -- Chapter CRUD --

    def create_chapter(self, book_id: int, title: str, content: str) -> Chapter:
        now = _now()
        row = self.conn.execute(
            "SELECT COALESCE(MAX(position), 0) FROM chapters WHERE book_id = ?",
            (book_id,),
        ).fetchone()
        position = row[0] + 1
        cursor = self.conn.execute(
            "INSERT INTO chapters (book_id, title, content, position, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (book_id, title, content, position, now, now),
        )
        self.conn.commit()
        return Chapter(
            id=cursor.lastrowid, book_id=book_id, title=title,
            content=content, position=position, created_at=now, updated_at=now,
        )

    def list_chapters(self, book_id: int) -> list[Chapter]:
        rows = self.conn.execute(
            "SELECT id, book_id, title, content, position, created_at, updated_at "
            "FROM chapters WHERE book_id = ? ORDER BY position",
            (book_id,),
        ).fetchall()
        return [Chapter(id=r[0], book_id=r[1], title=r[2], content=r[3],
                        position=r[4], created_at=r[5], updated_at=r[6]) for r in rows]

    def get_chapter(self, chapter_id: int) -> Chapter | None:
        row = self.conn.execute(
            "SELECT id, book_id, title, content, position, created_at, updated_at "
            "FROM chapters WHERE id = ?",
            (chapter_id,),
        ).fetchone()
        if row is None:
            return None
        return Chapter(id=row[0], book_id=row[1], title=row[2], content=row[3],
                       position=row[4], created_at=row[5], updated_at=row[6])

    def update_chapter(self, chapter_id: int, title: str | None = None, content: str | None = None) -> None:
        now = _now()
        chapter = self.get_chapter(chapter_id)
        if chapter is None:
            return
        new_title = title if title is not None else chapter.title
        new_content = content if content is not None else chapter.content
        self.conn.execute(
            "UPDATE chapters SET title = ?, content = ?, updated_at = ? WHERE id = ?",
            (new_title, new_content, now, chapter_id),
        )
        self.conn.commit()

    def move_chapter(self, chapter_id: int, new_position: int) -> None:
        chapter = self.get_chapter(chapter_id)
        if chapter is None:
            return
        old_position = chapter.position
        book_id = chapter.book_id
        if new_position == old_position:
            return
        if new_position < old_position:
            self.conn.execute(
                "UPDATE chapters SET position = position + 1 "
                "WHERE book_id = ? AND position >= ? AND position < ?",
                (book_id, new_position, old_position),
            )
        else:
            self.conn.execute(
                "UPDATE chapters SET position = position - 1 "
                "WHERE book_id = ? AND position > ? AND position <= ?",
                (book_id, old_position, new_position),
            )
        self.conn.execute(
            "UPDATE chapters SET position = ? WHERE id = ?",
            (new_position, chapter_id),
        )
        self.conn.commit()

    def delete_chapter(self, chapter_id: int) -> None:
        self.conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
        self.conn.commit()

    def chapter_count(self, book_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM chapters WHERE book_id = ?", (book_id,),
        ).fetchone()
        return row[0]
