# Vertragsplanung MVP

Flask-Web-App zur Verwaltung von Kunden- und Lieferantenverträgen. Aus Vertragspositionen mit zeitgültigen Versionen werden monatliche Planungsdaten für Erlöse und Kosten erzeugt und als CSV oder Excel exportiert.

## Aktueller Funktionsumfang

- Dashboard mit Kennzahlen zu Kunden, Lieferanten, Verträgen, Positionen und Forecast-Verträgen
- Kunden- und Lieferantenverwaltung inklusive Kontaktdaten und Adresse
- Vertragsverwaltung für Erlös- und Kostenverträge
- Zuordnung eines Vertrags zu genau einem Kunden oder einem Lieferanten
- Vertragspositionen mit Typ `revenue` oder `cost`
- Fortschreibung von Positionsversionen mit automatischem Schließen vorheriger Versionen
- Monatliche Planungsrechnung mit Zeitraum, Erlös-/Kostenfilter und Forecast-Option
- Planungsexport als Excel oder CSV
- CSV-/Excel-Import von Vertragspositionsversionen
- Listenansichten mit Suche, Filtern und Sortierung
- Bootstrap-basierte Server-Side-Rendered-Weboberfläche

## Technische Basis

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- SQLite als Standarddatenbank
- Pandas und OpenPyXL für Import und Export

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python create_db.py
python run.py
```

Die App läuft danach unter:

```text
http://127.0.0.1:5000
```

Die Datenbank liegt standardmäßig als SQLite-Datei `contract_planning.db` im Flask-Instance-Verzeichnis. Über die Umgebungsvariable `DATABASE_URL` kann eine andere Datenbank-URL gesetzt werden.

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

Für Lieferantenverträge wird `partner_type=supplier` verwendet. Falls `supplier_name` leer ist, nutzt der Import ersatzweise `customer_name` als Partnername.

## Planung und Export

Die Planung erzeugt je Monat eine Zeile pro aktiver, gültiger Position. Unterstützte Rhythmen sind:

- `monthly`
- `quarterly`
- `yearly`
- `once`

Kostenpositionen werden in der Planung und im Export als negative Beträge ausgegeben. Verträge mit Status `forecast` werden nur berücksichtigt, wenn die Forecast-Option aktiv ist.
