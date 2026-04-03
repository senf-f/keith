import os
import shlex

from keith.db import Database
from keith.editor import open_editor
from keith.export import export_book_to_markdown, slugify
from keith.models import Book


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
        title = input("Book title: ").strip()
        if not title:
            print("Title cannot be empty.")
            return
        book = self.db.create_book(title)
        self.active_book = book
        print(f"Created book '{book.title}' (id: {book.id})")

    def book_list(self) -> None:
        books = self.db.list_books()
        if not books:
            print("No books yet.")
            return
        for book in books:
            print(f"  [{book.id}] {book.title}  ({book.created_at[:10]})")

    def book_select(self) -> None:
        books = self.db.list_books()
        if not books:
            print("No books yet. Create one with 'book new'.")
            return
        for i, book in enumerate(books, 1):
            print(f"  {i}. {book.title}")
        choice = input("Select book number: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(books):
                self.active_book = books[idx]
                print(f"Selected: {self.active_book.title}")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

    def book_info(self) -> None:
        if not self._require_active_book():
            return
        book = self.active_book
        count = self.db.chapter_count(book.id)
        print(f"  Title:    {book.title}")
        print(f"  Chapters: {count}")
        print(f"  Created:  {book.created_at[:10]}")
        print(f"  Updated:  {book.updated_at[:10]}")

    def book_delete(self) -> None:
        if not self._require_active_book():
            return
        confirm = input(f"Delete '{self.active_book.title}'? (y/n): ").strip().lower()
        if confirm == "y":
            self.db.delete_book(self.active_book.id)
            print(f"Deleted '{self.active_book.title}'.")
            self.active_book = None
        else:
            print("Cancelled.")

    # -- Chapter commands --

    def add_chapter(self) -> None:
        if not self._require_active_book():
            return
        title = input("Chapter title: ").strip()
        if not title:
            print("Title cannot be empty.")
            return
        content = open_editor()
        if content is None:
            print("Editor failed. Chapter not created.")
            return
        if not content.strip():
            confirm = input("Chapter is empty. Save anyway? (y/n): ").strip().lower()
            if confirm != "y":
                print("Discarded.")
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
        for ch in chapters:
            print(f"  {ch.position}. {ch.title}  ({ch.created_at[:10]})")

    def edit_chapter(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters to edit.")
            return
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {ch.title}")
        choice = input("Select chapter number: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(chapters):
                chapter = chapters[idx]
                content = open_editor(initial_content=chapter.content)
                if content is not None:
                    self.db.update_chapter(chapter.id, content=content)
                    print(f"Updated '{chapter.title}'.")
                else:
                    print("Editor failed. No changes saved.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

    def show_chapter(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters.")
            return
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {ch.title}")
        choice = input("Select chapter number: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(chapters):
                chapter = chapters[idx]
                print(f"\n--- {chapter.title} ---\n")
                print(chapter.content)
                print(f"\n--- end ---\n")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

    def move_chapter(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters to move.")
            return
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {ch.title}")
        choice = input("Move which chapter? (number): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(chapters):
                chapter = chapters[idx]
                new_pos = input(f"New position (1-{len(chapters)}): ").strip()
                new_pos_int = int(new_pos)
                if 1 <= new_pos_int <= len(chapters):
                    self.db.move_chapter(chapter.id, new_pos_int)
                    print(f"Moved '{chapter.title}' to position {new_pos_int}.")
                else:
                    print("Invalid position.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

    def delete_chapter(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters to delete.")
            return
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {ch.title}")
        choice = input("Delete which chapter? (number): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(chapters):
                chapter = chapters[idx]
                confirm = input(f"Delete '{chapter.title}'? (y/n): ").strip().lower()
                if confirm == "y":
                    self.db.delete_chapter(chapter.id)
                    print(f"Deleted '{chapter.title}'.")
                else:
                    print("Cancelled.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

    # -- Search --

    def handle_search(self, args_str: str) -> None:
        parts = shlex.split(args_str)
        if not parts:
            print("Usage: search [--title] [--book <id>] [--from <date>] [--to <date>] <query>")
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
                book_id = int(parts[i])
            elif parts[i] == "--from" and i + 1 < len(parts):
                i += 1
                date_from = parts[i]
            elif parts[i] == "--to" and i + 1 < len(parts):
                i += 1
                date_to = parts[i]
            else:
                query_parts.append(parts[i])
            i += 1

        query = " ".join(query_parts)
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
            print(f"  [{r.book_title}] {r.chapter_title} ({r.created_at[:10]})")
            print(f"    {r.snippet}")
            print()

    # -- Export --

    def export(self) -> None:
        if not self._require_active_book():
            return
        md = export_book_to_markdown(self.db, self.active_book.id)
        filename = f"{slugify(self.active_book.title)}.md"
        if os.path.exists(filename):
            confirm = input(f"'{filename}' exists. Overwrite? (y/n): ").strip().lower()
            if confirm != "y":
                filename = input("Enter new filename: ").strip()
                if not filename:
                    print("Cancelled.")
                    return
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Exported to {filename}")
