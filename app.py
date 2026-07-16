from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_FILE = BASE_DIR / "data" / "events.json"
HOST = "127.0.0.1"
PORT = 8000


def load_events() -> list[dict]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_events(events: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(events, file, ensure_ascii=False, indent=2)
        file.write("\n")


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
            events = load_events()
            for event in events:
                if event["id"] == event_id:
                    event["interested_count"] += 1
                    save_events(events)
                    self.send_json(event)
                    return

            self.send_json({"error": "Event not found"}, status=404)
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
    DATA_FILE.parent.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), DorfEventHandler)
    print(f"Dorf Event App laeuft auf http://{HOST}:{PORT}")
    print("Zum Beenden Strg+C druecken.")
    server.serve_forever()


if __name__ == "__main__":
    main()

