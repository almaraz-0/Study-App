"""Fetch a YouTube transcript with timestamps, for linking cards back to the moment."""

import sys
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


class NoTranscript(Exception):
    pass


def video_id(url: str) -> str:
    u = urlparse(url)
    host = (u.hostname or "").removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        vid = u.path.lstrip("/").split("/")[0]
    elif host == "youtube.com":
        if u.path == "/watch":
            vid = parse_qs(u.query).get("v", [""])[0]
        elif u.path.startswith(("/shorts/", "/embed/", "/live/")):
            vid = u.path.split("/")[2]
        else:
            vid = ""
    else:
        vid = ""
    if not vid:
        raise ValueError(f"Not a YouTube video link: {url}")
    return vid


def timestamp_url(vid: str, seconds: float) -> str:
    return f"https://youtu.be/{vid}?t={int(seconds)}"


def fetch(url: str, languages=("es", "en")) -> list[tuple[float, str]]:
    vid = video_id(url)
    try:
        snippets = YouTubeTranscriptApi().fetch(vid, languages=list(languages))
        return [(s.start, s.text) for s in snippets]
    except Exception as e:
        raise NoTranscript("No transcript for this video. Paste the parts you care about instead.") from e


def format_lines(url: str, lines: list[tuple[float, str]]) -> str:
    out = [f"URL: {url}"]
    for start, text in lines:
        m, s = divmod(int(start), 60)
        out.append(f"[{m:02d}:{s:02d}] {text}")
    return "\n".join(out)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m studyhelper.youtube <url>", file=sys.stderr)
        return 2
    try:
        print(format_lines(argv[0], fetch(argv[0])))
    except (NoTranscript, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
