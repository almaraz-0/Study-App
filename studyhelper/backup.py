"""Copy the Anki collection somewhere safe and check the copy is complete."""

import sqlite3
from datetime import datetime
from pathlib import Path


class BackupFailed(Exception):
    pass


MANUAL_HINT = "Make one by hand in Anki with File → Create Backup, then try again."


def backup_collection(src: Path, dest_dir: Path, expected_notes: int) -> Path:
    src = Path(src)
    if not src.exists():
        raise BackupFailed(f"Collection not found at {src}. {MANUAL_HINT}")
    out_dir = Path(dest_dir) / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "collection.anki2"
    try:
        # The online backup API gives a consistent copy even while Anki has the file open.
        source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        target = sqlite3.connect(out)
        with target:
            source.backup(target)
        source.close()
        # Only count(*): other queries can hit Anki's custom "unicase" collation.
        count = target.execute("select count(*) from notes").fetchone()[0]
        target.close()
    except sqlite3.Error as e:
        raise BackupFailed(f"Backup failed ({e}). {MANUAL_HINT}") from e
    if count != expected_notes:
        raise BackupFailed(
            f"Backup has {count} notes but Anki reports {expected_notes}. {MANUAL_HINT}"
        )
    return out
