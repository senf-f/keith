# keith

A CLI tool for writing and organizing books. Named after G.K. Chesterton.

> "A good novel tells us the truth about its hero; but a bad novel tells us the truth about its author."
> — G.K. Chesterton

## Features

- **Interactive REPL** with command autocomplete and history
- **Multiple books** in a single library
- **Chapter management** with ordering, editing via `$EDITOR`, and display
- **Notes** per book (ideas, outline, characters, places) — searchable but never exported
- **Short-form writing** — blog posts and articles, with draft/published tracking
- **Full-text search** across all books (titles and content) with date range filters
- **Markdown export** with table of contents, or plain prose for single-chapter pieces
- **Cross-platform** — works on Bash and PowerShell

## Installation

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/senf-f/keith.git
cd keith
uv sync
```

### Install globally

To run `keith` from any directory (not just the project folder), install it as a uv tool:

```bash
uv tool install --editable .
```

Then `keith` is available on your PATH everywhere. `--editable` means code changes take effect without reinstalling. If the command isn't found afterward, run `uv tool update-shell` once and reopen your terminal. Update or remove later with `uv tool upgrade keith` / `uv tool uninstall keith`.

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
| `article new` | Write a blog post or article — one title, one body |
| `publish` | Mark the active book/article published |
| `unpublish` | Mark it a draft again |
| `add chapter` | Add a new chapter (opens `$EDITOR`) |
| `list chapters` | List chapters in order |
| `edit chapter` | Edit a chapter in `$EDITOR` |
| `show chapter` | Display a chapter in the terminal |
| `move chapter` | Reorder a chapter |
| `delete chapter` | Delete a chapter |
| `note new` | Add a note (idea/outline/character/place/other) |
| `note list` | List notes grouped by category |
| `note list <category>` | List notes in one category |
| `note show` | Display a note |
| `note edit` | Edit a note in `$EDITOR` |
| `note delete` | Delete a note |
| `search <query>` | Full-text search across all books |
| `search --title <query>` | Search titles only |
| `search --book <id> <query>` | Search within a specific book |
| `search --from <date> --to <date> <query>` | Search with date range |
| `export` | Export active book to markdown |
| `backup` | Back up the entire database to a file |
| `restore` | Replace all data from a backup file |
| `help` | Show available commands |
| `exit` | Leave keith |

## Short-form writing

A blog post or article is just a book with a single chapter, so it gets search, notes, export, and backup for free — no separate concept to learn. `article new` skips the two-step dance of `book new` then `add chapter`: it asks for one title and opens `$EDITOR` for the body.

```
keith> article new
Article title: Why Fairy Tales Matter
# Opens your $EDITOR to write the body

keith [Why Fairy Tales Matter]> publish
Marked 'Why Fairy Tales Matter' published.
```

Everything in keith starts as a `draft`. `publish` and `unpublish` flip that, `book list` marks the drafts, and `book info` shows the status. It's a label for your own benefit — keith doesn't post anything anywhere.

**Export adapts to length.** A book with exactly one chapter exports as plain prose — title, date, body — with no table of contents and no `Chapter 1:` heading:

```markdown
# Why Fairy Tales Matter

*Created: 2026-09-22 | Last updated: 2026-09-22*

Fairy tales do not tell children that dragons exist.
```

Add a second chapter and the table of contents and chapter headings come back. The tradeoff is that a book you've only written one chapter of also exports in the plain style until you write the next one.

## Data storage

Books and chapters are stored in a SQLite database at `~/.keith/keith.db`. Full-text search is powered by SQLite FTS5.

### Using keith on multiple machines

keith itself isn't synced — you install it on each machine and point them all at one shared database file.

1. **Install keith on each machine** using the [Installation](#installation) steps above (`uv sync`, or `uv tool install --editable .` for a global command).
2. **Put the database in a synced folder** — Dropbox, iCloud, OneDrive, or Syncthing. On the first machine, either set `KEITH_DB` before creating anything, or `backup` your existing `~/.keith/keith.db` into the synced folder.
3. **Set `KEITH_DB` to that shared path on every machine** (same file, same folder):

   ```bash
   export KEITH_DB="~/Dropbox/keith/keith.db"
   ```

   Add that line to your `~/.bashrc` / `~/.zshrc` (or a PowerShell profile) so it persists across sessions.

Once the synced folder finishes copying the file to a machine, `keith` there sees the same books, chapters, and notes.

On exit keith checkpoints the write-ahead log back into the `.db` file, so the single file is always self-contained and safe to sync. **Edit from one machine at a time** — like any file-synced SQLite database, concurrent writes on two machines can corrupt it, and you should let the folder finish syncing before opening keith on the next machine. For true simultaneous editing you'd want a hosted libSQL/Turso setup instead.

#### When sync goes wrong

If you open keith before the folder has finished syncing, you'll be writing on top of a stale file, and your sync tool resolves it by parking the losing version in a conflict file — Dropbox as `keith (conflicted copy).db`, Syncthing as `keith.sync-conflict-<timestamp>.db`. Nothing is lost, but the writes in that file are no longer in the database keith reads.

keith can't prevent this — the machine has no way to know a newer version exists before sync delivers it — so instead it checks for those files on startup and warns you:

```
WARNING: your sync tool parked conflicting copies beside keith.db — writes made
on another machine may be missing here:
  ~/Dropbox/keith/keith (conflicted copy).db
Salvage text with 'export', or swap a copy in wholesale with 'restore'.
```

To recover, decide which copy is the one you want. Point `KEITH_DB` at the conflict file temporarily and `export` the chapters you're missing, then paste them back — or if the conflict file is simply the better version, `restore` from it to replace everything. Delete the conflict file once you're done so the warning clears.

OneDrive names its conflicts `keith-<MACHINE>.db`, which is indistinguishable from a backup filename, so those aren't detected.

## Backup and restore

Everything lives in a single SQLite file, so backups are whole-database snapshots (all books, chapters, and notes).

```
keith> backup
Backup to file path: ~/keith-2026-07-04.db
Backed up to ~/keith-2026-07-04.db

keith> restore
Restore from file path: ~/keith-2026-07-04.db
This replaces ALL current data with the backup. Continue? (y/n): y
Restored from ~/keith-2026-07-04.db
```

- `backup` writes a consistent snapshot using SQLite's online backup API — safe to run at any time.
- `restore` **replaces all current data** with the contents of the backup file, so it asks for confirmation first.

This is a full binary snapshot for disaster recovery — distinct from `export`, which produces human-readable markdown of a single book.

## Running tests

```bash
uv run pytest -v
```
