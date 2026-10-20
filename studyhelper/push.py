"""Write approved drafts into Anki. Safe to re-run.

Each added note carries a run tag (sh::<run>::<draft id>). Before adding, push looks
for that tag, so a crash, a lost reply or a lost pushed.json never creates a duplicate.
"""

import fcntl
import json
import os
import sys
from pathlib import Path

from studyhelper.anki import Anki, AnkiError
from studyhelper.drafts import DraftError, example_item, normalize_tags, slug_tag, to_anki_note, validate
from studyhelper.notetypes import ensure_models


def run_tag(run_id: str, draft_id: str) -> str:
    return slug_tag("sh::", run_id) + "::" + slug_tag("", draft_id)


def _append_example(examples_html: str, item: str) -> str:
    if item in examples_html:  # already merged on an earlier run
        return examples_html
    if examples_html.rstrip().endswith("</ul>"):
        head = examples_html.rstrip()[: -len("</ul>")]
        return head + item + "</ul>"
    return examples_html + f"<ul>{item}</ul>"


def _push_one(anki: Anki, d: dict, subject: str, run_id: str) -> int:
    action = d["action"]
    if action == "add":
        note = to_anki_note(d, subject)
        if run_id:
            tag = run_tag(run_id, d["id"])
            existing = anki.invoke("findNotes", query=f"tag:{tag}")
            if existing:
                return existing[0]
            note["tags"].append(tag)
        return anki.invoke("addNote", note=note)
    nid = d["match_note_id"]
    if action == "merge":
        [info] = anki.invoke("notesInfo", notes=[nid])
        if not info:
            raise AnkiError(f"note {nid} no longer exists in Anki")
        current = info["fields"].get("Examples", {}).get("value", "")
        item = example_item({"es": d["sentence"], "en": d.get("sentence_en", "")})
        updated = _append_example(current, item)
        if updated != current:
            anki.invoke("updateNoteFields", note={"id": nid, "fields": {"Examples": updated}})
    tags = normalize_tags(d.get("tags"))
    if tags:
        anki.invoke("addTags", notes=[nid], tags=" ".join(tags))
    return nid


def push(anki: Anki, approved: dict, subject: str, already: set[str], run_id: str = "", on_result=None) -> list[dict]:
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
            nid, error = _push_one(anki, d, subject, run_id), None
        except Exception as e:  # record and move on; one bad draft never stops the rest
            nid, error = None, str(e) or type(e).__name__
        result = {"draft_id": d["id"], "note_id": nid, "action": d["action"], "error": error}
        results.append(result)
        if on_result:
            on_result(result)
    return results


def summarize(results: list[dict]) -> str:
    ok = [r for r in results if not r["error"]]
    count = lambda a: sum(1 for r in ok if r["action"] == a)
    failed = [r for r in results if r["error"]]
    lines = [f"Added {count('add')} · merged {count('merge')} · tagged {count('tag_only')} · failed {len(failed)}"]
    lines += [f"  {r['draft_id']}: {r['error']}" for r in failed]
    return "\n".join(lines)


def _write_atomic(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m studyhelper.push <run_dir>", file=sys.stderr)
        return 2
    run = Path(argv[0])
    with open(run / ".push.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another push for this run is still going. Wait for it to finish.", file=sys.stderr)
            return 1
        approved = json.loads((run / "approved.json").read_text(encoding="utf-8"))
        drafts_file = run / "drafts.json"
        subject = json.loads(drafts_file.read_text(encoding="utf-8")).get("subject", "spanish") if drafts_file.exists() else "spanish"
        pushed_file = run / "pushed.json"
        previous = json.loads(pushed_file.read_text(encoding="utf-8"))["results"] if pushed_file.exists() else []
        record = {r["draft_id"]: r for r in previous}
        already = {r["draft_id"] for r in previous if not r["error"]}

        def save(result):
            record[result["draft_id"]] = result
            _write_atomic(pushed_file, {"results": list(record.values())})

        try:
            results = push(Anki(), approved, subject, already, run_id=run.name, on_result=save)
        except (AnkiError, DraftError) as e:
            print(e, file=sys.stderr)
            return 1
        skipped = len([d for d in approved["drafts"] if d["id"] in already])
        print(summarize(results) + (f"\n  ({skipped} already pushed earlier, skipped)" if skipped else ""))
        return 1 if any(r["error"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
