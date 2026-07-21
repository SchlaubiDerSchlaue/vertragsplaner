# Vertragsplanung MVP

Flask-Web-App zur Verwaltung von Kunden- und Lieferantenverträgen. Aus Vertragspositionen mit zeitgültigen Versionen werden monatliche Planungsdaten für Erlöse und Kosten erzeugt und als CSV oder Excel exportiert.

## Aktueller Funktionsumfang

- Dashboard mit Kennzahlen zu Kunden, Lieferanten, Verträgen, Positionen und Forecast-Verträgen
- Kunden- und Lieferantenverwaltung inklusive Kontaktdaten und Adresse
- Vertragsverwaltung für Erlös- und Kostenverträge
- Zuordnung eines Vertrags zu genau einem Kunden oder einem Lieferanten
- Vertragslaufzeit mit Kündigungsfrist, berechnetem Kündigungsstichtag und Filter für bald kündbare Verträge
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

Optional für lokale Entwicklung und Tests:

```bash
pip install -r requirements-dev.txt
pytest
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

Verträge können zusätzlich eine Kündigungsfrist in Tagen, Wochen oder Monaten speichern. Aus Vertragsende und Kündigungsfrist berechnet die App den Stichtag „Kündbar bis“ und bietet in der Vertragsliste Filter für jetzt bzw. innerhalb von 30, 60 oder 90 Tagen kündbare Verträge.

## Zugriff und Rollen

Die Weboberfläche ist zugriffsgeschützt. Es gibt drei Rollen:

- `read`: Daten ansehen, Planung berechnen und Exporte herunterladen
- `write`: zusätzlich Kunden, Lieferanten, Verträge, Positionen, Versionen und Importe bearbeiten
- `admin`: zusätzlich Benutzer und API-Tokens verwalten

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

Admins können in der Weboberfläche unter `Admin` weitere Benutzer und API-Tokens anlegen.

## JSON-API für KI-Agenten und Skripte

Die App stellt eine read-only JSON-API unter `/api/v1` bereit. Sie ist für lokale oder interne Agenten und Automatisierungen gedacht. Schreibzugriffe, Importe und Löschungen sind über diese API nicht möglich.

Kurztest mit API-Token:

```bash
export VERTRAGSPLANER_BASE_URL="http://127.0.0.1:5000/api/v1"
export VERTRAGSPLANER_API_TOKEN="dein-token"

curl -H "Authorization: Bearer $VERTRAGSPLANER_API_TOKEN" "$VERTRAGSPLANER_BASE_URL/health"
```

Ausführliche Dokumentation inklusive Endpunkten, Filtern, Antwortformaten und Sicherheitsnotizen steht in [`docs/API.md`](docs/API.md).

Lauffähige Beispiele liegen unter [`examples/`](examples/):

- [`examples/curl-api.sh`](examples/curl-api.sh) - Healthcheck, Verträge und Planung per curl abrufen
- [`examples/python-api.py`](examples/python-api.py) - kleiner Python-Client mit Planungssumme nach Monat

Beispiel:

```bash
export VERTRAGSPLANER_API_TOKEN="dein-token"
./examples/curl-api.sh
python examples/python-api.py
```

Für LAN-Zugriff kann die Flask-App auf einer LAN-Adresse gebunden werden, z. B. mit `flask run --host=0.0.0.0`. Die API sollte nicht ohne HTTPS, Reverse Proxy und stärkere Absicherung direkt im Internet veröffentlicht werden.
