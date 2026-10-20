# `/study` Skill + Anki Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A one-time Anki reset into `Archive::` / `Learn::`, plus a `/study` Claude Code skill that turns screenshots, pasted text, YouTube links or word lists into a quiz, then reviewed drafts, then rich Anki cards, and saves a study note each run.

**Architecture:** A small Python package `studyhelper/` does every deterministic job: talking to AnkiConnect, backup, reset, note types, draft validation, duplicate lookup, pushing cards, grading, the local quiz/review server, study notes, and YouTube transcripts. Each job is a `python -m studyhelper.<module>` CLI. The skill (`skills/study/SKILL.md`) is the orchestrator. Claude does the language work (reading input, writing quiz questions and drafts, judging same-vs-different meaning) and calls the CLIs. Quiz and review are local HTML pages served on 127.0.0.1. The server writes the user's submission to disk and exits, which wakes Claude.

**Tech Stack:** Python 3.14 (stdlib `http.server`, `urllib`, `sqlite3`, `json`), `uv` for env, `pytest`, `youtube-transcript-api` (1.x API), AnkiConnect v6 on `localhost:8765`, plain HTML/JS pages (no build step).

**Spec:** `docs/superpowers/specs/2026-10-19-study-skill-and-anki-reset-design.md`

## Global Constraints

- Repo root: `/Users/bryanalmaraz/Code/projects/anki-study-helper`. Every CLI is run as `uv run --project <repo root> python -m studyhelper.<module>` so it works from any cwd.
- AnkiConnect: `http://127.0.0.1:8765`, `"version": 6`. Anki must be open. If it's unreachable, fail with the message `Anki isn't reachable. Open Anki on this Mac (AnkiConnect must be installed) and try again.` and write nothing.
- Collection path: `~/Library/Application Support/Anki2/User 1/collection.anki2`.
- Decks: `Learn::Spanish::Vocab`, `Learn::Spanish::Grammar`, `Archive::<old deck name>`.
- Decks kept active: `Languages::Spanish::Vocabulary::April` and `Languages::Spanish::Vocabulary::Session_2026` move to `Learn::Spanish::Vocab` and get the tag `source::legacy`.
- Note type names: `Learn Vocab` and `Learn Grammar`.
- Tags: `source::book::chNN`, `source::chatgpt`, `source::youtube`, `source::words`, `source::legacy`, plus lowercase topic tags (e.g. `emociones`, `mandatos`).
- **No audio/TTS** anywhere on cards.
- Card text is HTML. A literal `**` or markdown must never reach a card field.
- Nothing is written to Anki without the user approving the drafts in the review page, and the reset requires an explicit `--apply` after a dry run.
- Never delete a card or note. Never reset scheduling. Card moves use `changeDeck`, which keeps review history.
- `notes/**/screenshots/` and `backups/` are gitignored.
- The recognize card is on by default: `RECOGNIZE_CARDS = True` in `studyhelper/config.py`.
- Spanish focus is Mexico. Mexico-specific tips only when they help.

## Review Focus

1. **Re-running push after a crash or a double click** must not create duplicate notes. Pushed draft ids are recorded and skipped. Test: Task 7 `test_push_is_idempotent`.
2. **Anki closed mid-flow:** a clear message, the drafts and results stay on disk, nothing is half-written silently. Test: Task 1 `test_unreachable_raises_friendly_error`, Task 7 `test_push_aborts_before_writing_when_anki_down`.
3. **Typed quiz answers with a different case or missing accents** (`Abrumado`, `alivido` vs `aliviado`, `atonito` vs `atónito`): case is ignored, and an accent-only difference counts as correct but is flagged. Test: Task 8 `test_grade_accent_only_is_correct_with_flag`.
4. **Drafts whose sentence has no `[target]` marker, or several:** a validation error before review, never a card with no blank. Test: Task 5 `test_sentence_requires_exactly_one_marker`.
5. **Phrases with spaces, punctuation or quotes in duplicate search** (`me da pena`, `al borde de...`, `"chamba"`): the query is escaped, there's no crash, and the whole phrase is matched. Test: Task 6 `test_query_escapes_phrase`.

---

## File Structure

```
pyproject.toml                    uv project: deps + pytest config
.gitignore                        + .venv/, backups/, notes/**/screenshots/, __pycache__/
studyhelper/__init__.py
studyhelper/config.py             constants: URLs, paths, deck/model names, RECOGNIZE_CARDS
studyhelper/anki.py               AnkiConnect client
studyhelper/backup.py             collection backup + verify
studyhelper/reset.py              plan/apply reset, CLI
studyhelper/notetypes.py          Learn Vocab / Learn Grammar definitions + ensure
studyhelper/drafts.py             draft schema, validation, -> Anki note fields
studyhelper/dedupe.py             candidate lookup in Learn::/Archive::
studyhelper/push.py               apply approved drafts to Anki, CLI
studyhelper/grade.py              grade quiz answers
studyhelper/serve.py              local page server (quiz + review), CLI
studyhelper/pages/quiz.html       quiz + results page (data injected)
studyhelper/pages/review.html     review drafts page (data injected)
studyhelper/notes.py              run.json + note.md writer, CLI
studyhelper/youtube.py            transcript fetch, CLI
skills/study/SKILL.md             the /study skill
scripts/install-skill.sh          symlink skill into ~/.claude/skills/study
tests/conftest.py                 FakeAnki fixture
tests/test_*.py                   one per module
```

### Shared data formats (all JSON, UTF-8)

A run lives in `notes/<subject>/<YYYY-MM-DD>-<slug>/`. Files written there:

- `quiz.json`: `{"title": str, "questions": [Question]}`, where `Question = {"id": str, "type": "cloze"|"choice", "prompt": str (contains "___"), "hint": str|null, "answer": str, "options": [str] (choice only), "item": str}`. `item` is the word or rule key the question tests.
- `results.json`: `{"answers": [{"id", "given", "correct": bool, "accent_only": bool}], "score": int, "total": int, "keep": [item]}`.
- `drafts.json`: `{"subject": "spanish", "drafts": [Draft]}`.
  - `VocabDraft = {"id", "kind": "vocab", "word", "meaning", "sentence" (Spanish with exactly one [target]), "sentence_en", "tip", "examples": [{"es" (one [target]), "en"}] (exactly 3), "source", "tags": [str], "recognize": bool, "action": "add"|"merge"|"tag_only", "match_note_id": int|null, "flag": "new_sense"|"archive_match"|null}`.
  - `GrammarDraft = {"id", "kind": "grammar", "rule_key", "text" (Anki cloze, e.g. "¡No {{c1::digas::decir, tú}} eso!"; 2–4 clozes), "rule", "reference", "source", "tags", "action", "match_note_id", "flag"}`.
- `approved.json`: `{"drafts": [Draft], "dropped": [id]}`. Edited drafts, written by the review page.
- `pushed.json`: `{"results": [{"draft_id", "note_id", "action", "error": str|null}]}`.
- `run.json` + `note.md`: Task 9.

---

### Task 1: Project scaffold + AnkiConnect client

**Files:**
- Create: `pyproject.toml`, `studyhelper/__init__.py`, `studyhelper/config.py`, `studyhelper/anki.py`, `tests/conftest.py`, `tests/test_anki.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `class AnkiError(Exception)`, `class AnkiUnreachable(AnkiError)`, `class Anki: __init__(url: str = config.ANKI_URL, transport=None)`, `Anki.invoke(action: str, **params) -> Any` (raises `AnkiError(msg)` when the response `error` is non-null), `Anki.ping() -> None` (raises `AnkiUnreachable`). `transport(payload: dict) -> dict` is injectable, and the default uses `urllib.request` with a 10s timeout.
- Produces in `tests/conftest.py`: fixture `fake_anki` returns `FakeAnki`, an in-memory stand-in that records `calls: list[tuple[str, dict]]` and implements the actions later tasks use (`version`, `deckNames`, `findCards`, `findNotes`, `getDecks`, `changeDeck`, `suspend`, `addTags`, `deleteDecks`, `modelNames`, `createModel`, `updateModelTemplates`, `updateModelStyling`, `createDeck`, `addNote`, `notesInfo`, `updateNoteFields`, `cardsToNotes`) over a small dict model of decks → cards → notes. Pass it as `Anki(transport=fake_anki)`.
- `config.py`: `ANKI_URL`, `COLLECTION_PATH`, `REPO_ROOT`, `NOTES_DIR`, `BACKUPS_DIR`, `DECKS = {"spanish": {"vocab": "Learn::Spanish::Vocab", "grammar": "Learn::Spanish::Grammar"}}`, `KEEP_DECKS = ["Languages::Spanish::Vocabulary::April", "Languages::Spanish::Vocabulary::Session_2026"]`, `VOCAB_MODEL = "Learn Vocab"`, `GRAMMAR_MODEL = "Learn Grammar"`, `RECOGNIZE_CARDS = True`, `UNREACHABLE_MSG` (exact text from Global Constraints).

- [ ] **Step 1:** `uv init --bare` (or write `pyproject.toml` by hand): name `studyhelper`, `requires-python = ">=3.12"`, deps `youtube-transcript-api>=1.0`, dev dep `pytest`, `[tool.pytest.ini_options] testpaths=["tests"]`. Append `.venv/`, `backups/`, `notes/**/screenshots/`, `__pycache__/` to `.gitignore`. Run `uv sync`.
- [ ] **Step 2: Write failing tests** in `tests/test_anki.py`:
  - `test_invoke_sends_v6_payload`: transport receives `{"action": "deckNames", "version": 6, "params": {}}`.
  - `test_invoke_raises_on_error_field`: a transport returning `{"result": None, "error": "boom"}` raises `AnkiError` whose message contains `"boom"`.
  - `test_unreachable_raises_friendly_error`: a transport raising `URLError` makes `ping()` raise `AnkiUnreachable` with `str(e) == config.UNREACHABLE_MSG`.
- [ ] **Step 3:** Run `uv run pytest tests/test_anki.py -v`. Expected: FAIL (import error).
- [ ] **Step 4:** Implement `studyhelper/anki.py`, `config.py` and the `FakeAnki` fixture.
- [ ] **Step 5:** Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 6:** Commit `feat: scaffold project and AnkiConnect client`.

### Task 2: Collection backup

**Files:** Create `studyhelper/backup.py`, `tests/test_backup.py`

**Interfaces:**
- Produces: `backup_collection(src: Path, dest_dir: Path, expected_notes: int) -> Path`. It writes `dest_dir/<YYYYmmdd-HHMMSS>/collection.anki2` with sqlite's online backup API (`sqlite3.connect(f"file:{src}?mode=ro", uri=True).backup(dst_conn)`), then opens the copy and checks `select count(*) from notes == expected_notes`. On a mismatch or any sqlite error it raises `BackupFailed(msg)`, and the msg tells the user to use Anki's **File → Create Backup** instead. Avoid queries that touch Anki's `unicase` collation (only `count(*)` on `notes`).

- [ ] **Step 1: Failing tests:** `test_backup_copies_and_verifies` (a tmp sqlite db with a `notes` table of 3 rows, so `expected_notes=3` returns a path that exists, and the copy has 3 rows) and `test_backup_count_mismatch_raises` (`expected_notes=4` raises `BackupFailed`).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: verified collection backup`.

### Task 3: Anki reset (plan, dry run, apply)

**Files:** Create `studyhelper/reset.py`, `tests/test_reset.py`

**Interfaces:**
- Consumes: `Anki`, `backup_collection`, `config`.
- Produces:
  - `@dataclass Move(src_deck: str, dest_deck: str, card_ids: list[int])`
  - `@dataclass ResetPlan(moves: list[Move], keep_note_ids: list[int], suspend_after: bool = True)`
  - `plan_reset(cards_by_deck: dict[str, list[int]], keep: list[str], notes_for_keep: list[int]) -> ResetPlan`. Pure. For each deck: a name in `keep` → `Learn::Spanish::Vocab`. A name already starting with `Learn::` or `Archive::` → skipped. Anything else → `Archive::<name>`, including `Default` → `Archive::Default`. Decks with zero cards produce no move.
  - `format_plan(plan) -> str`: one line per move (`<src> → <dest> (<n> cards)`), then the totals `Keep active: N cards`, `Archive + suspend: M cards`.
  - `apply_reset(anki: Anki, plan: ResetPlan) -> None`, in this order:
    1. `createDeck` for each dest.
    2. `changeDeck` per move.
    3. `addTags(keep_note_ids, "source::legacy")`.
    4. `suspend(findCards('deck:"Archive::*"'))`.
    5. Delete old source decks only if `findCards('deck:"<src>"')` is now empty, never `Default`.
  - CLI `python -m studyhelper.reset [--apply]`: it pings, then gathers `getDecks(findCards("deck:*"))`, with keep notes from `cardsToNotes` of the keep decks' cards. It prints `format_plan`. With `--apply`, it runs `backup_collection(COLLECTION_PATH, BACKUPS_DIR, len(findNotes("deck:*")))` first and aborts on `BackupFailed`, then `apply_reset`, and prints `Done. Backup at <path>`.

- [ ] **Step 1: Failing tests:**
  - `test_plan_moves_keep_decks_to_learn`: `{"Languages::Spanish::Vocabulary::April": [1, 2]}` gives one move to `Learn::Spanish::Vocab`.
  - `test_plan_archives_everything_else_including_default`: `"Default"` → `"Archive::Default"`, and `"Music Theory"` → `"Archive::Music Theory"`.
  - `test_plan_parent_deck_not_kept`: `"Languages::Spanish::Vocabulary"` (the parent of a kept deck) → `"Archive::Languages::Spanish::Vocabulary"`.
  - `test_plan_is_idempotent`: decks already under `Archive::`/`Learn::` produce no moves.
  - `test_apply_never_deletes_nonempty_or_default` (FakeAnki): after apply, `deleteDecks` was only called for decks with no remaining cards and never for `Default`, and every archived card is suspended.
  - `test_apply_tags_legacy_notes`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: anki reset with dry run`.

### Task 4: Note types

**Files:** Create `studyhelper/notetypes.py`, `tests/test_notetypes.py`

**Interfaces:**
- Produces: `VOCAB_FIELDS = ["Word", "Meaning", "Prompt", "Sentence", "SentenceEN", "Tip", "Examples", "Source", "Recognize"]`, `GRAMMAR_FIELDS = ["Text", "Rule", "Reference", "Source"]`, `ensure_models(anki: Anki) -> list[str]` (creates whichever of the two models are missing, and returns the created names). Templates:
  - **Learn Vocab / Produce:** front `{{Meaning}}` + `{{Prompt}}`; back `{{FrontSide}}<hr id=answer>` + `{{Word}}` (large) + `{{Sentence}}` + `{{SentenceEN}}` (muted) + `{{#Tip}}Tip block{{/Tip}}` + `{{Examples}}` + `{{Source}}` (small, muted).
  - **Learn Vocab / Recognize:** front wrapped in `{{#Recognize}}{{Word}}{{/Recognize}}`, so the card is only generated when Recognize is non-empty. Back: Meaning, Tip, Examples, Source.
  - **Learn Grammar:** `isCloze=True`. Front `{{cloze:Text}}`, back `{{cloze:Text}}` + `{{Rule}}` + `{{Reference}}` + `{{Source}}`.
  - One shared CSS: readable on desktop and iPad, dark-mode aware via `.nightMode`, `b` in the accent color. No `{{tts}}` and no `[sound:]`.

- [ ] **Step 1: Failing tests:** `test_ensure_creates_both_when_missing` (FakeAnki without the models, so `createModel` is called twice with exactly those field lists, and Grammar has `isCloze: True`), `test_ensure_skips_existing`, and `test_templates_have_no_tts` (no `tts` or `[sound:` in any template string).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: Learn Vocab and Learn Grammar note types`.

### Task 5: Drafts: validation and conversion to Anki fields

**Files:** Create `studyhelper/drafts.py`, `tests/test_drafts.py`

**Interfaces:**
- Produces:
  - `class DraftError(ValueError)`.
  - `validate(draft: dict) -> None`, which raises `DraftError(f"{id}: <reason>")` when:
    - the vocab `sentence` or any example `es` doesn't have exactly one `[...]` marker;
    - `examples` has fewer or more than 3 entries;
    - the grammar `text` has no `{{c1::`;
    - `action` is not one of `add|merge|tag_only`;
    - `merge`/`tag_only` has no `match_note_id`;
    - any text field contains `**`.
  - `mark(s: str) -> str`: `[x]` becomes `<b>x</b>`.
  - `blank(s: str) -> str`: `[x]` becomes `<span class=blank>[...]</span>`.
  - `vocab_fields(d: dict, recognize: bool) -> dict[str, str]`, which maps onto `VOCAB_FIELDS`:
    - `Prompt = blank(sentence)`, `Sentence = mark(sentence)`
    - `Examples` = an `<ul>` of `mark(es)` + `<i>en</i>` items
    - `Recognize = "y" if recognize else ""`
    - all user text HTML-escaped before the markers are converted.
  - `grammar_fields(d) -> dict[str, str]`.
  - `to_anki_note(d: dict, subject: str) -> dict`, which returns the `addNote` note dict with `deckName` from `config.DECKS[subject][kind]`, `modelName`, `fields`, `tags` (deduplicated and lowercased), and `options={"allowDuplicate": True}`. Duplicate control is `dedupe`'s job, because a new meaning of the same word must be allowed. `recognize` is `d.get("recognize", config.RECOGNIZE_CARDS)`.

- [ ] **Step 1: Failing tests:**
  - `test_sentence_requires_exactly_one_marker`: zero markers raises, two markers raise.
  - `test_examples_must_be_three`.
  - `test_rejects_markdown_bold`.
  - `test_vocab_fields_blank_and_mark`: `"Me siento [abrumado]."` gives `Prompt` containing `[...]` and not `abrumado`, and `Sentence` containing `<b>abrumado</b>`.
  - `test_html_escaped`: `"<script>"` in `tip` comes out escaped.
  - `test_recognize_flag_off`: `Recognize == ""`.
  - `test_to_anki_note_deck_and_tags`: a vocab draft goes to `Learn::Spanish::Vocab`, and the tags come out lowercased with no duplicates.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: draft validation and field mapping`.

### Task 6: Duplicate candidates

**Files:** Create `studyhelper/dedupe.py`, `tests/test_dedupe.py`

**Interfaces:**
- Produces:
  - `@dataclass Candidate(note_id: int, kind: Literal["vocab", "legacy", "grammar", "archive"], summary: str)`. `summary` is the first ~160 chars of the note's fields, joined with `" | "`, with HTML stripped.
  - `quote(term: str) -> str`: an Anki search-safe quoted term. It escapes `\`, `"`, `*`, `_`, `:` and wraps the term in double quotes.
  - `find_candidates(anki, draft: dict) -> list[Candidate]`. Queries:
    - vocab: `note:"Learn Vocab" Word:<quote(word)>`;
    - legacy: `deck:"Learn::*" tag:source::legacy <quote(word)>`;
    - grammar: `note:"Learn Grammar" <quote(rule_key)>`;
    - archive (info only): `deck:"Archive::*" <quote(word or rule_key)>`.
  - CLI `python -m studyhelper.dedupe <drafts.json>` prints a JSON `{draft_id: [Candidate...]}`.

  Claude, in the skill, reads the candidates and decides each draft's `action` and `match_note_id`:
  - same meaning on a `vocab` candidate → `merge`;
  - a `legacy` match → `tag_only`;
  - a different meaning → `add`, flagged in review;
  - an `archive` match → `add`, with the match noted.

- [ ] **Step 1: Failing tests:**
  - `test_query_escapes_phrase`: `quote('al borde de...')` is `'"al borde de..."'`, and `quote('say "hi"')` escapes the inner quotes.
  - `test_vocab_candidate_found` (FakeAnki has a Learn Vocab note with Word `harto`).
  - `test_legacy_candidate_kind`.
  - `test_archive_candidate_kind`.
  - `test_no_candidates_returns_empty`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. FakeAnki's `findNotes` only needs to support these query shapes, using substring matching.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: duplicate candidate lookup`.

### Task 7: Push approved drafts

**Files:** Create `studyhelper/push.py`, `tests/test_push.py`

**Interfaces:**
- Consumes: `Anki`, `drafts.validate`, `drafts.to_anki_note`, `drafts.mark`, `notetypes.ensure_models`.
- Produces:
  - `push(anki, approved: dict, subject: str, already: set[str]) -> list[dict]`. It returns pushed-result dicts in the `pushed.json` shape and skips draft ids in `already`. Steps:
    1. `ping()` and validate every draft **before any write**.
    2. `ensure_models`.
    3. Then, per draft:
       - `add` → `addNote`;
       - `merge` → `notesInfo([match])`, append one new `<li>` built from the draft's `sentence` with `mark()` to `Examples`, `updateNoteFields`, then `addTags`;
       - `tag_only` → `addTags` only. Fields are never touched.
    4. A per-draft `AnkiError` is recorded in `error` and the loop continues.
  - CLI `python -m studyhelper.push <run_dir>` reads `approved.json`, merges into `pushed.json` (successful ids become `already` on a re-run), and prints `Added N · merged M · tagged K · failed F`, with each failure on its own line.

- [ ] **Step 1: Failing tests:**
  - `test_push_adds_notes`.
  - `test_push_merge_appends_example_only` (the other fields are unchanged).
  - `test_push_tag_only_does_not_update_fields` (no `updateNoteFields` call).
  - `test_push_is_idempotent` (a second run with `already` from the first makes no `addNote` calls).
  - `test_push_aborts_before_writing_when_anki_down` (ping raises `AnkiUnreachable`, and there are zero write calls).
  - `test_invalid_draft_blocks_all_writes`.
  - `test_one_failure_doesnt_stop_others`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: push approved drafts to Anki`.

### Task 8: Grading + local quiz/review pages

**Files:** Create `studyhelper/grade.py`, `studyhelper/serve.py`, `studyhelper/pages/quiz.html`, `studyhelper/pages/review.html`, `tests/test_grade.py`, `tests/test_serve.py`

**Interfaces:**
- Produces:
  - `grade(quiz: dict, given: dict[str, str]) -> dict`. It returns the `results.json` shape, with `keep` pre-filled with the `item`s of wrong answers. A cloze answer is compared after `strip()` + `casefold()`. If it only matches after accent stripping (`unicodedata` NFD, drop combining marks), it gets `correct=True, accent_only=True`. A choice question is an exact option match.
  - `render(page: Literal["quiz", "review"], data: dict) -> str`. It injects `data` as JSON into `<script id="data" type="application/json">`, with `</` escaped as `<\/`.
  - `serve(run_dir: Path, page: str, port: int = 0) -> None`. It writes `run_dir/<page>.html` (the self-contained copy that's kept with the note), serves it on `127.0.0.1`, prints `OPEN http://127.0.0.1:<port>/` and opens the browser.
    - quiz: `POST /grade` with `{given}` returns `grade(...)`, and the page shows the results with the `keep` checkboxes pre-ticked and extras tickable. `POST /submit` with `{results}` writes `results.json` and exits 0.
    - review: `POST /submit` with `{drafts, dropped}` writes `approved.json` and exits 0.
    - Exits non-zero after 2 hours idle.
  - CLI `python -m studyhelper.serve <run_dir> quiz|review`. The skill runs it in the background, and the process exiting is the signal to continue.
- Page behavior:
  - **quiz.html:** one question at a time. Cloze uses a text input, choice uses buttons. Show the hint when present. On finish, call `/grade` and show the score, then the missed items **pre-ticked**, then the correct items unticked. "Done → make cards" calls `/submit`.
  - **review.html:** one card per draft, with all its fields editable (word, meaning, sentence, tip, the 3 examples, tags) and a recognize toggle for vocab. Badges: `merge` → "already in Anki: adds this example", `tag_only` → "matches an old card: only adds a tag", and a draft with `"flag": "new_sense"` → "same word, different meaning". Keep/Drop per card, then "Send N cards to Anki" calls `/submit`.
  - Both pages are mobile-friendly, light/dark aware, and work with no network.

- [ ] **Step 1: Failing tests:**
  - `test_grade_exact_and_case`: `"Abrumado"` against `"abrumado"` is correct and not `accent_only`.
  - `test_grade_accent_only_is_correct_with_flag`: `"atonito"` against `"atónito"` gives `correct=True, accent_only=True`.
  - `test_grade_wrong_goes_to_keep`.
  - `test_grade_choice_exact`.
  - `test_render_escapes_script_close`: data containing `"</script>"` doesn't end the tag.
  - `test_serve_submit_writes_and_exits`: start `serve` in a thread on port 0 with a tmp `run_dir`, POST `/submit`, then assert `approved.json` exists and the thread ends.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement `grade.py`, `serve.py`, and both pages.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Manual check:** `uv run python -m studyhelper.serve /tmp/x quiz` with a 3-question sample `quiz.json`. Complete it in the browser, and confirm the results screen pre-ticks the misses and that `results.json` is written.
- [ ] **Step 6:** Commit `feat: local quiz and review pages`.

### Task 9: Study notes

**Files:** Create `studyhelper/notes.py`, `tests/test_notes.py`

**Interfaces:**
- Produces:
  - `new_run_dir(subject: str, slug: str, today: date | None = None) -> Path`. It creates `NOTES_DIR/<subject>/<YYYY-MM-DD>-<slug>/`, adding a `-2`, `-3`… suffix if the folder exists.
  - `write_run(run_dir: Path) -> Path`. It reads whichever of `source.json`, `items.json`, `quiz.json`, `results.json`, `approved.json` and `pushed.json` exist, then writes `run.json` and `note.md`, and returns the `note.md` path.
  - `run.json` shape: `{"schema": 1, "subject", "date", "slug", "path": "quiz"|"direct", "source": {"type": "book"|"chatgpt"|"youtube"|"words", "label", "url": str|null}, "items": [{"key", "summary", "carded": bool}], "quiz": null | {"questions", "results"}, "cards": [{"draft_id", "note_id", "action"}]}`.
  - `note.md` contains:
    - a title;
    - the date and source (as a link if a url is present);
    - a `## Quiz` section with the score and each question (✓/✗, given vs answer), shown **only when** there's a quiz;
    - `## Items` listing **every** item, marked carded or not;
    - `## Cards added` with the Anki note ids.
  - `source.json` and `items.json` are written by Claude in the skill. `items.json` is `[{"key", "summary"}]`, the full list, including items that won't become cards.
  - CLI `python -m studyhelper.notes new <subject> <slug>` prints the dir. `python -m studyhelper.notes write <run_dir>` prints the `note.md` path.

- [ ] **Step 1: Failing tests:**
  - `test_new_run_dir_suffixes_on_collision`.
  - `test_write_run_with_quiz` (the note has `## Quiz` and the score line).
  - `test_write_run_direct_path_has_no_quiz` (`path == "direct"`, no `## Quiz`, `quiz` null).
  - `test_items_marked_carded_from_pushed` (an item whose key matches a pushed draft's `word`/`rule_key` gets `carded=True`; the others stay false but are still listed).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: study notes per run`.

### Task 10: YouTube transcripts

**Files:** Create `studyhelper/youtube.py`, `tests/test_youtube.py`

**Interfaces:**
- Produces:
  - `video_id(url: str) -> str`. It handles `youtu.be/<id>?si=…`, `youtube.com/watch?v=<id>&…`, `/shorts/<id>` and `/embed/<id>`, and raises `ValueError` otherwise.
  - `timestamp_url(vid: str, seconds: float) -> str`, which returns `https://youtu.be/<vid>?t=<int(seconds)>`.
  - `fetch(url: str, languages=("es", "en")) -> list[tuple[float, str]]`. It uses `YouTubeTranscriptApi().fetch(vid, languages=list(languages))`, and on any library error raises `NoTranscript("No transcript for this video. Paste the parts you care about instead.")`.
  - CLI `python -m studyhelper.youtube <url>` prints the header line `URL: <url>` and then `[mm:ss] text` lines.
  - Skill rule: vocab and grammar drafts from a video get `source` = `"<video title or url> @ mm:ss"` linked with `timestamp_url`.

- [ ] **Step 1: Failing tests:**
  - `test_video_id_variants`, including `https://youtu.be/RocA3wA3QjU?si=Uux6mqCei3Iv-wUK` → `RocA3wA3QjU`.
  - `test_timestamp_url`: 125.7 → `?t=125`.
  - `test_fetch_wraps_errors` (monkeypatch the API to raise).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: youtube transcript fetch`.

### Task 11: The `/study` skill, install, and live reset

**Files:** Create `skills/study/SKILL.md`, `scripts/install-skill.sh`. Modify `README.md` (create it with a short what/how).

**Interfaces:**
- Consumes: every CLI above.
- `SKILL.md` frontmatter: `name: study`, with a description that triggers on "/study", "make Anki cards from…", "quiz me on this chapter", screenshots of the Spanish book, a pasted word list, or a YouTube link to learn from. The body is the orchestration, written as steps:
  1. **Identify** the input type (screenshots / pasted text / YouTube / word list) and subject (only `spanish` for now; for anything else, say it isn't set up yet). Decide the path: **quiz** for material already studied (a book section, a watched video) and **direct** for brand-new words. Say which in one line, and let the user override. Ask in one line only if it's unclear.
  2. `notes new spanish <slug>`, then write `source.json` and `items.json` (every item found). Copy screenshots into `<run>/screenshots/`.
  3. **Quiz path:** write `quiz.json` with a mix of cloze (`___` + hint) and multiple choice, about 10–20 questions over the items. Run `serve <run> quiz` **in the background**, tell the user the URL, and wait for the process to exit. Read `results.json`. The `keep` items become drafts.
  4. **Direct path:** every item becomes a draft.
  5. **Drafts:** write `drafts.json` following the formats and quality bar in the spec:
     - vocab: a usage tip (prepositions, register, near-synonyms; Mexico notes only when useful), 1 sentence + 3 varied examples with `[target]` markers and natural, correct Spanish;
     - grammar: 2–4 cloze sentences with an `infinitive, person` hint (regular / irregular / tricky case), a 1–2 line rule, and the book reference;
     - tags: source tag + topic tags; vocab `recognize` = `config.RECOGNIZE_CARDS`.

     Run `dedupe` and decide `action`/`match_note_id`/`flag` per the rules in Task 6. `push` validates every draft before writing. If unsure about a Spanish usage, say so in the draft's tip rather than guessing.
  6. Run `serve <run> review` in the background, wait for exit, then read `approved.json`.
  7. `push <run>`, then `notes write <run>`. Report the push summary line, the note path, and any failures.
  8. If Anki isn't reachable at step 5 or 7, tell the user to open Anki, keep all files, and resume from that step when asked.
- `scripts/install-skill.sh`: `ln -sfn "<repo>/skills/study" ~/.claude/skills/study`. If a non-symlink exists there, refuse and print why.

- [ ] **Step 1:** Write `SKILL.md`, `install-skill.sh`, `README.md`. Run `bash scripts/install-skill.sh`, then `ls -l ~/.claude/skills/study`. Expected: a symlink to the repo.
- [ ] **Step 2:** Run `uv run pytest -v`. Expected: all pass.
- [ ] **Step 3: Live dry run** (Anki open): `uv run python -m studyhelper.reset`. **Show the user the printed plan** and get explicit approval. Expected: April + Session_2026 (53 cards) go to Learn, and everything else goes to `Archive::`.
- [ ] **Step 4:** Only after approval: `uv run python -m studyhelper.reset --apply`. Then verify with AnkiConnect:
  - `findCards('deck:"Learn::*" is:suspended')` → 0;
  - `findCards('deck:"Archive::*" -is:suspended')` → 0;
  - `findCards('deck:"Learn::*"')` → 53;
  - the note count is unchanged from before.

  Report the backup path.
- [ ] **Step 5: End-to-end smoke test** with the user: run `/study` with 3 emotion words (the direct path), have them review, push, then confirm in Anki that the cards render on desktop, with the recognize card present and no `**` or audio. Then delete nothing. If they want to remove the test cards, they do it themselves in Anki.
- [ ] **Step 6:** Commit `feat: /study skill and install script`.
