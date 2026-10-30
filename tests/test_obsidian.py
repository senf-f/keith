import os

import pytest

from keith.importers import SourceError
from keith.obsidian import ObsidianSource, split_front_matter


def fetch(folder):
    return ObsidianSource(folder).fetch()


def test_reads_only_md_files_directly_in_folder(tmp_path):
    (tmp_path / "a.md").write_bytes(b"alpha")
    (tmp_path / "a.txt").write_bytes(b"nope")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.md").write_bytes(b"nope")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "x.md").write_bytes(b"nope")
    (tmp_path / "b.md.icloud").write_bytes(b"nope")
    (tmp_path / ".hidden.md").write_bytes(b"nope")
    result = fetch(tmp_path)
    assert [i.key for i in result.items] == ["a.md"]
    assert result.items[0].source == "Obsidian"


def test_title_line_added_from_filename(tmp_path):
    (tmp_path / "Dragons.md").write_bytes(b"fairy tales")
    item = fetch(tmp_path).items[0]
    assert item.text.startswith("Dragons\n")
    assert "fairy tales" in item.text


def test_title_not_duplicated(tmp_path):
    (tmp_path / "Ideas.md").write_bytes(b"\n# Ideas\nmore")
    item = fetch(tmp_path).items[0]
    assert item.text.count("Ideas") == 1


def test_front_matter_tags_both_forms(tmp_path):
    assert split_front_matter("---\ntags: [orthodoxy, #character]\n---\nbody") == (
        ["orthodoxy", "character"], "body")
    assert split_front_matter("---\ntags:\n  - orthodoxy\n  - #idea\n---\nbody") == (
        ["orthodoxy", "idea"], "body")
    assert split_front_matter("---\ntags: orthodoxy\n---\nbody") == (["orthodoxy"], "body")
    assert split_front_matter("no front matter") == ([], "no front matter")
    (tmp_path / "N.md").write_bytes(b"---\ntags: [orthodoxy, character]\n---\nbody")
    item = fetch(tmp_path).items[0]
    assert item.text.splitlines()[-1].split() == ["#orthodoxy", "#character"]


def test_front_matter_with_crlf(tmp_path):
    (tmp_path / "N.md").write_bytes(b"---\r\ntags: [orthodoxy]\r\n---\r\nbody")
    item = fetch(tmp_path).items[0]
    assert "---" not in item.text
    assert "#orthodoxy" in item.text


def test_empty_file_skipped(tmp_path):
    (tmp_path / "e.md").write_bytes(b"---\ntags: [x]\n---\n  \n")
    result = fetch(tmp_path)
    assert result.skipped == {"empty": 1}
    assert result.items == []


def test_non_utf8_reported(tmp_path):
    (tmp_path / "bad.md").write_bytes(b"\xff\xfe")
    result = fetch(tmp_path)
    assert result.problems == ['skipped "bad.md" — not valid UTF-8']
    assert result.items == []


def test_missing_folder_raises(tmp_path):
    with pytest.raises(SourceError, match="folder not found"):
        fetch(tmp_path / "nope")


def test_file_instead_of_folder_raises(tmp_path):
    f = tmp_path / "f.md"
    f.write_bytes(b"x")
    with pytest.raises(SourceError, match="not a folder"):
        fetch(f)


def test_created_at_is_mtime_utc_iso(tmp_path):
    p = tmp_path / "a.md"
    p.write_bytes(b"x")
    os.utime(p, (86400, 86400))
    assert fetch(tmp_path).items[0].created_at == "1970-01-02T00:00:00.000000+00:00"


def test_vault_untouched(tmp_path):
    p = tmp_path / "a.md"
    p.write_bytes(b"x")
    before = (p.stat().st_mtime_ns, sorted(os.listdir(tmp_path)))
    fetch(tmp_path)
    assert (p.stat().st_mtime_ns, sorted(os.listdir(tmp_path))) == before


def test_bom_is_stripped_and_title_not_duplicated(tmp_path):
    (tmp_path / "Ideas.md").write_bytes(b"\xef\xbb\xbf# Ideas\nmore")
    assert [i.text for i in fetch(tmp_path).items] == ["# Ideas\nmore"]
