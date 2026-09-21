"""Локальное табло подписчиков «Слово Акробата»."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "history.json"
HOST = "127.0.0.1"
PORT = 4174
REFRESH_SECONDS = 180

NETWORKS = ("telegram", "youtube", "vk", "tiktok", "dzen", "max")
LOCK = threading.Lock()
STATE = {network: None for network in NETWORKS}


def load_history() -> dict:
    if not DATA_PATH.exists():
        return {"days": {}}
    try:
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"days": {}}
    payload.setdefault("days", {})
    return payload


def save_history(history: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept": "text/html,application/json,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def parse_compact_number(text: str) -> int | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(тыс|млн|млрд)?", text, re.I)
    if not match:
        return None
    number = float(match.group(1).replace(",", "."))
    unit = (match.group(2) or "").lower()
    multiplier = {"": 1, "тыс": 1_000, "млн": 1_000_000, "млрд": 1_000_000_000}
    return int(number * multiplier[unit])


def fetch_telegram() -> int | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        try:
            raw = fetch_text(
                "https://api.telegram.org/bot"
                + token
                + "/getChatMemberCount?chat_id=@acrotim"
            )
            payload = json.loads(raw)
            result = payload.get("result")
            if payload.get("ok") and isinstance(result, int):
                return result
        except Exception:
            return None
        return None
    html = fetch_text("https://t.me/acrotim")
    match = re.search(r"tgme_page_extra[^>]*>(.*?)</div>", html, re.S)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def fetch_youtube() -> int | None:
    html = fetch_text("https://www.youtube.com/channel/UCBG6Fg2flgYnhQGiBZkyK7Q")
    match = re.search(r'"content":"([^"]*подписчик[^"]*)"', html)
    if not match:
        return None
    return parse_compact_number(match.group(1))


def fetch_vk() -> int | None:
    html = fetch_text("https://vk.ru/club225676956")
    match = re.search(r'"members_count":(\d+)', html)
    return int(match.group(1)) if match else None


def fetch_tiktok() -> int | None:
    html = fetch_text("https://www.tiktok.com/@slovoacrobata")
    match = re.search(r'"followerCount":(\d+)', html)
    return int(match.group(1)) if match else None


def fetch_dzen() -> int | None:
    raw = fetch_text("https://dzen.ru/api/v3/launcher/export?channel_name=gymacro.ru")
    match = re.search(
        r'"subscribers":(\d+),"is_verified":(?:true|false),"url":"gymacro\.ru"',
        raw,
    )
    return int(match.group(1)) if match else None


def fetch_max() -> int | None:
    raw = fetch_text("https://max.ru/se14052651_biz/__data.json")
    payload = json.loads(raw)
    for node in payload.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        data = node.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, dict) and "participantsCount" in item:
                value = data[item["participantsCount"]]
                if isinstance(value, int):
                    return value
    return None


def remember(counts: dict[str, int | None]) -> None:
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    day = history["days"].setdefault(today, {})
    for network, count in counts.items():
        if count is not None:
            day[network] = count
    days = sorted(history["days"])
    for old in days[:-14]:
        history["days"].pop(old, None)
    save_history(history)


def snapshot() -> dict:
    history = load_history()
    days = sorted(history["days"])
    today = datetime.now().strftime("%Y-%m-%d")
    previous_days = [day for day in days if day < today]
    yesterday = previous_days[-1] if previous_days else None
    week = days[-7:]

    networks = []
    for network in NETWORKS:
        count = STATE.get(network)
        series = []
        for day in week:
            value = history["days"].get(day, {}).get(network)
            if value is not None:
                series.append(value)
        delta = None
        if count is not None and yesterday is not None:
            previous = history["days"].get(yesterday, {}).get(network)
            if previous is not None:
                delta = count - previous
        networks.append(
            {
                "id": network,
                "count": count,
                "delta": delta,
                "series": series or ([count] if count is not None else []),
            }
        )
    return {"networks": networks}


FETCHERS = {
    "telegram": fetch_telegram,
    "youtube": fetch_youtube,
    "vk": fetch_vk,
    "tiktok": fetch_tiktok,
    "dzen": fetch_dzen,
    "max": fetch_max,
}


def refresh() -> None:
    counts: dict[str, int | None] = {}

    def run(network: str, fetcher) -> None:
        try:
            value = fetcher()
        except Exception:
            value = None
        if value is None:
            value = STATE.get(network)
        counts[network] = value

    workers = [
        threading.Thread(target=run, args=(network, fetcher), daemon=True)
        for network, fetcher in FETCHERS.items()
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=45)
    for network in NETWORKS:
        counts.setdefault(network, STATE.get(network))
    with LOCK:
        STATE.update(counts)
        remember(counts)


def refresh_loop() -> None:
    while True:
        time.sleep(REFRESH_SECONDS)
        try:
            refresh()
        except Exception:
            continue


PUBLIC_FILES = {
    "/": ROOT / "index.html",
    "/index.html": ROOT / "index.html",
    "/styles.css": ROOT / "styles.css",
    "/app.js": ROOT / "app.js",
}
FILE_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/api/stats", "/stats.json"):
            body = json.dumps(snapshot(), ensure_ascii=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body, "no-store")
            return
        file_path = PUBLIC_FILES.get(path)
        if file_path is None or not file_path.is_file():
            self._send(404, "text/plain; charset=utf-8", b"Not found", "no-store")
            return
        self._send(200, FILE_TYPES[file_path.suffix], file_path.read_bytes(), "no-cache")

    def _send(self, status: int, content_type: str, body: bytes, cache: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def load_last_counts() -> None:
    history = load_history()
    latest: dict[str, int] = {}
    for day in sorted(history["days"]):
        for network, value in history["days"][day].items():
            if isinstance(value, int):
                latest[network] = value
    with LOCK:
        STATE.update(latest)


def export_stats() -> None:
    load_last_counts()
    refresh()
    payload = snapshot()
    (ROOT / "stats.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    history = load_history()
    today = history["days"].get(datetime.now().strftime("%Y-%m-%d"), {})
    with LOCK:
        for network in NETWORKS:
            if network in today:
                STATE[network] = today[network]
    threading.Thread(target=refresh, daemon=True).start()
    threading.Thread(target=refresh_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
