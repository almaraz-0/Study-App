# `/study` skill + Anki reset: design

Date: 2026-10-19
Project 1 of 3 (next: personal study web app; later: iPad queue, other subjects)

## Why

Bryan studies Spanish (priority), and later guitar, music theory and programming. What they learn rarely gets into Anki:

- **Textbook** (*Spanish for Dummies*, an ebook that blocks copying past a point): they read a section, ask an AI to quiz them, get a list of what they missed, and the list stays in a chat they never find again.
- **ChatGPT word sessions** (e.g. emotion words to express himself better): same problem, a long list buried in a chat.
- **Spanish YouTube videos**: maybe a word or two written down, never followed up.

When things do reach Anki, the cards are thin: one obscure example sentence, no sense of how the word is really used (which preposition it takes, how it shifts in other sentences). They built two Claude artifacts that fix this, but they live outside Anki, which they want as the single place they review, since it's full-featured, offline, and already syncs to their iPad.

Their Anki collection is also disorganized: decks used as folders, almost no tags, duplicates, and many hand-made card formats.

Inspiration: a YouTube workflow ("Anki + Claude Code", https://youtu.be/RocA3wA3QjU): source → AI quiz → find gaps → create cards for the gaps directly in Anki via a Claude Code skill. Its key point, which Bryan agrees with: **don't auto-dump everything**; quiz first, then cards for what you actually missed, with a human review before anything goes in.

## What success looks like

From any Claude Code chat on the Mac, Bryan types `/study` and hands it screenshots, pasted text, a YouTube link or a few words. Minutes later they have: taken a quiz, picked and tweaked the cards, and seen them land in a clean, tagged, deduplicated Anki deck. A study note with everything (including what didn't become a card) is saved in this repo where they can always find it.

## Goals

1. One-time **Anki reset**: archive the old collection, start a clean `Learn::` tree.
2. A **`/study` skill** that takes any input and runs: quiz → results → review drafts → Anki.
3. **Rich card formats** for Spanish vocab and grammar.
4. **Study notes** saved to this repo for every run.
5. Built so new subjects (guitar, music theory, programming) slot in later as new `Learn::<Subject>` decks without redesign.

## Non-goals (for this project)

- The personal study web app that ports the two artifacts (Project 2).
- Creating cards from the iPad / a cloud queue (later). **Mac only for now.**
- Guitar / music theory / programming card formats (later; only don't block them).
- Audio. **No TTS on cards.** Bryan dislikes robotic voices.
- Obsidian or any other notes app.
- Rebuilding the 53 legacy cards in the new format (optional future offer, not this project).

## Anti-goals (failure even if it "works")

- Cards written to Anki that Bryan didn't see and approve.
- Bulk-dumping every word from a source instead of what they missed or chose.
- Creating duplicates of words already in `Learn::`.
- Losing or altering review history of existing cards.
- Card text that's wrong Spanish. Generated examples and tips must be natural, correct Spanish; flag uncertainty instead of guessing.
- Inconsistent formatting (e.g. literal `**markdown**` showing on cards, which is in the current collection today).

## Constraints and environment

- macOS, Anki desktop, profile `User 1` (`~/Library/Application Support/Anki2/User 1/collection.anki2`). Anki syncs to their iPad.
- **AnkiConnect is installed and verified** (`localhost:8765`, version 6). Anki must be open for any read/write.
- This folder (`/Users/bryanalmaraz/Code/projects/anki-study-helper`) is now a git repo; Bryan will back it up to a remote. `.superpowers/` is gitignored.
- Book screenshots are their own copy, used only for their study: keep them local (gitignored), commit only the extracted notes.
- Spanish focus: Mexico (they're oriented to Mexico City Spanish, per their artifacts). Include Mexico-specific tips **when they help**, not on every card.

## Part A: Anki reset (one-time)

Current state (read from a copy on 2026-10-19): 1,686 notes, ~24 decks, 1,579 notes untagged, 67 duplicate fronts (mostly in the premade Neri's deck), last review 2026-09-30. Spanish spread across ~9 decks, including ~1,000 never-studied premade cards.

Decided:

1. **Back up first** (verified backup before any change).
2. Create `Learn::Spanish::Vocab` and `Learn::Spanish::Grammar`.
3. Move **`Languages::Spanish::Vocabulary::April`** (11 cards) and **`Languages::Spanish::Vocabulary::Session_2026`** (42 cards) into `Learn::Spanish::Vocab`, keeping their note types and review history; tag them `source::legacy`. These stay active.
4. Move **every other deck** under `Archive::`, with its structure intact (e.g. `Archive::Languages::Spanish::Fundamentals`, `Archive::Music Theory`), and **suspend all archived cards** so they stop appearing in reviews. Bryan can unsuspend later.
5. Show Bryan a dry run (what moves where, how many cards get suspended) and get their OK before applying.

Builder's call: the `Default` deck (id 1) can't be renamed/moved in Anki. Leave it, and suspend anything in it with the archive.

## Part B: the `/study` skill

### Inputs it must handle

- **Book screenshots** (images of ebook pages, possibly several). Claude reads them, including tables and conjugation charts.
- **Pasted text** (e.g. a ChatGPT word list or explanation).
- **A YouTube URL**: fetch the transcript (e.g. `youtube-transcript-api`). Card sources link to the timestamp where the item appears.
- **A quick list of words** Bryan jotted down.

The skill figures out which kind of input it got and which subject. Spanish is the only subject built now. If it's unclear whether the material is vocab, grammar or both, it decides and says so in one line.

### The four steps (Bryan approved this flow with mockups)

**Two paths (Bryan decided):**

- **Material already studied** (a book section just read, a video just watched): full flow, quiz → results → drafts → Anki.
- **Brand-new words** (a fresh ChatGPT list, words jotted down): **skip the quiz** and go straight to step 3, with every item drafted.

The skill picks the path from the input and says which one in one line (e.g. "These look like new words, so I'm skipping the quiz and drafting cards"). If it's unclear, it asks in one line. Bryan can override either way.

1. **Quiz**: a page opened in their browser. A mix of **fill-in-the-blank (cloze-style) and multiple choice** (the formats they found most useful), covering the material.
2. **Results**: score, with the **items they missed pre-selected** for cards. They can also tick items they got right but want to keep.
3. **Review drafts**: each draft card shown in full (word, meaning, tip, examples, tags, deck) with **Keep / Edit / Drop**. Items already in `Learn::` are flagged (see Duplicates). Nothing is written until they confirm.
4. **Send to Anki**: create the approved notes via AnkiConnect, then report what was added.

Requirement: getting quiz results from the browser back to Claude must take at most one simple action from Bryan (e.g. a "copy results" button they paste into the chat). Better if it's automatic. Mechanism is the builder's call.

### Card formats

**Vocab note** → `Learn::Spanish::Vocab`, a custom note type (one note per word or phrase):

- Fields (roughly): Word, Meaning, Sentence (prompt sentence with the word blanked), Sentence answer / translation, Tip, Examples (3, word highlighted), Source, and a flag that turns the second card on.
- **Card 1 (produce)**: front = meaning + the sentence with the word blanked; back = the word, the tip, three more examples with the word highlighted, and the source.
- **Card 2 (recognize)**: front = the Spanish word or phrase; back = meaning, tip, examples. **Optional per note, on by default for now.** The skill should have one setting to stop generating it for future notes. Existing ones can be suspended from the Anki browser.
- Tip = how the word actually behaves: prepositions it takes (*agradecido **por** algo / **con** alguien*), register, near-synonyms (*abrumado* vs *agobiado*), Mexico usage when relevant.
- Reference for tone and depth: their "Cómo me siento" artifact (https://claude.ai/artifact/Sy1btfQwfHQe6K5SsddD57), whose `RAW`/`EXTRA` data are exactly this shape.

**Grammar note** → `Learn::Spanish::Grammar`, a custom cloze note type (one note per rule):

- Front: a sentence with the conjugated verb blanked, and a hint giving the infinitive and person, e.g. *¡No {{c1::digas::decir, tú}} eso!*
- Back: the answer, the rule in 1–2 plain lines, and the book reference (e.g. *Ch. 1 §7*).
- About **three sentences per rule**, each its own blank (a regular verb, an irregular, a tricky case), so they practice the rule rather than one sentence.
- Reference: their "Gramática en corto" artifact (https://claude.ai/artifact/JJYm6XxiXE6oiokbXYEXbr) for chapter 1.

Formatting: real HTML on cards (no literal markdown), and both note types look consistent and readable on desktop and iPad.

### Tags

Every note gets a source tag and topic tags, e.g. `source::book::ch01`, `source::chatgpt`, `source::youtube`, `source::legacy`; topics like `emociones`, `mandatos`. Decks say *what* you study; tags say *where it came from* and *what it's about*.

### Duplicates

Before creating anything, check `Learn::` for the same word or rule. Matching is **by meaning, not just spelling**: one note per word *and sense*.

- **Same word, same meaning, existing note is the new vocab type:** offer to add the new example and tag to that note instead of creating a new one.
- **Same word, different meaning** (e.g. a second sense of *quedar*): flag it in review as "same word, different meaning", and Bryan decides whether it becomes its own note.
- **Match is one of the 53 legacy cards** (old note types, no Tip/Examples fields): only add the new source tag. Don't edit its fields. Show the rich draft for reference, and leave the legacy card's review history alone.
- **Match only in `Archive::`:** mention it, but don't block a new card (archived cards are suspended).

### Study notes (saved every run)

Under this repo, one folder per run organized by subject and date (e.g. `notes/spanish/2026-10-19-emociones/`), containing a readable note with: date, source (book chapter / video link / "ChatGPT session"), the quiz questions and their answers and score (absent on no-quiz runs, so the format must allow both shapes), **the full item list including what didn't become cards**, and which cards were created (with Anki note IDs). The quiz page is saved alongside it. Screenshots, if kept, are gitignored.

These notes are the input for Project 2 (the web app), so keep them in a consistent, parseable shape.

## Calls I made (Bryan to check)

- Deck names `Learn::` / `Archive::` (Bryan said "Learn is fine").
- Few decks + tags instead of topic decks.
- Legacy cards keep their old note types; no rebuild now.
- Study notes live in this repo, not Obsidian.
- The quiz page is a one-off file saved with each study note, not part of a web app yet.
- The skill's source lives in this repo but is installed so `/study` works from **any** Claude Code chat, not only in this folder (Bryan wants "any chat").
- Archive matches don't block new cards.
- Duplicates are matched by meaning; a new meaning of an existing word is flagged and Bryan decides.
- A match against a legacy card only gets the new tag; its fields aren't edited.
- Produce card: recall, not typed answer.

## Left to the builder

- Exact note-type field names, templates and styling.
- How quiz results return to Claude (within the one-action requirement).
- Whether the review step is in the browser (as mocked) or partly in chat, as long as they see every draft and can edit or drop it before anything is written.
- Transcript library and fallback when a video has no transcript.
- Backup method for Part A.
