import os
import tempfile
from unittest.mock import patch

import pytest

from keith.commands import CommandHandler
from keith.db import Database


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    os.unlink(path)


@pytest.fixture
def handler(db):
    return CommandHandler(db)


def test_book_new(handler, capsys):
    with patch("builtins.input", return_value="My Novel"):
        handler.book_new()
    assert handler.db.list_books()[0].title == "My Novel"


def test_book_list(handler, capsys):
    handler.db.create_book("Book A")
    handler.db.create_book("Book B")
    handler.book_list()
    out = capsys.readouterr().out
    assert "Book A" in out
    assert "Book B" in out


def test_book_select(handler):
    handler.db.create_book("Novel")
    with patch("builtins.input", return_value="1"):
        handler.book_select()
    assert handler.active_book is not None
    assert handler.active_book.title == "Novel"


def test_book_info_no_active(handler, capsys):
    handler.book_info()
    out = capsys.readouterr().out
    assert "No book selected" in out


def test_book_info(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Ch 1", "text")
    handler.book_info()
    out = capsys.readouterr().out
    assert "Novel" in out
    assert "1" in out  # chapter count


def test_book_delete(handler):
    book = handler.db.create_book("To Delete")
    handler.active_book = book
    with patch("builtins.input", return_value="y"):
        handler.book_delete()
    assert handler.db.get_book(book.id) is None
    assert handler.active_book is None


def test_add_chapter(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    with patch("builtins.input", return_value="Chapter One"):
        with patch("keith.commands.open_editor", return_value="Chapter content"):
            handler.add_chapter()
    chapters = handler.db.list_chapters(book.id)
    assert len(chapters) == 1
    assert chapters[0].title == "Chapter One"
    assert chapters[0].content == "Chapter content"


def test_add_chapter_no_active_book(handler, capsys):
    handler.add_chapter()
    out = capsys.readouterr().out
    assert "No book selected" in out


def test_list_chapters(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Ch 1", "")
    handler.db.create_chapter(book.id, "Ch 2", "")
    handler.list_chapters()
    out = capsys.readouterr().out
    assert "Ch 1" in out
    assert "Ch 2" in out


def test_search(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.db.create_chapter(book.id, "Dawn", "The sun rose over the hills.")
    handler.handle_search("sun")
    out = capsys.readouterr().out
    assert "Dawn" in out
