import os
import tempfile

import pytest

from keith.db import Database


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    os.unlink(path)


def test_create_note(db):
    book = db.create_book("Novel")
    note = db.create_note(book.id, "character", "Gandalf\nGrey wizard")
    assert note.id == 1
    assert note.book_id == book.id
    assert note.category == "character"
    assert note.content == "Gandalf\nGrey wizard"
    assert note.created_at is not None
    assert note.updated_at is not None


def test_list_notes(db):
    book = db.create_book("Novel")
    db.create_note(book.id, "idea", "Twist ending")
    db.create_note(book.id, "character", "Gandalf")
    notes = db.list_notes(book.id)
    assert len(notes) == 2


def test_list_notes_filter_by_category(db):
    book = db.create_book("Novel")
    db.create_note(book.id, "idea", "Twist ending")
    db.create_note(book.id, "character", "Gandalf")
    db.create_note(book.id, "character", "Frodo")
    characters = db.list_notes(book.id, category="character")
    assert len(characters) == 2
    assert {n.content for n in characters} == {"Gandalf", "Frodo"}


def test_list_notes_scoped_to_book(db):
    book1 = db.create_book("Book One")
    book2 = db.create_book("Book Two")
    db.create_note(book1.id, "idea", "Idea for one")
    assert len(db.list_notes(book2.id)) == 0


def test_get_note(db):
    book = db.create_book("Novel")
    created = db.create_note(book.id, "place", "The Shire")
    note = db.get_note(created.id)
    assert note is not None
    assert note.content == "The Shire"


def test_get_note_not_found(db):
    assert db.get_note(999) is None


def test_update_note(db):
    book = db.create_book("Novel")
    note = db.create_note(book.id, "idea", "Old idea")
    db.update_note(note.id, content="New idea")
    updated = db.get_note(note.id)
    assert updated.content == "New idea"
    assert updated.updated_at > note.updated_at


def test_delete_note(db):
    book = db.create_book("Novel")
    note = db.create_note(book.id, "idea", "Disposable")
    db.delete_note(note.id)
    assert db.get_note(note.id) is None


def test_cascade_delete_notes(db):
    book = db.create_book("Novel")
    db.create_note(book.id, "idea", "Some idea")
    db.delete_book(book.id)
    assert len(db.list_notes(book.id)) == 0
