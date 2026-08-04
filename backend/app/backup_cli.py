"""Encrypted, full-database backups for Luna's SQLite database.

The regular web application does not import this module. It is intended to run as
an isolated Docker service or as a maintenance CLI.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MAGIC = b"LUNABKP1"
FORMAT_VERSION = 1
NONCE_SIZE = 12
AAD = MAGIC + bytes((FORMAT_VERSION,))
BACKUP_SUFFIX = ".luna-backup"


class BackupError(RuntimeError):
    """A safe, user-facing backup operation failure."""


@dataclass(frozen=True)
class DatabaseInspection:
    size_bytes: int
    schema_version: int
    integrity_ok: bool
    foreign_key_errors: int


def generate_key() -> str:
    """Return a URL-safe base64 encoded 256-bit key."""

    return base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii")


def decode_key(encoded_key: str) -> bytes:
    value = encoded_key.strip()
    if not value:
        raise BackupError("PERIOD_TRACKER_BACKUP_KEY is not configured.")
    try:
        key = base64.b64decode(value, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise BackupError("Backup key is not valid URL-safe base64.") from exc
    if len(key) != 32:
        raise BackupError("Backup key must decode to exactly 32 bytes (256 bits).")
    return key


def key_from_environment() -> bytes:
    return decode_key(os.getenv("PERIOD_TRACKER_BACKUP_KEY", ""))


def initialise_env_file(path: Path) -> None:
    """Create a secret env file without ever printing its key."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise BackupError(f"Refusing to overwrite existing key file: {path}") from exc

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"PERIOD_TRACKER_BACKUP_KEY={generate_key()}\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _readonly_uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro"


def inspect_database(path: Path) -> DatabaseInspection:
    if not path.is_file():
        raise BackupError(f"SQLite database does not exist: {path}")
    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as connection:
            integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
            integrity_ok = integrity_rows == [("ok",)]
            foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
            schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.Error as exc:
        raise BackupError(f"SQLite validation failed for {path.name}: {exc}") from exc

    return DatabaseInspection(
        size_bytes=path.stat().st_size,
        schema_version=schema_version,
        integrity_ok=integrity_ok,
        foreign_key_errors=foreign_key_errors,
    )


def _require_valid_database(path: Path) -> DatabaseInspection:
    inspection = inspect_database(path)
    if not inspection.integrity_ok:
        raise BackupError(f"SQLite integrity_check failed for {path.name}.")
    if inspection.foreign_key_errors:
        raise BackupError(
            f"SQLite foreign_key_check found {inspection.foreign_key_errors} error(s)."
        )
    return inspection


def create_sqlite_snapshot(source_path: Path, snapshot_path: Path) -> None:
    """Use SQLite's online backup API to produce a consistent snapshot."""

    if not source_path.is_file():
        raise BackupError(f"SQLite database does not exist: {source_path}")
    try:
        with sqlite3.connect(_readonly_uri(source_path), uri=True) as source:
            with sqlite3.connect(snapshot_path) as destination:
                source.backup(destination)
    except sqlite3.Error as exc:
        raise BackupError(f"Could not create SQLite snapshot: {exc}") from exc


def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, AAD)
    return AAD + nonce + ciphertext


def decrypt_bytes(payload: bytes, key: bytes) -> bytes:
    header_size = len(AAD) + NONCE_SIZE
    if len(payload) <= header_size or payload[: len(AAD)] != AAD:
        raise BackupError("Unknown or damaged Luna backup format.")
    nonce = payload[len(AAD) : header_size]
    ciphertext = payload[header_size:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, AAD)
    except InvalidTag as exc:
        raise BackupError(
            "Backup authentication failed: the key is wrong or the file was changed."
        ) from exc


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def create_backup(database_path: Path, backup_dir: Path, key: bytes) -> Path:
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="luna-snapshot-") as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.db"
            create_sqlite_snapshot(database_path, snapshot_path)
            _require_valid_database(snapshot_path)
            encrypted = encrypt_bytes(snapshot_path.read_bytes(), key)
    except OSError as exc:
        raise BackupError(f"Could not prepare encrypted backup: {exc}") from exc

    target = backup_dir / f"luna-{_timestamp()}{BACKUP_SUFFIX}"
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".luna-writing-", dir=backup_dir
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                temporary_path.chmod(0o600)
            except OSError:
                pass
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
    except OSError as exc:
        raise BackupError(f"Could not write encrypted backup: {exc}") from exc
    return target


def _decrypt_to_temporary(backup_path: Path, key: bytes) -> tuple[tempfile.TemporaryDirectory, Path]:
    if not backup_path.is_file():
        raise BackupError(f"Encrypted backup does not exist: {backup_path}")
    plaintext = decrypt_bytes(backup_path.read_bytes(), key)
    temp_dir = tempfile.TemporaryDirectory(prefix="luna-verify-")
    database_path = Path(temp_dir.name) / "verified.db"
    database_path.write_bytes(plaintext)
    return temp_dir, database_path


def verify_backup(backup_path: Path, key: bytes) -> DatabaseInspection:
    temp_dir, database_path = _decrypt_to_temporary(backup_path, key)
    try:
        return _require_valid_database(database_path)
    finally:
        temp_dir.cleanup()


def restore_backup(
    backup_path: Path,
    output_path: Path,
    key: bytes,
    *,
    replace: bool = False,
) -> Path | None:
    """Validate and restore a backup atomically.

    When replacing an existing database, a plaintext pre-restore safety copy is
    retained beside it and returned to the caller.
    """

    output_path = output_path.resolve()
    if output_path.exists() and not replace:
        raise BackupError(
            f"Refusing to overwrite existing file: {output_path}. Use --replace explicitly."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_dir, decrypted_path = _decrypt_to_temporary(backup_path, key)
    safety_copy: Path | None = None
    staged_path = output_path.with_name(f".{output_path.name}.restoring")
    try:
        _require_valid_database(decrypted_path)
        if output_path.exists():
            safety_copy = output_path.with_name(
                f"{output_path.stem}.pre-restore-{_timestamp()}{output_path.suffix}"
            )
            shutil.copy2(output_path, safety_copy)
        shutil.copy2(decrypted_path, staged_path)
        _require_valid_database(staged_path)
        os.replace(staged_path, output_path)
    finally:
        staged_path.unlink(missing_ok=True)
        temp_dir.cleanup()
    return safety_copy


def encrypted_backups(backup_dir: Path) -> list[Path]:
    if not backup_dir.is_dir():
        return []
    return sorted(
        backup_dir.glob(f"*{BACKUP_SUFFIX}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def prune_backups(
    backup_dir: Path,
    retention_days: int,
    minimum_files: int,
    *,
    now: float | None = None,
) -> list[Path]:
    if retention_days < 1:
        raise BackupError("Backup retention must be at least 1 day.")
    if minimum_files < 1:
        raise BackupError("At least one encrypted backup must be retained.")

    cutoff = (time.time() if now is None else now) - retention_days * 86400
    deleted: list[Path] = []
    for path in encrypted_backups(backup_dir)[minimum_files:]:
        if path.stat().st_mtime < cutoff:
            path.unlink()
            deleted.append(path)
    return deleted


def _positive_int_env(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise BackupError(f"{name} must be an integer.") from exc
    if parsed < 1:
        raise BackupError(f"{name} must be at least 1.")
    return parsed


def configured_paths() -> tuple[Path, Path]:
    database = Path(os.getenv("PERIOD_TRACKER_DB", "data/period_tracker.db"))
    backup_dir = Path(os.getenv("PERIOD_TRACKER_BACKUP_DIR", "backups"))
    return database, backup_dir


def run_once() -> Path:
    database_path, backup_dir = configured_paths()
    key = key_from_environment()
    created = create_backup(database_path, backup_dir, key)
    deleted = prune_backups(
        backup_dir,
        _positive_int_env("PERIOD_TRACKER_BACKUP_RETENTION_DAYS", 30),
        _positive_int_env("PERIOD_TRACKER_BACKUP_MIN_FILES", 3),
    )
    print(f"Created and verified encrypted backup: {created.name}", flush=True)
    if deleted:
        print(f"Pruned {len(deleted)} expired encrypted backup(s).", flush=True)
    return created


def run_schedule() -> None:
    interval_hours = _positive_int_env("PERIOD_TRACKER_BACKUP_INTERVAL_HOURS", 24)
    retry_seconds = min(interval_hours * 3600, 300)
    while True:
        try:
            run_once()
            time.sleep(interval_hours * 3600)
        except BackupError as exc:
            print(f"Backup failed: {exc}", file=sys.stderr, flush=True)
            time.sleep(retry_seconds)


def _latest_backup_or_error(backup_dir: Path) -> Path:
    backups = encrypted_backups(backup_dir)
    if not backups:
        raise BackupError(f"No encrypted backups found in {backup_dir}.")
    return backups[0]


def list_backups(backup_dir: Path) -> list[Path]:
    backups = encrypted_backups(backup_dir)
    if not backups:
        print(f"No encrypted backups found in {backup_dir}.")
        return []
    for path in backups:
        created = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        print(f"{path.name}\t{path.stat().st_size} bytes\t{created}")
    return backups


def check_status() -> Path:
    _, backup_dir = configured_paths()
    latest = _latest_backup_or_error(backup_dir)
    interval_hours = _positive_int_env("PERIOD_TRACKER_BACKUP_INTERVAL_HOURS", 24)
    maximum_age = interval_hours * 3600 * 2 + 3600
    if time.time() - latest.stat().st_mtime > maximum_age:
        raise BackupError(f"Latest encrypted backup is too old: {latest.name}")
    verify_backup(latest, key_from_environment())
    return latest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Luna encrypted SQLite backup manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-env", help="create a new secret key env file")
    init_parser.add_argument("--path", type=Path, default=Path(".env.backup"))

    subparsers.add_parser("create", help="create, verify and prune encrypted backups")
    subparsers.add_parser("schedule", help="run an immediate backup, then repeat")
    subparsers.add_parser("status", help="verify that the newest backup is fresh and valid")
    subparsers.add_parser("list", help="list encrypted backup filenames and timestamps")

    verify_parser = subparsers.add_parser("verify", help="authenticate and validate one backup")
    verify_parser.add_argument("backup", type=Path)

    restore_parser = subparsers.add_parser("restore", help="restore one validated backup")
    restore_parser.add_argument("backup", type=Path)
    restore_parser.add_argument("--output", type=Path, required=True)
    restore_parser.add_argument("--replace", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init-env":
            initialise_env_file(args.path)
            print(f"Created backup key file: {args.path.resolve()}")
            print("Store a separate copy in a password manager; lost keys cannot be recovered.")
        elif args.command == "create":
            run_once()
        elif args.command == "schedule":
            run_schedule()
        elif args.command == "status":
            latest = check_status()
            print(f"Latest encrypted backup is healthy: {latest.name}")
        elif args.command == "list":
            _, backup_dir = configured_paths()
            list_backups(backup_dir)
        elif args.command == "verify":
            inspection = verify_backup(args.backup, key_from_environment())
            print(
                "Backup is authentic and SQLite checks passed "
                f"(schema v{inspection.schema_version}, {inspection.size_bytes} bytes)."
            )
        elif args.command == "restore":
            safety_copy = restore_backup(
                args.backup,
                args.output,
                key_from_environment(),
                replace=args.replace,
            )
            print(f"Restored and verified SQLite database: {args.output.resolve()}")
            if safety_copy:
                print(f"Previous database safety copy: {safety_copy}")
        return 0
    except BackupError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
