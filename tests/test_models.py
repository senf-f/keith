from datetime import datetime

from keith.models import Book, Chapter, Note, SearchResult


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


def _note(content: str) -> Note:
    return Note(
        id=1,
        book_id=1,
        category="character",
        content=content,
        created_at="2026-06-29T10:00:00",
        updated_at="2026-06-29T10:00:00",
    )


def test_note_creation():
    note = _note("Gandalf\nthe grey wizard")
    assert note.id == 1
    assert note.book_id == 1
    assert note.category == "character"
    assert note.content == "Gandalf\nthe grey wizard"


def test_note_label_first_nonempty_line():
    assert _note("Gandalf, the grey wizard").label == "Gandalf, the grey wizard"


def test_note_label_skips_leading_blank_lines():
    assert _note("\n\n  Gandalf  \nmore text").label == "Gandalf"


def test_note_label_truncates_long_line():
    long_line = "x" * 80
    label = _note(long_line).label
    assert len(label) == 60
    assert label.endswith("...")
    assert label[:57] == "x" * 57


def test_note_label_empty_content():
    assert _note("").label == "(empty)"
    assert _note("   \n  ").label == "(empty)"


def test_search_result_defaults_to_chapter():
    result = SearchResult(
        book_id=1,
        book_title="Book",
        chapter_id=2,
        chapter_title="Ch",
        snippet="snip",
        created_at="2026-06-29T10:00:00",
    )
    assert result.kind == "chapter"
    assert result.category is None


def test_search_result_note_kind():
    result = SearchResult(
        book_id=1,
        book_title="Book",
        chapter_id=2,
        chapter_title="Gandalf",
        snippet="snip",
        created_at="2026-06-29T10:00:00",
        kind="note",
        category="character",
    )
    assert result.kind == "note"
    assert result.category == "character"
