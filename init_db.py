from __future__ import annotations

from sqlalchemy import text

from database import Base, engine
from models import Event, Location, User


def add_missing_columns() -> None:
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE events ADD COLUMN IF NOT EXISTS interested_count INTEGER NOT NULL DEFAULT 0")
        )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    add_missing_columns()
    print("Tabellen wurden erstellt oder waren bereits vorhanden.")


if __name__ == "__main__":
    main()
