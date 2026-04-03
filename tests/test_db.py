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
