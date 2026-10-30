import sqlite3

import pytest


def test_create_note_keeps_given_date(db):
    book = db.create_book("Novel")
    note = db.create_note(book.id, "idea", "x", created_at="2026-01-02T03:04:05.000000+00:00")
    assert db.get_note(note.id).created_at == "2026-01-02T03:04:05.000000+00:00"


def test_imported_note_is_recorded(db):
    book = db.create_book("Novel")
    db.create_imported_note("telegram", "1:7", book.id, "idea", "x", "2026-01-02T00:00:00.000000+00:00")
    assert db.is_imported("telegram", "1:7")
    assert not db.is_imported("obsidian", "1:7")


def test_imported_note_is_atomic(db):
    book = db.create_book("Novel")
    db.create_imported_note("telegram", "1:7", book.id, "idea", "x", "2026-01-02T00:00:00.000000+00:00")
    with pytest.raises(sqlite3.IntegrityError):  # same (source, key) again
        db.create_imported_note("telegram", "1:7", book.id, "idea", "y", "2026-01-02T00:00:00.000000+00:00")
    assert [n.content for n in db.list_notes(book.id)] == ["x"]


def test_deleted_import_stays_recorded(db):
    book = db.create_book("Novel")
    note = db.create_imported_note("obsidian", "a.md", book.id, "idea", "x", "2026-01-02T00:00:00.000000+00:00")
    db.delete_note(note.id)
    assert db.is_imported("obsidian", "a.md")


def test_move_note_updates_search_by_book_title(db):
    old, new = db.create_book("Orthodoxy"), db.create_book("Heretics")
    note = db.create_note(old.id, "idea", "lantern")
    db.move_note(note.id, new.id)
    assert db.get_note(note.id).book_id == new.id
    assert len(db.search("Heretics")) == 1
    assert db.search("Orthodoxy") == []


def test_inbox_created_once_and_reuses_existing(db):
    first = db.get_or_create_inbox()
    assert first.title == "Inbox"
    assert db.get_or_create_inbox().id == first.id
    assert [b.title for b in db.list_books()].count("Inbox") == 1
