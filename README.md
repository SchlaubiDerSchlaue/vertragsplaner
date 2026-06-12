# Vertragsplanung MVP

Web-App zur Verwaltung von Kundenverträgen mit Fokus auf Planungsdaten für Erlöse und später auch Kosten.

## Funktionen Phase 1

- Kundenverwaltung
- Vertragsverwaltung
- Vertragspositionen
- Zeitgültige Positionsversionen
- Status `forecast` als optional planbarer Vertragsstatus
- Monatliche Planungslogik
- Erlöse/Kosten-Umschaltung
- CSV-/Excel-Import
- CSV-/Excel-Export der Planung
- Klassische Flask-Weboberfläche mit Bootstrap

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt
flask db init
flask db migrate -m "Initial tables"
flask db upgrade
python run.py
```

Die App läuft danach unter:

```text
http://127.0.0.1:5000
```

## Importformat

Eine Importzeile entspricht einer Vertragspositionsversion.

Pflichtspalten:

- customer_name
- contract_title
- status
- position_name
- valid_from
- amount
- account
- cost_center_1
- cost_center_2
- recurrence

Optionale Spalten:

- customer_no
- contract_no
- contract_type
- position_type
- contract_start
- contract_end
- currency
