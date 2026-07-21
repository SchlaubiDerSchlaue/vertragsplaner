# JSON-API

Die Anwendung stellt eine read-only JSON-API unter `/api/v1` bereit. Sie ist für lokale Skripte, interne Automatisierungen und KI-Agenten gedacht, die Vertrags-, Positions- und Planungsdaten auslesen sollen.

> Wichtig: Die API erlaubt aktuell keine Schreibzugriffe, Importe oder Löschungen.

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

API-Tokens werden in der Weboberfläche unter `Admin -> API-Tokens` angelegt. Für die read-only API reicht die Rolle `read`; `write` und `admin` funktionieren ebenfalls, haben über die JSON-API aber keine zusätzlichen Schreibrechte.

Empfehlung für Beispiele und Skripte:

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

Listen-Endpunkte unterstützen:

| Parameter | Standard | Maximum | Beschreibung |
| --- | ---: | ---: | --- |
| `limit` | `100` | `500` | Maximale Anzahl Einträge |
| `offset` | `0` | - | Anzahl zu überspringender Einträge |

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

### Verträge

```http
GET /contracts
GET /contracts/<id>
```

Filter für die Liste:

| Parameter | Beschreibung |
| --- | --- |
| `q` | Suche in Vertragsnummer, Titel, Verantwortlichem, Vertrags-/Rechnungslink und Partnername |
| `status` | Exakter Vertragsstatus, z. B. `active` oder `forecast` |
| `contract_type` | `revenue` oder `cost` |
| `partner_type` | `customer` oder `supplier` |
| `limit`, `offset` | Pagination |

Antwortfelder für Laufzeit und Kündigung:

| Feld | Beschreibung |
| --- | --- |
| `start_date` | Vertragsbeginn |
| `end_date` | Vertragsende bzw. letzter Leistungszeitraum |
| `cancellation_date` | Wirksames Kündigungsende, wenn bereits gekündigt |
| `cancellation_period_value` | Zahlenwert der Kündigungsfrist |
| `cancellation_period_unit` | Einheit der Kündigungsfrist: `days`, `weeks` oder `months` |
| `cancellation_period_label` | Lesbare Darstellung, z. B. `3 Monate` |
| `cancellation_deadline` | Berechneter Stichtag „Kündbar bis“ |
| `renewal_type` | `none`, `manual` oder `automatic` |

Beispiel aktive Erlösverträge:

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
| `contract_type` | Alias für `position_type` |
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
| `include_revenue` | `true` | Erlöspositionen einschließen |
| `include_cost` | `false` | Kostenpositionen einschließen |
| `include_forecast` | `false` | Forecast-Verträge einschließen |

Boolesche Werte können als `true`, `false`, `1`, `0`, `yes`, `on` oder `ja` übergeben werden. Alles außer den wahr-Werten wird als falsch behandelt.

Beispiel Jahresplanung für Erlöse und Kosten ohne Forecast:

```bash
curl -sS \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  "$VERTRAGSPLANER_BASE_URL/planning?start_date=2026-01-01&end_date=2026-12-31&include_revenue=true&include_cost=true&include_forecast=false"
```

## Schnellstart mit jq

Alle aktiven Verträge als Kurzliste:

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

Im Repository liegen lauffähige Beispiele unter `examples/`:

- `examples/curl-api.sh` - ruft Healthcheck, Verträge und Planung per curl ab
- `examples/python-api.py` - kleiner Python-Client mit Summierung der Planung nach Monat

Beide Beispiele lesen `VERTRAGSPLANER_BASE_URL` und `VERTRAGSPLANER_API_TOKEN` aus der Umgebung.

## Sicherheitshinweise

- API-Tokens wie Passwörter behandeln und nicht commiten.
- Die aktuelle API ist für interne Nutzung gedacht. Für öffentliche Bereitstellung sollte sie hinter HTTPS, Reverse Proxy, Rate-Limit und sauberem Secret-Management laufen.
- Bei direktem Flask-Development-Server im Internet können Scanner viele 404/400-Requests erzeugen; produktiv besser Gunicorn/systemd plus Reverse Proxy verwenden.
