# Planungsstand Vertragsplanung-App

Stand: 2026-05-31

## Ziel

Entwicklung einer Web-App zur Verwaltung von Kundenverträgen mit Fokus auf die Ableitung von Planungsdaten für eine Planungsrechnung.

Die App soll zunächst Erlösverträge abbilden, später aber auch für Kostenverträge nutzbar sein.

## Technologische Basis

- Python
- Flask
- SQLAlchemy
- Flask-Migrate
- SQLite für den Start
- später PostgreSQL möglich
- Jinja Templates
- Bootstrap
- Pandas/OpenPyXL für Import und Export

## Fachliche Grundannahmen

- Ein Vertrag gehört genau zu einem Kunden.
- Ein Vertrag kann mehrere Positionen haben.
- Eine Position kann mehrere zeitgültige Versionen haben.
- Änderungen gelten immer ab einem bestimmten Datum.
- Die Planung erfolgt auf Monatsbasis.
- Für v1 erfolgt keine taggenaue Abgrenzung.
- Konten und Kostenstellen sind zunächst Freitextfelder.
- Später können Konten und Kostenstellen über Stammdaten eingeschränkt werden.
- Forecast-Verträge können optional in der Planung berücksichtigt werden.

## Statusarten Vertrag

| Status | Bedeutung für Planung |
|---|---|
| draft | nicht berücksichtigen |
| active | standardmäßig berücksichtigen |
| forecast | nur berücksichtigen, wenn Option aktiviert |
| cancelled | bis Enddatum berücksichtigen |
| ended | nicht berücksichtigen |

## Datenmodell v1

### Customer

Kundenstammdaten:

- Kundennummer
- Name
- Status
- Ansprechpartner
- E-Mail
- Notizen

### Contract

Vertragskopf:

- Kunde
- Vertragsnummer
- Titel
- Vertragstyp: revenue / cost
- Status: draft / active / forecast / cancelled / ended
- Startdatum
- Enddatum
- Kündigungsdatum
- Verlängerungstyp
- Verantwortlicher
- Beschreibung

### ContractPosition

Fachliche Position innerhalb eines Vertrags:

- Vertrag
- Name
- Positionstyp: revenue / cost
- Status: active / inactive
- Sortierung

### ContractPositionVersion

Zeitgültige Werte einer Position:

- Position
- gültig ab
- gültig bis
- Betrag
- Währung
- Konto
- Kostenstelle 1
- Kostenstelle 2
- Rhythmus: monthly / quarterly / yearly / once
- Fälligkeitstag
- aktiv
- Notiz

## Planungslogik v1

Die App erzeugt monatliche Planungszeilen anhand von:

- gewähltem Zeitraum
- Vertragsstatus
- Vertragslaufzeit
- Positionsstatus
- gültiger Positionsversion
- Rhythmus
- Erlös-/Kostenfilter
- Forecast-Option

Kostenpositionen werden im Export als negative Beträge ausgegeben.

## Import v1

Massenimport über CSV oder Excel.

Eine Zeile entspricht einer Vertragspositionsversion.

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

## Export v1

Export der erzeugten Planungszeilen als:

- Excel
- CSV

## Roadmap

### Phase 1: MVP

- Kunden
- Verträge
- Positionen
- Versionen
- Monatsplanung
- Forecast-Option
- CSV-/Excel-Import
- CSV-/Excel-Export
- einfache Flask-Weboberfläche

### Phase 2

- Kontenstamm
- Kostenstellenstamm
- Dashboard mit Aggregationen
- Planung nach Konto
- Planung nach Kostenstelle
- Planung nach Kunde
- Vertragsereignisse

### Phase 3

- Planungsszenarien
- Budgetplanung
- Best Case / Worst Case
- Genehmigungsworkflow
- Benutzerrechte
- PostgreSQL-Produktivbetrieb

### Phase 4

- REST API
- DATEV-Export
- ERP-Anbindung
- Automatische Forecast-Berechnung
- Erweiterte Reporting-Funktionen
