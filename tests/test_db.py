import os
import tempfile

import pytest

from keith.db import Database
from keith.models import Book


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
