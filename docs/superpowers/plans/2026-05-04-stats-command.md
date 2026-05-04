# Stats Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `stats` REPL command that shows per-chapter word counts with percentages and a book total.

**Architecture:** A `word_count()` helper function and a `stats()` method on the existing `CommandHandler` class. REPL gets dispatch + help entry. No new files, no new tables.

**Tech Stack:** Python 3.10+, existing keith codebase

---

## File Map

| File | Change |
|---|---|
| `src/keith/commands.py` | Add `word_count(text)` helper, add `stats()` method to `CommandHandler` |
| `src/keith/repl.py` | Add `"stats"` to COMMANDS, add dispatch case, add to HELP_TEXT |
| `tests/test_commands.py` | Add tests for `stats` (multiple chapters, no chapters, empty content, no active book) |

---

### Task 1: Add Tests for Stats Command

**Files:**
- Modify: `tests/test_commands.py`

- [ ] **Step 1: Add stats tests to test_commands.py**

Append these tests to `tests/test_commands.py`:

```python
def test_stats_no_active_book(handler, capsys):
    handler.stats()
    out = capsys.readouterr().out
    assert "No book selected" in out


def test_stats_no_chapters(handler, capsys):
    book = handler.db.create_book("Empty Book")
    handler.active_book = book
    handler.stats()
    out = capsys.readouterr().out
    assert "No chapters yet." in out


def test_stats_multiple_chapters(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Ch 1", "one two three four five")
    handler.db.create_chapter(book.id, "Ch 2", "one two three")
    handler.db.create_chapter(book.id, "Ch 3", "one two")
    handler.stats()
    out = capsys.readouterr().out
    assert "Ch 1" in out
    assert "5 words" in out
    assert "(50%)" in out
    assert "Ch 2" in out
    assert "3 words" in out
    assert "(30%)" in out
    assert "Ch 3" in out
    assert "2 words" in out
    assert "(20%)" in out
    assert "10 words" in out


def test_stats_empty_content(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Empty Chapter", "")
    handler.db.create_chapter(book.id, "Has Words", "hello world")
    handler.stats()
    out = capsys.readouterr().out
    assert "0 words" in out
    assert "2 words" in out
    assert "(0%)" in out
    assert "(100%)" in out


def test_stats_single_chapter(handler, capsys):
    book = handler.db.create_book("Novel")
    handler.active_book = book
    handler.db.create_chapter(book.id, "Only Chapter", "word word word")
    handler.stats()
    out = capsys.readouterr().out
    assert "Only Chapter" in out
    assert "3 words" in out
    assert "(100%)" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_commands.py::test_stats_no_active_book -v`

Expected: FAIL with `AttributeError: 'CommandHandler' object has no attribute 'stats'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_commands.py
git -c user.email=mate.mrse@gmail.com commit -m "test: add tests for stats command"
```

---

### Task 2: Implement Stats Command

**Files:**
- Modify: `src/keith/commands.py`

- [ ] **Step 1: Add `word_count` helper and `stats` method**

Add the `word_count` function after the imports (before the `CommandHandler` class):

```python
def word_count(text: str) -> int:
    return len(text.split())
```

Add this method to the `CommandHandler` class, after the `export` method:

```python
    # -- Stats --

    def stats(self) -> None:
        if not self._require_active_book():
            return
        chapters = self.db.list_chapters(self.active_book.id)
        if not chapters:
            print("No chapters yet.")
            return

        counts = [(ch.title, word_count(ch.content)) for ch in chapters]
        total = sum(c for _, c in counts)

        title_width = max(len(title) for title, _ in counts)
        for i, (title, count) in enumerate(counts, 1):
            pct = round(count / total * 100) if total > 0 else 0
            print(f"  {i}. {title:<{title_width}}  {count:,} words  ({pct}%)")

        separator_width = title_width + 30
        print(f"  {'─' * separator_width}")
        print(f"  {'Total':<{title_width + 3}} {total:,} words")
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_commands.py -k stats -v`

Expected: all 5 stats tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/keith/commands.py
git -c user.email=mate.mrse@gmail.com commit -m "feat: add stats command with word counts and percentages"
```

---

### Task 3: Wire Stats Into REPL

**Files:**
- Modify: `src/keith/repl.py`

- [ ] **Step 1: Add "stats" to COMMANDS list**

In `src/keith/repl.py`, change the `COMMANDS` list to include `"stats"`:

```python
COMMANDS = [
    "book new", "book list", "book select", "book info", "book delete",
    "add chapter", "list chapters", "edit chapter", "show chapter",
    "move chapter", "delete chapter",
    "search", "export", "stats", "help", "exit", "quit",
]
```

- [ ] **Step 2: Add stats to HELP_TEXT**

In the `HELP_TEXT` string, add `stats` to the "Other" section:

```python
  Other:
    export          Export active book to markdown
    stats           Show word count per chapter
    help            Show this help
    exit / quit     Leave keith
```

- [ ] **Step 3: Add dispatch case**

In the `while True` loop, add a dispatch case for `stats`. Insert it after the `elif text == "export":` block:

```python
        elif text == "stats":
            handler.stats()
```

- [ ] **Step 4: Verify the REPL imports and runs**

Run: `uv run python -c "from keith.repl import COMMANDS; assert 'stats' in COMMANDS; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/keith/repl.py
git -c user.email=mate.mrse@gmail.com commit -m "feat: wire stats command into REPL dispatch and help"
```
