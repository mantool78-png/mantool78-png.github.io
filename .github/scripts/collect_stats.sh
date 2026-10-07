#!/usr/bin/env bash
# Снимает цифры и запоминает history.json, с которого начался съём.
# publish_stats.py переносит на main только то, что изменилось относительно
# этого снимка, поэтому повтор старого запуска не затирает уже записанные дни.
set -euo pipefail

cd "$(dirname "$0")/../.."

base="${REFRESH_BASE_HISTORY:-/tmp/refresh-base/history.json}"
mkdir -p "$(dirname "$base")"
cp data/history.json "$base"
exec python collect.py
