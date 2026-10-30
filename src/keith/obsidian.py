from datetime import datetime, timezone
from pathlib import Path

from keith.importers import FetchResult, RawItem, SourceError


def _clean_tag(raw: str) -> str:
    return raw.strip().strip("'\"").lstrip("#").strip()


def split_front_matter(text: str) -> tuple[list[str], str]:
    """Return (tags, body) with a leading ---/--- block removed.

    Only the `tags:` field is read: `[a, b]`, a `- a` list, or a bare value.
    """
    lines = text.lstrip("﻿").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return [], text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return [], text

    tags: list[str] = []
    in_list = False
    for line in lines[1:end]:
        stripped = line.strip()
        if line.startswith("tags:"):
            value = line[len("tags:"):].strip()
            in_list = value == ""
            if value.startswith("[") and value.endswith("]"):
                value = value[1:-1]
                tags.extend(_clean_tag(t) for t in value.split(","))
            elif value:
                tags.append(_clean_tag(value))
        elif in_list and stripped.startswith("-"):
            tags.append(_clean_tag(stripped[1:]))
        elif stripped:
            in_list = False
    return [t for t in tags if t], "".join(lines[end + 1:])


class ObsidianSource:
    name = "Obsidian"

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def fetch(self) -> FetchResult:
        folder = self.folder
        if not folder.exists():
            raise SourceError(f"folder not found: {folder}")
        if not folder.is_dir():
            raise SourceError(f"not a folder: {folder}")

        result = FetchResult([])
        files = sorted(
            (p for p in folder.glob("*.md") if p.is_file() and not p.name.startswith(".")),
            key=lambda p: p.name,
        )
        for path in files:
            try:
                raw = path.read_bytes().decode("utf-8")
                mtime = path.stat().st_mtime
            except UnicodeDecodeError:
                result.problems.append(f'skipped "{path.name}" — not valid UTF-8')
                continue
            except OSError as exc:
                result.problems.append(f'skipped "{path.name}" — {exc.strerror or exc}')
                continue
            tags, body = split_front_matter(raw)
            body = body.strip()
            if not body:
                result.skipped["empty"] = result.skipped.get("empty", 0) + 1
                continue
            parts = []
            first = body.split("\n", 1)[0].strip()
            if first.removeprefix("# ").strip() != path.stem:
                parts.append(path.stem)
            parts.append(body)
            if tags:
                parts.append(" ".join(f"#{t}" for t in tags))
            created_at = datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="microseconds")
            result.items.append(RawItem(self.name, path.name, "\n".join(parts), created_at))
        return result
