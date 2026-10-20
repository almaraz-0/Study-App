from studyhelper import config
from studyhelper.anki import Anki
from studyhelper.dedupe import field_term, find_candidates, quote


def vocab(word):
    return {"id": "v1", "kind": "vocab", "word": word}


def test_query_escapes_phrase():
    assert quote("al borde de...") == '"al borde de..."'
    assert quote('say "hi"') == '"say \\"hi\\""'
    assert quote("a_b*c:d") == '"a\\_b\\*c\\:d"'
    assert field_term("Word", "me da pena") == '"Word:me da pena"'


def test_vocab_candidate_found(fake_anki):
    nid, _ = fake_anki.add("Learn::Spanish::Vocab", {"Word": "harto", "Meaning": "fed up"}, model=config.VOCAB_MODEL)
    found = find_candidates(Anki(transport=fake_anki), vocab("harto"))
    assert [(c.note_id, c.kind) for c in found] == [(nid, "vocab")]
    assert "fed up" in found[0].summary


def test_phrase_candidate_found(fake_anki):
    fake_anki.add("Learn::Spanish::Vocab", {"Word": "me da pena", "Meaning": "I feel embarrassed"}, model=config.VOCAB_MODEL)
    found = find_candidates(Anki(transport=fake_anki), vocab("me da pena"))
    assert [c.kind for c in found] == ["vocab"]


def test_legacy_candidate_kind(fake_anki):
    nid, _ = fake_anki.add(
        "Learn::Spanish::Vocab",
        {"Front": "Do you appear in the photo?", "Back": "aparecer - <b>apareces</b> en la foto"},
        tags=[config.LEGACY_TAG],
    )
    found = find_candidates(Anki(transport=fake_anki), vocab("aparecer"))
    assert [(c.note_id, c.kind) for c in found] == [(nid, "legacy")]
    assert "<b>" not in found[0].summary


def test_archive_candidate_kind(fake_anki):
    fake_anki.add("Archive::Languages::Spanish::Vocabulary", {"Front": "to waste", "Back": "desperdiciar"})
    found = find_candidates(Anki(transport=fake_anki), vocab("desperdiciar"))
    assert [c.kind for c in found] == ["archive"]


def test_grammar_candidate_kind(fake_anki):
    fake_anki.add(
        "Learn::Spanish::Grammar",
        {"Text": "¡No {{c1::digas}}!", "Rule": "yo form, drop -o, add -es/-as"},
        model=config.GRAMMAR_MODEL,
        tags=["rule::negative_tú_commands"],
    )
    draft = {"id": "g1", "kind": "grammar", "rule_key": "negative tú commands"}
    assert [c.kind for c in find_candidates(Anki(transport=fake_anki), draft)] == ["grammar"]


def test_no_candidates_returns_empty(fake_anki):
    assert find_candidates(Anki(transport=fake_anki), vocab("chiveado")) == []


def test_grammar_note_created_by_push_is_found(fake_anki):
    import copy
    from studyhelper.push import push
    from test_drafts import GRAMMAR
    anki = Anki(transport=fake_anki)
    push(anki, {"drafts": [copy.deepcopy(GRAMMAR)], "dropped": []}, "spanish", already=set(), run_id="r1")
    found = find_candidates(anki, {"id": "g9", "kind": "grammar", "rule_key": "Negative tú commands"})
    assert [c.kind for c in found] == ["grammar"]
