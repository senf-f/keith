# keith

A CLI tool for writing and organizing books. Named after G.K. Chesterton.

> "A good novel tells us the truth about its hero; but a bad novel tells us the truth about its author."
> — G.K. Chesterton

## Features

- **Interactive REPL** with command autocomplete and history
- **Multiple books** in a single library
- **Chapter management** with ordering, editing via `$EDITOR`, and display
- **Full-text search** across all books (titles and content) with date range filters
- **Markdown export** with table of contents
- **Cross-platform** — works on Bash and PowerShell

## Installation

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/senf-f/keith.git
cd keith
uv sync
```

## Usage

Launch the interactive REPL:

```bash
uv run keith
```

You'll see a prompt where you can type commands:

```
keith> book new
Book title: Orthodoxy
Created book 'Orthodoxy' (id: 1)

keith [Orthodoxy]> add chapter
Chapter title: The Maniac
# Opens your $EDITOR to write the chapter content

keith [Orthodoxy]> list chapters
  1. The Maniac  (2026-04-03)

keith [Orthodoxy]> search madman
  [Orthodoxy] The Maniac (2026-04-03)
    The >>>madman<<< is not the man who has lost his reason.

keith [Orthodoxy]> export
Exported to orthodoxy.md
```

### Non-interactive commands

```bash
uv run keith version       # Show version
uv run keith list          # List all books
uv run keith export <id>   # Export a book to markdown
```

### REPL commands

| Command | Description |
|---|---|
| `book new` | Create a new book |
| `book list` | List all books |
| `book select` | Select a book to work on |
| `book info` | Show active book details |
| `book delete` | Delete the active book |
| `add chapter` | Add a new chapter (opens `$EDITOR`) |
| `list chapters` | List chapters in order |
| `edit chapter` | Edit a chapter in `$EDITOR` |
| `show chapter` | Display a chapter in the terminal |
| `move chapter` | Reorder a chapter |
| `delete chapter` | Delete a chapter |
| `search <query>` | Full-text search across all books |
| `search --title <query>` | Search titles only |
| `search --book <id> <query>` | Search within a specific book |
| `search --from <date> --to <date> <query>` | Search with date range |
| `export` | Export active book to markdown |
| `help` | Show available commands |
| `exit` | Leave keith |

## Data storage

Books and chapters are stored in a SQLite database at `~/.keith/keith.db`. Full-text search is powered by SQLite FTS5.

## Running tests

```bash
uv run pytest -v
```
