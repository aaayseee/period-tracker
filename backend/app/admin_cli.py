import argparse
import getpass
import sqlite3

from fastapi import HTTPException

from .auth import generate_recovery_code, hash_password, hash_recovery_code, normalize_email
from .database import connect, init_database


def create_admin_account(
    connection: sqlite3.Connection,
    email: str,
    password: str,
) -> str:
    normalized_email = normalize_email(email)
    if len(password) < 8 or len(password) > 128:
        raise ValueError("Parola 8 ile 128 karakter arasında olmalıdır.")
    if connection.execute(
        "SELECT 1 FROM accounts WHERE email = ? COLLATE NOCASE",
        (normalized_email,),
    ).fetchone():
        raise ValueError("Bu e-posta adresi zaten kullanılıyor.")

    salt, password_digest = hash_password(password)
    recovery_code = generate_recovery_code()
    connection.execute(
        """
        INSERT INTO accounts (
            email, password_hash, password_salt, recovery_code_hash, role
        ) VALUES (?, ?, ?, ?, 'admin')
        """,
        (
            normalized_email,
            password_digest,
            salt,
            hash_recovery_code(recovery_code),
        ),
    )
    connection.commit()
    return recovery_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Luna yönetici hesabı oluşturur.")
    parser.add_argument("command", choices=["create"])
    parser.add_argument("--email", help="Yönetici e-posta adresi")
    args = parser.parse_args()

    init_database()
    email = args.email or input("Yönetici e-posta adresi: ").strip()
    password = getpass.getpass("Yönetici parolası: ")
    confirmation = getpass.getpass("Yönetici parolası (tekrar): ")
    if password != confirmation:
        raise SystemExit("Parolalar eşleşmiyor.")

    try:
        with connect() as connection:
            recovery_code = create_admin_account(connection, email, password)
    except (ValueError, HTTPException) as exc:
        message = exc.detail if isinstance(exc, HTTPException) else str(exc)
        raise SystemExit(str(message)) from exc

    print("Yönetici hesabı oluşturuldu.")
    print(f"Kurtarma kodu: {recovery_code}")
    print("Bu kod yalnızca şimdi gösterilir; güvenli bir yerde saklayın.")


if __name__ == "__main__":
    main()
