import pytest

from studyhelper import youtube
from studyhelper.youtube import NoTranscript, fetch, format_lines, timestamp_url, video_id


@pytest.mark.parametrize("url", [
    "https://youtu.be/RocA3wA3QjU?si=Uux6mqCei3Iv-wUK",
    "https://www.youtube.com/watch?v=RocA3wA3QjU&t=42s",
    "https://youtube.com/shorts/RocA3wA3QjU",
    "https://www.youtube.com/embed/RocA3wA3QjU",
    "https://m.youtube.com/watch?feature=share&v=RocA3wA3QjU",
])
def test_video_id_variants(url):
    assert video_id(url) == "RocA3wA3QjU"


def test_video_id_rejects_other_urls():
    with pytest.raises(ValueError):
        video_id("https://example.com/watch?v=RocA3wA3QjU")


def test_timestamp_url():
    assert timestamp_url("RocA3wA3QjU", 125.7) == "https://youtu.be/RocA3wA3QjU?t=125"


def test_fetch_wraps_errors(monkeypatch):
    class Boom:
        def fetch(self, *a, **k):
            raise RuntimeError("disabled")

    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", Boom)
    with pytest.raises(NoTranscript, match="Paste the parts"):
        fetch("https://youtu.be/RocA3wA3QjU")


def test_fetch_returns_start_and_text(monkeypatch):
    class Snip:
        def __init__(self, start, text):
            self.start, self.text = start, text

    class Api:
        def fetch(self, vid, languages):
            assert vid == "RocA3wA3QjU" and languages == ["es", "en"]
            return [Snip(0.0, "Hola"), Snip(65.2, "¿Qué tal?")]

    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", Api)
    lines = fetch("https://youtu.be/RocA3wA3QjU")
    assert lines == [(0.0, "Hola"), (65.2, "¿Qué tal?")]
    assert format_lines("U", lines) == "URL: U\n[00:00] Hola\n[01:05] ¿Qué tal?"
