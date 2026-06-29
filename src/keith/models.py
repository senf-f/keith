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
class Note:
    id: int
    book_id: int
    category: str
    content: str
    created_at: str
    updated_at: str

    @property
    def label(self) -> str:
        for line in self.content.splitlines():
            stripped = line.strip()
            if stripped:
                if len(stripped) > 60:
                    return stripped[:57] + "..."
                return stripped
        return "(empty)"


@dataclass
class SearchResult:
    book_id: int
    book_title: str
    chapter_id: int
    chapter_title: str
    snippet: str
    created_at: str
    kind: str = "chapter"
    category: str | None = None
