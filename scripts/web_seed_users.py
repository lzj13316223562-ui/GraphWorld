#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.security import hash_password, verify_password
from backend.app.db.models import Run, User
from backend.app.db.session import SessionLocal


@dataclass(frozen=True)
class SeedUser:
    user_id: str
    username: str
    display_name: str
    role: str
    password: str


def default_users(count: int) -> list[SeedUser]:
    users = [
        SeedUser(
            user_id="admin",
            username="admin",
            display_name="Administrator",
            role="admin",
            password="admin123",
        )
    ]
    for index in range(1, count + 1):
        users.append(
            SeedUser(
                user_id=f"user{index:02d}",
                username=f"user{index:02d}",
                display_name=f"User {index:02d}",
                role="user",
                password=f"graphworld{index:02d}",
            )
        )
    return users


def seed_user(user: SeedUser, *, reset_passwords: bool) -> str:
    with SessionLocal() as db:
        existing = db.get(User, user.user_id)
        if existing is None:
            db.add(
                User(
                    id=user.user_id,
                    username=user.username,
                    display_name=user.display_name,
                    role=user.role,
                    password_hash=hash_password(user.password),
                    is_active=True,
                )
            )
            db.commit()
            return f"created {user.username} ({user.role}) password={user.password}"
        existing.username = user.username
        existing.display_name = user.display_name
        existing.role = user.role
        existing.is_active = True
        changed_password = False
        if reset_passwords or not verify_password(user.password, existing.password_hash):
            existing.password_hash = hash_password(user.password)
            changed_password = True
        db.commit()
        suffix = f" password={user.password}" if changed_password else ""
        return f"updated {user.username} ({user.role}){suffix}"


def assign_orphan_runs_to_admin() -> int:
    with SessionLocal() as db:
        runs = list(db.scalars(select(Run).where(Run.owner_user_id.is_(None))).all())
        for run in runs:
            run.owner_user_id = "admin"
        db.commit()
        return len(runs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed GraphWorld web users.")
    parser.add_argument("--users", type=int, default=20, help="Number of normal user accounts to create.")
    parser.add_argument("--reset-passwords", action="store_true", help="Reset seeded passwords to their defaults.")
    args = parser.parse_args()
    count = max(1, min(20, int(args.users)))
    for user in default_users(count):
        print(seed_user(user, reset_passwords=args.reset_passwords))
    orphan_count = assign_orphan_runs_to_admin()
    if orphan_count:
        print(f"assigned {orphan_count} existing runs to admin")


if __name__ == "__main__":
    main()
