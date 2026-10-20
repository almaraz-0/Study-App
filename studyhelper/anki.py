"""Minimal AnkiConnect client."""

import json
import urllib.request
from urllib.error import URLError

from studyhelper import config


class AnkiError(Exception):
    pass


class AnkiUnreachable(AnkiError):
    pass


def _http_transport(url):
    def send(payload):
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"))
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    return send


class Anki:
    def __init__(self, url=config.ANKI_URL, transport=None):
        self._send = transport or _http_transport(url)

    def invoke(self, action, **params):
        try:
            reply = self._send({"action": action, "version": 6, "params": params})
        except (URLError, ConnectionError, TimeoutError) as e:
            raise AnkiUnreachable(config.UNREACHABLE_MSG) from e
        if reply.get("error") is not None:
            raise AnkiError(f"{action}: {reply['error']}")
        return reply.get("result")

    def ping(self):
        self.invoke("version")
