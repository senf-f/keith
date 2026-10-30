import os
import shlex
from typing import Callable, TypeVar

from keith.db import Database
from keith.editor import open_editor
from keith.export import export_book_to_markdown, slugify
from keith.importers import configured_sources, format_report, run_import
from keith.models import DRAFT, PUBLISHED, VALID_CATEGORIES, Book, Chapter, Note


SEARCH_USAGE = "Usage: search [--title] [--book <id>] [--from <date>] [--to <date>] <query>"

T = TypeVar("T")


def word_count(text: str) -> int:
    return len(text.split())


def format_book_line(book: Book) -> str:
    marker = "  draft" if book.status == DRAFT else ""
    return f"  [{book.id}] {book.title}  ({book.created_at[:10]}){marker}"


def _confirm(question: str) -> bool:
    return input(f"{question} (y/n): ").strip().lower() == "y"


def _ask_title(prompt: str) -> str | None:
    title = input(prompt).strip()
    if not title:
        print("Title cannot be empty.")
        return None
    return title


def _compose(kind: str) -> str | None:
    """Body for a new article, chapter or note from $EDITOR; None if abandoned."""
    content = open_editor()
    if content is None:
        print(f"Editor failed. {kind} not created.")
        return None
    if not content.strip() and not _confirm(f"{kind} is empty. Save anyway?"):
        print("Discarded.")
        return None
    return content


def _pick(items: list[T], describe: Callable[[T], str], prompt: str) -> T | None:
    """Number the items, ask for one, and return it; None on a bad choice."""
    for i, item in enumerate(items, 1):
        print(f"  {i}. {describe(item)}")
    try:
        idx = int(input(prompt).strip()) - 1
    except ValueError:
        print("Invalid input.")
        return None
    if 0 <= idx < len(items):
        return items[idx]
    print("Invalid selection.")
    return None


class CommandHandler:
    def __init__(self, db: Database):
        self.db = db
        self.active_book: Book | None = None

    def _require_active_book(self) -> bool:
        if self.active_book is None:
            print("No book selected. Use 'book select' first.")
            return False
        return True

    # -- Book commands --

    def book_new(self) -> None:
        title = _ask_title("Book title: ")
        if title is None:
            return
        book = self.db.create_book(title)
        self.active_book = book
        print(f"Created book '{book.title}' (id: {book.id})")

    def article_new(self) -> None:
        title = _ask_title("Article title: ")
        if title is None:
            return
        content = _compose("Article")
        if content is None:
            return
        book = self.db.create_book(title)
        self.db.create_chapter(book.id, title, content)
        self.active_book = book
        print(f"Created article '{title}' (id: {book.id})")

    def book_list(self) -> None:
        books = self.db.list_books()
        if not books:
            print("No books yet.")
            return
        for book in books:
            print(format_book_line(book))

    def publish(self) -> None:
        self._set_status(PUBLISHED)

    def unpublish(self) -> None:
        self._set_status(DRAFT)

    def _set_status(self, status: str) -> None:
        if not self._require_active_book():
            return
        self.db.set_status(self.active_book.id, status)
        self.active_book = self.db.get_book(self.active_book.id)
        print(f"Marked '{self.active_book.title}' {status}.")

    def book_select(self) -> None:
        books = self.db.list_books()
        if not books:
            print("No books yet. Create one with 'book new'.")
            return
        book = _pick(books, lambda b: b.title, "Select book number: ")
        if book is not None:
            self.active_book = book
            print(f"Selected: {book.title}")

    def book_info(self) -> None:
        if not self._require_active_book():
            return
        book = self.active_book
        count = self.db.chapter_count(book.id)
        print(f"  Title:    {book.title}")
        print(f"  Chapters: {count}")
        print(f"  Status:   {book.status}")
        print(f"  Created:  {book.created_at[:10]}")
        print(f"  Updated:  {book.updated_at[:10]}")

    def book_delete(self) -> None:
        if not self._require_active_book():
            return
        if _confirm(f"Delete '{self.active_book.title}'?"):
            self.db.delete_book(self.active_book.id)
            print(f"Deleted '{self.active_book.title}'.")
            self.active_book = None
        else:
            print("Cancelled.")

    # -- Chapter commands --

    def _pick_chapter(self, none_message: str, prompt: str) -> tuple[Chapter, list[Chapter]] | None:
        """Pick a chapter of the active book, also returning the full ordered list."""
        if not self._require_active_book():
            return None
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print(none_message)
            return None
        chapter = _pick(chapters, lambda ch: ch.title, prompt)
        return (chapter, chapters) if chapter is not None else None

    def add_chapter(self) -> None:
        if not self._require_active_book():
            return
        title = _ask_title("Chapter title: ")
        if title is None:
            return
        content = _compose("Chapter")
        if content is None:
            return
        self.db.create_chapter(self.active_book.id, title, content)
        print(f"Added chapter '{title}'.")

    def list_chapters(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters yet.")
            return
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {ch.title}  ({ch.created_at[:10]})")

    def edit_chapter(self) -> None:
        picked = self._pick_chapter("No chapters to edit.", "Select chapter number: ")
        if picked is None:
            return
        chapter, _ = picked
        content = open_editor(initial_content=chapter.content)
        if content is None:
            print("Editor failed. No changes saved.")
            return
        self.db.update_chapter(chapter.id, content=content)
        print(f"Updated '{chapter.title}'.")

    def show_chapter(self) -> None:
        picked = self._pick_chapter("No chapters.", "Select chapter number: ")
        if picked is None:
            return
        chapter, _ = picked
        print(f"\n--- {chapter.title} ---\n")
        print(chapter.content)
        print("\n--- end ---\n")

    def move_chapter(self) -> None:
        picked = self._pick_chapter("No chapters to move.", "Move which chapter? (number): ")
        if picked is None:
            return
        chapter, chapters = picked
        try:
            new_pos = int(input(f"New position (1-{len(chapters)}): ").strip())
        except ValueError:
            print("Invalid input.")
            return
        if not 1 <= new_pos <= len(chapters):
            print("Invalid position.")
            return
        # Stored positions can have gaps (books made before deletes compacted
        # them), so move to the slot the user sees.
        self.db.move_chapter(chapter.id, chapters[new_pos - 1].position)
        print(f"Moved '{chapter.title}' to position {new_pos}.")

    def delete_chapter(self) -> None:
        picked = self._pick_chapter("No chapters to delete.", "Delete which chapter? (number): ")
        if picked is None:
            return
        chapter, _ = picked
        if _confirm(f"Delete '{chapter.title}'?"):
            self.db.delete_chapter(chapter.id)
            print(f"Deleted '{chapter.title}'.")
        else:
            print("Cancelled.")

    # -- Note commands --

    def _pick_note(self, prompt: str) -> Note | None:
        if not self._require_active_book():
            return None
        notes = self.db.list_notes(self.active_book.id)
        if not notes:
            print("No notes.")
            return None
        return _pick(notes, lambda n: f"[{n.category}] {n.label}", prompt)

    def note_new(self) -> None:
        if not self._require_active_book():
            return
        category = input(f"Category ({'/'.join(VALID_CATEGORIES)}): ").strip().lower()
        if category not in VALID_CATEGORIES:
            print(f"Unknown category. Choose one of: {', '.join(VALID_CATEGORIES)}.")
            return
        content = _compose("Note")
        if content is None:
            return
        self.db.create_note(self.active_book.id, category, content)
        print(f"Added {category} note.")

    def note_list(self, args_str: str) -> None:
        if not self._require_active_book():
            return
        category = args_str.strip().lower() or None
        notes = self.db.list_notes(self.active_book.id, category=category)
        if not notes:
            if category:
                print(f"No notes in '{category}'.")
            else:
                print("No notes yet.")
            return
        for i, note in enumerate(notes, 1):
            print(f"  {i}. [{note.category}] {note.label}")

    def note_show(self) -> None:
        note = self._pick_note("Select note number: ")
        if note is None:
            return
        print(f"\n--- [{note.category}] {note.label} ---\n")
        print(note.content)
        print("\n--- end ---\n")

    def note_edit(self) -> None:
        note = self._pick_note("Select note number: ")
        if note is None:
            return
        content = open_editor(initial_content=note.content)
        if content is None:
            print("Editor failed. No changes saved.")
            return
        self.db.update_note(note.id, content=content)
        print("Note updated.")

    def note_move(self) -> None:
        note = self._pick_note("Move which note? (number): ")
        if note is None:
            return
        others = [b for b in self.db.list_books() if b.id != note.book_id]
        if not others:
            print("No other book to move it to.")
            return
        book = _pick(others, lambda b: b.title, "Move to book number: ")
        if book is None:
            return
        self.db.move_note(note.id, book.id)
        print(f"Moved note to '{book.title}'.")

    # -- Capture --

    def pull(self, args_str: str) -> None:
        source = args_str.strip().lower()
        if source not in ("", "telegram", "obsidian"):
            print(f"Unknown source: {args_str.strip()}. Choose telegram or obsidian.")
            return
        sources, not_configured = configured_sources(os.environ)
        if source:
            sources = [s for s in sources if s.name.lower() == source]
            not_configured = [m for m in not_configured if m.lower().startswith(source)]
        print(format_report(run_import(self.db, sources, self.active_book), not_configured))

    def note_delete(self) -> None:
        note = self._pick_note("Delete which note? (number): ")
        if note is None:
            return
        if _confirm(f"Delete [{note.category}] {note.label}?"):
            self.db.delete_note(note.id)
            print("Note deleted.")
        else:
            print("Cancelled.")

    # -- Search --

    def handle_search(self, args_str: str) -> None:
        try:
            parts = shlex.split(args_str)
        except ValueError:
            print("Unbalanced quote in search query.")
            return
        if not parts:
            print(SEARCH_USAGE)
            return

        title_only = False
        book_id = None
        date_from = None
        date_to = None
        query_parts = []
        i = 0
        while i < len(parts):
            if parts[i] == "--title":
                title_only = True
            elif parts[i] == "--book" and i + 1 < len(parts):
                i += 1
                try:
                    book_id = int(parts[i])
                except ValueError:
                    print(f"Invalid book id: {parts[i]}")
                    return
            elif parts[i] == "--from" and i + 1 < len(parts):
                i += 1
                date_from = parts[i]
            elif parts[i] == "--to" and i + 1 < len(parts):
                i += 1
                date_to = parts[i]
            else:
                query_parts.append(parts[i])
            i += 1

        query = " ".join(query_parts).strip()
        if not query:
            print("No search query provided.")
            return

        results = self.db.search(
            query, title_only=title_only, book_id=book_id,
            date_from=date_from, date_to=date_to,
        )
        if not results:
            print("No results found.")
            return
        for r in results:
            if r.kind == "note":
                print(f"  [{r.book_title}/note:{r.category}] {r.title}")
            else:
                print(f"  [{r.book_title}] {r.title} ({r.created_at[:10]})")
            print(f"    {r.snippet}")
            print()

    # -- Export --

    def export(self) -> None:
        if not self._require_active_book():
            return
        md = export_book_to_markdown(self.db, self.active_book.id)
        filename = f"{slugify(self.active_book.title)}.md"
        if os.path.exists(filename) and not _confirm(f"'{filename}' exists. Overwrite?"):
            filename = input("Enter new filename: ").strip()
            if not filename:
                print("Cancelled.")
                return
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Exported to {filename}")

    # -- Backup / restore --

    def backup(self) -> None:
        dest = input("Backup to file path: ").strip()
        if not dest:
            print("Cancelled.")
            return
        dest = os.path.expanduser(dest)
        if os.path.exists(dest) and not _confirm(f"'{dest}' exists. Overwrite?"):
            print("Cancelled.")
            return
        self.db.backup(dest)
        print(f"Backed up to {dest}")

    def restore(self) -> None:
        src = input("Restore from file path: ").strip()
        if not src:
            print("Cancelled.")
            return
        src = os.path.expanduser(src)
        if not os.path.exists(src):
            print(f"File not found: {src}")
            return
        if not _confirm("This replaces ALL current data with the backup. Continue?"):
            print("Cancelled.")
            return
        self.db.restore(src)
        self.active_book = None
        print(f"Restored from {src}")

    # -- Stats --

    def stats(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters yet.")
            return

        counts = [(ch.title, word_count(ch.content)) for ch in chapters]
        total = sum(c for _, c in counts)

        title_width = max(len(title) for title, _ in counts)
        for i, (title, count) in enumerate(counts, 1):
            pct = round(count / total * 100) if total > 0 else 0
            print(f"  {i}. {title:<{title_width}}  {count:,} words  ({pct}%)")

        separator_width = title_width + 30
        print(f"  {'─' * separator_width}")
        print(f"  {'Total':<{title_width + 3}} {total:,} words")
