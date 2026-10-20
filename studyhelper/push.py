"""Write approved drafts into Anki. Safe to re-run: drafts already pushed are skipped."""

import json
import sys
from pathlib import Path

from studyhelper.anki import Anki, AnkiError
from studyhelper.drafts import DraftError, example_item, normalize_tags, to_anki_note, validate
from studyhelper.notetypes import ensure_models


def _append_example(examples_html: str, item: str) -> str:
    if examples_html.rstrip().endswith("</ul>"):
        head = examples_html.rstrip()[: -len("</ul>")]
        return head + item + "</ul>"
    return examples_html + f"<ul>{item}</ul>"


def _push_one(anki: Anki, d: dict, subject: str) -> int:
    action = d["action"]
    if action == "add":
        return anki.invoke("addNote", note=to_anki_note(d, subject))
    nid = d["match_note_id"]
    if action == "merge":
        [info] = anki.invoke("notesInfo", notes=[nid])
        current = info["fields"].get("Examples", {}).get("value", "")
        item = example_item({"es": d["sentence"], "en": d.get("sentence_en", "")})
        anki.invoke("updateNoteFields", note={"id": nid, "fields": {"Examples": _append_example(current, item)}})
    tags = normalize_tags(d.get("tags"))
    if tags:
        anki.invoke("addTags", notes=[nid], tags=" ".join(tags))
    return nid


def push(anki: Anki, approved: dict, subject: str, already: set[str]) -> list[dict]:
    anki.ping()
    todo = [d for d in approved["drafts"] if d["id"] not in already]
    for d in todo:  # every draft is checked before anything is written
        validate(d)
    if not todo:
        return []
    ensure_models(anki)
    for deck in sorted({to_anki_note(d, subject)["deckName"] for d in todo if d["action"] == "add"}):
        anki.invoke("createDeck", deck=deck)  # no-op when it exists; addNote fails on a missing deck
    results = []
    for d in todo:
        try:
            nid, error = _push_one(anki, d, subject), None
        except AnkiError as e:
            nid, error = None, str(e)
        results.append({"draft_id": d["id"], "note_id": nid, "action": d["action"], "error": error})
    return results


def summarize(results: list[dict]) -> str:
    ok = [r for r in results if not r["error"]]
    count = lambda a: sum(1 for r in ok if r["action"] == a)
    failed = [r for r in results if r["error"]]
    lines = [f"Added {count('add')} · merged {count('merge')} · tagged {count('tag_only')} · failed {len(failed)}"]
    lines += [f"  {r['draft_id']}: {r['error']}" for r in failed]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m studyhelper.push <run_dir>", file=sys.stderr)
        return 2
    run = Path(argv[0])
    approved = json.loads((run / "approved.json").read_text(encoding="utf-8"))
    drafts_file = run / "drafts.json"
    subject = json.loads(drafts_file.read_text(encoding="utf-8")).get("subject", "spanish") if drafts_file.exists() else "spanish"
    pushed_file = run / "pushed.json"
    previous = json.loads(pushed_file.read_text(encoding="utf-8"))["results"] if pushed_file.exists() else []
    already = {r["draft_id"] for r in previous if not r["error"]}
    try:
        results = push(Anki(), approved, subject, already)
    except (AnkiError, DraftError) as e:
        print(e, file=sys.stderr)
        return 1
    merged = {r["draft_id"]: r for r in previous}
    merged.update({r["draft_id"]: r for r in results})
    pushed_file.write_text(json.dumps({"results": list(merged.values())}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summarize(results))
    return 1 if any(r["error"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
