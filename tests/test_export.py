import os
import tempfile

import pytest

from keith.db import Database
from keith.export import export_book_to_markdown, slugify


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    os.unlink(path)


def test_slugify():
    assert slugify("The Man Who Was Thursday") == "the-man-who-was-thursday"
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  Spaces  Everywhere  ") == "spaces-everywhere"


def test_export_basic(db):
    book = db.create_book("Test Book")
    db.create_chapter(book.id, "First Chapter", "Content of first chapter.")
    db.create_chapter(book.id, "Second Chapter", "Content of second chapter.")

    md = export_book_to_markdown(db, book.id)

    assert "# Test Book" in md
    assert "## Table of Contents" in md
    assert "1. [First Chapter]" in md
    assert "2. [Second Chapter]" in md
    assert "## Chapter 1: First Chapter" in md
    assert "Content of first chapter." in md
    assert "## Chapter 2: Second Chapter" in md
    assert "Content of second chapter." in md


def test_export_empty_book(db):
    book = db.create_book("Empty Book")
    md = export_book_to_markdown(db, book.id)
    assert "# Empty Book" in md
    assert "## Table of Contents" in md


def test_export_preserves_chapter_order(db):
    book = db.create_book("Ordered")
    db.create_chapter(book.id, "Ch A", "A")
    db.create_chapter(book.id, "Ch B", "B")
    db.create_chapter(book.id, "Ch C", "C")

    md = export_book_to_markdown(db, book.id)
    pos_a = md.index("Ch A")
    pos_b = md.index("Ch B")
    pos_c = md.index("Ch C")
    assert pos_a < pos_b < pos_c
