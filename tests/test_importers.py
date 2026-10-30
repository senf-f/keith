import pytest

from keith.importers import (
    FetchResult, Imported, RawItem, SourceError, SourceReport, format_report, run_import,
)


class FakeSource:
    def __init__(self, name, items, raise_error=None):
        self.name = name
        self.items = items
        self.raise_error = raise_error
        self.acked = []

    def fetch(self):
        if self.raise_error:
            raise self.raise_error
        return FetchResult(list(self.items))

    def acknowledge(self, failed_keys):
        self.acked.append(set(failed_keys))


def item(key, text, created_at="2026-01-02T03:04:05.000006+00:00"):
    return RawItem("Fake", key, text, created_at)


def test_imports_and_routes(db):
    book = db.create_book("Orthodoxy")
    src = FakeSource("Fake", [item("1", "#orthodoxy hi")])
    [report] = run_import(db, [src], None)
    assert report.imported == [Imported("Orthodoxy", "idea", "hi")]
    assert [n.content for n in db.list_notes(book.id)] == ["hi"]
    assert src.acked == [set()]


def test_duplicates_counted_as_already(db):
    db.create_book("Orthodoxy")
    src = FakeSource("Fake", [item("1", "#orthodoxy hi")])
    run_import(db, [src], None)
    [report] = run_import(db, [src], None)
    assert report.imported == []
    assert report.already == 1


def test_untagged_without_active_goes_to_inbox(db):
    [report] = run_import(db, [FakeSource("Fake", [item("1", "loose thought")])], None)
    assert report.imported[0].book_title == "Inbox"


def test_all_tagged_creates_no_inbox(db):
    db.create_book("Orthodoxy")
    run_import(db, [FakeSource("Fake", [item("1", "#orthodoxy hi")])], None)
    assert [b.title for b in db.list_books()] == ["Orthodoxy"]


def test_untagged_goes_to_active_book(db):
    book = db.create_book("Orthodoxy")
    [report] = run_import(db, [FakeSource("Fake", [item("1", "hi")])], book)
    assert report.imported[0].book_title == "Orthodoxy"


def test_send_date_kept(db):
    book = db.create_book("Orthodoxy")
    run_import(db, [FakeSource("Fake", [item("1", "#orthodoxy hi")])], None)
    assert db.list_notes(book.id)[0].created_at == "2026-01-02T03:04:05.000006+00:00"


def test_failed_item_reported_and_acknowledged_as_failed(db, monkeypatch):
    book = db.create_book("Orthodoxy")
    real = db.create_imported_note

    def flaky(source, key, *args, **kwargs):
        if key == "bad":
            raise RuntimeError("boom")
        return real(source, key, *args, **kwargs)

    monkeypatch.setattr(db, "create_imported_note", flaky)
    src = FakeSource("Fake", [item("bad", "#orthodoxy a"), item("ok", "#orthodoxy b")])
    [report] = run_import(db, [src], None)
    assert [i.label for i in report.imported] == ["b"]
    assert src.acked == [{"bad"}]
    assert "bad:" in report.problems[0]
    assert [n.content for n in db.list_notes(book.id)] == ["b"]


def test_tags_only_item_is_skipped_not_recorded(db):
    book = db.create_book("Orthodoxy")
    src = FakeSource("Fake", [item("1", "#orthodoxy #idea")])
    [report] = run_import(db, [src], None)
    assert report.skipped == {"no text": 1}
    assert report.imported == []
    assert not db.is_imported("Fake", "1")
    assert db.list_notes(book.id) == []
    assert src.acked == [set()]


def test_source_error_isolated(db):
    db.create_book("Orthodoxy")
    bad = FakeSource("Bad", [], raise_error=SourceError("down"))
    good = FakeSource("Fake", [item("1", "#orthodoxy hi")])
    bad_report, good_report = run_import(db, [bad, good], None)
    assert bad_report.error == "down"
    assert bad.acked == []
    assert len(good_report.imported) == 1


def test_fetch_result_defaults_not_shared():
    a, b = FetchResult([]), FetchResult([])
    a.skipped["x"] = 1
    a.problems.append("p")
    assert b.skipped == {} and b.problems == []


SPEC_OUTPUT = """\
Telegram: 4 imported, 1 skipped (no text)
  → Orthodoxy / character   Syme is a poet who hates disorder
  → Orthodoxy / idea        the madman has lost everything except his reason
  → Inbox / idea            maybe a story about a lighthouse keeper
  → Thursday / place        Saffron Park
Obsidian: 1 imported, 2 already imported
  → Inbox / idea            Dragons and fairy tales
Obsidian: skipped "draft.md" — not valid UTF-8
5 notes added. 2 went to Inbox — file them with 'note move'."""


def test_format_report_matches_spec_example():
    reports = [
        SourceReport("Telegram", [
            Imported("Orthodoxy", "character", "Syme is a poet who hates disorder"),
            Imported("Orthodoxy", "idea", "the madman has lost everything except his reason"),
            Imported("Inbox", "idea", "maybe a story about a lighthouse keeper"),
            Imported("Thursday", "place", "Saffron Park"),
        ], 0, {"no text": 1}, [], None),
        SourceReport("Obsidian", [Imported("Inbox", "idea", "Dragons and fairy tales")],
                     2, {}, ['skipped "draft.md" — not valid UTF-8'], None),
    ]
    assert format_report(reports, []) == SPEC_OUTPUT


def test_format_report_nothing_new():
    out = format_report([SourceReport("Telegram", [], 0, {}, [], None)], [])
    assert out.endswith("No new notes.")
    assert out.splitlines()[0] == "Telegram: 0 imported"


def test_format_report_singular_error_and_not_configured():
    reports = [
        SourceReport("Obsidian", [], 0, {}, [], "folder missing"),
        SourceReport("Telegram", [Imported("Orthodoxy", "idea", "x")], 0, {}, [], None),
    ]
    out = format_report(reports, ["Telegram: not configured (set KEITH_TELEGRAM_TOKEN)"])
    lines = out.splitlines()
    assert lines[0] == "Telegram: not configured (set KEITH_TELEGRAM_TOKEN)"
    assert "Obsidian: folder missing" in lines
    assert lines[-1] == "1 note added."
