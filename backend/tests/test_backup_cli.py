import os
import sqlite3
import time

import pytest

from app.backup_cli import (
    AAD,
    BACKUP_SUFFIX,
    BackupError,
    create_backup,
    decode_key,
    generate_key,
    initialise_env_file,
    prune_backups,
    restore_backup,
    verify_backup,
)


def create_source_database(path, secret="private-health-note"):
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 5")
        connection.execute(
            "CREATE TABLE private_data (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO private_data (value) VALUES (?)", (secret,))
        connection.commit()


def read_secret(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT value FROM private_data").fetchone()[0]


def test_create_verify_and_restore_encrypted_backup(tmp_path):
    source = tmp_path / "source.db"
    backup_dir = tmp_path / "backups"
    output = tmp_path / "restored.db"
    create_source_database(source)
    key = decode_key(generate_key())

    backup = create_backup(source, backup_dir, key)
    encrypted = backup.read_bytes()

    assert backup.name.endswith(BACKUP_SUFFIX)
    assert encrypted.startswith(AAD)
    assert not encrypted.startswith(b"SQLite format 3")
    assert b"private-health-note" not in encrypted

    inspection = verify_backup(backup, key)
    assert inspection.integrity_ok is True
    assert inspection.foreign_key_errors == 0
    assert inspection.schema_version == 5

    assert restore_backup(backup, output, key) is None
    assert read_secret(output) == "private-health-note"


def test_wrong_key_and_tampering_are_rejected(tmp_path):
    source = tmp_path / "source.db"
    create_source_database(source)
    key = decode_key(generate_key())
    backup = create_backup(source, tmp_path / "backups", key)

    with pytest.raises(BackupError, match="authentication failed"):
        verify_backup(backup, decode_key(generate_key()))

    damaged = bytearray(backup.read_bytes())
    damaged[-1] ^= 1
    backup.write_bytes(damaged)
    with pytest.raises(BackupError, match="authentication failed"):
        verify_backup(backup, key)


def test_restore_requires_explicit_replace_and_keeps_safety_copy(tmp_path):
    source = tmp_path / "source.db"
    output = tmp_path / "live.db"
    create_source_database(source, "new-value")
    create_source_database(output, "old-value")
    key = decode_key(generate_key())
    backup = create_backup(source, tmp_path / "backups", key)

    with pytest.raises(BackupError, match="Refusing to overwrite"):
        restore_backup(backup, output, key)

    safety_copy = restore_backup(backup, output, key, replace=True)
    assert safety_copy is not None
    assert safety_copy.is_file()
    assert read_secret(output) == "new-value"
    assert read_secret(safety_copy) == "old-value"


def test_prune_honours_retention_and_minimum_file_count(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    now = time.time()
    paths = []
    for index, age_days in enumerate((0, 1, 10, 11)):
        path = backup_dir / f"backup-{index}{BACKUP_SUFFIX}"
        path.write_bytes(b"test")
        timestamp = now - age_days * 86400
        os.utime(path, (timestamp, timestamp))
        paths.append(path)

    deleted = prune_backups(
        backup_dir,
        retention_days=7,
        minimum_files=2,
        now=now,
    )

    assert set(deleted) == {paths[2], paths[3]}
    assert paths[0].exists()
    assert paths[1].exists()


def test_key_file_is_created_once_without_overwrite(tmp_path):
    env_file = tmp_path / ".env.backup"
    initialise_env_file(env_file)

    prefix, encoded_key = env_file.read_text(encoding="utf-8").strip().split("=", 1)
    assert prefix == "PERIOD_TRACKER_BACKUP_KEY"
    assert len(decode_key(encoded_key)) == 32

    with pytest.raises(BackupError, match="Refusing to overwrite"):
        initialise_env_file(env_file)
