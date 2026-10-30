from pathlib import Path
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory

from keith.commands import CommandHandler
from keith.db import Database, sync_conflicts
from keith.tips import WRITING_TIPS


EXIT_COMMANDS = ("exit", "quit")

HELP_TEXT = """
  Book commands:
    book new        Create a new book
    book list       List all books
    book select     Select a book to work on
    book info       Show active book details
    book delete     Delete the active book

  Short-form writing:
    article new     Write a blog post or article (one title, one body)
    publish         Mark the active book/article published
    unpublish       Mark it a draft again

  Chapter commands (requires active book):
    add chapter     Add a new chapter
    list chapters   List chapters in order
    edit chapter    Edit a chapter in $EDITOR
    show chapter    Display a chapter
    move chapter    Reorder a chapter
    delete chapter  Delete a chapter

  Note commands (requires active book; notes are never exported):
    note new            Add a note (idea/outline/character/place/other)
    note list           List notes grouped by category
    note list <cat>     List notes in one category
    note show           Display a note
    note edit           Edit a note in $EDITOR
    note move           Move a note to another book
    note delete         Delete a note

  Search:
    search <query>              Full-text search
    search --title <query>      Search titles only
    search --book <id> <query>  Search within a book
    search --from <date> --to <date> <query>  Date range filter

  Capture:
    pull [telegram|obsidian]  Import new notes from capture sources

  Other:
    export          Export active book to markdown
    stats           Show word count per chapter
    tips            Show writing advice from great authors
    backup          Back up the whole database to a file
    restore         Replace all data from a backup file
    help            Show this help
    exit / quit     Leave keith
""".strip()


class Commands:
    """Every REPL command in one place: dispatch and autocomplete both read
    from here, and a test checks HELP_TEXT mentions each one."""

    def __init__(self, handler: CommandHandler):
        self.no_args: dict[str, Callable[[], None]] = {
            "book new": handler.book_new,
            "book list": handler.book_list,
            "book select": handler.book_select,
            "book info": handler.book_info,
            "book delete": handler.book_delete,
            "article new": handler.article_new,
            "publish": handler.publish,
            "unpublish": handler.unpublish,
            "add chapter": handler.add_chapter,
            "list chapters": handler.list_chapters,
            "edit chapter": handler.edit_chapter,
            "show chapter": handler.show_chapter,
            "move chapter": handler.move_chapter,
            "delete chapter": handler.delete_chapter,
            "note new": handler.note_new,
            "note show": handler.note_show,
            "note edit": handler.note_edit,
            "note move": handler.note_move,
            "note delete": handler.note_delete,
            "export": handler.export,
            "stats": handler.stats,
            "backup": handler.backup,
            "restore": handler.restore,
            "tips": lambda: print(WRITING_TIPS),
            "help": lambda: print(HELP_TEXT),
        }
        # These receive whatever follows their name ("" when nothing does).
        self.with_args: dict[str, Callable[[str], None]] = {
            "note list": handler.note_list,
            "search": handler.handle_search,
            "pull": handler.pull,
        }

    @property
    def names(self) -> list[str]:
        return [*self.no_args, *self.with_args, *EXIT_COMMANDS]

    def dispatch(self, text: str) -> None:
        if text in self.no_args:
            self.no_args[text]()
            return
        for name, action in self.with_args.items():
            if text == name or text.startswith(name + " "):
                action(text[len(name):].strip())
                return
        print(f"Unknown command: {text}. Type 'help' for available commands.")


def _get_prompt(handler: CommandHandler) -> str:
    if handler.active_book:
        return f"keith [{handler.active_book.title}]> "
    return "keith> "


def run_repl() -> None:
    db = Database()
    # try/finally so a crash still checkpoints the WAL into the synced .db file.
    try:
        _session(db)
    finally:
        db.close()
    print("Goodbye.")


def _session(db: Database) -> None:
    handler = CommandHandler(db)

    conflicts = sync_conflicts(db.path)
    if conflicts:
        print(f"WARNING: your sync tool parked conflicting copies beside {db.path.name} — writes made\n"
              "on another machine may be missing here:")
        for path in conflicts:
            print(f"  {path}")
        print("Salvage text with 'export', or swap a copy in wholesale with 'restore'.\n")

    history_dir = Path.home() / ".keith"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "history"

    commands = Commands(handler)
    completer = WordCompleter(commands.names, sentence=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
    )

    print("keith — a book writing tool. Type 'help' for commands.")

    while True:
        try:
            text = session.prompt(_get_prompt(handler)).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not text:
            continue
        if text in EXIT_COMMANDS:
            return
        commands.dispatch(text)
