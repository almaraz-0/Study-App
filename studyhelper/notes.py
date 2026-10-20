"""Study notes: one folder per /study run, with run.json (for tools) and note.md (for you)."""

import json
import sys
from datetime import date
from pathlib import Path

from studyhelper import config


def new_run_dir(subject: str, slug: str, today: date | None = None) -> Path:
    base = config.NOTES_DIR / subject
    stem = f"{(today or date.today()).isoformat()}-{slug}"
    run, n = base / stem, 2
    while run.exists():
        run, n = base / f"{stem}-{n}", n + 1
    run.mkdir(parents=True)
    return run


def _load(run: Path, name: str, default=None):
    f = run / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def build_run(run: Path) -> dict:
    source = _load(run, "source.json", {"type": "words", "label": "", "url": None})
    items = _load(run, "items.json", [])
    quiz, results = _load(run, "quiz.json"), _load(run, "results.json")
    drafts = {d["id"]: d for d in _load(run, "approved.json", {"drafts": []})["drafts"]}
    pushed = [r for r in _load(run, "pushed.json", {"results": []})["results"] if not r["error"]]
    carded_keys = set()
    for r in pushed:
        d = drafts.get(r["draft_id"], {})
        carded_keys.add(d.get("word") or d.get("rule_key"))
    return {
        "schema": 1,
        "subject": run.parent.name,
        "date": run.name[:10],
        "slug": run.name[11:],
        "path": "quiz" if quiz and results else "direct",
        "source": source,
        "items": [dict(i, carded=i["key"] in carded_keys) for i in items],
        "quiz": {"questions": quiz["questions"], "results": results} if quiz and results else None,
        "cards": [{"draft_id": r["draft_id"], "note_id": r["note_id"], "action": r["action"]} for r in pushed],
    }


def render_note(meta: dict) -> str:
    src = meta["source"]
    label = src.get("label") or src["type"]
    source = f"[{label}]({src['url']})" if src.get("url") else label
    lines = [f"# {meta['slug'].replace('-', ' ').capitalize()}", "", f"{meta['date']} · {meta['subject']} · {source}", ""]
    if meta["quiz"]:
        res = meta["quiz"]["results"]
        answers = {a["id"]: a for a in res["answers"]}
        lines += ["## Quiz", "", f"Score: **{res['score']} / {res['total']}**", ""]
        for q in meta["quiz"]["questions"]:
            a = answers.get(q["id"], {"given": "", "correct": False, "accent_only": False})
            mark = "✓" if a["correct"] else "✗"
            detail = "" if a["correct"] and not a["accent_only"] else f" (you: {a['given'] or 'blank'} · answer: {q['answer']})"
            lines.append(f"- {mark} {q['prompt'].replace('___', q['answer'])}{detail}")
        lines.append("")
    lines += ["## Items", ""]
    for i in meta["items"]:
        lines.append(f"- [{'x' if i['carded'] else ' '}] **{i['key']}**: {i.get('summary', '')}")
    lines += ["", "## Cards added", ""]
    if meta["cards"]:
        lines += [f"- {c['draft_id']} → note {c['note_id']} ({c['action']})" for c in meta["cards"]]
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def write_run(run_dir: Path) -> Path:
    run = Path(run_dir)
    meta = build_run(run)
    (run / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    note = run / "note.md"
    note.write_text(render_note(meta), encoding="utf-8")
    return note


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 3 and argv[0] == "new":
        print(new_run_dir(argv[1], argv[2]))
        return 0
    if len(argv) == 2 and argv[0] == "write":
        print(write_run(Path(argv[1])))
        return 0
    print("usage: python -m studyhelper.notes new <subject> <slug> | write <run_dir>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
