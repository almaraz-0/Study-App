import sqlite3

import pytest

from studyhelper.backup import BackupFailed, backup_collection


def _make_db(path, rows):
    con = sqlite3.connect(path)
    con.execute("create table notes (id integer primary key)")
    con.executemany("insert into notes values (?)", [(i,) for i in range(rows)])
    con.commit()
    con.close()


def test_backup_copies_and_verifies(tmp_path):
    src = tmp_path / "collection.anki2"
    _make_db(src, 3)
    out = backup_collection(src, tmp_path / "backups", expected_notes=3)
    assert out.exists()
    assert out.name == "collection.anki2"
    con = sqlite3.connect(out)
    assert con.execute("select count(*) from notes").fetchone()[0] == 3


def test_backup_count_mismatch_raises(tmp_path):
    src = tmp_path / "collection.anki2"
    _make_db(src, 3)
    with pytest.raises(BackupFailed, match="Create Backup"):
        backup_collection(src, tmp_path / "backups", expected_notes=4)


def test_backup_missing_source_raises(tmp_path):
    with pytest.raises(BackupFailed):
        backup_collection(tmp_path / "nope.anki2", tmp_path / "backups", expected_notes=0)
