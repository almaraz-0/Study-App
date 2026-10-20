# anki-study-helper

My personal study home. What I learn (book sections, ChatGPT word lists, YouTube videos) goes through a quiz and a review step and lands in Anki as rich, tagged cards. A study note for every run is saved under `notes/`.

## Use

In any Claude Code chat on this Mac, with Anki open:

```
/study   (then paste text, drop screenshots, or give a YouTube link)
```

Material you've already studied gets a quiz first. Brand-new words go straight to draft cards. Either way you review every card in the browser before anything reaches Anki.

## Setup

1. Install the AnkiConnect add-on in Anki (code `2055492159`).
2. `uv sync`
3. `bash scripts/install-skill.sh` links the skill into `~/.claude/skills/study`.

## Anki layout

- `Learn::Spanish::Vocab`, `Learn::Spanish::Grammar`: active study.
- `Archive::…`: the old collection, suspended. Unsuspend anything from the Anki browser.
- Tags: `source::book::chNN`, `source::chatgpt`, `source::youtube`, `source::words`, `source::legacy`, plus topics.

To stop making the Spanish → meaning card for new words, set `RECOGNIZE_CARDS = False` in `studyhelper/config.py`.

## Develop

`uv run pytest`. The design is in `docs/superpowers/specs/`, and the plan is in `docs/superpowers/plans/`.
