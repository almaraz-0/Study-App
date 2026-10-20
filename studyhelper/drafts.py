"""Draft cards: check them, then turn them into Anki note fields.

Sentences mark the target word with [brackets]: exactly one per sentence.
"""

import html
import re

from studyhelper import config

MARKER = re.compile(r"\[([^\[\]]+)\]")
ACTIONS = {"add", "merge", "tag_only"}


class DraftError(ValueError):
    pass


def _text_values(d):
    for key, value in d.items():
        if isinstance(value, str):
            yield key, value
    for ex in d.get("examples", []):
        yield "examples", ex.get("es", "")
        yield "examples", ex.get("en", "")


def validate(d: dict) -> None:
    did = d.get("id", "?")

    def fail(reason):
        raise DraftError(f"{did}: {reason}")

    if d.get("kind") not in ("vocab", "grammar"):
        fail("kind must be vocab or grammar")
    if d.get("action") not in ACTIONS:
        fail(f"action must be one of {sorted(ACTIONS)}")
    if d["action"] in ("merge", "tag_only") and not d.get("match_note_id"):
        fail(f"{d['action']} needs match_note_id")
    for key, value in _text_values(d):
        if "**" in value:
            fail(f"{key} contains markdown '**'; use <b> or [target] instead")

    if d["kind"] == "vocab":
        for key in ("word", "meaning", "sentence"):
            if not d.get(key, "").strip():
                fail(f"{key} is empty")
        if len(MARKER.findall(d["sentence"])) != 1:
            fail("sentence needs exactly one [target] marker")
        examples = d.get("examples", [])
        if len(examples) != 3:
            fail(f"needs exactly 3 examples, got {len(examples)}")
        for i, ex in enumerate(examples, 1):
            if len(MARKER.findall(ex.get("es", ""))) != 1:
                fail(f"example {i} needs exactly one [target] marker")
    else:
        if not d.get("text") or "{{c1::" not in d["text"]:
            fail("grammar text needs at least one {{c1::...}} cloze")
        if not d.get("rule", "").strip():
            fail("rule is empty")


def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def _esc_allow_bold(s: str) -> str:
    return re.sub(r"&lt;(/?)b&gt;", r"<\1b>", _esc(s))


def mark(s: str) -> str:
    return MARKER.sub(lambda m: f"<b>{m.group(1)}</b>", _esc(s))


def blank(s: str) -> str:
    return MARKER.sub('<span class="blank">[...]</span>', _esc(s))


def example_item(ex: dict) -> str:
    en = f' <span class="en">{_esc(ex["en"])}</span>' if ex.get("en") else ""
    return f"<li>{mark(ex['es'])}{en}</li>"


def vocab_fields(d: dict, recognize: bool) -> dict[str, str]:
    return {
        "Word": _esc(d["word"]),
        "Meaning": _esc(d["meaning"]),
        "Prompt": blank(d["sentence"]),
        "Sentence": mark(d["sentence"]),
        "SentenceEN": _esc(d.get("sentence_en", "")),
        "Tip": _esc_allow_bold(d.get("tip", "")),
        "Examples": "<ul>" + "".join(example_item(ex) for ex in d["examples"]) + "</ul>",
        "Source": _esc(d.get("source", "")),
        "Recognize": "y" if recognize else "",
    }


def grammar_fields(d: dict) -> dict[str, str]:
    return {
        "Text": _esc(d["text"]),
        "Rule": _esc_allow_bold(d["rule"]),
        "Reference": _esc(d.get("reference", "")),
        "Source": _esc(d.get("source", "")),
    }


def normalize_tags(tags) -> list[str]:
    out = []
    for t in tags or []:
        t = t.strip().lower().replace(" ", "_")
        if t and t not in out:
            out.append(t)
    return out


def to_anki_note(d: dict, subject: str) -> dict:
    if d["kind"] == "vocab":
        model = config.VOCAB_MODEL
        fields = vocab_fields(d, d.get("recognize", config.RECOGNIZE_CARDS))
    else:
        model = config.GRAMMAR_MODEL
        fields = grammar_fields(d)
    return {
        "deckName": config.DECKS[subject][d["kind"]],
        "modelName": model,
        "fields": fields,
        "tags": normalize_tags(d.get("tags")),
        # Duplicate control is dedupe's job: a new meaning of the same word is allowed.
        "options": {"allowDuplicate": True},
    }
