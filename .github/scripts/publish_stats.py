#!/usr/bin/env python3
"""Кладёт свежий съём на актуальный main и пушит его без force.

Повтор старого запуска чекаутит тот SHA, на котором он когда-то стартовал.
Обычный push с этого коммита GitHub отклоняет как non-fast-forward, и цифры
пропадают. Слепой rebase конфликтует в history.json и легко стирает дни,
которые уже записаны в main.

Здесь коммит всегда строится поверх текущего origin/main. Из съёма на него
переносятся только те значения, которые реально изменились относительно
history.json, прочитанного перед collect. Остальные дни остаются как в main.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
BASE_SNAPSHOT = Path(os.environ.get("REFRESH_BASE_HISTORY", "/tmp/refresh-base/history.json"))
HISTORY_PATH = Path("data/history.json")
STATS_PATH = Path("stats.json")
COMMIT_MESSAGE = "Обновить цифры подписчиков"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
MAX_PUSH_ATTEMPTS = int(os.environ.get("PUBLISH_MAX_ATTEMPTS", "5"))
RETRY_SECONDS = int(os.environ.get("PUBLISH_RETRY_SECONDS", "2"))

_DELETE = object()


def git(args: list[str], *, input_bytes: bytes | None = None, check: bool = True, echo: bool = False) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, input=input_bytes, check=False, capture_output=True)
    if echo or result.returncode != 0:
        if result.stdout:
            sys.stdout.buffer.write(result.stdout)
        if result.stderr:
            sys.stderr.buffer.write(result.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
    return result


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} должен быть JSON-объектом")
    return payload


def dump_history(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def dump_stats(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def show_file(rev: str, path: str) -> bytes:
    result = git(["git", "show", f"{rev}:{path}"])
    return result.stdout


def changed_days(base: dict, fresh: dict) -> dict[str, dict]:
    """Значения дней, которые этот съём реально перезаписал."""
    base_days = base.get("days") if isinstance(base.get("days"), dict) else {}
    fresh_days = fresh.get("days") if isinstance(fresh.get("days"), dict) else {}
    updates: dict[str, dict] = {}
    for day, networks in fresh_days.items():
        if not isinstance(networks, dict):
            continue
        before = base_days.get(day)
        if not isinstance(before, dict):
            before = {}
        delta = {
            network: value
            for network, value in networks.items()
            if before.get(network) != value
        }
        if delta:
            updates[str(day)] = delta
    return updates


def changed_insights(base: dict, fresh: dict) -> dict:
    before = base.get("insights") if isinstance(base.get("insights"), dict) else {}
    after = fresh.get("insights") if isinstance(fresh.get("insights"), dict) else {}
    delta: dict = {}
    for key in sorted(set(before) | set(after), key=str):
        if before.get(key) != after.get(key):
            delta[key] = after[key] if key in after else _DELETE
    return delta


def apply_measurement(main: dict, day_updates: dict[str, dict], insight_delta: dict) -> dict:
    result = copy.deepcopy(main)
    days = result.get("days")
    if not isinstance(days, dict):
        days = {}
        result["days"] = days
    for day, delta in day_updates.items():
        slot = days.get(day)
        if not isinstance(slot, dict):
            slot = {}
            days[day] = slot
        slot.update(delta)
    if insight_delta:
        stored = result.get("insights")
        if not isinstance(stored, dict):
            stored = {}
        for key, value in insight_delta.items():
            if value is _DELETE:
                stored.pop(key, None)
            else:
                stored[key] = copy.deepcopy(value)
        if stored:
            result["insights"] = stored
        else:
            result.pop("insights", None)
    # День, которого не было на main, не должен прилипнуть в конец не по дате.
    result["days"] = {day: days[day] for day in sorted(days)}
    return result


def ensure_tz() -> None:
    # День в истории — календарь Екатеринбурга, как в шаге «Снять цифры».
    os.environ["TZ"] = "Asia/Yekaterinburg"
    if hasattr(time, "tzset"):
        time.tzset()


def render_stats(merged_history: dict, generated_at: object) -> dict:
    """Собирает stats.json той же функцией, что и обычный съём.

    Счётчики берутся из уже слитой истории, а не из файла со старого SHA:
    иначе на табло на один цикл вернулись бы вчерашние числа.
    """
    ensure_tz()
    sys.path.insert(0, str(Path.cwd()))
    import server

    saved_path = server.DATA_PATH
    saved_state = dict(server.STATE)
    saved_reach = dict(server.REACH)
    saved_meta = dict(server.META)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            path.write_bytes(dump_history(merged_history))
            server.DATA_PATH = path
            with server.LOCK:
                for network in server.NETWORKS:
                    server.STATE[network] = None
                    server.REACH[network] = None
                if isinstance(generated_at, str) and generated_at:
                    server.META["generated_at"] = generated_at
                else:
                    server.META["generated_at"] = None
            server.load_last_counts()
            saved = merged_history.get("insights")
            if isinstance(saved, dict):
                with server.LOCK:
                    for network, payload in saved.items():
                        if network not in server.REACH:
                            continue
                        server.REACH[network] = server.clean_insight(payload)
            return server.snapshot()
    finally:
        server.DATA_PATH = saved_path
        with server.LOCK:
            server.STATE.clear()
            server.STATE.update(saved_state)
            server.REACH.clear()
            server.REACH.update(saved_reach)
            server.META.clear()
            server.META.update(saved_meta)


def files_to_commit(base: dict, fresh_history: dict, fresh_history_bytes: bytes, fresh_stats: dict, fresh_stats_bytes: bytes) -> tuple[bytes, bytes]:
    main_bytes = show_file("origin/main", "data/history.json")
    main_history = json.loads(main_bytes.decode("utf-8"))
    if not isinstance(main_history, dict):
        raise SystemExit("data/history.json на main должен быть объектом")
    if main_history == base:
        # Съём шёл с той же истории, что сейчас на main. Байты collect.py
        # уже правильные, пересобирать их не нужно.
        return fresh_history_bytes, fresh_stats_bytes

    day_updates = changed_days(base, fresh_history)
    insight_delta = changed_insights(base, fresh_history)
    if day_updates:
        print("Переношу на main дни: " + ", ".join(sorted(day_updates)), flush=True)
    merged = apply_measurement(main_history, day_updates, insight_delta)
    stats = render_stats(merged, fresh_stats.get("generated_at"))
    return dump_history(merged), dump_stats(stats)


def commit_on_main(history_bytes: bytes, stats_bytes: bytes) -> str | None:
    """Коммит поверх origin/main, не двигая остальные файлы рабочего дерева.

    Индекс отдельный: иначе коммит со старого SHA утащил бы в main весь
    устаревший снимок репозитория.
    """
    tip = git(["git", "rev-parse", "origin/main"]).stdout.decode().strip()
    index_dir = tempfile.mkdtemp(prefix="refresh-index-")
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = str(Path(index_dir) / "index")

    def run_index(args: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(args, input=input_bytes, env=env, check=False, capture_output=True)
        if result.returncode != 0:
            if result.stdout:
                sys.stdout.buffer.write(result.stdout)
            if result.stderr:
                sys.stderr.buffer.write(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
        return result

    try:
        run_index(["git", "read-tree", tip])
        for path, payload in (("data/history.json", history_bytes), ("stats.json", stats_bytes)):
            blob = run_index(["git", "hash-object", "-w", "--stdin"], input_bytes=payload).stdout.decode().strip()
            run_index(["git", "update-index", "--add", "--cacheinfo", "100644", blob, path])
        tree = run_index(["git", "write-tree"]).stdout.decode().strip()
    finally:
        shutil.rmtree(index_dir, ignore_errors=True)

    tip_tree = git(["git", "rev-parse", f"{tip}^{{tree}}"]).stdout.decode().strip()
    if tree == tip_tree:
        return None

    commit_env = os.environ.copy()
    commit_env.update(
        {
            "GIT_AUTHOR_NAME": BOT_NAME,
            "GIT_AUTHOR_EMAIL": BOT_EMAIL,
            "GIT_COMMITTER_NAME": BOT_NAME,
            "GIT_COMMITTER_EMAIL": BOT_EMAIL,
        }
    )
    commit = subprocess.run(
        ["git", "commit-tree", tree, "-p", tip, "-m", COMMIT_MESSAGE],
        env=commit_env,
        check=False,
        capture_output=True,
    )
    if commit.returncode != 0:
        if commit.stderr:
            sys.stderr.buffer.write(commit.stderr)
        raise subprocess.CalledProcessError(commit.returncode, commit.args, commit.stdout, commit.stderr)
    return commit.stdout.decode().strip()


def push_commit(sha: str) -> bool:
    result = git(["git", "push", "origin", f"{sha}:main"], check=False, echo=True)
    if result.returncode == 0:
        return True
    # Ответ мог потеряться уже после того, как main принял коммит.
    remote = git(["git", "ls-remote", "origin", "refs/heads/main"], check=False)
    if remote.returncode == 0 and remote.stdout.decode().startswith(sha):
        print("main уже указывает на этот коммит", flush=True)
        return True
    return False


def write_worktree(history_bytes: bytes, stats_bytes: bytes) -> None:
    HISTORY_PATH.write_bytes(history_bytes)
    STATS_PATH.write_bytes(stats_bytes)


def sync_head(sha: str) -> None:
    # Смешанный reset не трогает файлы. Данные съёма уже лежат в рабочем
    # дереве, а следующий collect прочитает именно их.
    git(["git", "reset", "-q", "--mixed", sha], check=False, echo=True)


def configure_git() -> None:
    git(["git", "config", "user.name", BOT_NAME])
    git(["git", "config", "user.email", BOT_EMAIL])


def load_inputs() -> tuple[dict, dict, bytes, dict, bytes]:
    if BASE_SNAPSHOT.is_file():
        base_bytes = BASE_SNAPSHOT.read_bytes()
    else:
        base_bytes = show_file("HEAD", "data/history.json")
    base = json.loads(base_bytes.decode("utf-8"))
    fresh_history_bytes = HISTORY_PATH.read_bytes()
    fresh_stats_bytes = STATS_PATH.read_bytes()
    fresh_history = load_json(HISTORY_PATH)
    fresh_stats = load_json(STATS_PATH)
    if not isinstance(base, dict):
        raise SystemExit("Базовая история должна быть объектом")
    return base, fresh_history, fresh_history_bytes, fresh_stats, fresh_stats_bytes


def main() -> int:
    os.chdir(ROOT)
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    ensure_tz()
    configure_git()
    base, fresh_history, fresh_history_bytes, fresh_stats, fresh_stats_bytes = load_inputs()

    for attempt in range(1, MAX_PUSH_ATTEMPTS + 1):
        try:
            # depth=1 — как checkout в Actions. «+» только у remote-tracking:
            # сам push ниже без --force и без «+».
            git(
                ["git", "fetch", "--depth=1", "origin", "+refs/heads/main:refs/remotes/origin/main"],
                echo=True,
            )
            history_bytes, stats_bytes = files_to_commit(
                base, fresh_history, fresh_history_bytes, fresh_stats, fresh_stats_bytes
            )
            write_worktree(history_bytes, stats_bytes)
            sha = commit_on_main(history_bytes, stats_bytes)
        except subprocess.CalledProcessError:
            print(f"Не удалось подготовить коммит (попытка {attempt}/{MAX_PUSH_ATTEMPTS})", flush=True)
            sha = ""
            if attempt == MAX_PUSH_ATTEMPTS:
                return 1
            if RETRY_SECONDS:
                time.sleep(attempt * RETRY_SECONDS)
            continue

        if sha is None:
            print("Цифры не изменились", flush=True)
            return 0
        if push_commit(sha):
            sync_head(sha)
            print("Цифры сохранены", flush=True)
            return 0
        if attempt == MAX_PUSH_ATTEMPTS:
            print("Не удалось запушить цифры", flush=True)
            return 1
        print(f"Пуш не прошёл, повтор ({attempt + 1}/{MAX_PUSH_ATTEMPTS})", flush=True)
        if RETRY_SECONDS:
            time.sleep(attempt * RETRY_SECONDS)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
