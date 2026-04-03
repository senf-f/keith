from datetime import datetime

from keith.models import Book, Chapter


def test_book_creation():
    book = Book(id=1, title="Test Book", created_at="2026-04-03T10:00:00", updated_at="2026-04-03T10:00:00")
    assert book.id == 1
    assert book.title == "Test Book"
    assert book.created_at == "2026-04-03T10:00:00"


def test_chapter_creation():
    chapter = Chapter(
        id=1,
        book_id=1,
        title="Chapter One",
        content="Some text",
        position=1,
        created_at="2026-04-03T10:00:00",
        updated_at="2026-04-03T10:00:00",
    )
    assert chapter.id == 1
    assert chapter.book_id == 1
    assert chapter.title == "Chapter One"
    assert chapter.content == "Some text"
    assert chapter.position == 1
