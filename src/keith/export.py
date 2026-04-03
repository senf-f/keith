import re

from keith.db import Database


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _make_anchor(position: int, title: str) -> str:
    return f"chapter-{position}-{slugify(title)}"


def export_book_to_markdown(db: Database, book_id: int) -> str:
    book = db.get_book(book_id)
    if book is None:
        raise ValueError(f"Book with id {book_id} not found")

    chapters = db.list_chapters(book_id)
    lines: list[str] = []

    # Title
    lines.append(f"# {book.title}")
    lines.append("")
    lines.append(f"*Created: {book.created_at[:10]} | Last updated: {book.updated_at[:10]}*")
    lines.append("")

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    for i, chapter in enumerate(chapters, 1):
        anchor = _make_anchor(i, chapter.title)
        lines.append(f"{i}. [{chapter.title}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Chapters
    for i, chapter in enumerate(chapters, 1):
        lines.append(f"## Chapter {i}: {chapter.title}")
        lines.append("")
        lines.append(chapter.content)
        lines.append("")

    return "\n".join(lines)
