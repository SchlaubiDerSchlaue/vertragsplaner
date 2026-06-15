# Vertragsplanung MVP

Flask-Web-App zur Verwaltung von Kunden- und Lieferantenvertraegen. Aus Vertragspositionen mit zeitgueltigen Versionen werden monatliche Planungsdaten fuer Erloese und Kosten erzeugt und als CSV oder Excel exportiert.

## Aktueller Funktionsumfang

- Dashboard mit Kennzahlen zu Kunden, Lieferanten, Vertraegen, Positionen und Forecast-Vertraegen
- Kunden- und Lieferantenverwaltung inklusive Kontaktdaten und Adresse
- Vertragsverwaltung fuer Erloes- und Kostenvertraege
- Zuordnung eines Vertrags zu genau einem Kunden oder einem Lieferanten
- Vertragspositionen mit Typ `revenue` oder `cost`
- Fortschreibung von Positionsversionen mit automatischem Schliessen vorheriger Versionen
- Monatliche Planungsrechnung mit Zeitraum, Erloes-/Kostenfilter und Forecast-Option
- Planungsexport als Excel oder CSV
- CSV-/Excel-Import von Vertragspositionsversionen
- Listenansichten mit Suche, Filtern und Sortierung
- Bootstrap-basierte Server-Side-Rendered-Weboberflaeche

## Technische Basis

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- SQLite als Standarddatenbank
- Pandas und OpenPyXL fuer Import und Export

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python create_db.py
python run.py
```

Die App laeuft danach unter:

```text
http://127.0.0.1:5000
```

Die Datenbank liegt standardmaessig als SQLite-Datei `contract_planning.db` im Flask-Instance-Verzeichnis. Ueber die Umgebungsvariable `DATABASE_URL` kann eine andere Datenbank-URL gesetzt werden.

## Importformat

Eine Importzeile entspricht einer Vertragspositionsversion. CSV-Dateien werden mit automatisch erkanntem Trennzeichen gelesen, Excel-Dateien als `.xlsx`.

Pflichtspalten:

- `customer_name`
- `contract_title`
- `status`
- `position_name`
- `valid_from`
- `amount`
- `account`
- `cost_center_1`
- `cost_center_2`
- `recurrence`

Optionale Spalten:

- `partner_type` (`customer` oder `supplier`, Standard: `customer`)
- `customer_no`
- `supplier_name`
- `supplier_no`
- `contract_no`
- `contract_type` (`revenue` oder `cost`)
- `position_type` (`revenue` oder `cost`)
- `contract_start`
- `contract_end`
- `currency`

Fuer Lieferantenvertraege wird `partner_type=supplier` verwendet. Falls `supplier_name` leer ist, nutzt der Import ersatzweise `customer_name` als Partnername.

## Planung und Export

Die Planung erzeugt je Monat eine Zeile pro aktiver, gueltiger Position. Unterstuetzte Rhythmen sind:

- `monthly`
- `quarterly`
- `yearly`
- `once`

Kostenpositionen werden in der Planung und im Export als negative Betraege ausgegeben. Vertraege mit Status `forecast` werden nur beruecksichtigt, wenn die Forecast-Option aktiv ist.

## JSON-API fuer KI-Agenten

Die App stellt eine read-only JSON-API unter `/api/v1` bereit. Sie ist fuer lokale oder LAN-interne Agenten und Skripte gedacht. Schreibzugriffe, Importe und Loeschungen sind ueber diese API nicht moeglich.

Vor dem Start muss ein API-Token gesetzt werden.

Windows PowerShell:

```powershell
$env:API_TOKEN="ein-langes-zufaelliges-token"
python run.py
```

Windows Eingabeaufforderung (`cmd.exe`):

```bat
set API_TOKEN=ein-langes-zufaelliges-token
python run.py
```

In `cmd.exe` den Wert nicht in Anfuehrungszeichen setzen. `set API_TOKEN="abc"` speichert die Anfuehrungszeichen sonst als Teil des Tokens.

Jeder API-Aufruf muss den Token als Bearer-Token senden:

```bash
curl -H "Authorization: Bearer ein-langes-zufaelliges-token" http://127.0.0.1:5000/api/v1/health
```

Verfuegbare Endpunkte:

- `GET /api/v1/health`
- `GET /api/v1/customers`
- `GET /api/v1/suppliers`
- `GET /api/v1/contracts`
- `GET /api/v1/contracts/<id>`
- `GET /api/v1/positions`
- `GET /api/v1/planning?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

Listen-Endpunkte unterstuetzen einfache Filter wie `q`, `status`, `contract_type`, `partner_type`, `limit` und `offset`, soweit sie zum jeweiligen Endpunkt passen.

Beispiele:

```bash
curl -H "Authorization: Bearer ein-langes-zufaelliges-token" "http://127.0.0.1:5000/api/v1/contracts?status=active&limit=50"
```

```bash
curl -H "Authorization: Bearer ein-langes-zufaelliges-token" "http://127.0.0.1:5000/api/v1/planning?start_date=2026-01-01&end_date=2026-12-31&include_revenue=true&include_cost=true&include_forecast=false"
```

Fuer LAN-Zugriff kann die Flask-App auf einer LAN-Adresse gebunden werden, z. B. mit `flask run --host=0.0.0.0`. Die API sollte nicht ohne HTTPS, Reverse Proxy und staerkere Absicherung direkt im Internet veroeffentlicht werden.
