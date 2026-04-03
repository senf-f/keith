import click

from keith import __version__
from keith.db import Database
from keith.export import export_book_to_markdown, slugify


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """keith — a book writing tool."""
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
    db = Database()
    books = db.list_books()
    if not books:
        click.echo("No books yet.")
    else:
        for book in books:
            click.echo(f"  [{book.id}] {book.title}  ({book.created_at[:10]})")
    db.close()


@main.command()
@click.argument("book_id", type=int)
def export(book_id):
    """Export a book to markdown."""
    db = Database()
    book = db.get_book(book_id)
    if book is None:
        click.echo(f"Book with id {book_id} not found.")
        db.close()
        return
    md = export_book_to_markdown(db, book_id)
    filename = f"{slugify(book.title)}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)
    click.echo(f"Exported to {filename}")
    db.close()
