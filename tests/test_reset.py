from studyhelper import config
from studyhelper.anki import Anki
from studyhelper.reset import Move, ResetPlan, apply_reset, format_plan, plan_reset

APRIL = "Languages::Spanish::Vocabulary::April"


def test_plan_moves_keep_decks_to_learn():
    plan = plan_reset({APRIL: [1, 2]}, keep=config.KEEP_DECKS, notes_for_keep=[10])
    assert plan.moves == [Move(APRIL, "Learn::Spanish::Vocab", [1, 2])]
    assert plan.keep_note_ids == [10]


def test_plan_archives_everything_else_including_default():
    plan = plan_reset({"Default": [1], "Music Theory": [2]}, keep=config.KEEP_DECKS, notes_for_keep=[])
    dests = {m.src_deck: m.dest_deck for m in plan.moves}
    assert dests == {"Default": "Archive::Default", "Music Theory": "Archive::Music Theory"}


def test_plan_parent_deck_not_kept():
    plan = plan_reset({"Languages::Spanish::Vocabulary": [5]}, keep=config.KEEP_DECKS, notes_for_keep=[])
    assert plan.moves[0].dest_deck == "Archive::Languages::Spanish::Vocabulary"


def test_plan_is_idempotent():
    plan = plan_reset(
        {"Archive::Math": [1], "Learn::Spanish::Vocab": [2], "Empty": []},
        keep=config.KEEP_DECKS,
        notes_for_keep=[],
    )
    assert plan.moves == []


def test_format_plan_totals():
    plan = ResetPlan(
        moves=[Move(APRIL, "Learn::Spanish::Vocab", [1, 2]), Move("Math", "Archive::Math", [3, 4, 5])],
        keep_note_ids=[9],
    )
    text = format_plan(plan)
    assert f"{APRIL} → Learn::Spanish::Vocab (2 cards)" in text
    assert "Keep active: 2 cards" in text
    assert "Archive + suspend: 3 cards" in text


def _collection(fake):
    fake.add(APRIL, {"Front": "aparecer"})
    fake.add("Languages::Spanish::Vocabulary", {"Front": "a menudo"})
    fake.add("Math", {"Front": "2+2"})
    fake.add("Default", {"Front": "intro"})
    return fake


def _plan_for(fake):
    anki = Anki(transport=fake)
    by_deck = anki.invoke("getDecks", cards=anki.invoke("findCards", query="deck:*"))
    keep_cards = [c for d in config.KEEP_DECKS for c in by_deck.get(d, [])]
    return anki, plan_reset(by_deck, config.KEEP_DECKS, anki.invoke("cardsToNotes", cards=keep_cards))


def test_apply_never_deletes_nonempty_or_default(fake_anki):
    anki, plan = _plan_for(_collection(fake_anki))
    apply_reset(anki, plan)
    deleted = [d for a, p in fake_anki.calls if a == "deleteDecks" for d in p["decks"]]
    assert "Default" not in deleted
    assert "Math" in deleted
    # Nothing was lost: every card still exists, in Learn:: or Archive::.
    assert len(fake_anki.cards) == 4
    for card in fake_anki.cards.values():
        assert card["deck"].startswith(("Learn::", "Archive::"))
        assert card["suspended"] == card["deck"].startswith("Archive::")


def test_apply_tags_legacy_notes(fake_anki):
    anki, plan = _plan_for(_collection(fake_anki))
    apply_reset(anki, plan)
    legacy = [n for n in fake_anki.notes.values() if config.LEGACY_TAG in n["tags"]]
    assert [n["fields"]["Front"] for n in legacy] == ["aparecer"]
