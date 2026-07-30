# Changelog

Alle wesentlichen Änderungen am Vertragsplaner werden in dieser Datei dokumentiert.

## 2026-07-30

### Hinzugefügt

- Schreibzugriffe für die JSON-API mit API-Tokens der Rollen `write` und `admin`.
- POST-Endpunkte zum Anlegen von Kunden, Lieferanten, Verträgen, Vertragspositionen und Positionsversionen.
- PATCH-Endpunkte zum gezielten Ändern dieser Ressourcen.
- GET-Detailendpunkte für Kunden, Lieferanten, Positionen und Positionsversionen.
- Strukturierte JSON-Validierungsfehler mit feldbezogenen Details.
- `Location`-Header und Status `201 Created` bei neu angelegten Ressourcen.
- Automatisches Schließen überlappender älterer Positionsversionen beim Fortschreiben.
- Integrationstests für Rollenprüfung, vollständige Schreibabläufe, Pflichtfelder, unbekannte Felder, Medientypen und bewusst nicht verfügbare Löschzugriffe.

### Sicherheit

- API-Tokens mit Rolle `read` bleiben auf Lesezugriffe beschränkt.
- Schreibrequests müssen `Content-Type: application/json` verwenden.
- Unbekannte JSON-Felder werden abgelehnt und nicht stillschweigend übernommen.
- Pflichtfelder, Datumsbereiche, Enum-Werte, Fremdschlüssel, Beträge, Währungen, URLs und Abrechnungstage werden validiert.
- DELETE- und PUT-Zugriffe bleiben in dieser ersten Ausbaustufe gesperrt.

### Dokumentation

- README und API-Dokumentation um Rollen, Schreibendpunkte, Request-Formate, Antwortcodes, Validierungsfehler und Beispiele ergänzt.

### Hinweise

- Es ist keine Datenbankmigration erforderlich.
- Bestehende read-only API-Tokens funktionieren unverändert weiter.
