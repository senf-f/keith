import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from keith.db import INBOX_TITLE, Database
from keith.export import slugify
from keith.models import VALID_CATEGORIES, Book, note_label


TAG_RE = re.compile(r"(?<!\S)#([\w-]+)")


@dataclass
class RawItem:
    source: str
    key: str
    text: str
    created_at: str


@dataclass
class Route:
    """Where an item goes; book=None means the Inbox."""
    book: Book | None
    category: str
    text: str


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def route(text: str, books: list[Book], active_book: Book | None) -> Route:
    slugs = {}
    for book in books:
        slugs.setdefault(slugify(book.title), []).append(book)

    category = None
    matched_books: dict[str, Book] = {}
    ambiguous = False
    spans = []
    for m in TAG_RE.finditer(text):
        tag = m.group(1).lower()
        if tag in VALID_CATEGORIES:
            if category is None:
                category = tag
            spans.append(m.span())
        elif tag in slugs:
            if len(slugs[tag]) > 1:
                ambiguous = True
            matched_books.setdefault(tag, slugs[tag][0])
            spans.append(m.span())

    category = category or "idea"
    if ambiguous or len(matched_books) > 1:
        return Route(None, category, text)
    if matched_books:
        book = next(iter(matched_books.values()))
    else:
        book = active_book
    if book is None:
        return Route(None, category, text)

    pieces, last = [], 0
    for start, end in spans:
        pieces.append(text[last:start])
        last = end
    pieces.append(text[last:])
    return Route(book, category, _clean("".join(pieces)))


class SourceError(Exception):
    """A whole source failed; the message is shown to the user verbatim."""


@dataclass
class FetchResult:
    items: list[RawItem]
    skipped: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


@dataclass
class Imported:
    book_title: str
    category: str
    label: str


@dataclass
class SourceReport:
    name: str
    imported: list[Imported]
    already: int
    skipped: dict[str, int]
    problems: list[str]
    error: str | None


def _import_source(db: Database, source, active_book: Book | None) -> SourceReport:
    report = SourceReport(source.name, [], 0, {}, [], None)
    try:
        fetched = source.fetch()
    except SourceError as exc:
        report.error = str(exc)
        return report
    report.skipped = dict(fetched.skipped)
    report.problems = list(fetched.problems)

    books = db.list_books()
    failed_keys: set[str] = set()
    for item in fetched.items:
        if db.is_imported(item.source, item.key):
            report.already += 1
            continue
        routed = route(item.text, books, active_book)
        if not routed.text:
            report.skipped["no text"] = report.skipped.get("no text", 0) + 1
            continue
        book = routed.book or db.get_or_create_inbox()
        try:
            db.create_imported_note(
                item.source, item.key, book.id, routed.category, routed.text, item.created_at,
            )
        except Exception as exc:
            report.problems.append(f"{item.key}: {exc}")
            failed_keys.add(item.key)
            continue
        report.imported.append(Imported(book.title, routed.category, note_label(routed.text)))

    acknowledge = getattr(source, "acknowledge", None)
    if acknowledge is not None:
        try:
            acknowledge(failed_keys)
        except SourceError as exc:
            # The notes are committed; rerunning pull is safe, so just report it.
            report.problems.append(str(exc))
    return report


def run_import(db: Database, sources: list, active_book: Book | None) -> list[SourceReport]:
    return [_import_source(db, source, active_book) for source in sources]


def format_report(reports: list[SourceReport], not_configured: list[str]) -> str:
    lines = list(not_configured)
    targets = [f"{i.book_title} / {i.category}" for r in reports for i in r.imported]
    width = max(map(len, targets), default=0)
    total = inbox = 0
    for r in reports:
        if r.error is None:
            summary = f"{r.name}: {len(r.imported)} imported"
            for reason, count in r.skipped.items():
                summary += f", {count} skipped ({reason})"
            if r.already:
                summary += f", {r.already} already imported"
            lines.append(summary)
        for i in r.imported:
            target = f"{i.book_title} / {i.category}"
            lines.append(f"  → {target:<{width}}   {i.label}")
        lines.extend(f"{r.name}: {p}" for p in r.problems)
        if r.error is not None:
            lines.append(f"{r.name}: {r.error}")
        total += len(r.imported)
        inbox += sum(1 for i in r.imported if i.book_title == INBOX_TITLE)
    if total == 0:
        lines.append("No new notes.")
    else:
        last = f"{total} note added." if total == 1 else f"{total} notes added."
        if inbox:
            last += f" {inbox} went to Inbox — file them with 'note move'."
        lines.append(last)
    return "\n".join(lines)


def configured_sources(env: Mapping[str, str]) -> tuple[list, list[str]]:
    """Sources whose settings are present, plus a line for each that is not."""
    # Imported here: both modules import from this one.
    from keith.obsidian import ObsidianSource
    from keith.telegram import TelegramSource

    sources: list = []
    not_configured: list[str] = []

    token = env.get("KEITH_TELEGRAM_TOKEN")
    user = env.get("KEITH_TELEGRAM_USER")
    if not token:
        not_configured.append("Telegram: not configured (set KEITH_TELEGRAM_TOKEN)")
    elif user and not user.strip().isdigit():
        not_configured.append(
            "Telegram: not configured (KEITH_TELEGRAM_USER must be a number)")
    else:
        sources.append(TelegramSource(token, int(user) if user else None))

    inbox = env.get("KEITH_OBSIDIAN_INBOX")
    if inbox:
        sources.append(ObsidianSource(Path(inbox).expanduser()))
    else:
        not_configured.append("Obsidian: not configured (set KEITH_OBSIDIAN_INBOX)")
    return sources, not_configured
