from contextlib import closing

import sys

import click

from keith import __version__
from keith.commands import CommandHandler, format_book_line
from keith.db import Database
from keith.export import export_book_to_markdown, slugify


def _tolerate_unencodable_output():
    """Print '?' instead of crashing on characters a non-UTF-8 pipe can't hold."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """keith — a book writing tool."""
    _tolerate_unencodable_output()
    if ctx.invoked_subcommand is None:
        from keith.repl import run_repl
        run_repl()


@main.command()
def version():
    """Show version."""
    click.echo(f"keith {__version__}")


@main.command(name="list")
def list_books():
    """List all books."""
    with closing(Database()) as db:
        books = db.list_books()
    if not books:
        click.echo("No books yet.")
    for book in books:
        click.echo(format_book_line(book))


@main.command()
@click.argument("book_id", type=int)
def export(book_id):
    """Export a book to markdown."""
    with closing(Database()) as db:
        book = db.get_book(book_id)
        if book is None:
            click.echo(f"Book with id {book_id} not found.")
            return
        md = export_book_to_markdown(db, book_id)
    filename = f"{slugify(book.title)}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)
    click.echo(f"Exported to {filename}")


@main.command()
@click.argument("source", required=False)
def pull(source):
    """Import new notes from Telegram and Obsidian (SOURCE: telegram or obsidian)."""
    with closing(Database()) as db:
        CommandHandler(db).pull(source or "")
