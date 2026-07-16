# JSON-API

Die Anwendung stellt eine read-only JSON-API unter `/api/v1` bereit. Sie ist fuer lokale Skripte, interne Automatisierungen und KI-Agenten gedacht, die Vertrags-, Positions- und Planungsdaten auslesen sollen.

> Wichtig: Die API erlaubt aktuell keine Schreibzugriffe, Importe oder Loeschungen.

## Basis-URL

Lokal:

```text
http://127.0.0.1:5000/api/v1
```

Auf der aktuell bereitgestellten Testinstanz:

```text
http://212.227.101.34:5000/api/v1
```

## Authentifizierung

Jeder Request braucht einen API-Token als Bearer-Token:

```http
Authorization: Bearer <API_TOKEN>
```

API-Tokens werden in der Weboberflaeche unter `Admin -> API-Tokens` angelegt. Fuer die read-only API reicht die Rolle `read`; `write` und `admin` funktionieren ebenfalls, haben ueber die JSON-API aber keine zusaetzlichen Schreibrechte.

Empfehlung fuer Beispiele und Skripte:

```bash
export VERTRAGSPLANER_BASE_URL="http://127.0.0.1:5000/api/v1"
export VERTRAGSPLANER_API_TOKEN="dein-token"
```

## Antwortformat

Listen liefern ein Objekt mit `data` und `meta`:

```json
{
  "data": [],
  "meta": {
    "count": 0,
    "total": 0,
    "limit": 100,
    "offset": 0
  }
}
```

Einzeldetails liefern ebenfalls `data`:

```json
{
  "data": {
    "id": 1
  }
}
```

Fehler liefern `error`:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Bitte Authorization: Bearer <API_TOKEN> senden."
  }
}
```

## Pagination

Listen-Endpunkte unterstuetzen:

| Parameter | Standard | Maximum | Beschreibung |
| --- | ---: | ---: | --- |
| `limit` | `100` | `500` | Maximale Anzahl Eintraege |
| `offset` | `0` | - | Anzahl zu ueberspringender Eintraege |

Beispiel:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/contracts?limit=50&offset=0"
```

## Endpunkte

### Healthcheck

```http
GET /health
```

Beispielantwort:

```json
{
  "api": "v1",
  "status": "ok"
}
```

### Kunden

```http
GET /customers
```

Filter:

| Parameter | Beschreibung |
| --- | --- |
| `q` | Suche in Name, Kontaktname und E-Mail |
| `status` | Exakter Kundenstatus |
| `limit`, `offset` | Pagination |

Beispiel:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/customers?q=GmbH&status=active"
```

### Lieferanten

```http
GET /suppliers
```

Filter:

| Parameter | Beschreibung |
| --- | --- |
| `q` | Suche in Name, Kontaktname und E-Mail |
| `status` | Exakter Lieferantenstatus |
| `limit`, `offset` | Pagination |

### Vertraege

```http
GET /contracts
GET /contracts/<id>
```

Filter fuer die Liste:

| Parameter | Beschreibung |
| --- | --- |
| `q` | Suche in Vertragsnummer, Titel, Verantwortlichem, Vertrags-/Rechnungslink und Partnername |
| `status` | Exakter Vertragsstatus, z. B. `active` oder `forecast` |
| `contract_type` | `revenue` oder `cost` |
| `partner_type` | `customer` oder `supplier` |
| `limit`, `offset` | Pagination |

Beispiel aktive Erloesvertraege:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/contracts?status=active&contract_type=revenue&limit=50"
```

Beispiel Vertragsdetails inklusive Positionen und Versionen:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/contracts/1"
```

### Positionen

```http
GET /positions
```

Filter:

| Parameter | Beschreibung |
| --- | --- |
| `q` | Suche in Positionsname, Vertragstitel und Partnername |
| `status` | Exakter Positionsstatus |
| `position_type` | `revenue` oder `cost` |
| `contract_type` | Alias fuer `position_type` |
| `partner_type` | `customer` oder `supplier` |
| `limit`, `offset` | Pagination |

Beispiel Kostenpositionen:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/positions?position_type=cost"
```

### Planung

```http
GET /planning?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Pflichtparameter:

| Parameter | Beschreibung |
| --- | --- |
| `start_date` | Startdatum im Format `YYYY-MM-DD` |
| `end_date` | Enddatum im Format `YYYY-MM-DD` |

Optionale Parameter:

| Parameter | Standard | Beschreibung |
| --- | --- | --- |
| `include_revenue` | `true` | Erloespositionen einschliessen |
| `include_cost` | `false` | Kostenpositionen einschliessen |
| `include_forecast` | `false` | Forecast-Vertraege einschliessen |

Boolesche Werte koennen als `true`, `false`, `1`, `0`, `yes`, `on` oder `ja` uebergeben werden. Alles ausser den wahr-Werten wird als falsch behandelt.

Beispiel Jahresplanung fuer Erloese und Kosten ohne Forecast:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/planning?start_date=2026-01-01&end_date=2026-12-31&include_revenue=true&include_cost=true&include_forecast=false"
```

## Schnellstart mit jq

Alle aktiven Vertraege als Kurzliste:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/contracts?status=active&limit=500" \
| jq -r '.data[] | [.id, .contract_no, .title, .contract_type, .partner.name] | @tsv'
```

Planung nach Kostenstelle summieren:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/planning?start_date=2026-01-01&end_date=2026-12-31&include_revenue=true&include_cost=true" \
| jq -r '.data[] | [.cost_center_1, .amount] | @tsv' \
| awk -F '\t' '{sum[$1]+=$2} END {for (k in sum) print k, sum[k]}'
```

## Beispielskripte

Im Repository liegen lauffaehige Beispiele unter `examples/`:

- `examples/curl-api.sh` - ruft Healthcheck, Vertraege und Planung per curl ab
- `examples/python-api.py` - kleiner Python-Client mit Summierung der Planung nach Monat

Beide Beispiele lesen `VERTRAGSPLANER_BASE_URL` und `VERTRAGSPLANER_API_TOKEN` aus der Umgebung.

## Sicherheitshinweise

- API-Tokens wie Passwoerter behandeln und nicht commiten.
- Die aktuelle API ist fuer interne Nutzung gedacht. Fuer oeffentliche Bereitstellung sollte sie hinter HTTPS, Reverse Proxy, Rate-Limit und sauberem Secret-Management laufen.
- Bei direktem Flask-Development-Server im Internet koennen Scanner viele 404/400-Requests erzeugen; produktiv besser Gunicorn/systemd plus Reverse Proxy verwenden.
