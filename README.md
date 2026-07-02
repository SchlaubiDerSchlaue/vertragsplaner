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

Optional fuer lokale Entwicklung und Tests:

```bash
pip install -r requirements-dev.txt
pytest
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

## Zugriff und Rollen

Die Weboberflaeche ist zugriffsgeschuetzt. Es gibt drei Rollen:

- `read`: Daten ansehen, Planung berechnen und Exporte herunterladen
- `write`: zusaetzlich Kunden, Lieferanten, Vertraege, Positionen, Versionen und Importe bearbeiten
- `admin`: zusaetzlich Benutzer und API-Tokens verwalten

Nach dem Erzeugen oder Aktualisieren der Datenbank muss mindestens ein Admin-Benutzer angelegt werden:

Windows PowerShell:

```powershell
python create_db.py
python create_admin.py --username admin
python run.py
```

Windows Eingabeaufforderung (`cmd.exe`):

```bat
python create_db.py
python create_admin.py --username admin
python run.py
```

Admins koennen in der Weboberflaeche unter `Admin` weitere Benutzer und API-Tokens anlegen.

## JSON-API fuer KI-Agenten und Skripte

Die App stellt eine read-only JSON-API unter `/api/v1` bereit. Sie ist fuer lokale oder interne Agenten und Automatisierungen gedacht. Schreibzugriffe, Importe und Loeschungen sind ueber diese API nicht moeglich.

Kurztest mit API-Token:

```bash
export VERTRAGSPLANER_BASE_URL="http://127.0.0.1:5000/api/v1"
export VERTRAGSPLANER_API_TOKEN="dein-token"

curl -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" "$VERTRAGSPLANER_BASE_URL/health"
```

Ausfuehrliche Dokumentation inklusive Endpunkten, Filtern, Antwortformaten und Sicherheitsnotizen steht in [`docs/API.md`](docs/API.md).

Lauffaehige Beispiele liegen unter [`examples/`](examples/):

- [`examples/curl-api.sh`](examples/curl-api.sh) - Healthcheck, Vertraege und Planung per curl abrufen
- [`examples/python-api.py`](examples/python-api.py) - kleiner Python-Client mit Planungssumme nach Monat

Beispiel:

```bash
export VERTRAGSPLANER_API_TOKEN="dein-token"
./examples/curl-api.sh
python examples/python-api.py
```

Fuer LAN-Zugriff kann die Flask-App auf einer LAN-Adresse gebunden werden, z. B. mit `flask run --host=0.0.0.0`. Die API sollte nicht ohne HTTPS, Reverse Proxy und staerkere Absicherung direkt im Internet veroeffentlicht werden.
