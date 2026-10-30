# keith

A CLI tool for writing and organizing books. Named after G.K. Chesterton.

> "A good novel tells us the truth about its hero; but a bad novel tells us the truth about its author."
> — G.K. Chesterton

## Features

- **Interactive REPL** with command autocomplete and history
- **Multiple books** in a single library
- **Chapter management** with ordering, editing via `$EDITOR`, and display
- **Notes** per book (ideas, outline, characters, places) — searchable but never exported
- **Capture import** — pull ideas from a Telegram bot or an Obsidian folder straight into notes
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
uv run keith pull [source] # Import notes from Telegram / Obsidian
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
| `note move` | Move a note to another book |
| `note delete` | Delete a note |
| `pull` | Import notes from every configured source (Telegram, Obsidian) |
| `pull <source>` | Import from one source: `telegram` or `obsidian` |
| `search <query>` | Full-text search across all books |
| `search --title <query>` | Search titles only |
| `search --book <id> <query>` | Search within a specific book |
| `search --from <date> --to <date> <query>` | Search with date range |
| `export` | Export active book to markdown |
| `backup` | Back up the entire database to a file |
| `restore` | Replace all data from a backup file |
| `help` | Show available commands |
| `exit` | Leave keith |

### Search

Every word of the query must appear, and words are matched literally — `self-help`, `don't` and `"quoted"` are all fine to type, and there are no `AND`/`OR`/`*` operators. With `--title`, every word must be in the chapter title.

Dates are `YYYY-MM-DD` and both ends are inclusive: `search --from 2026-04-01 --to 2026-04-03 madman` finds chapters created on April 1st through the whole of April 3rd. A shorter prefix works too — `--from 2026-04 --to 2026-04` means all of April.

### Editor

keith opens `$VISUAL`, then `$EDITOR`, falling back to `notepad` on Windows and `vi` elsewhere. The value may include arguments, so GUI editors that need to block until you close the file work:

```bash
export EDITOR="code --wait"
```

If the editor can't be started or exits with an error, keith reports "Editor failed" and saves nothing.

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

## Capturing ideas

Ideas get jotted on the go. `pull` brings them in from a Telegram bot and an Obsidian inbox folder and files each one as a note — no retyping. Message the bot during the day, run `pull` in the evening, and every idea is already under the right book and category.

Imports are always notes (never chapters), one per message or file, and a one-time copy: editing the original later changes nothing in keith. Settings come from environment variables, like `KEITH_DB`, and are never stored in the database. Set whichever sources you use; a source you haven't set up is just reported as not configured.

```
keith> pull              # every configured source
keith> pull telegram     # just one
keith> pull obsidian
```

Or from the command line: `uv run keith pull [source]`. There is no active book on the command line, so untagged items go to Inbox (see [Routing](#routing)).

### Telegram setup

1. In Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`, and follow the prompts. It gives you a bot token.
2. Set `KEITH_TELEGRAM_TOKEN` to that token. **The token is a secret** — anyone who has it controls your bot. Keep it in your shell profile or environment, never in a repository. keith never prints it.

   ```bash
   export KEITH_TELEGRAM_TOKEN="123456:ABC..."
   ```

   ```powershell
   $env:KEITH_TELEGRAM_TOKEN = "123456:ABC..."
   ```

3. Send your bot a message, then find your numeric Telegram user ID by running `pull` once without `KEITH_TELEGRAM_USER`. keith imports nothing and acknowledges nothing, so no message is lost; it just lists who has written to the bot:

   ```
   keith> pull telegram
   Telegram: set KEITH_TELEGRAM_USER to import. Senders waiting:
     123456789  Anna (2 messages)
   No new notes.
   ```

4. Set `KEITH_TELEGRAM_USER` to your ID and `pull` again:

   ```bash
   export KEITH_TELEGRAM_USER="123456789"
   ```

   ```powershell
   $env:KEITH_TELEGRAM_USER = "123456789"
   ```

Only messages from that ID are imported; messages from anyone else are dropped, and the report counts them. A photo or voice message with a caption imports the caption; a sticker or an uncaptioned photo is skipped ("no text"). Edited messages are ignored. Each note is dated by when you sent the message, so `search --from/--to` works by when the idea was written.

The bot must not have a webhook set — if it does, `pull` says "remove the bot's webhook".

### Obsidian setup

Set `KEITH_OBSIDIAN_INBOX` to a folder (`~` works):

```bash
export KEITH_OBSIDIAN_INBOX="~/Vault/Inbox"
```

```powershell
$env:KEITH_OBSIDIAN_INBOX = "$HOME\Vault\Inbox"
```

- Only `.md` files directly in that folder are read — subfolders, other file types and `.obsidian/` are ignored. keith never writes to, moves or deletes anything in your vault.
- The filename becomes the note's first line, unless the file already opens with that line.
- A leading front-matter block is removed. Its `tags:` field (as `[a, b]` or a `- a` list) is routed as if you had written `#a`; other fields are dropped.
- `[[links]]` stay as plain text and attachments are not copied.
- The note is dated by the file's modification time.
- Empty files are skipped and picked up once you fill them. A file that isn't valid UTF-8 is reported and skipped.

### Routing

Hashtags in the text choose the book and category:

- A tag is `#` at the start of the text or after whitespace, followed by letters, digits, `_` or `-`, case-insensitive. `C#`, `issue#4` and `page#intro` are not tags, and neither are nested tags like `#orthodoxy/characters`. Only the tag itself and the blank beside it are removed; the rest of the note keeps its spacing and indentation.
- **Category:** `#idea`, `#outline`, `#character`, `#place` or `#other`. The first one wins; with none, the category is `idea`. These names are reserved, so a book titled "Outline" can't be addressed as `#outline`.
- **Book:** a tag matches a book when it is the book's title in lowercase with hyphens between words and punctuation dropped — `#orthodoxy`, `#the-man-who-was-thursday`.
- Matched tags are removed from the note; any other tag stays in the text.
- Exactly one book tag files the note under that book. No book tag files it under the active book. With no book tag and no active book — or with two or more different book tags — it goes to Inbox, with all its tags left in the text so nothing is lost.

For example, with books called Orthodoxy and Thursday:

| Text | Book | Category | Note text |
|---|---|---|---|
| `#orthodoxy #character Syme is a poet who hates disorder` | Orthodoxy | character | `Syme is a poet who hates disorder` |
| `the madman has lost everything except his reason #orthodoxy` | Orthodoxy | idea | `the madman has lost everything except his reason` |
| `maybe a story about a lighthouse keeper` (no active book) | Inbox | idea | unchanged |
| `#orthodoxy #thursday compare the two villains` | Inbox | idea | unchanged, both tags kept |
| `Rewrite in C# #other` | active book, or Inbox | other | `Rewrite in C#` |

### Inbox and `note move`

Notes that can't be routed land in a book called **Inbox**, created the first time it's needed. If you already have a book with that exact title, it is reused. Use `note move` to file a note into the right book: it asks which note, then which book.

```
keith [Inbox]> note move
Move which note? (number): 1
Move to book number: 2
Moved note to 'Orthodoxy'.
```

(The prompts also list the notes and books to choose from.) Search by the new book's title finds the moved note straight away.

### What `pull` prints

Each source prints one summary line, then one `→ book / category   label` line per imported note, and a final total. A source that isn't set up prints `<Source>: not configured (set <VAR>)`. This is a real run of `pull obsidian` against a folder holding two files:

```
keith> pull obsidian
Obsidian: 2 imported
  → Inbox / idea            Fairy tales
  → Orthodoxy / character   Syme
2 notes added. 1 went to Inbox — file them with 'note move'.
```

With both sources configured it looks like this (illustrative):

```
keith> pull
Telegram: 4 imported, 1 skipped (no text)
  → Orthodoxy / character   Syme is a poet who hates disorder
  → Orthodoxy / idea        the madman has lost everything except his reason
  → Inbox / idea            maybe a story about a lighthouse keeper
  → Thursday / place        Saffron Park
Obsidian: 1 imported, 2 already imported
  → Inbox / idea            Dragons and fairy tales
Obsidian: skipped "draft.md" — not valid UTF-8
5 notes added. 2 went to Inbox — file them with 'note move'.
```

Sources run independently, and one bad item doesn't stop the rest, so re-running `pull` after any failure is safe: anything already imported is skipped. A deleted imported note stays deleted.

### Caveats

- **Renaming an Obsidian file re-imports it.** keith remembers files by name, so a renamed file looks new. Editing a file does nothing.
- **Telegram keeps unfetched bot messages for only 24 hours.** Run `pull` at least daily or older messages are gone.
- **One pull takes at most 100 Telegram messages.** Run `pull` again for the rest.
- Machines sharing one `KEITH_DB` never import the same item twice.

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

keith can't prevent this — the machine has no way to know a newer version exists before sync delivers it — so instead it checks for those files on startup and warns you. Only copies of the database itself count (same name and `.db` extension), so other conflicted files in the folder don't trigger it:

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
Backed up to /home/you/keith-2026-07-04.db

keith> restore
Restore from file path: ~/keith-2026-07-04.db
This replaces ALL current data with the backup. Continue? (y/n): y
Restored from /home/you/keith-2026-07-04.db
```

Paths may start with `~` for your home directory, on every platform.

- `backup` writes a consistent snapshot using SQLite's online backup API — safe to run at any time.
- `restore` **replaces all current data** with the contents of the backup file, so it asks for confirmation first.

This is a full binary snapshot for disaster recovery — distinct from `export`, which produces human-readable markdown of a single book.

## Running tests

```bash
uv run pytest -v
```
