"""Fixed names and paths shared by every studyhelper command."""

from pathlib import Path

ANKI_URL = "http://127.0.0.1:8765"
COLLECTION_PATH = Path.home() / "Library/Application Support/Anki2/User 1/collection.anki2"

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "notes"
BACKUPS_DIR = REPO_ROOT / "backups"

DECKS = {
    "spanish": {"vocab": "Learn::Spanish::Vocab", "grammar": "Learn::Spanish::Grammar"},
}
LEARN_PREFIX = "Learn::"
ARCHIVE_PREFIX = "Archive::"
KEEP_DECKS = [
    "Languages::Spanish::Vocabulary::April",
    "Languages::Spanish::Vocabulary::Session_2026",
]
KEEP_DEST = DECKS["spanish"]["vocab"]
LEGACY_TAG = "source::legacy"

VOCAB_MODEL = "Learn Vocab"
GRAMMAR_MODEL = "Learn Grammar"

# Whether new vocab notes also get the Spanish -> meaning "recognize" card.
RECOGNIZE_CARDS = True

UNREACHABLE_MSG = (
    "Anki isn't reachable. Open Anki on this Mac (AnkiConnect must be installed) and try again."
)
