"""Create the application tables in the configured database."""

from app.db.base import Base, engine
from app.db import models  # noqa: F401 - registers model metadata


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready.")


if __name__ == "__main__":
    main()
