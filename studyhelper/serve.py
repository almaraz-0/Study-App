"""Serve the quiz or review page for one run on 127.0.0.1.

The process exits 0 once the page submits, which is Claude's signal to continue.
"""

import json
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib import resources
from pathlib import Path

from studyhelper.drafts import DraftError, validate
from studyhelper.grade import grade

IDLE_SECONDS = 2 * 60 * 60
INPUTS = {"quiz": "quiz.json", "review": "drafts.json"}


def render(page: str, data: dict) -> str:
    template = resources.files("studyhelper").joinpath(f"pages/{page}.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("/*DATA*/", payload)


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def serve(run_dir: Path, page: str, port: int = 0, open_browser: bool = True) -> int:
    run_dir = Path(run_dir)
    data = json.loads((run_dir / INPUTS[page]).read_text(encoding="utf-8"))
    html = render(page, data)
    (run_dir / f"{page}.html").write_text(html, encoding="utf-8")
    state = {"done": False, "last": time.monotonic()}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, code, body, ctype="application/json"):
            raw = body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            state["last"] = time.monotonic()
            if self.path in ("/", f"/{page}.html"):
                self._reply(200, html, "text/html")
            else:
                self._reply(404, {"error": "not found"})

        def do_POST(self):
            state["last"] = time.monotonic()
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._reply(400, {"errors": ["invalid JSON"]})
            if page == "quiz" and self.path == "/grade":
                return self._reply(200, grade(data, body.get("given", {})))
            if self.path != "/submit":
                return self._reply(404, {"error": "not found"})
            if page == "quiz":
                _write_json(run_dir / "results.json", body["results"])
            else:
                errors = []
                for d in body.get("drafts", []):
                    try:
                        validate(d)
                    except DraftError as e:
                        errors.append(str(e))
                if errors:
                    return self._reply(400, {"errors": errors})
                _write_json(run_dir / "approved.json", {"drafts": body.get("drafts", []), "dropped": body.get("dropped", [])})
            state["done"] = True
            self._reply(200, {"ok": True})

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"OPEN {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        while not state["done"]:
            server.handle_request()
            if time.monotonic() - state["last"] > IDLE_SECONDS:
                print("Timed out waiting for the page.", file=sys.stderr)
                return 3
    finally:
        server.server_close()
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[1] not in INPUTS:
        print("usage: python -m studyhelper.serve <run_dir> quiz|review", file=sys.stderr)
        return 2
    return serve(Path(argv[0]), argv[1])


if __name__ == "__main__":
    sys.exit(main())
