import os
import tempfile
from unittest.mock import patch

from keith.commands import CommandHandler
from keith.db import Database
from keith.export import export_book_to_markdown


def test_full_workflow():
    """Create a book, add chapters, search, export."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    handler = CommandHandler(db)

    # Create a book
    with patch("builtins.input", return_value="Orthodoxy"):
        handler.book_new()
    assert handler.active_book is not None
    assert handler.active_book.title == "Orthodoxy"

    # Add chapters
    with patch("builtins.input", return_value="The Maniac"):
        with patch("keith.commands.open_editor", return_value="The madman is not the man who has lost his reason."):
            handler.add_chapter()

    with patch("builtins.input", return_value="The Suicide of Thought"):
        with patch("keith.commands.open_editor", return_value="There is a thought that stops thought."):
            handler.add_chapter()

    # List chapters
    chapters = db.list_chapters(handler.active_book.id)
    assert len(chapters) == 2
    assert chapters[0].title == "The Maniac"
    assert chapters[1].title == "The Suicide of Thought"

    # Search
    results = db.search("madman")
    assert len(results) == 1
    assert results[0].chapter_title == "The Maniac"

    # Export
    md = export_book_to_markdown(db, handler.active_book.id)
    assert "# Orthodoxy" in md
    assert "## Table of Contents" in md
    assert "1. [The Maniac]" in md
    assert "## Chapter 1: The Maniac" in md
    assert "The madman is not the man who has lost his reason." in md

    db.close()
    os.unlink(path)
