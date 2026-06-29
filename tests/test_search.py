import os
import tempfile

import pytest

from keith.db import Database, SearchResult


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    os.unlink(path)


@pytest.fixture
def populated_db(db):
    book1 = db.create_book("The Man Who Was Thursday")
    db.create_chapter(book1.id, "The Two Poets", "Syme walked through the park at dawn.")
    db.create_chapter(book1.id, "The Secret of Gabriel Syme", "Sunday was the president of the council.")
    book2 = db.create_book("Orthodoxy")
    db.create_chapter(book2.id, "Introduction", "This is a personal philosophy book.")
    return db


def test_search_by_content(populated_db):
    results = populated_db.search("park")
    assert len(results) == 1
    assert results[0].chapter_title == "The Two Poets"


def test_search_by_chapter_title(populated_db):
    results = populated_db.search("Gabriel")
    assert len(results) == 1
    assert results[0].chapter_title == "The Secret of Gabriel Syme"


def test_search_by_book_title(populated_db):
    results = populated_db.search("Thursday")
    assert len(results) == 2  # Both chapters in that book match via book_title


def test_search_no_results(populated_db):
    results = populated_db.search("nonexistent")
    assert len(results) == 0


def test_search_title_only(populated_db):
    results = populated_db.search("Syme", title_only=True)
    assert len(results) == 1
    assert results[0].chapter_title == "The Secret of Gabriel Syme"


def test_search_filter_by_book(populated_db):
    books = populated_db.list_books()
    orthodoxy_id = [b for b in books if b.title == "Orthodoxy"][0].id
    results = populated_db.search("philosophy", book_id=orthodoxy_id)
    assert len(results) == 1


def test_search_filter_by_date(populated_db):
    results = populated_db.search("park", date_from="2020-01-01", date_to="2099-12-31")
    assert len(results) == 1
    results = populated_db.search("park", date_from="2099-01-01")
    assert len(results) == 0


def test_search_finds_notes(populated_db):
    books = populated_db.list_books()
    book_id = [b for b in books if b.title == "Orthodoxy"][0].id
    populated_db.create_note(book_id, "character", "Gandalf the grey wizard")
    results = populated_db.search("Gandalf")
    assert len(results) == 1
    assert results[0].kind == "note"
    assert results[0].category == "character"
    assert results[0].chapter_title == "Gandalf the grey wizard"


def test_search_marks_chapters_as_chapter_kind(populated_db):
    results = populated_db.search("park")
    assert results[0].kind == "chapter"
    assert results[0].category is None


def test_search_returns_chapters_before_notes(populated_db):
    books = populated_db.list_books()
    book_id = books[0].id
    populated_db.create_note(book_id, "idea", "A clever park scheme")
    results = populated_db.search("park")
    kinds = [r.kind for r in results]
    assert kinds == ["chapter", "note"]


def test_search_title_only_skips_notes(populated_db):
    books = populated_db.list_books()
    book_id = books[0].id
    populated_db.create_note(book_id, "character", "Syme the detective")
    results = populated_db.search("Syme", title_only=True)
    assert all(r.kind == "chapter" for r in results)


def test_search_notes_filter_by_book(populated_db):
    books = populated_db.list_books()
    orthodoxy_id = [b for b in books if b.title == "Orthodoxy"][0].id
    thursday_id = [b for b in books if b.title == "The Man Who Was Thursday"][0].id
    populated_db.create_note(orthodoxy_id, "idea", "unique_marker_word")
    populated_db.create_note(thursday_id, "idea", "unique_marker_word")
    results = populated_db.search("unique_marker_word", book_id=orthodoxy_id)
    assert len(results) == 1
    assert results[0].book_id == orthodoxy_id
