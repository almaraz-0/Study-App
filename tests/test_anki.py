from urllib.error import URLError

import pytest

from studyhelper import config
from studyhelper.anki import Anki, AnkiError, AnkiUnreachable


def test_invoke_sends_v6_payload():
    sent = []

    def transport(payload):
        sent.append(payload)
        return {"result": [], "error": None}

    Anki(transport=transport).invoke("deckNames")
    assert sent == [{"action": "deckNames", "version": 6, "params": {}}]


def test_invoke_raises_on_error_field():
    anki = Anki(transport=lambda p: {"result": None, "error": "boom"})
    with pytest.raises(AnkiError, match="boom"):
        anki.invoke("deckNames")


def test_unreachable_raises_friendly_error():
    def transport(payload):
        raise URLError("refused")

    with pytest.raises(AnkiUnreachable) as e:
        Anki(transport=transport).ping()
    assert str(e.value) == config.UNREACHABLE_MSG


def test_fake_anki_works_as_transport(fake_anki):
    fake_anki.add("Spanish", {"Front": "hola"})
    assert "Spanish" in Anki(transport=fake_anki).invoke("deckNames")
