#!/usr/bin/env bash
# Ждёт 15 минут и ставит следующий запуск «Обновить цифры».
# Короткий HTTP 500 не должен обрывать цепочку. Если GitHub так и не принял
# dispatch, этот же job продолжает снимать цифры и пробовать снова: слот
# concurrency занят, поэтому вторая параллельная цепочка не стартует.
set -euo pipefail

cd "$(dirname "$0")/../.."

WORKFLOW="${WORKFLOW_FILE:-refresh.yml}"
REF="${DISPATCH_REF:-main}"
INTERVAL="${REFRESH_INTERVAL_SECONDS:-900}"
MAX_ATTEMPTS="${DISPATCH_MAX_ATTEMPTS:-6}"
RECOVERY_ATTEMPTS="${RECOVERY_DISPATCH_ATTEMPTS:-3}"
RETRY_BASE="${DISPATCH_RETRY_BASE:-15}"
RETRY_CAP="${DISPATCH_RETRY_CAP:-120}"
LAND_CHECK_SECONDS="${LAND_CHECK_SECONDS:-5}"
# 10 циклов по 15 минут держат табло живым около трёх часов, если API
# лежит долго. Дольше нельзя: у job лимит 6 часов, и его надо оставить с запасом.
MAX_RECOVERY="${MAX_RECOVERY_CYCLES:-10}"
RUN_ID="${GITHUB_RUN_ID:-}"

repo_args=()
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
  repo_args=(--repo "$GITHUB_REPOSITORY")
fi

dispatch_once() {
  local errfile code=0
  errfile=$(mktemp)
  gh workflow run "$WORKFLOW" --ref "$REF" "${repo_args[@]}" 2>"$errfile" || code=$?
  if [ -s "$errfile" ]; then
    cat "$errfile" >&2
  fi
  if [ "$code" -eq 0 ]; then
    rm -f "$errfile"
    return 0
  fi
  # 4xx (кроме 408/409) повторами не лечится: неверное имя workflow, права, ref.
  if grep -Eq 'HTTP 40[0134]|HTTP 422' "$errfile"; then
    rm -f "$errfile"
    echo "workflow_dispatch отклонён без повтора (ошибка клиента)" >&2
    return 2
  fi
  rm -f "$errfile"
  return 1
}

# 500 иногда приходит уже после того, как запуск создан. Тогда второй
# dispatch только плодит очередь, которую concurrency тут же отменит.
landed_since() {
  local since="$1"
  local ids code=0
  ids=$(gh run list \
    --workflow "$WORKFLOW" \
    --event workflow_dispatch \
    --limit 20 \
    --json databaseId,createdAt,status \
    --jq "[.[] | select(.createdAt > \"$since\" and .status != \"cancelled\" and (.databaseId | tostring) != \"$RUN_ID\") | .databaseId] | length") || code=$?
  if [ "$code" -ne 0 ]; then
    echo "не удалось проверить очередь запусков" >&2
    return 1
  fi
  [ "${ids:-0}" -ge 1 ]
}

try_dispatch() {
  local max_attempts="$1"
  local attempt=1
  local delay="$RETRY_BASE"
  local since code
  since=$(date -u -d '30 seconds ago' +%Y-%m-%dT%H:%M:%SZ)

  while true; do
    code=0
    dispatch_once || code=$?
    if [ "$code" -eq 0 ]; then
      echo "Следующий запуск поставлен в очередь"
      return 0
    fi
    if [ "$code" -eq 2 ]; then
      return 2
    fi

    echo "workflow_dispatch не удался (попытка ${attempt}/${max_attempts})"
    sleep "$LAND_CHECK_SECONDS"
    if landed_since "$since"; then
      echo "Запуск уже есть в очереди, повторно не ставим"
      return 0
    fi
    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "Не удалось поставить следующий запуск после ${max_attempts} попыток"
      return 1
    fi
    echo "Повтор через ${delay} с"
    sleep "$delay"
    attempt=$((attempt + 1))
    if [ "$delay" -lt "$RETRY_CAP" ]; then
      delay=$((delay * 2))
      if [ "$delay" -gt "$RETRY_CAP" ]; then
        delay="$RETRY_CAP"
      fi
    fi
  done
}

echo "Жду ${INTERVAL} с до следующего съёма"
sleep "$INTERVAL"

code=0
try_dispatch "$MAX_ATTEMPTS" || code=$?
if [ "$code" -eq 0 ]; then
  exit 0
fi
if [ "$code" -eq 2 ]; then
  exit 1
fi

cycle=1
while [ "$cycle" -le "$MAX_RECOVERY" ]; do
  echo "API не принял запуск. Снимаю цифры в этом же запуске (${cycle}/${MAX_RECOVERY}), чтобы цепочка не оборвалась"
  if bash .github/scripts/collect_stats.sh; then
    python .github/scripts/publish_stats.py || echo "Сохранить цифры не удалось, пробую dispatch ещё раз"
  else
    echo "Съём не удался, пробую dispatch ещё раз"
  fi
  echo "Жду ${INTERVAL} с и снова передаю цепочку"
  sleep "$INTERVAL"
  code=0
  try_dispatch "$RECOVERY_ATTEMPTS" || code=$?
  if [ "$code" -eq 0 ]; then
    exit 0
  fi
  if [ "$code" -eq 2 ]; then
    exit 1
  fi
  cycle=$((cycle + 1))
done

echo "Цепочка оборвалась: workflow_dispatch так и не создался"
exit 1
