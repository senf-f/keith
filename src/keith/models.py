from dataclasses import dataclass


@dataclass
class Book:
    id: int
    title: str
    created_at: str
    updated_at: str


@dataclass
class Chapter:
    id: int
    book_id: int
    title: str
    content: str
    position: int
    created_at: str
    updated_at: str


@dataclass
class SearchResult:
    book_id: int
    book_title: str
    chapter_id: int
    chapter_title: str
    snippet: str
    created_at: str
