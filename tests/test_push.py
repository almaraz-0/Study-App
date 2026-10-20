import copy

import pytest

from studyhelper import config
from studyhelper.anki import Anki, AnkiUnreachable
from studyhelper.drafts import DraftError
from studyhelper.push import push

from test_drafts import GRAMMAR, VOCAB


def approved(*drafts):
    return {"drafts": [copy.deepcopy(d) for d in drafts], "dropped": []}


def test_push_adds_notes(fake_anki):
    results = push(Anki(transport=fake_anki), approved(VOCAB, GRAMMAR), "spanish", already=set())
    assert [r["action"] for r in results] == ["add", "add"]
    assert all(r["error"] is None and r["note_id"] for r in results)
    words = [n["fields"].get("Word") for n in fake_anki.notes.values()]
    assert "abrumado" in words
    assert config.VOCAB_MODEL in fake_anki.models


def test_push_merge_appends_example_only(fake_anki):
    nid, _ = fake_anki.add(
        "Learn::Spanish::Vocab",
        {"Word": "abrumado", "Meaning": "overwhelmed", "Examples": "<ul><li>old</li></ul>", "Tip": "keep me"},
        model=config.VOCAB_MODEL,
    )
    d = dict(copy.deepcopy(VOCAB), action="merge", match_note_id=nid)
    [r] = push(Anki(transport=fake_anki), approved(d), "spanish", already=set())
    fields = fake_anki.notes[nid]["fields"]
    assert r == {"draft_id": "v1", "note_id": nid, "action": "merge", "error": None}
    assert fields["Examples"].startswith("<ul><li>old</li><li>")
    assert "<b>abrumado</b>" in fields["Examples"]
    assert fields["Tip"] == "keep me" and fields["Meaning"] == "overwhelmed"
    assert "source::chatgpt" in fake_anki.notes[nid]["tags"]


def test_push_tag_only_does_not_update_fields(fake_anki):
    nid, _ = fake_anki.add("Learn::Spanish::Vocab", {"Front": "x", "Back": "aparecer"}, tags=[config.LEGACY_TAG])
    d = dict(copy.deepcopy(VOCAB), action="tag_only", match_note_id=nid)
    push(Anki(transport=fake_anki), approved(d), "spanish", already=set())
    assert "updateNoteFields" not in [a for a, _ in fake_anki.calls]
    assert "emociones" in fake_anki.notes[nid]["tags"]


def test_push_is_idempotent(fake_anki):
    anki = Anki(transport=fake_anki)
    first = push(anki, approved(VOCAB, GRAMMAR), "spanish", already=set())
    before = len(fake_anki.notes)
    second = push(anki, approved(VOCAB, GRAMMAR), "spanish", already={r["draft_id"] for r in first})
    assert second == []
    assert len(fake_anki.notes) == before


def test_push_aborts_before_writing_when_anki_down(fake_anki):
    fake_anki.down = True
    with pytest.raises(AnkiUnreachable):
        push(Anki(transport=fake_anki), approved(VOCAB), "spanish", already=set())
    assert fake_anki.writes() == []


def test_invalid_draft_blocks_all_writes(fake_anki):
    bad = dict(copy.deepcopy(GRAMMAR), id="g2", text="no cloze")
    with pytest.raises(DraftError, match="g2"):
        push(Anki(transport=fake_anki), approved(VOCAB, bad), "spanish", already=set())
    assert fake_anki.writes() == []


def test_one_failure_doesnt_stop_others(fake_anki):
    anki = Anki(transport=fake_anki)
    d2 = dict(copy.deepcopy(VOCAB), id="v2", action="merge", match_note_id=999999)
    results = push(anki, approved(d2, GRAMMAR), "spanish", already=set())
    assert results[0]["error"] and results[0]["note_id"] is None
    assert results[1]["error"] is None and results[1]["note_id"]


def test_merge_into_deleted_note_is_an_error_not_a_crash(fake_anki):
    anki = Anki(transport=fake_anki)
    d2 = dict(copy.deepcopy(VOCAB), id="v2", action="merge", match_note_id=424242)
    results = push(anki, approved(VOCAB, d2), "spanish", already=set(), run_id="r1")
    assert results[0]["error"] is None
    assert results[1]["error"] and "424242" in results[1]["error"]


def test_rerun_without_record_does_not_duplicate(fake_anki):
    anki = Anki(transport=fake_anki)
    push(anki, approved(VOCAB), "spanish", already=set(), run_id="r1")
    # pushed.json lost (crash before it was written): the run tag still finds the note
    [r] = push(anki, approved(VOCAB), "spanish", already=set(), run_id="r1")
    assert r["error"] is None
    assert [a for a, _ in fake_anki.calls].count("addNote") == 1
    assert sum(1 for n in fake_anki.notes.values() if n["fields"].get("Word") == "abrumado") == 1


def test_lost_reply_after_add_does_not_duplicate(fake_anki):
    anki = Anki(transport=fake_anki)
    fake_anki.lose_reply = {"addNote"}
    [first] = push(anki, approved(VOCAB), "spanish", already=set(), run_id="r1")
    assert first["error"]
    fake_anki.lose_reply = set()
    [second] = push(anki, approved(VOCAB), "spanish", already=set(), run_id="r1")
    assert second["error"] is None and second["note_id"]
    assert sum(1 for n in fake_anki.notes.values() if n["fields"].get("Word") == "abrumado") == 1


def test_merge_rerun_does_not_append_twice(fake_anki):
    nid, _ = fake_anki.add("Learn::Spanish::Vocab", {"Word": "abrumado", "Examples": "<ul><li>old</li></ul>"}, model=config.VOCAB_MODEL)
    d = dict(copy.deepcopy(VOCAB), action="merge", match_note_id=nid)
    anki = Anki(transport=fake_anki)
    push(anki, approved(d), "spanish", already=set(), run_id="r1")
    push(anki, approved(d), "spanish", already=set(), run_id="r1")
    assert fake_anki.notes[nid]["fields"]["Examples"].count("<li>") == 2


def test_results_reported_as_they_happen(fake_anki):
    seen = []
    push(Anki(transport=fake_anki), approved(VOCAB, GRAMMAR), "spanish", already=set(), run_id="r1", on_result=seen.append)
    assert [r["draft_id"] for r in seen] == ["v1", "g1"]


def test_main_refuses_while_another_push_runs(tmp_path, monkeypatch):
    import fcntl, json as _json
    from studyhelper import push as push_mod
    (tmp_path / "approved.json").write_text(_json.dumps(approved(VOCAB)))
    with open(tmp_path / ".push.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        monkeypatch.setattr(push_mod, "push", lambda *a, **k: pytest.fail("pushed while locked"))
        assert push_mod.main([str(tmp_path)]) == 1
