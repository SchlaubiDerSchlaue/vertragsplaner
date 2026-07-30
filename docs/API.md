# JSON-API

Die Anwendung stellt eine JSON-API unter `/api/v1` bereit. Sie ist für lokale Skripte, interne Automatisierungen und KI-Agenten gedacht, die Vertrags-, Positions- und Planungsdaten lesen und mit passender Berechtigung pflegen sollen.

> Wichtig: Schreibzugriffe benötigen einen API-Token mit Rolle `write` oder `admin`. Importe und Löschungen werden über die API nicht angeboten.

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

API-Tokens werden in der Weboberfläche unter `Admin -> API-Tokens` angelegt. Für GET-Requests reicht die Rolle `read`. POST- und PATCH-Requests benötigen mindestens die Rolle `write`; `admin` schließt diese Rechte ein.

| Rolle | Rechte über die JSON-API |
| --- | --- |
| `read` | Daten und Planung lesen |
| `write` | lesen, Ressourcen anlegen und ändern |
| `admin` | wie `write`; weiterhin keine Löschungen über die API |

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

Validierungsfehler ergänzen feldbezogene Details:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Die übermittelten Daten sind ungültig.",
    "details": {
      "start_date": ["Dieses Feld muss ein gültiges Datum im Format YYYY-MM-DD sein."]
    }
  }
}
```

Schreibzugriffe verwenden ausschließlich `Content-Type: application/json`. Unbekannte JSON-Felder werden abgelehnt, statt stillschweigend ignoriert zu werden. Erfolgreiche POST-Requests antworten mit `201 Created` und einem `Location`-Header, PATCH-Requests mit `200 OK`.

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
GET /customers/<id>
POST /customers
PATCH /customers/<id>
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

Kunden anlegen (`write` oder `admin`):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_no": "K-100",
    "name": "Beispiel GmbH",
    "status": "active",
    "email": "kontakt@example.com",
    "city": "Kiel"
  }' \
  "$VERTRAGSPLANER_BASE_URL/customers"
```

Änderbare Felder: `customer_no`, `name`, `status`, `contact_name`, `email`, `street`, `postal_code`, `city`, `country`, `notes`. Erlaubte Statuswerte sind `active` und `inactive`.

### Lieferanten

```http
GET /suppliers
GET /suppliers/<id>
POST /suppliers
PATCH /suppliers/<id>
```

Filter:

| Parameter | Beschreibung |
| --- | --- |
| `q` | Suche in Name, Kontaktname und E-Mail |
| `status` | Exakter Lieferantenstatus |
| `limit`, `offset` | Pagination |

Änderbare Felder: `supplier_no`, `name`, `status`, `contact_name`, `email`, `street`, `postal_code`, `city`, `country`, `notes`. Das JSON-Format entspricht dem Kundenformat, verwendet aber `supplier_no` statt `customer_no`.

### Verträge

```http
GET /contracts
GET /contracts/<id>
POST /contracts
PATCH /contracts/<id>
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

Vertrag anlegen (`write` oder `admin`):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "partner_type": "customer",
    "partner_id": 1,
    "contract_no": "V-100",
    "title": "Servicevertrag",
    "contract_type": "revenue",
    "status": "active",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "cancellation_period_value": 3,
    "cancellation_period_unit": "months",
    "renewal_type": "automatic",
    "contract_link": "https://example.com/vertrag"
  }' \
  "$VERTRAGSPLANER_BASE_URL/contracts"
```

Pflichtfelder beim Anlegen: `partner_type`, `partner_id`, `title`, `start_date`. `partner_type` ist `customer` oder `supplier`. Weitere Felder: `contract_no`, `contract_type`, `status`, `end_date`, `cancellation_date`, `cancellation_period_value`, `cancellation_period_unit`, `renewal_type`, `responsible`, `contract_link`, `invoice_link`, `description`.

Erlaubte Werte:

- `contract_type`: `revenue`, `cost`
- `status`: `draft`, `active`, `forecast`, `cancelled`, `ended`
- `cancellation_period_unit`: `days`, `weeks`, `months`
- `renewal_type`: `none`, `manual`, `automatic`

Ein PATCH enthält nur die zu ändernden Felder. Zum Wechsel des Vertragspartners sollten `partner_type` und `partner_id` gemeinsam gesendet werden.

### Positionen

```http
GET /positions
GET /positions/<id>
POST /contracts/<contract_id>/positions
PATCH /positions/<id>
POST /positions/<position_id>/versions
GET /versions/<id>
PATCH /versions/<id>
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

Position anlegen (`write` oder `admin`):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Grundgebühr","position_type":"revenue","status":"active","sort_order":10}' \
  "$VERTRAGSPLANER_BASE_URL/contracts/1/positions"
```

Positionsfelder: `name`, `position_type` (`revenue` oder `cost`), `status` (`active` oder `inactive`) und `sort_order`. Fehlt `position_type` beim Anlegen, wird der Typ des Vertrags übernommen.

Neue Positionsversion anlegen:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "valid_from": "2026-01-01",
    "amount": "99.90",
    "currency": "EUR",
    "recurrence": "monthly",
    "billing_day": 1,
    "is_active": true,
    "account": "8400",
    "cost_center_1": "VERTRIEB"
  }' \
  "$VERTRAGSPLANER_BASE_URL/positions/1/versions"
```

Pflichtfelder: `valid_from`, `amount`. Weitere Felder: `currency`, `recurrence`, `billing_day`, `is_active`, `account`, `cost_center_1`, `cost_center_2`, `note`. Beim Anlegen einer späteren Version werden überlappende ältere Versionen automatisch auf den Vortag begrenzt. `valid_to` ist nur beim PATCH einer bestehenden Version änderbar.

Erlaubte Rhythmen: `monthly`, `quarterly`, `yearly`, `once`.

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
- Für Automatisierungen getrennte Tokens verwenden und nur die tatsächlich notwendige Rolle vergeben.
- Änderungen zunächst gegen eine Testinstanz prüfen; DELETE-Endpunkte sind absichtlich nicht vorhanden.
- Die aktuelle API ist für interne Nutzung gedacht. Für öffentliche Bereitstellung sollte sie hinter HTTPS, Reverse Proxy, Rate-Limit und sauberem Secret-Management laufen.
- Bei direktem Flask-Development-Server im Internet können Scanner viele 404/400-Requests erzeugen; produktiv besser Gunicorn/systemd plus Reverse Proxy verwenden.
