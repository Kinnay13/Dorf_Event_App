from __future__ import annotations

import json
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Event

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
HOST = "127.0.0.1"
PORT = 8000


WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def load_events() -> list[dict]:
    with SessionLocal() as session:
        events = session.scalars(
            select(Event)
            .options(joinedload(Event.location), joinedload(Event.user))
            .order_by(Event.start_time)
        ).all()
        return [event_to_dict(event) for event in events]


def event_to_dict(event: Event) -> dict:
    location = event.location
    start_time = event.start_time

    return {
        "id": str(event.id),
        "title": event.title,
        "category": event.category,
        "location": location.name,
        "address": location.address or location.city,
        "lat": location.latitude,
        "lng": location.longitude,
        "start_time": start_time.isoformat(),
        "time_label": format_time_label(start_time),
        "timeframe": get_timeframe(start_time),
        "description": event.description or "",
        "organization": event.user.name,
        "verified": True,
        "interested_count": event.interested_count,
    }


def format_time_label(value: datetime) -> str:
    weekday = WEEKDAYS[value.weekday()]
    return f"{weekday}, {value:%d.%m.%Y, %H:%M}"


def get_timeframe(value: datetime) -> str:
    today = datetime.now(value.tzinfo).date()
    event_date = value.date()

    if event_date == today:
        return "today"

    if event_date.weekday() in {5, 6}:
        return "weekend"

    return "later"


def increment_interest(event_id: str) -> dict | None:
    try:
        numeric_event_id = int(event_id)
    except ValueError:
        return None

    with SessionLocal() as session:
        event = session.scalar(
            select(Event)
            .options(joinedload(Event.location), joinedload(Event.user))
            .where(Event.id == numeric_event_id)
        )

        if event is None:
            return None

        event.interested_count += 1
        session.commit()
        session.refresh(event)
        return event_to_dict(event)


class DorfEventHandler(SimpleHTTPRequestHandler):
    server_version = "DorfEventApp/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/events":
            self.send_json(self.filtered_events(parse_qs(parsed.query)))
            return

        if parsed.path.startswith("/api/events/"):
            event_id = parsed.path.removeprefix("/api/events/").strip("/")
            event = next((item for item in load_events() if item["id"] == event_id), None)
            if event is None:
                self.send_json({"error": "Event not found"}, status=404)
                return
            self.send_json(event)
            return

        if parsed.path in {"/", "/index.html"}:
            self.path = "/static/index.html"

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path.startswith("/api/events/") and parsed.path.endswith("/interest"):
            event_id = parsed.path.split("/")[3]
            event = increment_interest(event_id)

            if event is None:
                self.send_json({"error": "Event not found"}, status=404)
                return

            self.send_json(event)
            return

        self.send_json({"error": "Endpoint not found"}, status=404)

    def translate_path(self, path: str) -> str:
        parsed_path = urlparse(path).path
        if parsed_path.startswith("/static/"):
            relative_path = parsed_path.removeprefix("/static/")
            return str(STATIC_DIR / relative_path)
        return str(STATIC_DIR / "index.html")

    def filtered_events(self, query: dict[str, list[str]]) -> list[dict]:
        events = load_events()
        category = self.first_query_value(query, "category")
        timeframe = self.first_query_value(query, "timeframe")
        search = self.first_query_value(query, "search").lower()

        if category and category != "all":
            events = [event for event in events if event["category"] == category]

        if timeframe and timeframe != "all":
            events = [event for event in events if event["timeframe"] == timeframe]

        if search:
            events = [
                event
                for event in events
                if search in event["title"].lower()
                or search in event["location"].lower()
                or search in event["description"].lower()
            ]

        return events

    @staticmethod
    def first_query_value(query: dict[str, list[str]], key: str) -> str:
        return query.get(key, [""])[0].strip()

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), DorfEventHandler)
    print(f"Dorf Event App laeuft auf http://{HOST}:{PORT}")
    print("Zum Beenden Strg+C druecken.")
    server.serve_forever()


if __name__ == "__main__":
    main()
