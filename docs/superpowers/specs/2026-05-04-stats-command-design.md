# Stats Command — Word Count & Progress

A REPL command that shows per-chapter word counts with percentages and a book total.

## Behavior

`stats` requires an active book. It derives word counts from existing chapter content — no new tables or persistence.

Output format:

```
  1. The Two Poets         1,243 words  (34%)
  2. The Secret of Syme      892 words  (24%)
  3. The Council            1,540 words  (42%)
  ─────────────────────────────────────────────
  Total                    3,675 words
```

Word counting: `len(content.split())`.

## Edge Cases

- Empty chapter content: 0 words
- Single chapter: shows 100%
- No chapters: prints "No chapters yet."
- All chapters empty: total is 0, percentages show 0%

## Formatting

- Chapter names right-padded for column alignment
- Word counts use thousands separator (comma)
- Percentages rounded to nearest integer
- Separator line (─) between chapter list and total

## Changes

| File | Change |
|---|---|
| `src/keith/commands.py` | Add `word_count(text)` helper function, add `stats()` method to `CommandHandler` |
| `src/keith/repl.py` | Add `"stats"` to `COMMANDS` list, add dispatch case, add to help text |
| `tests/test_commands.py` | Add tests for `stats` output (multiple chapters, no chapters, empty content) |

## Non-Goals

- No daily goals or session tracking
- No changes to existing commands (`book info`, `list chapters`)
- No new database tables or schema changes
- No non-interactive CLI subcommand (REPL only)
