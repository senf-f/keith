# src/keith/repl.py
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from pathlib import Path

from keith.commands import CommandHandler
from keith.db import Database


COMMANDS = [
    "book new", "book list", "book select", "book info", "book delete",
    "add chapter", "list chapters", "edit chapter", "show chapter",
    "move chapter", "delete chapter",
    "search", "export", "help", "exit", "quit",
]

HELP_TEXT = """
  Book commands:
    book new        Create a new book
    book list       List all books
    book select     Select a book to work on
    book info       Show active book details
    book delete     Delete the active book

  Chapter commands (requires active book):
    add chapter     Add a new chapter
    list chapters   List chapters in order
    edit chapter    Edit a chapter in $EDITOR
    show chapter    Display a chapter
    move chapter    Reorder a chapter
    delete chapter  Delete a chapter

  Search:
    search <query>              Full-text search
    search --title <query>      Search titles only
    search --book <id> <query>  Search within a book
    search --from <date> --to <date> <query>  Date range filter

  Other:
    export          Export active book to markdown
    help            Show this help
    exit / quit     Leave keith
""".strip()


def _get_prompt(handler: CommandHandler) -> str:
    if handler.active_book:
        return f"keith [{handler.active_book.title}]> "
    return "keith> "


def run_repl() -> None:
    db = Database()
    handler = CommandHandler(db)

    history_dir = Path.home() / ".keith"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "history"

    completer = WordCompleter(COMMANDS, sentence=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
    )

    print("keith — a book writing tool. Type 'help' for commands.")

    while True:
        try:
            text = session.prompt(_get_prompt(handler)).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not text:
            continue

        if text in ("exit", "quit"):
            break
        elif text == "help":
            print(HELP_TEXT)
        elif text == "book new":
            handler.book_new()
        elif text == "book list":
            handler.book_list()
        elif text == "book select":
            handler.book_select()
        elif text == "book info":
            handler.book_info()
        elif text == "book delete":
            handler.book_delete()
        elif text == "add chapter":
            handler.add_chapter()
        elif text == "list chapters":
            handler.list_chapters()
        elif text == "edit chapter":
            handler.edit_chapter()
        elif text == "show chapter":
            handler.show_chapter()
        elif text == "move chapter":
            handler.move_chapter()
        elif text == "delete chapter":
            handler.delete_chapter()
        elif text.startswith("search "):
            handler.handle_search(text[7:])
        elif text == "search":
            print("Usage: search [--title] [--book <id>] [--from <date>] [--to <date>] <query>")
        elif text == "export":
            handler.export()
        else:
            print(f"Unknown command: {text}. Type 'help' for available commands.")

    db.close()
    print("Goodbye.")
