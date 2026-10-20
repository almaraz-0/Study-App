"""Find notes that may already cover a draft. Claude judges same vs different meaning."""

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from studyhelper import config
from studyhelper.anki import Anki, AnkiError
from studyhelper.drafts import rule_tag


@dataclass
class Candidate:
    note_id: int
    kind: Literal["vocab", "legacy", "grammar", "archive"]
    summary: str


def _esc(term: str) -> str:
    # Anki search: \ and " must be escaped; * and _ are wildcards; : starts a field search.
    return re.sub(r'([\\"*_:])', r"\\\1", term)


def quote(term: str) -> str:
    return f'"{_esc(term)}"'


def field_term(field: str, value: str) -> str:
    return f'"{field}:{_esc(value)}"'


def _summary(info: dict) -> str:
    values = [f["value"] for f in sorted(info["fields"].values(), key=lambda f: f["order"])]
    text = re.sub(r"<[^>]+>", "", " | ".join(v for v in values if v))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:160]


def _queries(draft: dict) -> list[tuple[str, str]]:
    learn = f'deck:"{config.LEARN_PREFIX}*"'
    archive = f'deck:"{config.ARCHIVE_PREFIX}*"'
    if draft["kind"] == "vocab":
        word = draft["word"]
        return [
            ("vocab", f'note:"{config.VOCAB_MODEL}" {field_term("Word", word)}'),
            ("legacy", f"{learn} tag:{config.LEGACY_TAG} {quote(word)}"),
            ("archive", f"{archive} {quote(word)}"),
        ]
    key = draft["rule_key"]
    return [
        ("grammar", f'note:"{config.GRAMMAR_MODEL}" tag:{rule_tag(key)}'),
        ("archive", f"{archive} {quote(key)}"),
    ]


def find_candidates(anki: Anki, draft: dict) -> list[Candidate]:
    found, seen = [], set()
    for kind, query in _queries(draft):
        ids = [n for n in anki.invoke("findNotes", query=query) if n not in seen]
        if not ids:
            continue
        seen.update(ids)
        for info in anki.invoke("notesInfo", notes=ids):
            found.append(Candidate(info["noteId"], kind, _summary(info)))
    return found


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m studyhelper.dedupe <drafts.json>", file=sys.stderr)
        return 2
    drafts = json.loads(Path(argv[0]).read_text(encoding="utf-8"))["drafts"]
    anki = Anki()
    try:
        anki.ping()
        out = {d["id"]: [asdict(c) for c in find_candidates(anki, d)] for d in drafts}
    except AnkiError as e:
        print(e, file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
