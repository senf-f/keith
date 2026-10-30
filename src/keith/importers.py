import re
from dataclasses import dataclass

from keith.export import slugify
from keith.models import VALID_CATEGORIES, Book


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
