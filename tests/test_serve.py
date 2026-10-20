import json
import socket
import threading
import time
import urllib.request
from urllib.error import HTTPError

import pytest

from studyhelper.serve import render, serve

from test_drafts import VOCAB
from test_grade import QUIZ


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def start(run_dir, page):
    port = free_port()
    codes = []
    t = threading.Thread(target=lambda: codes.append(serve(run_dir, page, port=port, open_browser=False)), daemon=True)
    t.start()
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.05)
    return port, t, codes


def test_render_escapes_script_close():
    html = render("quiz", {"title": "</script><b>x"})
    data_tag = html.split('<script id="data" type="application/json">', 1)[1]
    assert data_tag.index("</script>") > data_tag.index("<\\/script>")


def test_quiz_grade_then_submit_writes_and_exits(tmp_path):
    (tmp_path / "quiz.json").write_text(json.dumps(QUIZ))
    port, t, codes = start(tmp_path, "quiz")
    assert (tmp_path / "quiz.html").exists()
    graded = post(port, "/grade", {"given": {"q1": "abrumado"}})
    assert graded["score"] == 1
    post(port, "/submit", {"results": graded})
    t.join(timeout=5)
    assert not t.is_alive() and codes == [0]
    assert json.loads((tmp_path / "results.json").read_text())["score"] == 1


def test_serve_submit_writes_and_exits(tmp_path):
    (tmp_path / "drafts.json").write_text(json.dumps({"subject": "spanish", "drafts": [VOCAB]}))
    port, t, codes = start(tmp_path, "review")
    post(port, "/submit", {"drafts": [VOCAB], "dropped": []})
    t.join(timeout=5)
    assert codes == [0]
    assert json.loads((tmp_path / "approved.json").read_text())["drafts"][0]["word"] == "abrumado"


def test_review_submit_rejects_invalid_draft(tmp_path):
    (tmp_path / "drafts.json").write_text(json.dumps({"subject": "spanish", "drafts": [VOCAB]}))
    port, t, codes = start(tmp_path, "review")
    bad = dict(VOCAB, sentence="no marker here")
    with pytest.raises(HTTPError) as e:
        post(port, "/submit", {"drafts": [bad], "dropped": []})
    assert e.value.code == 400
    assert "v1" in json.loads(e.value.read())["errors"][0]
    assert not (tmp_path / "approved.json").exists()
    post(port, "/submit", {"drafts": [VOCAB], "dropped": []})
    t.join(timeout=5)
    assert codes == [0]
