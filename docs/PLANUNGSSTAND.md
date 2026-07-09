# Planungsstand Vertragsplanung-App

Stand: 2026-06-13

## Ziel

Entwicklung einer Web-App zur Verwaltung von Kunden- und Lieferantenverträgen mit Fokus auf die Ableitung monatlicher Planungsdaten für eine Planungsrechnung.

Die App bildet Erlös- und Kostenverträge ab. Erlöse werden typischerweise Kunden zugeordnet, Kosten typischerweise Lieferanten. Technisch hängt ein Vertrag genau an einem Partner: entweder Kunde oder Lieferant.

## Technologische Basis

- Python
- Flask
- SQLAlchemy
- Flask-Migrate
- SQLite für den lokalen Start
- Jinja Templates
- Bootstrap
- Pandas/OpenPyXL für Import und Export

PostgreSQL bleibt als spätere Produktivoption vorgesehen.

## Umgesetzter Stand

- App-Factory mit Blueprints für Dashboard, Kunden, Lieferanten, Verträge, Planung, Import und Export
- Dashboard mit Zählwerten für Kunden, Lieferanten, Verträge, Positionen und Forecast-Verträge
- Kundenstamm inklusive Nummer, Status, Kontakt, E-Mail, Adresse und Notizen
- Lieferantenstamm inklusive Nummer, Status, Kontakt, E-Mail, Adresse und Notizen
- Vertragsliste mit Suche, Statusfilter, Vertragstypfilter, Partnerfilter und Sortierung
- Positionsliste mit Suche, Statusfilter, Positionstypfilter, Partnerfilter und Sortierung
- Vertragsanlage/-bearbeitung mit Partnerauswahl Kunde oder Lieferant
- Vertragsdetail mit Positionen und Versionen
- Positionsanlage/-bearbeitung
- Versionsanlage/-bearbeitung
- Fortschreibung neuer Versionen schließt vorherige überschneidende Versionen automatisch
- Monatsplanung mit Zeitraum, Erlös-/Kostenfilter und Forecast-Option
- Export der Planung als Excel oder CSV
- Separater Exportscreen mit Plausibilisierung des Zeitraums
- Import von CSV- und Excel-Dateien
- Initialisierung/Aktualisierung der lokalen Datenbank über `create_db.py`

## Fachliche Grundannahmen

- Ein Vertrag gehört genau zu einem Kunden oder genau zu einem Lieferanten.
- Ein Vertrag kann mehrere Positionen haben.
- Eine Position kann mehrere zeitgültige Versionen haben.
- Änderungen gelten immer ab einem bestimmten Datum.
- Die Planung erfolgt auf Monatsbasis.
- Für v1 erfolgt keine taggenaue Abgrenzung innerhalb eines Monats.
- Konten und Kostenstellen sind Freitextfelder.
- Forecast-Verträge können optional in der Planung berücksichtigt werden.
- Kostenpositionen werden im Planungsexport als negative Beträge ausgegeben.

## Statusarten Vertrag

| Status | Bedeutung für Planung |
|---|---|
| `draft` | nicht berücksichtigen |
| `active` | berücksichtigen |
| `forecast` | nur berücksichtigen, wenn Forecast-Option aktiviert ist |
| `cancelled` | berücksichtigen, solange der Planungsmonat innerhalb der wirksamen Laufzeit liegt |
| `ended` | nicht berücksichtigen |

## Laufzeit, Kuendigung und Verlaengerung

- `start_date` ist der Beginn der Planung. Vor diesem Datum wird der Vertrag nicht beruecksichtigt.
- `end_date` ist das Vertragsende bzw. der letzte Leistungszeitraum der gepflegten Laufzeit.
- `cancellation_date` bedeutet "gekuendigt zum" und ist das wirksame Ende. Wenn dieses Datum gesetzt ist, endet die Planung danach auch bei automatischer Verlaengerung.
- `renewal_type = none`: keine Verlaengerung; die Planung endet nach `end_date`.
- `renewal_type = manual`: manuelle Verlaengerung; die Planung endet nach `end_date`, ausser die Laufzeit wird aktiv fortgeschrieben.
- `renewal_type = automatic`: automatische Verlaengerung; ohne `cancellation_date` laeuft der Vertrag in der Planung ueber `end_date` hinaus weiter.
- `status = cancelled` ist damit ein fachlicher Status fuer gekuendigte Vertraege; geplant wird trotzdem bis zum wirksamen Ende.
- `status = ended` beendet die Beruecksichtigung immer sofort.

## Datenmodell

### Customer

- Kundennummer
- Name
- Status
- Ansprechpartner
- E-Mail
- Straße
- PLZ
- Ort
- Land
- Notizen

### Supplier

- Lieferantennummer
- Name
- Status
- Ansprechpartner
- E-Mail
- Straße
- PLZ
- Ort
- Land
- Notizen

### Contract

- Kunde oder Lieferant
- Vertragsnummer
- Titel
- Vertragstyp: `revenue` / `cost`
- Status: `draft` / `active` / `forecast` / `cancelled` / `ended`
- Startdatum
- Enddatum
- Kündigungsdatum
- Verlängerungstyp
- Verantwortlicher
- Beschreibung

### ContractPosition

- Vertrag
- Name
- Positionstyp: `revenue` / `cost`
- Status: `active` / `inactive`
- Sortierung

### ContractPositionVersion

- Position
- gültig ab
- gültig bis
- Betrag
- Währung
- Konto
- Kostenstelle 1
- Kostenstelle 2
- Rhythmus: `monthly` / `quarterly` / `yearly` / `once`
- Fälligkeitstag
- aktiv
- Notiz

## Planungslogik

Die App erzeugt monatliche Planungszeilen anhand von:

- gewähltem Zeitraum
- Vertragsstatus
- Vertragslaufzeit
- Positionsstatus
- gültiger Positionsversion
- Rhythmus
- Erlös-/Kostenfilter
- Forecast-Option

Die erzeugten Zeilen enthalten aktuell:

- Monat
- Partnername
- Partnertyp
- Vertragsnummer
- Vertragstitel
- Vertragsstatus
- Position
- Positionstyp
- Betrag
- Währung
- Konto
- Kostenstelle 1
- Kostenstelle 2

## Import

Massenimport über CSV oder Excel. Eine Zeile entspricht einer Vertragspositionsversion.

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

- `partner_type`
- `customer_no`
- `supplier_name`
- `supplier_no`
- `contract_no`
- `contract_type`
- `position_type`
- `contract_start`
- `contract_end`
- `currency`

Hinweis: Für Lieferantenverträge wird `partner_type=supplier` erwartet. Ohne Angabe wird `customer` angenommen.

## Export

Export der erzeugten Planungszeilen als:

- Excel (`planung.xlsx`)
- CSV (`planung.csv`, Semikolon-getrennt, UTF-8)

## Offene Punkte und nächste Schritte

- Importvorlage um Lieferanten-/Partnerfelder erweitern
- UI-Texte und Fehlermeldungen vollständig auf Umlaute/UTF-8 prüfen
- Automatisierte Tests für Planungslogik, Import und Routen ergänzen
- Echte Alembic-Migrationen statt manueller Aktualisierung in `create_db.py` aufbauen
- Lösch-/Archivierungslogik für Stammdaten und Verträge klären
- Umgang mit Kündigungsdatum fachlich schärfen
- Optional: Konten- und Kostenstellenstamm einführen

## Roadmap

### Phase 1: MVP

- Kunden
- Lieferanten
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
- Planung nach Partner
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
