import copy

import pytest

from studyhelper.drafts import DraftError, blank, mark, to_anki_note, validate, vocab_fields

VOCAB = {
    "id": "v1",
    "kind": "vocab",
    "word": "abrumado",
    "meaning": "overwhelmed (by too many things)",
    "sentence": "Con tantos correos sin leer, me siento [abrumado].",
    "sentence_en": "With so many unread emails, I feel overwhelmed.",
    "tip": "abrumado <b>por</b> / <b>con</b> algo",
    "examples": [
        {"es": "Me siento [abrumado] con tantas decisiones.", "en": "I feel overwhelmed by so many decisions."},
        {"es": "Estaba [abrumada] por el cariño de todos.", "en": "She was overwhelmed by everyone's affection."},
        {"es": "No te sientas [abrumado].", "en": "Don't feel overwhelmed."},
    ],
    "source": "Cómo me siento · emociones",
    "tags": ["Emociones", "source::chatgpt", "emociones"],
    "recognize": True,
    "action": "add",
    "match_note_id": None,
    "flag": None,
}

GRAMMAR = {
    "id": "g1",
    "kind": "grammar",
    "rule_key": "negative tú commands",
    "text": "¡No {{c1::digas::decir, tú}} eso! ¡No {{c2::hables::hablar, tú}}!",
    "rule": "Negative tú: yo form, drop -o, add -es (-ar) / -as (-er, -ir).",
    "reference": "Ch. 1 §7",
    "source": "Spanish Grammar For Dummies",
    "tags": ["mandatos", "source::book::ch01"],
    "action": "add",
    "match_note_id": None,
    "flag": None,
}


def v(**changes):
    d = copy.deepcopy(VOCAB)
    d.update(changes)
    return d


def test_valid_drafts_pass():
    validate(VOCAB)
    validate(GRAMMAR)


def test_sentence_requires_exactly_one_marker():
    with pytest.raises(DraftError, match="v1"):
        validate(v(sentence="Me siento abrumado."))
    with pytest.raises(DraftError):
        validate(v(sentence="Me siento [muy] [abrumado]."))
    bad_example = copy.deepcopy(VOCAB["examples"])
    bad_example[0]["es"] = "Sin marcador."
    with pytest.raises(DraftError):
        validate(v(examples=bad_example))


def test_examples_must_be_three():
    with pytest.raises(DraftError):
        validate(v(examples=VOCAB["examples"][:2]))


def test_rejects_markdown_bold():
    with pytest.raises(DraftError, match=r"\*\*"):
        validate(v(tip="Use **por** here"))


def test_merge_requires_match():
    with pytest.raises(DraftError):
        validate(v(action="merge", match_note_id=None))
    with pytest.raises(DraftError):
        validate(v(action="replace"))


def test_grammar_requires_cloze():
    g = dict(GRAMMAR, text="¡No digas eso!")
    with pytest.raises(DraftError):
        validate(g)


def test_mark_and_blank():
    assert mark("me siento [abrumado].") == "me siento <b>abrumado</b>."
    assert "abrumado" not in blank("me siento [abrumado].")
    assert "[...]" in blank("me siento [abrumado].")


def test_vocab_fields_blank_and_mark():
    f = vocab_fields(VOCAB, recognize=True)
    assert "[...]" in f["Prompt"] and "abrumado" not in f["Prompt"]
    assert "<b>abrumado</b>" in f["Sentence"]
    assert f["Examples"].count("<li>") == 3
    assert "<b>abrumada</b>" in f["Examples"]
    assert f["Recognize"] == "y"


def test_html_escaped():
    f = vocab_fields(v(meaning="<script>x</script>"), recognize=True)
    assert "<script>" not in f["Meaning"]
    assert "&lt;script&gt;" in f["Meaning"]


def test_tip_allows_bold_only():
    f = vocab_fields(v(tip="agradecido <b>por</b> algo <i>x</i>"), recognize=True)
    assert "<b>por</b>" in f["Tip"]
    assert "<i>" not in f["Tip"]


def test_recognize_flag_off():
    assert vocab_fields(VOCAB, recognize=False)["Recognize"] == ""


def test_to_anki_note_deck_and_tags():
    note = to_anki_note(VOCAB, "spanish")
    assert note["deckName"] == "Learn::Spanish::Vocab"
    assert note["modelName"] == "Learn Vocab"
    assert note["tags"] == ["emociones", "source::chatgpt"]
    assert note["options"]["allowDuplicate"] is True


def test_to_anki_note_grammar():
    note = to_anki_note(GRAMMAR, "spanish")
    assert note["deckName"] == "Learn::Spanish::Grammar"
    assert note["modelName"] == "Learn Grammar"
    assert note["fields"]["Text"] == GRAMMAR["text"]
