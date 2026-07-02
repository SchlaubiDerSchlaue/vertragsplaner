#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${VERTRAGSPLANER_BASE_URL:-http://127.0.0.1:5000/api/v1}"
TOKEN="${VERTRAGSPLANER_API_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "Bitte VERTRAGSPLANER_API_TOKEN setzen." >&2
  echo "Beispiel: export VERTRAGSPLANER_API_TOKEN='dein-token'" >&2
  exit 1
fi

api_get() {
  local path="$1"
  curl -sS \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/json" \
    "${BASE_URL}${path}"
}

echo "== Healthcheck =="
api_get "/health"
echo

echo "== Erste 10 aktive Vertraege =="
api_get "/contracts?status=active&limit=10"
echo

echo "== Planung aktuelles Beispieljahr =="
api_get "/planning?start_date=2026-01-01&end_date=2026-12-31&include_revenue=true&include_cost=true&include_forecast=false"
echo
