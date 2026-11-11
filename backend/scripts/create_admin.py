"""Interactively create the first administrator account."""

import getpass
import re

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.db import models
from app.core.security import get_password_hash
from app.db.base import SessionLocal, engine


def main() -> None:
    if not inspect(engine).has_table("users"):
        raise SystemExit("Database tables are missing. Run: python -m scripts.init_db")

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.role == models.UserRole.admin).first()
        if existing:
            raise SystemExit(f"An administrator already exists ({existing.username}); no changes made.")

        username = input("Admin username (3-32 letters, numbers, underscores): ").strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username):
            raise SystemExit("Invalid username. Use 3-32 letters, numbers, or underscores.")
        if db.query(models.User).filter(models.User.username == username).first():
            raise SystemExit("That username already exists; choose another username.")

        password = getpass.getpass("Admin password (6-72 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if not 6 <= len(password) <= 72:
            raise SystemExit("Password must contain 6-72 characters.")
        if password != confirmation:
            raise SystemExit("Passwords do not match.")

        user = models.User(
            username=username,
            password_hash=get_password_hash(password),
            role=models.UserRole.admin,
            receive_notifications=False,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise SystemExit("That username already exists; no administrator was created.")
        print(f"Administrator '{username}' created. Keep the password in a secure password manager.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
