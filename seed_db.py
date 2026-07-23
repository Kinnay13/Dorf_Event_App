from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from database import SessionLocal
from models import Event, Location, User


BASE_DIR = Path(__file__).resolve().parent
EVENTS_FILE = BASE_DIR / "data" / "events.json"


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main() -> None:
    with EVENTS_FILE.open("r", encoding="utf-8") as file:
        event_data = json.load(file)

    with SessionLocal() as session:
        if session.query(Event).count() > 0:
            print("Seed wurde uebersprungen, weil bereits Events vorhanden sind.")
            return

        user = User(
            name="Demo Veranstalter",
            email="demo@example.com",
            password_hash="demo-password-hash",
            role="organizer",
        )
        session.add(user)
        session.flush()

        locations_by_name: dict[str, Location] = {}

        for item in event_data:
            location_name = item["location"]
            location = locations_by_name.get(location_name)

            if location is None:
                location = Location(
                    name=location_name,
                    address=item.get("address"),
                    postal_code=None,
                    city="Esens",
                    latitude=item.get("lat"),
                    longitude=item.get("lng"),
                )
                session.add(location)
                session.flush()
                locations_by_name[location_name] = location

            event = Event(
                user_id=user.id,
                location_id=location.id,
                title=item["title"],
                description=item.get("description"),
                category=item["category"],
                status="published",
                interested_count=item.get("interested_count", 0),
                start_time=parse_datetime(item["start_time"]),
                end_time=None,
            )
            session.add(event)

        session.commit()
        print(f"{len(event_data)} Demo-Events wurden gespeichert.")


if __name__ == "__main__":
    main()
