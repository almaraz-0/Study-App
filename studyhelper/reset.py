"""One-time reset: kept decks move to Learn::, everything else to Archive:: (suspended).

Dry run by default; `--apply` backs up the collection first.
"""

import argparse
import sys
from dataclasses import dataclass

from studyhelper import config
from studyhelper.anki import Anki, AnkiError
from studyhelper.backup import BackupFailed, backup_collection


@dataclass
class Move:
    src_deck: str
    dest_deck: str
    card_ids: list[int]


@dataclass
class ResetPlan:
    moves: list[Move]
    keep_note_ids: list[int]
    suspend_after: bool = True


def plan_reset(cards_by_deck: dict[str, list[int]], keep: list[str], notes_for_keep: list[int]) -> ResetPlan:
    moves = []
    for deck in sorted(cards_by_deck):
        cards = cards_by_deck[deck]
        if not cards or deck.startswith((config.LEARN_PREFIX, config.ARCHIVE_PREFIX)):
            continue
        dest = config.KEEP_DEST if deck in keep else config.ARCHIVE_PREFIX + deck
        moves.append(Move(deck, dest, list(cards)))
    return ResetPlan(moves=moves, keep_note_ids=list(notes_for_keep))


def format_plan(plan: ResetPlan) -> str:
    lines = [f"{m.src_deck} → {m.dest_deck} ({len(m.card_ids)} cards)" for m in plan.moves]
    kept = sum(len(m.card_ids) for m in plan.moves if not m.dest_deck.startswith(config.ARCHIVE_PREFIX))
    archived = sum(len(m.card_ids) for m in plan.moves if m.dest_deck.startswith(config.ARCHIVE_PREFIX))
    lines += ["", f"Keep active: {kept} cards", f"Archive + suspend: {archived} cards"]
    return "\n".join(lines)


def _quoted_deck(name: str) -> str:
    return 'deck:"' + name.replace('"', '\\"') + '"'


def apply_reset(anki: Anki, plan: ResetPlan) -> None:
    for dest in sorted({m.dest_deck for m in plan.moves}):
        anki.invoke("createDeck", deck=dest)
    for m in plan.moves:
        anki.invoke("changeDeck", cards=m.card_ids, deck=m.dest_deck)
    if plan.keep_note_ids:
        anki.invoke("addTags", notes=plan.keep_note_ids, tags=config.LEGACY_TAG)
    if plan.suspend_after:
        archived = anki.invoke("findCards", query=f'deck:"{config.ARCHIVE_PREFIX}*"')
        if archived:
            anki.invoke("suspend", cards=archived)
    # Remove the old, now-empty decks (including empty parents). Never Default,
    # and never a deck that still holds any card.
    for deck in sorted(anki.invoke("deckNames"), key=len, reverse=True):
        if deck == "Default" or deck.startswith((config.LEARN_PREFIX, config.ARCHIVE_PREFIX)):
            continue
        if deck in ("Learn", "Archive"):
            continue
        if not anki.invoke("findCards", query=_quoted_deck(deck)):
            anki.invoke("deleteDecks", decks=[deck], cardsToo=True)


def gather(anki: Anki) -> ResetPlan:
    by_deck = anki.invoke("getDecks", cards=anki.invoke("findCards", query="deck:*"))
    keep_cards = [c for d in config.KEEP_DECKS for c in by_deck.get(d, [])]
    notes = anki.invoke("cardsToNotes", cards=keep_cards) if keep_cards else []
    return plan_reset(by_deck, config.KEEP_DECKS, notes)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="make the changes (after a backup)")
    args = ap.parse_args(argv)
    anki = Anki()
    try:
        anki.ping()
        plan = gather(anki)
        print(format_plan(plan))
        if not args.apply:
            print("\nDry run. Nothing changed. Re-run with --apply to make these changes.")
            return 0
        expected = len(anki.invoke("findNotes", query="deck:*"))
        backup = backup_collection(config.COLLECTION_PATH, config.BACKUPS_DIR, expected)
        apply_reset(anki, plan)
        print(f"\nDone. Backup at {backup}")
        return 0
    except (AnkiError, BackupFailed) as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
