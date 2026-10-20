---
name: study
description: Turn what Bryan is studying into reviewed Anki cards. Use for "/study", "make Anki cards from this", "quiz me on this chapter/section", screenshots of the Spanish book, a pasted word list (e.g. from ChatGPT), or a YouTube link to learn from. Runs quiz → results → review drafts → Anki, and saves a study note each run.
---

# /study

Bryan hands you something they're learning. You turn it into a quiz (when useful), then draft cards they review in their browser, then push the approved ones into Anki and save a study note. **Nothing reaches Anki until they approve it in the review page.**

The toolkit lives in the repo below. Run every command exactly like this, from any directory:

```bash
REPO=/Users/bryanalmaraz/Code/projects/anki-study-helper
uv run --project "$REPO" python -m studyhelper.<module> ...
```

The design spec, if you need the why: `$REPO/docs/superpowers/specs/2026-10-19-study-skill-and-anki-reset-design.md`.

## 1. Identify

- **Input:** book screenshots (images), pasted text, a YouTube URL, or a quick list of words.
- **Subject:** only `spanish` is set up. For anything else, say it isn't set up yet and stop.
- **Path:**
  - **quiz:** material they've already studied (a book section they just read, a video they watched).
  - **direct:** brand-new words (a fresh ChatGPT list, words they jotted down). No quiz; every item becomes a draft.

  Say which path in one line ("These look like new words, so I'm skipping the quiz and drafting cards."). Ask in one line only if it's genuinely unclear. They can override either way.
- **YouTube:** `uv run --project "$REPO" python -m studyhelper.youtube <url>` prints `[mm:ss] text` lines. If there's no transcript, ask them to paste the parts they care about.

## 2. Start the run

```bash
RUN=$(uv run --project "$REPO" python -m studyhelper.notes new spanish <short-slug>)
```

Slug examples: `ch01-s7-commands`, `emociones-2`, `video-ser-estar`. Then write into `$RUN`:

- `source.json`: `{"type": "book"|"chatgpt"|"youtube"|"words", "label": "<e.g. Spanish Grammar For Dummies ch. 1 §7>", "url": <video url or null>}`
- `items.json`: `[{"key": "<word or rule>", "summary": "<one line>"}]`. **Every** item you found, including ones that won't become cards. This is what makes the material findable later.
- Book screenshots: copy them into `$RUN/screenshots/` (gitignored).

## 3a. Quiz path

Write `$RUN/quiz.json`:

```json
{"title": "...", "questions": [
  {"id": "q1", "type": "cloze", "prompt": "Con tantos correos, me siento ___.", "hint": "overwhelmed", "answer": "abrumado", "item": "abrumado"},
  {"id": "q2", "type": "choice", "prompt": "Me ___ rabia que mientan.", "hint": null, "answer": "da", "options": ["pone", "da", "deja", "siente"], "item": "me da rabia"}
]}
```

- About 10–20 questions, a mix of cloze (fill in the blank) and multiple choice. Those are the formats they find most useful.
- `prompt` contains `___` exactly once.
- `item` must equal a `key` in `items.json`.
- For grammar, blank the conjugated verb and put `infinitive, person` in the hint (`decir, tú`).

Then run it **in the background** (Bash `run_in_background: true`):

```bash
uv run --project "$REPO" python -m studyhelper.serve "$RUN" quiz
```

It prints `OPEN http://127.0.0.1:<port>/` and opens their browser. Tell them the URL and that you'll pick up when they press "Done → make cards". You're woken when the process exits. Read `$RUN/results.json`: its `keep` list holds the items to draft (the ones they missed, plus any they ticked).

## 3b. Direct path

Every item in `items.json` becomes a draft.

## 4. Drafts

Write `$RUN/drafts.json` as `{"subject": "spanish", "drafts": [...]}`.

**Vocab draft:**
```json
{"id": "v1", "kind": "vocab", "word": "abrumado", "meaning": "overwhelmed (by too many things)",
 "sentence": "Con tantos correos sin leer, me siento [abrumado].",
 "sentence_en": "With so many unread emails, I feel overwhelmed.",
 "tip": "abrumado <b>por</b> / <b>con</b> algo. Compare agobiado: pressure from too much at once.",
 "examples": [{"es": "Me siento [abrumado] con tantas decisiones.", "en": "..."}, {"es": "...", "en": "..."}, {"es": "...", "en": "..."}],
 "source": "ChatGPT emotions session", "tags": ["emociones", "source::chatgpt"],
 "recognize": true, "action": "add", "match_note_id": null, "flag": null}
```

**Grammar draft:**
```json
{"id": "g1", "kind": "grammar", "rule_key": "negative tú commands",
 "text": "¡No {{c1::digas::decir, tú}} eso! ¡No {{c2::hables::hablar, tú}} tan rápido! ¡No {{c3::tengas::tener, tú}} miedo!",
 "rule": "Negative tú: take the yo form, drop -o, add <b>-es</b> (-ar) or <b>-as</b> (-er/-ir).",
 "reference": "Spanish Grammar For Dummies, ch. 1 §7", "source": "Book ch. 1", "tags": ["mandatos", "source::book::ch01"],
 "action": "add", "match_note_id": null, "flag": null}
```

Quality bar:

- **Mark the target word in brackets:** exactly one `[target]` per sentence and per example, and exactly 3 examples, each showing the word in a *different* shape or situation.
- **Tips say how the word behaves:** the prepositions it takes, register, near-synonyms, and Mexico usage **only when it actually helps**. Keep it to 1–2 lines. Use `<b>` for emphasis. Never markdown `**`.
- **Grammar notes** get 2–4 blanks: a regular verb, an irregular one, and a tricky case. Each blank's hint is `infinitive, person`.
- **Tags:** one source tag (`source::book::chNN`, `source::chatgpt`, `source::youtube`, `source::words`) plus lowercase topic tags.
- **Video sources:** `source` is `"<video title> @ mm:ss — https://youtu.be/<id>?t=<seconds>"`.
- **Correctness:** natural, correct Spanish. If you're unsure about a usage, say so in the tip rather than guessing.
- **Recognize card:** set `recognize` from `RECOGNIZE_CARDS` in `$REPO/studyhelper/config.py` (currently on).

**Duplicates:** run

```bash
uv run --project "$REPO" python -m studyhelper.dedupe "$RUN/drafts.json"
```

For each candidate, read its summary and decide:

| Candidate | Same meaning? | Set |
|---|---|---|
| `vocab` | yes | `action: "merge"`, `match_note_id` (adds this example + tags to the existing note) |
| `vocab` | different meaning | keep `action: "add"`, `flag: "new_sense"` (they decide in review) |
| `legacy` | — | `action: "tag_only"`, `match_note_id` (old card format; only the tag is added) |
| `grammar` | same rule | `action: "merge"` isn't supported for grammar, so drop the draft and mention it |
| `archive` only | — | keep `action: "add"`, `flag: "archive_match"` |

Save `drafts.json` again after deciding.

## 5. Review

Run in the background:

```bash
uv run --project "$REPO" python -m studyhelper.serve "$RUN" review
```

Tell them the URL. They edit, drop, and send. The page refuses drafts that break the rules and tells them what to fix. When the process exits, `$RUN/approved.json` holds what they approved.

## 6. Push and save

```bash
uv run --project "$REPO" python -m studyhelper.push "$RUN"
uv run --project "$REPO" python -m studyhelper.notes write "$RUN"
```

Report the push summary line (`Added N · merged M · tagged K · failed F`), any failures, and the path of `note.md`. Re-running push is safe: drafts that already went in are skipped.

## When Anki isn't reachable

`dedupe` and `push` need Anki open on this Mac. If either prints the "Anki isn't reachable" message, tell them to open Anki. Everything stays on disk in `$RUN`. Resume from the same step when they say so.

## Don'ts

- Don't write to Anki any other way than `push` after review.
- Don't draft every item on the quiz path. Only `keep`.
- Don't add audio or TTS.
- Don't edit fields of legacy (`source::legacy`) cards.
