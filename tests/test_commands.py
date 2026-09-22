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


def test_article_new_creates_a_book_holding_one_chapter(handler):
    with patch("builtins.input", return_value="On Cheese"), \
         patch("keith.commands.open_editor", return_value="Poets have been silent."):
        handler.article_new()

    books = handler.db.list_books()
    assert [b.title for b in books] == ["On Cheese"]
    chapters = handler.db.list_chapters(books[0].id)
    assert len(chapters) == 1
    assert chapters[0].title == "On Cheese"
    assert chapters[0].content == "Poets have been silent."
    assert handler.active_book.id == books[0].id


def test_article_new_writes_nothing_when_the_editor_fails(handler, capsys):
    with patch("builtins.input", return_value="Doomed"), \
         patch("keith.commands.open_editor", return_value=None):
        handler.article_new()

    assert handler.db.list_books() == []
    assert "Editor failed" in capsys.readouterr().out


def test_publish_and_unpublish(handler):
    book = handler.db.create_book("Post")
    handler.active_book = book
    handler.publish()
    assert handler.db.get_book(book.id).status == "published"
    handler.unpublish()
    assert handler.db.get_book(book.id).status == "draft"


def test_publish_requires_an_active_book(handler, capsys):
    handler.publish()
    assert "No book selected" in capsys.readouterr().out


def test_book_list_marks_drafts(handler, capsys):
    handler.db.create_book("Unfinished")
    done = handler.db.create_book("Out The Door")
    handler.db.set_status(done.id, "published")

    handler.book_list()
    out = capsys.readouterr().out

    unfinished_line = next(ln for ln in out.splitlines() if "Unfinished" in ln)
    done_line = next(ln for ln in out.splitlines() if "Out The Door" in ln)
    assert "draft" in unfinished_line
    assert "draft" not in done_line


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


def test_stats_no_active_book(handler, capsys):
    handler.stats()
    out = capsys.readouterr().out
    assert "No book selected" in out


def test_stats_no_chapters(handler, capsys):
    book = handler.db.create_book("Empty Book")
    handler.active_book = book
    handler.stats()
    out = capsys.readouterr().out
    assert "No chapters yet." in out


def test_stats_multiple_chapters(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Ch 1", "one two three four five")
    handler.db.create_chapter(book.id, "Ch 2", "one two three")
    handler.db.create_chapter(book.id, "Ch 3", "one two")
    handler.stats()
    out = capsys.readouterr().out
    assert "Ch 1" in out
    assert "5 words" in out
    assert "(50%)" in out
    assert "Ch 2" in out
    assert "3 words" in out
    assert "(30%)" in out
    assert "Ch 3" in out
    assert "2 words" in out
    assert "(20%)" in out
    assert "10 words" in out


def test_stats_empty_content(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Empty Chapter", "")
    handler.db.create_chapter(book.id, "Has Words", "hello world")
    handler.stats()
    out = capsys.readouterr().out
    assert "0 words" in out
    assert "2 words" in out
    assert "(0%)" in out
    assert "(100%)" in out


def test_stats_single_chapter(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Only Chapter", "word word word")
    handler.stats()
    out = capsys.readouterr().out
    assert "Only Chapter" in out
    assert "3 words" in out
    assert "(100%)" in out


# -- Note commands --


def test_note_new_no_active_book(handler, capsys):
    handler.note_new()
    out = capsys.readouterr().out
    assert "No book selected" in out


def test_note_new(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    with patch("builtins.input", return_value="character"):
        with patch("keith.commands.open_editor", return_value="Gandalf\nGrey wizard"):
            handler.note_new()
    notes = handler.db.list_notes(book.id)
    assert len(notes) == 1
    assert notes[0].category == "character"
    assert notes[0].content == "Gandalf\nGrey wizard"


def test_note_new_invalid_category(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    with patch("builtins.input", return_value="banana"):
        handler.note_new()
    out = capsys.readouterr().out
    assert "Unknown category" in out
    assert len(handler.db.list_notes(book.id)) == 0


def test_note_new_empty_body_declined(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    with patch("builtins.input", side_effect=["idea", "n"]):
        with patch("keith.commands.open_editor", return_value="   "):
            handler.note_new()
    assert len(handler.db.list_notes(book.id)) == 0


def test_note_list_empty(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.note_list("")
    out = capsys.readouterr().out
    assert "No notes yet." in out


def test_note_list_groups_by_category(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_note(book.id, "idea", "Twist ending")
    handler.db.create_note(book.id, "character", "Gandalf the grey")
    handler.note_list("")
    out = capsys.readouterr().out
    assert "idea" in out
    assert "Twist ending" in out
    assert "character" in out
    assert "Gandalf the grey" in out


def test_note_list_filter_by_category(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_note(book.id, "idea", "Twist ending")
    handler.db.create_note(book.id, "character", "Gandalf")
    handler.note_list("character")
    out = capsys.readouterr().out
    assert "Gandalf" in out
    assert "Twist ending" not in out


def test_note_list_filter_no_matches(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_note(book.id, "idea", "Twist ending")
    handler.note_list("place")
    out = capsys.readouterr().out
    assert "No notes in 'place'." in out


def test_note_show(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_note(book.id, "place", "The Shire\nGreen and pleasant")
    with patch("builtins.input", return_value="1"):
        handler.note_show()
    out = capsys.readouterr().out
    assert "Green and pleasant" in out


def test_note_edit(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    note = handler.db.create_note(book.id, "idea", "Old idea")
    with patch("builtins.input", return_value="1"):
        with patch("keith.commands.open_editor", return_value="New idea"):
            handler.note_edit()
    assert handler.db.get_note(note.id).content == "New idea"


def test_note_delete(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    note = handler.db.create_note(book.id, "idea", "Disposable")
    with patch("builtins.input", side_effect=["1", "y"]):
        handler.note_delete()
    assert handler.db.get_note(note.id) is None


def test_note_delete_cancelled(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    note = handler.db.create_note(book.id, "idea", "Keep me")
    with patch("builtins.input", side_effect=["1", "n"]):
        handler.note_delete()
    assert handler.db.get_note(note.id) is not None


def test_search_prints_note_marker(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_note(book.id, "character", "Gandalf the grey wizard")
    handler.handle_search("Gandalf")
    out = capsys.readouterr().out
    assert "note:character" in out
    assert "Gandalf the grey wizard" in out


# -- Backup / restore commands --


def test_backup_writes_file(handler, capsys, tmp_path):
    handler.db.create_book("Novel")
    dest = str(tmp_path / "keith-backup.db")
    with patch("builtins.input", return_value=dest):
        handler.backup()
    assert os.path.exists(dest)
    out = capsys.readouterr().out
    assert dest in out


def test_backup_empty_path_cancels(handler, capsys):
    handler.db.create_book("Novel")
    with patch("builtins.input", return_value=""):
        handler.backup()
    out = capsys.readouterr().out
    assert "Cancelled" in out


def test_restore_replaces_data(handler, capsys, tmp_path):
    original = handler.db.create_book("Original")
    src = str(tmp_path / "snap.db")
    handler.db.backup(src)
    handler.db.delete_book(original.id)
    handler.db.create_book("Replacement")

    with patch("builtins.input", side_effect=[src, "y"]):
        handler.restore()
    assert [b.title for b in handler.db.list_books()] == ["Original"]


def test_restore_cancelled_when_declined(handler, capsys, tmp_path):
    handler.db.create_book("Current")
    src = str(tmp_path / "snap.db")
    handler.db.backup(src)
    handler.db.create_book("Extra")

    with patch("builtins.input", side_effect=[src, "n"]):
        handler.restore()
    out = capsys.readouterr().out
    assert "Cancelled" in out
    assert [b.title for b in handler.db.list_books()] == ["Current", "Extra"]


def test_restore_missing_file(handler, capsys, tmp_path):
    handler.db.create_book("Current")
    missing = str(tmp_path / "does-not-exist.db")
    with patch("builtins.input", return_value=missing):
        handler.restore()
    out = capsys.readouterr().out
    assert "not found" in out.lower()
    assert [b.title for b in handler.db.list_books()] == ["Current"]
