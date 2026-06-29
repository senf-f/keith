import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from keith.models import Book, Chapter, Note, SearchResult


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

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS fts_notes USING fts5(
                book_title,
                category,
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

        if "fts_notes_insert" not in existing:
            self.conn.execute("""
                CREATE TRIGGER fts_notes_insert AFTER INSERT ON notes
                BEGIN
                    INSERT INTO fts_notes(rowid, book_title, category, content)
                    SELECT NEW.id,
                           (SELECT title FROM books WHERE id = NEW.book_id),
                           NEW.category,
                           NEW.content;
                END;
            """)

        if "fts_notes_update" not in existing:
            self.conn.execute("""
                CREATE TRIGGER fts_notes_update AFTER UPDATE ON notes
                BEGIN
                    DELETE FROM fts_notes WHERE rowid = OLD.id;
                    INSERT INTO fts_notes(rowid, book_title, category, content)
                    SELECT NEW.id,
                           (SELECT title FROM books WHERE id = NEW.book_id),
                           NEW.category,
                           NEW.content;
                END;
            """)

        if "fts_notes_delete" not in existing:
            self.conn.execute("""
                CREATE TRIGGER fts_notes_delete AFTER DELETE ON notes
                BEGIN
                    DELETE FROM fts_notes WHERE rowid = OLD.id;
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

    # -- Note CRUD --

    def create_note(self, book_id: int, category: str, content: str) -> Note:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO notes (book_id, category, content, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (book_id, category, content, now, now),
        )
        self.conn.commit()
        return Note(
            id=cursor.lastrowid, book_id=book_id, category=category,
            content=content, created_at=now, updated_at=now,
        )

    def list_notes(self, book_id: int, category: str | None = None) -> list[Note]:
        sql = (
            "SELECT id, book_id, category, content, created_at, updated_at "
            "FROM notes WHERE book_id = ?"
        )
        params: list = [book_id]
        if category is not None:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        return [Note(id=r[0], book_id=r[1], category=r[2], content=r[3],
                     created_at=r[4], updated_at=r[5]) for r in rows]

    def get_note(self, note_id: int) -> Note | None:
        row = self.conn.execute(
            "SELECT id, book_id, category, content, created_at, updated_at "
            "FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
        if row is None:
            return None
        return Note(id=row[0], book_id=row[1], category=row[2], content=row[3],
                    created_at=row[4], updated_at=row[5])

    def update_note(self, note_id: int, category: str | None = None, content: str | None = None) -> None:
        now = _now()
        note = self.get_note(note_id)
        if note is None:
            return
        new_category = category if category is not None else note.category
        new_content = content if content is not None else note.content
        self.conn.execute(
            "UPDATE notes SET category = ?, content = ?, updated_at = ? WHERE id = ?",
            (new_category, new_content, now, note_id),
        )
        self.conn.commit()

    def delete_note(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    # -- Search --

    def search(
        self,
        query: str,
        title_only: bool = False,
        book_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[SearchResult]:
        if title_only:
            fts_query = f'chapter_title:{query}'
        else:
            fts_query = query

        sql = """
            SELECT
                c.book_id,
                b.title,
                c.id,
                c.title,
                snippet(fts_chapters, 2, '>>>', '<<<', '...', 32),
                c.created_at
            FROM fts_chapters fts
            JOIN chapters c ON c.id = fts.rowid
            JOIN books b ON b.id = c.book_id
            WHERE fts_chapters MATCH ?
        """
        params: list = [fts_query]

        if book_id is not None:
            sql += " AND c.book_id = ?"
            params.append(book_id)
        if date_from is not None:
            sql += " AND c.created_at >= ?"
            params.append(date_from)
        if date_to is not None:
            sql += " AND c.created_at <= ?"
            params.append(date_to)

        sql += " ORDER BY rank"

        rows = self.conn.execute(sql, params).fetchall()
        results = [
            SearchResult(
                book_id=r[0], book_title=r[1], chapter_id=r[2],
                chapter_title=r[3], snippet=r[4], created_at=r[5],
                kind="chapter", category=None,
            )
            for r in rows
        ]

        if title_only:
            return results

        results.extend(self._search_notes(query, book_id, date_from, date_to))
        return results

    def _search_notes(
        self,
        query: str,
        book_id: int | None,
        date_from: str | None,
        date_to: str | None,
    ) -> list[SearchResult]:
        sql = """
            SELECT
                n.book_id,
                b.title,
                n.id,
                n.content,
                n.category,
                snippet(fts_notes, 2, '>>>', '<<<', '...', 32),
                n.created_at
            FROM fts_notes fts
            JOIN notes n ON n.id = fts.rowid
            JOIN books b ON b.id = n.book_id
            WHERE fts_notes MATCH ?
        """
        params: list = [query]

        if book_id is not None:
            sql += " AND n.book_id = ?"
            params.append(book_id)
        if date_from is not None:
            sql += " AND n.created_at >= ?"
            params.append(date_from)
        if date_to is not None:
            sql += " AND n.created_at <= ?"
            params.append(date_to)

        sql += " ORDER BY rank"

        rows = self.conn.execute(sql, params).fetchall()
        return [
            SearchResult(
                book_id=r[0], book_title=r[1], chapter_id=r[2],
                chapter_title=Note(r[2], r[0], r[4], r[3], "", "").label,
                snippet=r[5], created_at=r[6],
                kind="note", category=r[4],
            )
            for r in rows
        ]
