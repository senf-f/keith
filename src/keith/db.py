import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from keith.models import Book, Chapter, Note, SearchResult, note_label


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


# ponytail: OneDrive names conflicts "<stem>-<MACHINE>.db", which can't be told
# apart from a backup file — those go undetected. Add if OneDrive is ever used.
CONFLICT_MARKERS = ("sync-conflict-", "conflicted copy")


def db_path() -> Path:
    env_path = os.environ.get("KEITH_DB")
    if env_path:
        path = Path(env_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    db_dir = Path.home() / ".keith"
    db_dir.mkdir(exist_ok=True)
    return db_dir / "keith.db"


def sync_conflicts(db_file: str | Path) -> list[Path]:
    """Copies a file-sync tool parked beside the database after a losing write."""
    db_file = Path(db_file)
    # Sync tools keep the original stem and extension, so an unrelated
    # "notes (conflicted copy).txt" in the same folder isn't ours.
    return sorted(
        p for p in db_file.parent.iterdir()
        if p != db_file
        and p.name.startswith(db_file.stem)
        and p.suffix == db_file.suffix
        and any(m in p.name for m in CONFLICT_MARKERS)
    )


def _fts_phrase(query: str) -> str:
    """Quote each word so FTS5 matches it literally instead of parsing it as
    syntax — otherwise "self-help" or "don't" raise an OperationalError."""
    return " ".join('"' + word.replace('"', '""') + '"' for word in query.split())


def _scope(book_id: int | None, date_from: str | None, date_to: str | None) -> tuple[str, list]:
    """WHERE clauses narrowing a search; the queries alias chapters and notes as `item`."""
    sql, params = "", []
    if book_id is not None:
        sql += " AND item.book_id = ?"
        params.append(book_id)
    # Compare only as many characters as the user typed, so "--to 2026-04-03"
    # includes the whole of that day rather than stopping at its midnight.
    if date_from is not None:
        sql += " AND substr(item.created_at, 1, ?) >= ?"
        params += [len(date_from), date_from]
    if date_to is not None:
        sql += " AND substr(item.created_at, 1, ?) <= ?"
        params += [len(date_to), date_to]
    return sql, params


INBOX_TITLE = "Inbox"

# Column lists in dataclass field order, so a row unpacks straight into the model.
BOOK_COLUMNS = "id, title, created_at, updated_at, status"
CHAPTER_COLUMNS = "id, book_id, title, content, position, created_at, updated_at"
NOTE_COLUMNS = "id, book_id, category, content, created_at, updated_at"

# Chapters and notes are mirrored into FTS5 tables, with the book's title copied
# in so searching for it finds the book's text. Per table: the FTS table, its
# middle column, and the source column that fills it.
FTS_MIRRORS = {
    "chapters": ("fts_chapters", "chapter_title", "title"),
    "notes": ("fts_notes", "category", "category"),
}


class Database:
    def __init__(self, db_path_override: str | Path | None = None):
        self.path = Path(db_path_override) if db_path_override is not None else db_path()
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft'
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

            CREATE TABLE IF NOT EXISTS imports (
                source      TEXT NOT NULL,
                key         TEXT NOT NULL,
                note_id     INTEGER,
                imported_at TEXT NOT NULL,
                PRIMARY KEY (source, key)
            );
        """)
        self._add_missing_columns()
        self._create_triggers()
        self.conn.commit()

    def _add_missing_columns(self):
        # CREATE TABLE IF NOT EXISTS leaves existing tables alone, so databases
        # made before a column was introduced need it added explicitly.
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(books)")}
        if "status" not in columns:
            self.conn.execute(
                "ALTER TABLE books ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'"
            )

    def _create_triggers(self):
        existing = {row[0] for row in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()}

        for table, (fts, fts_column, source_column) in FTS_MIRRORS.items():
            insert = (
                f"INSERT INTO {fts}(rowid, book_title, {fts_column}, content) "
                f"SELECT NEW.id, (SELECT title FROM books WHERE id = NEW.book_id), "
                f"NEW.{source_column}, NEW.content;"
            )
            delete = f"DELETE FROM {fts} WHERE rowid = OLD.id;"
            bodies = {"insert": insert, "update": f"{delete} {insert}", "delete": delete}
            for event, body in bodies.items():
                name = f"{fts}_{event}"
                if name not in existing:
                    self.conn.execute(
                        f"CREATE TRIGGER {name} AFTER {event.upper()} ON {table} "
                        f"BEGIN {body} END;"
                    )

    def close(self):
        # Fold the WAL back into the .db so the file is self-contained —
        # safe to sync via Dropbox/iCloud/Syncthing without losing recent writes.
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.conn.close()

    # -- Backup / restore --

    def backup(self, dest_path: str | Path) -> None:
        dest = sqlite3.connect(str(dest_path))
        try:
            self.conn.backup(dest)
        finally:
            dest.close()

    def restore(self, src_path: str | Path) -> None:
        src = sqlite3.connect(str(src_path))
        try:
            src.backup(self.conn)
        finally:
            src.close()
        self.conn.commit()
        # A backup from before a table/column existed lacks it; add it back.
        self._create_schema()

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
        rows = self.conn.execute(f"SELECT {BOOK_COLUMNS} FROM books ORDER BY id").fetchall()
        return [Book(*r) for r in rows]

    def get_book(self, book_id: int) -> Book | None:
        row = self.conn.execute(
            f"SELECT {BOOK_COLUMNS} FROM books WHERE id = ?", (book_id,),
        ).fetchone()
        return Book(*row) if row else None

    def set_status(self, book_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE books SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), book_id),
        )
        self.conn.commit()

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
            f"SELECT {CHAPTER_COLUMNS} FROM chapters WHERE book_id = ? ORDER BY position",
            (book_id,),
        ).fetchall()
        return [Chapter(*r) for r in rows]

    def get_chapter(self, chapter_id: int) -> Chapter | None:
        row = self.conn.execute(
            f"SELECT {CHAPTER_COLUMNS} FROM chapters WHERE id = ?", (chapter_id,),
        ).fetchone()
        return Chapter(*row) if row else None

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
        chapter = self.get_chapter(chapter_id)
        if chapter is None:
            return
        self.conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
        # Close the gap so positions stay 1..N.
        self.conn.execute(
            "UPDATE chapters SET position = position - 1 "
            "WHERE book_id = ? AND position > ?",
            (chapter.book_id, chapter.position),
        )
        self.conn.commit()

    def chapter_count(self, book_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM chapters WHERE book_id = ?", (book_id,),
        ).fetchone()
        return row[0]

    # -- Note CRUD --

    def create_note(
        self, book_id: int, category: str, content: str, created_at: str | None = None,
    ) -> Note:
        note = self._insert_note(book_id, category, content, created_at)
        self.conn.commit()
        return note

    def _insert_note(
        self, book_id: int, category: str, content: str, created_at: str | None,
    ) -> Note:
        """Insert without committing, so callers can bundle it with other writes."""
        created = created_at if created_at is not None else _now()
        cursor = self.conn.execute(
            "INSERT INTO notes (book_id, category, content, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (book_id, category, content, created, created),
        )
        return Note(
            id=cursor.lastrowid, book_id=book_id, category=category,
            content=content, created_at=created, updated_at=created,
        )

    def is_imported(self, source: str, key: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM imports WHERE source = ? AND key = ?", (source, key),
        ).fetchone()
        return row is not None

    def create_imported_note(
        self, source: str, key: str, book_id: int, category: str, content: str,
        created_at: str,
    ) -> Note:
        # One transaction: the note and its imports row both persist, or neither.
        with self.conn:
            note = self._insert_note(book_id, category, content, created_at)
            self.conn.execute(
                "INSERT INTO imports (source, key, note_id, imported_at) VALUES (?, ?, ?, ?)",
                (source, key, note.id, _now()),
            )
        return note

    def move_note(self, note_id: int, book_id: int) -> None:
        # The fts_notes_update trigger re-reads the book title from NEW.book_id.
        self.conn.execute(
            "UPDATE notes SET book_id = ?, updated_at = ? WHERE id = ?",
            (book_id, _now(), note_id),
        )
        self.conn.commit()

    def get_or_create_inbox(self) -> Book:
        row = self.conn.execute(
            f"SELECT {BOOK_COLUMNS} FROM books WHERE title = ? ORDER BY id LIMIT 1",
            (INBOX_TITLE,),
        ).fetchone()
        return Book(*row) if row else self.create_book(INBOX_TITLE)

    def list_notes(self, book_id: int, category: str | None = None) -> list[Note]:
        sql = f"SELECT {NOTE_COLUMNS} FROM notes WHERE book_id = ?"
        params: list = [book_id]
        if category is not None:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        return [Note(*r) for r in rows]

    def get_note(self, note_id: int) -> Note | None:
        row = self.conn.execute(
            f"SELECT {NOTE_COLUMNS} FROM notes WHERE id = ?", (note_id,),
        ).fetchone()
        return Note(*row) if row else None

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
        match = _fts_phrase(query)
        scope = _scope(book_id, date_from, date_to)
        if title_only:
            return self._search_chapters(f"chapter_title : ({match})", scope)
        return self._search_chapters(match, scope) + self._search_notes(match, scope)

    def _search_chapters(self, match: str, scope: tuple[str, list]) -> list[SearchResult]:
        scope_sql, scope_params = scope
        rows = self.conn.execute(f"""
            SELECT
                item.book_id,
                b.title,
                item.id,
                item.title,
                snippet(fts_chapters, 2, '>>>', '<<<', '...', 32),
                item.created_at
            FROM fts_chapters fts
            JOIN chapters item ON item.id = fts.rowid
            JOIN books b ON b.id = item.book_id
            WHERE fts_chapters MATCH ? {scope_sql}
            ORDER BY rank
        """, [match, *scope_params]).fetchall()
        return [
            SearchResult(
                book_id=r[0], book_title=r[1], item_id=r[2], title=r[3],
                snippet=r[4], created_at=r[5], kind="chapter",
            )
            for r in rows
        ]

    def _search_notes(self, match: str, scope: tuple[str, list]) -> list[SearchResult]:
        scope_sql, scope_params = scope
        rows = self.conn.execute(f"""
            SELECT
                item.book_id,
                b.title,
                item.id,
                item.content,
                item.category,
                snippet(fts_notes, 2, '>>>', '<<<', '...', 32),
                item.created_at
            FROM fts_notes fts
            JOIN notes item ON item.id = fts.rowid
            JOIN books b ON b.id = item.book_id
            WHERE fts_notes MATCH ? {scope_sql}
            ORDER BY rank
        """, [match, *scope_params]).fetchall()
        return [
            SearchResult(
                book_id=r[0], book_title=r[1], item_id=r[2], title=note_label(r[3]),
                snippet=r[5], created_at=r[6], kind="note", category=r[4],
            )
            for r in rows
        ]
