import json
from datetime import date

from studyhelper import notes
from studyhelper.notes import new_run_dir, write_run

from test_drafts import GRAMMAR, VOCAB
from test_grade import QUIZ


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def base_run(tmp_path, monkeypatch):
    monkeypatch.setattr(notes.config, "NOTES_DIR", tmp_path)
    run = new_run_dir("spanish", "emociones", today=date(2026, 10, 19))
    dump(run / "source.json", {"type": "chatgpt", "label": "Emotion words session", "url": None})
    dump(run / "items.json", [
        {"key": "abrumado", "summary": "overwhelmed"},
        {"key": "harto", "summary": "fed up"},
        {"key": "negative tú commands", "summary": "No + yo form -o + es/as"},
    ])
    dump(run / "approved.json", {"drafts": [VOCAB, GRAMMAR], "dropped": []})
    dump(run / "pushed.json", {"results": [
        {"draft_id": "v1", "note_id": 111, "action": "add", "error": None},
        {"draft_id": "g1", "note_id": None, "action": "add", "error": "boom"},
    ]})
    return run


def test_new_run_dir_suffixes_on_collision(tmp_path, monkeypatch):
    monkeypatch.setattr(notes.config, "NOTES_DIR", tmp_path)
    a = new_run_dir("spanish", "ch01", today=date(2026, 10, 19))
    b = new_run_dir("spanish", "ch01", today=date(2026, 10, 19))
    assert a.name == "2026-10-19-ch01" and b.name == "2026-10-19-ch01-2"
    assert a.parent == tmp_path / "spanish"


def test_write_run_with_quiz(tmp_path, monkeypatch):
    run = base_run(tmp_path, monkeypatch)
    dump(run / "quiz.json", QUIZ)
    dump(run / "results.json", {"answers": [
        {"id": "q1", "given": "agobiado", "correct": False, "accent_only": False},
        {"id": "q2", "given": "atónito", "correct": True, "accent_only": False},
        {"id": "q3", "given": "da", "correct": True, "accent_only": False},
    ], "score": 2, "total": 3, "keep": ["abrumado"]})
    md = write_run(run).read_text(encoding="utf-8")
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    assert meta["path"] == "quiz" and meta["schema"] == 1
    assert "## Quiz" in md and "2 / 3" in md
    assert "agobiado" in md


def test_write_run_direct_path_has_no_quiz(tmp_path, monkeypatch):
    run = base_run(tmp_path, monkeypatch)
    md = write_run(run).read_text(encoding="utf-8")
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    assert meta["path"] == "direct" and meta["quiz"] is None
    assert "## Quiz" not in md
    assert meta["date"] == "2026-10-19" and meta["slug"] == "emociones"


def test_items_marked_carded_from_pushed(tmp_path, monkeypatch):
    run = base_run(tmp_path, monkeypatch)
    md = write_run(run).read_text(encoding="utf-8")
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    carded = {i["key"]: i["carded"] for i in meta["items"]}
    # g1 failed to push, so its item is not carded
    assert carded == {"abrumado": True, "harto": False, "negative tú commands": False}
    assert meta["cards"] == [{"draft_id": "v1", "note_id": 111, "action": "add"}]
    assert "harto" in md and "111" in md
