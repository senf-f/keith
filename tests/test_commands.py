import os
from unittest.mock import patch

import pytest

from keith.commands import CommandHandler


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


def test_backup_and_restore_expand_home(handler, capsys, tmp_path):
    handler.db.create_book("Novel")
    home = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    with patch.dict(os.environ, home):
        with patch("builtins.input", return_value="~/snap.db"):
            handler.backup()
        assert (tmp_path / "snap.db").exists()
        with patch("builtins.input", side_effect=["~/snap.db", "y"]):
            handler.restore()
    assert "Restored" in capsys.readouterr().out


def test_search_unbalanced_quote_does_not_crash(handler, capsys):
    handler.handle_search('"unclosed')
    assert "Unbalanced quote" in capsys.readouterr().out


def test_search_non_numeric_book_id_does_not_crash(handler, capsys):
    handler.handle_search("--book abc park")
    assert "Invalid book id" in capsys.readouterr().out


def test_move_chapter_works_with_gapped_positions(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    ch1 = handler.db.create_chapter(book.id, "One", "")
    handler.db.create_chapter(book.id, "Two", "")
    # Simulate a database whose deletes left gaps: positions 2 and 3.
    handler.db.conn.execute("UPDATE chapters SET position = position + 1")
    handler.db.conn.commit()
    with patch("builtins.input", side_effect=["1", "2"]):
        handler.move_chapter()
    assert [c.title for c in handler.db.list_chapters(book.id)] == ["Two", "One"]
    assert ch1.id == handler.db.list_chapters(book.id)[1].id


def test_list_chapters_numbers_from_one_regardless_of_position(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "One", "")
    handler.db.conn.execute("UPDATE chapters SET position = 5")
    handler.db.conn.commit()
    handler.list_chapters()
    assert "  1. One" in capsys.readouterr().out


def test_publish_refreshes_updated_date(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.db.conn.execute("UPDATE books SET updated_at = '2000-01-01T00:00:00'")
    handler.db.conn.commit()
    handler.active_book = handler.db.get_book(book.id)
    handler.publish()
    assert handler.active_book.status == "published"
    assert handler.active_book.updated_at > "2000-01-01T00:00:00"


# -- Pickers (book select, chapter and note selection) --


@pytest.fixture
def two_chapters(handler):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Dawn", "Morning text")
    handler.db.create_chapter(book.id, "Dusk", "Evening text")
    return book


def test_book_select_picks_by_number(handler, capsys):
    handler.db.create_book("A")
    handler.db.create_book("B")
    with patch("builtins.input", return_value="2"):
        handler.book_select()
    assert handler.active_book.title == "B"
    assert "Selected: B" in capsys.readouterr().out


@pytest.mark.parametrize("choice, message", [("9", "Invalid selection."), ("x", "Invalid input.")])
def test_pickers_reject_bad_choices(handler, two_chapters, capsys, choice, message):
    handler.db.create_note(two_chapters.id, "idea", "Twist")
    for command in (handler.book_select, handler.edit_chapter, handler.show_chapter,
                    handler.move_chapter, handler.delete_chapter, handler.note_show):
        with patch("builtins.input", return_value=choice):
            command()
        assert message in capsys.readouterr().out


def test_show_chapter_prints_content(handler, two_chapters, capsys):
    with patch("builtins.input", return_value="2"):
        handler.show_chapter()
    out = capsys.readouterr().out
    assert "--- Dusk ---" in out
    assert "Evening text" in out
    assert "--- end ---" in out


def test_edit_chapter_saves_editor_text(handler, two_chapters, capsys):
    with patch("builtins.input", return_value="1"):
        with patch("keith.commands.open_editor", return_value="New dawn"):
            handler.edit_chapter()
    assert handler.db.list_chapters(two_chapters.id)[0].content == "New dawn"
    assert "Updated 'Dawn'." in capsys.readouterr().out


def test_edit_chapter_editor_failure_saves_nothing(handler, two_chapters, capsys):
    with patch("builtins.input", return_value="1"):
        with patch("keith.commands.open_editor", return_value=None):
            handler.edit_chapter()
    assert handler.db.list_chapters(two_chapters.id)[0].content == "Morning text"
    assert "Editor failed. No changes saved." in capsys.readouterr().out


def test_delete_chapter_confirmed(handler, two_chapters, capsys):
    with patch("builtins.input", side_effect=["1", "y"]):
        handler.delete_chapter()
    assert [c.title for c in handler.db.list_chapters(two_chapters.id)] == ["Dusk"]


def test_move_chapter_rejects_out_of_range_position(handler, two_chapters, capsys):
    with patch("builtins.input", side_effect=["1", "3"]):
        handler.move_chapter()
    assert "Invalid position." in capsys.readouterr().out


def test_add_chapter_editor_failure(handler, two_chapters, capsys):
    with patch("builtins.input", return_value="Noon"):
        with patch("keith.commands.open_editor", return_value=None):
            handler.add_chapter()
    assert "Editor failed. Chapter not created." in capsys.readouterr().out


def test_article_new_empty_body_discarded(handler, capsys):
    with patch("builtins.input", side_effect=["Essay", "n"]):
        with patch("keith.commands.open_editor", return_value="  "):
            handler.article_new()
    assert handler.db.list_books() == []
    assert "Discarded." in capsys.readouterr().out


def test_empty_title_rejected(handler, two_chapters, capsys):
    for command in (handler.book_new, handler.article_new, handler.add_chapter):
        with patch("builtins.input", return_value="  "):
            command()
        assert "Title cannot be empty." in capsys.readouterr().out


def _clear_capture_env(monkeypatch):
    for name in ("KEITH_TELEGRAM_TOKEN", "KEITH_TELEGRAM_USER", "KEITH_OBSIDIAN_INBOX"):
        monkeypatch.delenv(name, raising=False)


def test_pull_runs_configured_sources(handler, capsys, tmp_path, monkeypatch):
    _clear_capture_env(monkeypatch)
    (tmp_path / "a.md").write_text("#idea hello", encoding="utf-8")
    monkeypatch.setenv("KEITH_OBSIDIAN_INBOX", str(tmp_path))
    handler.active_book = handler.db.create_book("Orthodoxy")

    handler.pull("")

    out = capsys.readouterr().out
    assert "Telegram: not configured (set KEITH_TELEGRAM_TOKEN)" in out
    assert "1 note added." in out
    assert [n.content for n in handler.db.list_notes(handler.active_book.id)] == ["a\n hello"]


def test_pull_unknown_source(handler, capsys, monkeypatch):
    _clear_capture_env(monkeypatch)
    handler.pull("fax")
    assert "Unknown source: fax. Choose telegram or obsidian." in capsys.readouterr().out


def test_pull_single_source_filters_not_configured(handler, capsys, tmp_path, monkeypatch):
    _clear_capture_env(monkeypatch)
    monkeypatch.setenv("KEITH_OBSIDIAN_INBOX", str(tmp_path))
    handler.pull("Obsidian")
    out = capsys.readouterr().out
    assert "Telegram" not in out
    assert "No new notes." in out


def test_non_numeric_telegram_user():
    from keith.importers import configured_sources
    sources, missing = configured_sources(
        {"KEITH_TELEGRAM_TOKEN": "t", "KEITH_TELEGRAM_USER": "me"})
    assert sources == []
    assert "Telegram: not configured (KEITH_TELEGRAM_USER must be a number)" in missing
    assert "Obsidian: not configured (set KEITH_OBSIDIAN_INBOX)" in missing


def test_configured_sources_telegram_without_user_and_obsidian(tmp_path):
    from keith.importers import configured_sources
    sources, missing = configured_sources(
        {"KEITH_TELEGRAM_TOKEN": "t", "KEITH_OBSIDIAN_INBOX": str(tmp_path)})
    assert [type(s).__name__ for s in sources] == ["TelegramSource", "ObsidianSource"]
    assert missing == []


def test_note_move(handler, capsys):
    a = handler.db.create_book("A")
    b = handler.db.create_book("B")
    handler.db.create_note(a.id, "idea", "wander")
    handler.active_book = a
    with patch("builtins.input", side_effect=["1", "1"]):
        handler.note_move()
    assert "Moved note to 'B'." in capsys.readouterr().out
    assert handler.db.list_notes(a.id) == []
    assert len(handler.db.list_notes(b.id)) == 1


def test_note_move_without_other_book(handler, capsys):
    a = handler.db.create_book("A")
    handler.db.create_note(a.id, "idea", "wander")
    handler.active_book = a
    with patch("builtins.input", side_effect=["1"]):
        handler.note_move()
    assert "No other book to move it to." in capsys.readouterr().out
    assert len(handler.db.list_notes(a.id)) == 1
