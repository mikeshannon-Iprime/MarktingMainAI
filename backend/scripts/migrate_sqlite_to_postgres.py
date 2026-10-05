#!/usr/bin/env python3
"""
Migrate data from legacy SQLite marketingmind.db into local PostgreSQL.

Usage (from backend/):
    python scripts/migrate_sqlite_to_postgres.py

If SQLite is empty (default), runs full PostgreSQL seed from test_data.json.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.db.database import _normalize_database_url
from app.db.models import (
    Base,
    CampaignContact,
    CampaignItem,
    JobApplication,
    Portal,
    User,
    UserSettings,
)

SQLITE_PATH = BACKEND_ROOT / "marketingmind.db"


def get_sqlite_counts() -> dict[str, int]:
    if not SQLITE_PATH.exists():
        return {}
    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()
    tables = [
        row[0]
        for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    ]
    counts = {}
    for table in tables:
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return counts


def migrate_sqlite_rows(session: Session) -> dict[str, int]:
    """Copy rows from legacy SQLite schema into PostgreSQL ORM tables."""
    if not SQLITE_PATH.exists():
        return {}

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    migrated = {"users": 0, "contacts": 0, "campaigns": 0, "portals": 0, "job_applications": 0}

    admin = session.query(User).filter(User.email == "admin@marketingmind.ai").first()
    admin_id = admin.id if admin else None

    for row in cur.execute("SELECT * FROM users"):
        email = (row["email"] or "").strip().lower()
        if not email or session.query(User).filter(User.email == email).first():
            continue
        password_hash = row["password_hash"] or ""
        if not password_hash.startswith("$2"):
            password_hash = hash_password(password_hash or "ChangeMe@123")
        user = User(
            external_id=f"u-sqlite-{row['id']}",
            name=row["name"] or "User",
            email=email,
            password_hash=password_hash,
            role=row["role"] or "user",
            is_active=bool(row["is_active"]) if row["is_active"] is not None else True,
        )
        session.add(user)
        session.flush()
        session.add(UserSettings(user_id=user.id))
        migrated["users"] += 1
        if admin_id is None and user.role in ("admin", "super_admin"):
            admin_id = user.id

    if admin_id is None:
        admin = session.query(User).order_by(User.id).first()
        admin_id = admin.id if admin else None

    for row in cur.execute("SELECT * FROM contacts"):
        session.add(
            CampaignContact(
                user_id=admin_id,
                name=row["name"] or "",
                email=row["email"] or "",
                company=row["company"] or "",
                status=row["status"] or "Queued",
                list_name=row["list_name"] or "Default",
            )
        )
        migrated["contacts"] += 1

    for row in cur.execute("SELECT * FROM campaigns"):
        session.add(
            CampaignItem(
                user_id=admin_id,
                name=row["name"] or "Campaign",
                subject=row["subject"] or row["name"] or "",
                body=row["body"] or "",
                status=row["status"] or "Draft",
                scheduled_for=row["scheduled_for"],
                sent_count=row["sent_count"] or 0,
                opened_count=row["opened_count"] or 0,
                replied_count=row["replied_count"] or 0,
            )
        )
        migrated["campaigns"] += 1

    for row in cur.execute("SELECT * FROM portals"):
        session.add(
            Portal(
                user_id=admin_id,
                name=row["name"] or "",
                url=row["url"] or "",
                status=row["status"] or "Active",
            )
        )
        migrated["portals"] += 1

    for row in cur.execute("SELECT * FROM job_applications"):
        session.add(
            JobApplication(
                user_id=admin_id,
                role=row["role"] or "",
                company=row["company"] or "",
                status=row["status"] or "Applied",
                stage=row["stage"] or "",
                updated_label=row["updated_label"] or "",
                action_label=row["action_label"] or "",
            )
        )
        migrated["job_applications"] += 1

    conn.close()
    session.flush()
    return migrated


def run_full_seed() -> None:
    from scripts.init_postgres_schema import main as seed_main

    seed_main()


def main() -> int:
    settings = get_settings()
    if not settings.database_url:
        print("ERROR: DATABASE_URL is not set in backend/.env")
        return 1

    sqlite_counts = get_sqlite_counts()
    print(f"SQLite file: {SQLITE_PATH}")
    print(f"SQLite tables: {sqlite_counts or '(file missing)'}")

    url = _normalize_database_url(settings.database_url)
    print(f"PostgreSQL target: {url.split('@')[-1]}")

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("PostgreSQL connection: OK")

    Base.metadata.create_all(bind=engine)
    print("PostgreSQL schema: tables ensured")

    sqlite_total = sum(sqlite_counts.values()) if sqlite_counts else 0

    with Session(engine) as session:
        if sqlite_total > 0:
            migrated = migrate_sqlite_rows(session)
            session.commit()
            print("Migrated from SQLite:", json.dumps(migrated))
        else:
            user_count = session.query(User).count()
            if user_count == 0:
                print("SQLite is empty — running full PostgreSQL seed (test_data.json)...")
                session.commit()
                run_full_seed()
            else:
                print(f"PostgreSQL already has {user_count} user(s). Skipping seed.")
                session.commit()

    with Session(engine) as session:
        users = session.query(User).count()
        portals = session.query(Portal).count()
        contacts = session.query(CampaignContact).count()
        print("\nPostgreSQL summary:")
        print(f"  users: {users}")
        print(f"  campaign_contacts: {contacts}")
        print(f"  portals: {portals}")
        print(f"  job_applications: {session.query(JobApplication).count()}")

    print("\nDone. Login with:")
    print("  admin@marketingmind.ai / Admin@123")
    print("  user@marketingmind.ai / User@123")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
