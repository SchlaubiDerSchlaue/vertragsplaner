#!/usr/bin/env python3
"""Minimaler Beispiel-Client fuer die Vertragsplaner-JSON-API.

Nutzung:
    export VERTRAGSPLANER_BASE_URL="http://127.0.0.1:5000/api/v1"
    export VERTRAGSPLANER_API_TOKEN="dein-token"
    python examples/python-api.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("VERTRAGSPLANER_BASE_URL", "http://127.0.0.1:5000/api/v1").rstrip("/")
TOKEN = os.environ.get("VERTRAGSPLANER_API_TOKEN")


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not TOKEN:
        raise SystemExit("Bitte VERTRAGSPLANER_API_TOKEN setzen.")

    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"

    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    health = api_get("/health")
    print(f"API: {health.get('api')} / Status: {health.get('status')}")

    contracts = api_get("/contracts", {"status": "active", "limit": 5})
    print("\nAktive Vertraege:")
    for contract in contracts.get("data", []):
        partner = contract.get("partner") or {}
        print(f"- #{contract['id']} {contract.get('title')} ({contract.get('contract_type')}, {partner.get('name')})")

    planning = api_get(
        "/planning",
        {
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "include_revenue": "true",
            "include_cost": "true",
            "include_forecast": "false",
        },
    )

    totals_by_month: dict[str, Decimal] = defaultdict(Decimal)
    for line in planning.get("data", []):
        month = str(line.get("month") or line.get("period") or line.get("date") or "unbekannt")[:7]
        totals_by_month[month] += Decimal(str(line.get("amount", "0")))

    print("\nPlanungssumme nach Monat:")
    for month, total in sorted(totals_by_month.items()):
        print(f"- {month}: {total:.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
