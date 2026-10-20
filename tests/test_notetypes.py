from studyhelper import config
from studyhelper.anki import Anki
from studyhelper.notetypes import GRAMMAR_FIELDS, VOCAB_FIELDS, ensure_models


def test_ensure_creates_both_when_missing(fake_anki):
    created = ensure_models(Anki(transport=fake_anki))
    assert created == [config.VOCAB_MODEL, config.GRAMMAR_MODEL]
    assert fake_anki.models[config.VOCAB_MODEL]["fields"] == VOCAB_FIELDS
    assert fake_anki.models[config.GRAMMAR_MODEL]["fields"] == GRAMMAR_FIELDS
    assert fake_anki.models[config.GRAMMAR_MODEL]["isCloze"] is True
    assert fake_anki.models[config.VOCAB_MODEL]["isCloze"] is False


def test_ensure_skips_existing(fake_anki):
    anki = Anki(transport=fake_anki)
    ensure_models(anki)
    assert ensure_models(anki) == []
    assert [a for a, _ in fake_anki.calls].count("createModel") == 2


def test_recognize_card_only_when_flag_set(fake_anki):
    ensure_models(Anki(transport=fake_anki))
    recognize = next(t for t in fake_anki.models[config.VOCAB_MODEL]["templates"] if t["Name"] == "Recognize")
    front = recognize["Front"]
    assert front.index("{{#Recognize}}") < front.index("{{Word}}") < front.index("{{/Recognize}}")


def test_templates_have_no_tts(fake_anki):
    ensure_models(Anki(transport=fake_anki))
    for model in fake_anki.models.values():
        for t in model["templates"]:
            for side in (t["Front"], t["Back"]):
                assert "tts" not in side and "[sound:" not in side
