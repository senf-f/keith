# Keith — CLI Book Writing Tool

A command-line application for writing and organizing books. Named after G.K. Chesterton.

**Language:** Python 3.10+
**Package manager:** uv + pyproject.toml
**Dependencies:** prompt_toolkit, click (everything else is stdlib)
**Platforms:** Bash, PowerShell

## Data Model

Single SQLite database at `~/.keith/keith.db` (resolved via `Path.home()`, e.g., `C:\Users\<user>\.keith\keith.db` on Windows, `~/.keith/keith.db` on Unix). The directory is created on first run if it doesn't exist. One global library containing all books.

### Tables

**books**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key, autoincrement |
| title | TEXT | Not null |
| created_at | TEXT | ISO 8601, set on creation |
| updated_at | TEXT | ISO 8601, updated on any change |

**chapters**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key, autoincrement |
| book_id | INTEGER | FK to books, cascade delete |
| title | TEXT | Not null |
| content | TEXT | Chapter body |
| position | INTEGER | Ordering within the book |
| created_at | TEXT | ISO 8601, set on creation |
| updated_at | TEXT | ISO 8601, updated on any change |

**fts_chapters** — FTS5 virtual table indexing chapter titles, chapter content, and book titles. Kept in sync via SQLite triggers on insert/update/delete of chapters.

## CLI Entry Points

### Interactive (default)

Running `keith` with no arguments drops into a REPL powered by prompt_toolkit. The prompt shows the active book:

```
keith> book select
keith [The Man Who Was Thursday]> add chapter
keith [The Man Who Was Thursday]> search "sunday"
```

Features: command autocomplete, input history, multiline support.

### Non-interactive

Accessed directly from the shell:

- `keith export <book_id>` — export a book to markdown
- `keith list books` — list all books
- `keith version` — version info

Handled by click.

## REPL Commands

### Book management
- `book new` — prompts for title, creates a book
- `book list` — lists all books with ID, title, date
- `book select` — prompts to pick a book (becomes active)
- `book info` — shows active book details (title, chapter count, dates)
- `book delete` — deletes active book (with confirmation)

### Chapter management (requires active book)
- `add chapter` — prompts for title, opens $EDITOR for content
- `list chapters` — lists chapters in order with position, title, date
- `edit chapter` — prompts to pick a chapter, opens $EDITOR with existing content
- `show chapter` — displays a chapter's content in the terminal (paged if long)
- `move chapter` — reorder a chapter's position
- `delete chapter` — deletes a chapter (with confirmation)

### Search
- `search <query>` — full-text search across all books (titles + content), shows matches with context snippets
- `search --title <query>` — search titles only
- `search --book <id> <query>` — limit search to a specific book
- `search --from 2026-01-01 --to 2026-03-01 <query>` — date range filter

### Other
- `export` — exports active book to markdown
- `help` — lists commands
- `exit` / `quit` — leaves the REPL

When a command needs the user to pick from a list (select book, select chapter), it shows a numbered list.

## Editor Integration

When adding or editing a chapter:

1. Create a temp file with `.md` extension (for editor syntax highlighting)
2. Pre-fill with existing content if editing, empty if new
3. Open `$EDITOR` (fallback: `notepad` on Windows, `vi` on Unix)
4. Wait for the editor to close
5. Read the temp file, store content in SQLite
6. Delete the temp file

If the editor is closed without saving or content is empty, ask whether to save an empty chapter or discard.

## Markdown Export

Produces a single `.md` file in the current working directory, named `<book-title-slugified>.md`:

```markdown
# The Man Who Was Thursday

*Created: 2026-03-15 | Last updated: 2026-04-01*

## Table of Contents

1. [The Two Poets](#chapter-1-the-two-poets)
2. [The Secret of Gabriel Syme](#chapter-2-the-secret-of-gabriel-syme)

---

## Chapter 1: The Two Poets

Chapter content here...

## Chapter 2: The Secret of Gabriel Syme

Chapter content here...
```

Chapters ordered by `position`. If the file already exists, ask to overwrite or pick a different name.

## Search Implementation

Uses SQLite FTS5 (bundled with Python's sqlite3):

- FTS index covers chapter titles, chapter content, and book titles
- Results show: book title, chapter title, snippet with match highlighted (FTS5 `snippet()`), date
- Ranked by relevance (FTS5 `rank`)
- Structured filters (`--title`, `--book`, `--from`/`--to`) applied as WHERE clauses on the joined query
- FTS table synced via SQLite triggers on chapter insert/update/delete

## Project Structure

```
keith/
├── pyproject.toml          # Package config, dependencies, entry point
├── src/
│   └── keith/
│       ├── __init__.py
│       ├── cli.py          # click entry points (export, list, version)
│       ├── repl.py         # prompt_toolkit REPL loop + command dispatch
│       ├── commands.py     # Command implementations (book, chapter, search)
│       ├── db.py           # SQLite connection, schema, migrations, FTS triggers
│       ├── editor.py       # $EDITOR integration (tempfile, subprocess)
│       ├── export.py       # Markdown export logic
│       └── models.py       # Data classes for Book, Chapter
└── tests/
    ├── test_commands.py
    ├── test_db.py
    ├── test_editor.py
    ├── test_export.py
    └── test_search.py
```
