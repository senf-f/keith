import os
import tempfile

import pytest

from keith.db import Database
from keith.models import Book


@pytest.fixture
def tmp_path_factory_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    os.unlink(path)


def test_create_book(db):
    book = db.create_book("My Novel")
    assert book.id == 1
    assert book.title == "My Novel"
    assert book.created_at is not None
    assert book.updated_at is not None


def test_list_books(db):
    db.create_book("Book A")
    db.create_book("Book B")
    books = db.list_books()
    assert len(books) == 2
    assert books[0].title == "Book A"
    assert books[1].title == "Book B"


def test_get_book(db):
    created = db.create_book("My Novel")
    book = db.get_book(created.id)
    assert book is not None
    assert book.title == "My Novel"


def test_get_book_not_found(db):
    book = db.get_book(999)
    assert book is None


def test_delete_book(db):
    book = db.create_book("To Delete")
    db.delete_book(book.id)
    assert db.get_book(book.id) is None


def test_create_chapter(db):
    book = db.create_book("Novel")
    chapter = db.create_chapter(book.id, "Chapter 1", "Once upon a time...")
    assert chapter.id == 1
    assert chapter.book_id == book.id
    assert chapter.title == "Chapter 1"
    assert chapter.content == "Once upon a time..."
    assert chapter.position == 1


def test_create_multiple_chapters_auto_position(db):
    book = db.create_book("Novel")
    ch1 = db.create_chapter(book.id, "Ch 1", "Text 1")
    ch2 = db.create_chapter(book.id, "Ch 2", "Text 2")
    assert ch1.position == 1
    assert ch2.position == 2


def test_list_chapters(db):
    book = db.create_book("Novel")
    db.create_chapter(book.id, "Ch 1", "Text 1")
    db.create_chapter(book.id, "Ch 2", "Text 2")
    chapters = db.list_chapters(book.id)
    assert len(chapters) == 2
    assert chapters[0].title == "Ch 1"
    assert chapters[1].title == "Ch 2"


def test_get_chapter(db):
    book = db.create_book("Novel")
    created = db.create_chapter(book.id, "Ch 1", "Text")
    chapter = db.get_chapter(created.id)
    assert chapter is not None
    assert chapter.title == "Ch 1"


def test_update_chapter(db):
    book = db.create_book("Novel")
    ch = db.create_chapter(book.id, "Ch 1", "Old text")
    db.update_chapter(ch.id, title="Chapter One", content="New text")
    updated = db.get_chapter(ch.id)
    assert updated.title == "Chapter One"
    assert updated.content == "New text"
    assert updated.updated_at > ch.updated_at


def test_move_chapter(db):
    book = db.create_book("Novel")
    ch1 = db.create_chapter(book.id, "Ch 1", "")
    ch2 = db.create_chapter(book.id, "Ch 2", "")
    ch3 = db.create_chapter(book.id, "Ch 3", "")
    db.move_chapter(ch3.id, new_position=1)
    chapters = db.list_chapters(book.id)
    assert [c.title for c in chapters] == ["Ch 3", "Ch 1", "Ch 2"]


def test_delete_chapter(db):
    book = db.create_book("Novel")
    ch = db.create_chapter(book.id, "Ch 1", "Text")
    db.delete_chapter(ch.id)
    assert db.get_chapter(ch.id) is None


def test_cascade_delete_chapters(db):
    book = db.create_book("Novel")
    db.create_chapter(book.id, "Ch 1", "Text")
    db.delete_book(book.id)
    chapters = db.list_chapters(book.id)
    assert len(chapters) == 0


def test_chapter_count(db):
    book = db.create_book("Novel")
    db.create_chapter(book.id, "Ch 1", "")
    db.create_chapter(book.id, "Ch 2", "")
    assert db.chapter_count(book.id) == 2


# -- Backup / restore --


def test_backup_creates_file(db, tmp_path_factory_db):
    db.create_book("Novel")
    db.backup(tmp_path_factory_db)
    assert os.path.exists(tmp_path_factory_db)
    assert os.path.getsize(tmp_path_factory_db) > 0


def test_backup_contains_data(db, tmp_path_factory_db):
    book = db.create_book("Backed Up")
    db.create_chapter(book.id, "Ch 1", "Some content")
    db.create_note(book.id, "idea", "A note")
    db.backup(tmp_path_factory_db)

    copy = Database(tmp_path_factory_db)
    books = copy.list_books()
    assert len(books) == 1
    assert books[0].title == "Backed Up"
    chapters = copy.list_chapters(books[0].id)
    assert len(chapters) == 1
    assert chapters[0].content == "Some content"
    notes = copy.list_notes(books[0].id)
    assert len(notes) == 1
    assert notes[0].content == "A note"
    copy.close()


def test_backup_is_consistent_snapshot_not_live_link(db, tmp_path_factory_db):
    db.create_book("First")
    db.backup(tmp_path_factory_db)
    db.create_book("Second")

    copy = Database(tmp_path_factory_db)
    titles = [b.title for b in copy.list_books()]
    assert titles == ["First"]
    copy.close()


def test_restore_replaces_data(db, tmp_path_factory_db):
    original = db.create_book("Original")
    db.backup(tmp_path_factory_db)

    db.delete_book(original.id)
    db.create_book("Replacement")
    assert [b.title for b in db.list_books()] == ["Replacement"]

    db.restore(tmp_path_factory_db)
    assert [b.title for b in db.list_books()] == ["Original"]


def test_restore_search_works_after(db, tmp_path_factory_db):
    book = db.create_book("Searchable")
    db.create_chapter(book.id, "Ch 1", "findme keyword here")
    db.backup(tmp_path_factory_db)
    db.delete_book(book.id)

    db.restore(tmp_path_factory_db)
    results = db.search("findme")
    assert len(results) == 1
    assert results[0].book_title == "Searchable"


def test_backup_roundtrip_preserves_chapter_order(db, tmp_path_factory_db):
    book = db.create_book("Novel")
    db.create_chapter(book.id, "Ch 1", "")
    db.create_chapter(book.id, "Ch 2", "")
    db.create_chapter(book.id, "Ch 3", "")
    db.backup(tmp_path_factory_db)

    copy = Database(tmp_path_factory_db)
    titles = [c.title for c in copy.list_chapters(book.id)]
    assert titles == ["Ch 1", "Ch 2", "Ch 3"]
    copy.close()


def test_keith_db_env_overrides_default_path(tmp_path_factory_db, monkeypatch):
    monkeypatch.setenv("KEITH_DB", tmp_path_factory_db)
    database = Database()
    database.create_book("Env Book")
    database.close()

    assert os.path.getsize(tmp_path_factory_db) > 0
    reopened = Database(tmp_path_factory_db)
    assert [b.title for b in reopened.list_books()] == ["Env Book"]
    reopened.close()


def test_close_checkpoints_wal_into_main_db(tmp_path_factory_db):
    database = Database(tmp_path_factory_db)
    database.create_book("Persisted")
    database.close()
    # TRUNCATE checkpoint folds the WAL back in, so the sidecar is empty/absent
    # and the .db alone is safe to file-sync.
    wal = tmp_path_factory_db + "-wal"
    assert not os.path.exists(wal) or os.path.getsize(wal) == 0
