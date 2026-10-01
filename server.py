"""Локальное табло подписчиков «Слово Акробата»."""

from __future__ import annotations

import html
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
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
REACH = {network: None for network in NETWORKS}
META = {"generated_at": None}
TELEGRAM_CHANNEL = "acrotim"
VK_OWNER_ID = -225676956
POST_WINDOW = timedelta(days=7)


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


def remember(counts: dict[str, int | None], insights: dict[str, dict | None] | None = None) -> None:
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    day = history["days"].setdefault(today, {})
    for network, count in counts.items():
        if count is not None:
            day[network] = count
    if insights is not None:
        stored = history.get("insights")
        if not isinstance(stored, dict):
            stored = {}
        vk_token = os.environ.get("VK_ACCESS_TOKEN", "").strip()
        if not vk_token:
            stored.pop("vk", None)
        for network, payload in insights.items():
            if network == "vk" and not vk_token:
                continue
            if payload:
                stored[network] = payload
            else:
                stored.pop(network, None)
        if stored:
            history["insights"] = stored
        else:
            history.pop("insights", None)
    save_history(history)


def parse_views(text: str) -> int | None:
    cleaned = text.replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([KkMm]|тыс\.?|млн\.?)?", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "").lower().rstrip(".")
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "тыс": 1_000, "млн": 1_000_000}
    if unit not in multiplier:
        return None
    return int(round(number * multiplier[unit]))


def clean_title(text: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = html.unescape(plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) > 140:
        plain = plain[:139].rstrip() + "…"
    return plain or "Пост"


def safe_post_url(url: object) -> str | None:
    if not isinstance(url, str):
        return None
    if url.startswith("https://t.me/") or url.startswith("https://vk.ru/") or url.startswith("https://vk.com/"):
        return url
    return None


def clean_insight(payload: object) -> dict | None:
    if not isinstance(payload, dict):
        return None
    cleaned: dict = {}
    reach = payload.get("reach")
    if isinstance(reach, int) and reach >= 0:
        cleaned["reach"] = reach
    best = payload.get("best_post")
    url = safe_post_url(best.get("url")) if isinstance(best, dict) else None
    views = best.get("views") if isinstance(best, dict) else None
    if url and isinstance(views, int) and views >= 0:
        title = best.get("title") if isinstance(best.get("title"), str) else ""
        date = best.get("date") if isinstance(best.get("date"), str) else ""
        cleaned["best_post"] = {
            "url": url,
            "views": views,
            "title": title or "Пост",
            "date": date,
        }
    return cleaned or None


def parse_telegram_posts(page: str) -> tuple[list[dict], list[int]]:
    ids = [int(item) for item in re.findall(r'data-post="[A-Za-z0-9_]+/(\d+)"', page)]
    posts = []
    for match in re.finditer(r'data-post="([A-Za-z0-9_]+)/(\d+)"', page):
        channel, post_id = match.group(1), int(match.group(2))
        body = page[match.end(): match.end() + 30000]
        boundary = body.find('data-post="')
        if boundary != -1:
            body = body[:boundary]
        views_match = re.search(r'tgme_widget_message_views">([^<]+)', body)
        date_match = re.search(r'datetime="([^"]+)"', body)
        if not views_match or not date_match:
            continue
        views = parse_views(views_match.group(1))
        if views is None:
            continue
        try:
            published = datetime.fromisoformat(date_match.group(1))
        except ValueError:
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        text_match = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', body, re.S)
        href_match = re.search(r'href="(https://t\.me/[^"]+/' + str(post_id) + ')"', body)
        posts.append(
            {
                "id": post_id,
                "url": href_match.group(1) if href_match else f"https://t.me/{channel}/{post_id}",
                "views": views,
                "published": published,
                "title": clean_title(text_match.group(1)) if text_match else "Пост",
            }
        )
    return posts, ids


def fetch_telegram_posts() -> list[dict]:
    by_id: dict[int, dict] = {}
    before: int | None = None
    cutoff = datetime.now(timezone.utc) - POST_WINDOW - timedelta(days=1)
    for _ in range(4):
        url = f"https://t.me/s/{TELEGRAM_CHANNEL}"
        if before is not None:
            url += f"?before={before}"
        page = fetch_text(url)
        posts, ids = parse_telegram_posts(page)
        if not ids:
            break
        for post in posts:
            by_id.setdefault(post["id"], post)
        oldest = min(ids)
        if before is not None and oldest >= before:
            break
        oldest_post = by_id.get(oldest)
        before = oldest
        if oldest_post and oldest_post["published"] <= cutoff:
            break
    return list(by_id.values())


def fetch_vk_posts() -> list[dict] | None:
    token = os.environ.get("VK_ACCESS_TOKEN", "").strip()
    if not token:
        return None
    posts: list[dict] = []
    offset = 0
    cutoff = datetime.now(timezone.utc) - POST_WINDOW - timedelta(days=1)
    for _ in range(3):
        query = urllib.parse.urlencode(
            {
                "owner_id": str(VK_OWNER_ID),
                "count": "100",
                "offset": str(offset),
                "filter": "owner",
                "v": "5.199",
                "access_token": token,
            }
        )
        try:
            raw = fetch_text("https://api.vk.com/method/wall.get?" + query)
        except Exception:
            raise RuntimeError("VK wall.get недоступен") from None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("VK wall.get вернул не JSON") from exc
        if not isinstance(payload, dict) or payload.get("error"):
            raise RuntimeError("VK wall.get отклонил запрос")
        items = (payload.get("response") or {}).get("items") or []
        if not isinstance(items, list) or not items:
            break
        oldest: datetime | None = None
        for item in items:
            if not isinstance(item, dict):
                continue
            views = item.get("views") if isinstance(item.get("views"), dict) else {}
            count = views.get("count")
            post_id = item.get("id")
            published_at = item.get("date")
            if not isinstance(count, int) or not isinstance(post_id, int) or not isinstance(published_at, int):
                continue
            published = datetime.fromtimestamp(published_at, tz=timezone.utc)
            oldest = published if oldest is None or published < oldest else oldest
            text = item.get("text") if isinstance(item.get("text"), str) else ""
            posts.append(
                {
                    "id": post_id,
                    "url": f"https://vk.ru/wall{VK_OWNER_ID}_{post_id}",
                    "views": count,
                    "published": published,
                    "title": clean_title(text),
                }
            )
        offset += len(items)
        if oldest is not None and oldest <= cutoff:
            break
        if len(items) < 100:
            break
    return posts


def summarize_posts(posts: list[dict] | None) -> dict | None:
    if not posts:
        return None
    now = datetime.now(timezone.utc)
    cutoff = now - POST_WINDOW
    recent = []
    for post in posts:
        published = post.get("published")
        views = post.get("views")
        url = safe_post_url(post.get("url"))
        if not isinstance(published, datetime) or not isinstance(views, int) or not url:
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= cutoff:
            recent.append({**post, "url": url, "published": published})
    if not recent:
        return None
    reach = int(round(sum(post["views"] for post in recent) / len(recent)))
    best = max(recent, key=lambda post: (post["views"], post["published"]))
    return clean_insight(
        {
            "reach": reach,
            "best_post": {
                "url": best["url"],
                "views": best["views"],
                "title": best.get("title") or "Пост",
                "date": best["published"].astimezone(timezone.utc).date().isoformat(),
            },
        }
    )


def fetch_telegram_insight() -> dict | None:
    return summarize_posts(fetch_telegram_posts())


def fetch_vk_insight() -> dict | None:
    return summarize_posts(fetch_vk_posts())


def load_saved_insights() -> None:
    history = load_history()
    saved = history.get("insights")
    if not isinstance(saved, dict):
        return
    vk_token = os.environ.get("VK_ACCESS_TOKEN", "").strip()
    with LOCK:
        for network, payload in saved.items():
            if network not in REACH or REACH.get(network) is not None:
                continue
            if network == "vk" and not vk_token:
                continue
            cleaned = clean_insight(payload)
            if cleaned:
                REACH[network] = cleaned


def snapshot() -> dict:
    history = load_history()
    days = sorted(day for day in history["days"] if isinstance(history["days"].get(day), dict))
    today = datetime.now().strftime("%Y-%m-%d")
    previous_days = [day for day in days if day < today]
    yesterday = previous_days[-1] if previous_days else None
    week = set(days[-7:])

    networks = []
    for network in NETWORKS:
        count = STATE.get(network)
        history_points = []
        for day in days:
            value = history["days"].get(day, {}).get(network)
            if isinstance(value, int):
                history_points.append({"date": day, "count": value})
        series = [point["count"] for point in history_points if point["date"] in week]
        if not series and isinstance(count, int):
            series = [count]
        if not history_points and isinstance(count, int):
            history_points = [{"date": today, "count": count}]
        delta = None
        if isinstance(count, int) and yesterday is not None:
            previous = history["days"].get(yesterday, {}).get(network)
            if isinstance(previous, int):
                delta = count - previous
        item = {
            "id": network,
            "count": count,
            "delta": delta,
            "series": series,
            "history": history_points,
        }
        insight = clean_insight(REACH.get(network))
        if insight and "reach" in insight:
            item["reach"] = insight["reach"]
        if insight and insight.get("best_post"):
            item["best_post"] = insight["best_post"]
        networks.append(item)
    payload = {"networks": networks}
    generated_at = META.get("generated_at")
    if isinstance(generated_at, str) and generated_at:
        payload["generated_at"] = generated_at
    return payload


FETCHERS = {
    "telegram": fetch_telegram,
    "youtube": fetch_youtube,
    "vk": fetch_vk,
    "tiktok": fetch_tiktok,
    "dzen": fetch_dzen,
    "max": fetch_max,
}


INSIGHT_FETCHERS = {
    "telegram": fetch_telegram_insight,
    "vk": fetch_vk_insight,
}
_FAILED = object()


def refresh() -> None:
    counts: dict[str, int | None] = {}
    insights: dict[str, object] = {}

    def run(network: str, fetcher) -> None:
        try:
            value = fetcher()
        except Exception:
            value = None
        if value is None:
            value = STATE.get(network)
        counts[network] = value

    def run_insight(network: str, fetcher) -> None:
        try:
            insights[network] = fetcher()
        except Exception:
            insights[network] = _FAILED

    workers = [
        threading.Thread(target=run, args=(network, fetcher), daemon=True)
        for network, fetcher in FETCHERS.items()
    ]
    workers += [
        threading.Thread(target=run_insight, args=(network, fetcher), daemon=True)
        for network, fetcher in INSIGHT_FETCHERS.items()
    ]
    for worker in workers:
        worker.start()
    deadline = time.time() + 55
    for worker in workers:
        remaining = deadline - time.time()
        if remaining > 0:
            worker.join(timeout=remaining)
    for network in NETWORKS:
        counts.setdefault(network, STATE.get(network))
    insight_updates: dict[str, dict | None] = {}
    with LOCK:
        STATE.update(counts)
        for network in INSIGHT_FETCHERS:
            if network not in insights or insights[network] is _FAILED:
                continue
            payload = insights[network]
            cleaned = clean_insight(payload) if payload else None
            REACH[network] = cleaned
            insight_updates[network] = cleaned
        META["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        remember(counts, insight_updates)


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
    "/avatar.jpg": ROOT / "avatar.jpg",
    "/cat-avatar.png": ROOT / "cat-avatar.png",
    "/favicon.ico": ROOT / "favicon.ico",
    "/favicon-32.png": ROOT / "favicon-32.png",
    "/apple-touch-icon.png": ROOT / "apple-touch-icon.png",
    "/og.png": ROOT / "og.png",
}
FILE_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".ico": "image/x-icon",
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
    load_saved_insights()
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
            if isinstance(today, dict) and network in today:
                STATE[network] = today[network]
    load_saved_insights()
    threading.Thread(target=refresh, daemon=True).start()
    threading.Thread(target=refresh_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
