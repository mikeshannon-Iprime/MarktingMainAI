from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    # Support legacy plaintext hashes from older seeds during migration.
    if not password_hash.startswith("$2"):
        return plain_password == password_hash
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
