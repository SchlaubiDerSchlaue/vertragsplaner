# Logging & Audit in Vertragsplaner

## Übersicht

Die App erfasst automatisch strukturierte Logs in drei Kategorien:

| Log-Datei | Zweck | Inhalt |
|---|---|---|
| `app.log` | Anwendungs-Logs | Startup, Errors, allgemeine Ereignisse |
| `audit.log` | Audit-Trail | Alle Datenänderungen (CREATE/UPDATE/DELETE) |
| `access.log` | Zugriffs-Protokoll | Alle HTTP-Requests mit User, Dauer, Status |

Alle Logs sind **JSON-strukturiert** und werden automatisch rotiert (10 Backups à 10 MB).

---

## Audit-Trail (Revisionssicherheit)

### Was wird protokolliert?

Der Audit-Log erfasst **jede Datenänderung** automatisch durch SQLAlchemy-Event-Listener:

- **Erstellen** von Kunden, Lieferanten, Verträgen, Positionen, Versionen, Benutzern
- **Ändern** mit Vorher-/Nachher-Werten jedes geänderten Feldes
- **Löschen** mit vollständiger Snapshot der gelöschten Daten

Jeder Audit-Eintrag enthält:

- **timestamp** – UTC-Zeitstempel
- **action** – create / update / delete / login / logout
- **resource_type** – Kunde, Lieferant, Vertrag, etc.
- **resource_id** – ID der betroffenen Entität
- **old_values** – Alte Werte (bei update/delete)
- **new_values** – Neue Werte (bei create/update)
- **user_id / username** – Wer hat die Änderung durchgeführt
- **api_token_name** – Falls über API erfolgt
- **request_id** – Korrelation mit access.log
- **ip_address** – Herkunft der Anfrage

### Beispiel-Audit-Eintrag

```json
{
  "timestamp": "2026-08-05T11:00:00+00:00",
  "action": "update",
  "resource_type": "Vertrag",
  "resource_id": 42,
  "username": "arne",
  "ip_address": "192.168.1.10",
  "old_values": {
    "status": "draft",
    "end_date": "2027-12-31"
  },
  "new_values": {
    "status": "active",
    "end_date": "2028-06-30"
  },
  "message": "Geändert: Vertrag"
}
```

---

## Tipps für Revisionssicherheit (GoBD)

### 1. Vollständigkeit des Audit-Trails

✅ **Erfüllt:** Alle Datenänderungen werden automatisch protokolliert, keine manuelle Instrumentierung nötig.  
✅ **Unveränderbarkeit:** Audit-Logs werden in separate Dateien geschrieben, die nicht über die App löschbar sind.

**Empfehlung:** Audit-Logs regelmäßig auf ein externes Medium oder WORM-Speicher sichern.

### 2. Zugriffskontrolle

✅ **Erfüllt:** Drei Rollen (read/write/admin) mit Passwort-Authentifizierung.  
✅ **API-Absicherung:** API-Tokens mit Hash-Speicherung und Rollenbeschränkung.

**Empfehlung:**
- Keine gemeinsamen Accounts – jeder Benutzer muss individuell identifizierbar sein
- Regelmäßige Passwortwechsel für Benutzerkonten
- API-Tokens nur mit minimal erforderlicher Rolle erstellen

### 3. Zeitstempel und Reihenfolge

✅ **Erfüllt:** UTC-Zeitstempel mit Millisekunden-Genauigkeit.  
✅ **Request-Korrelation:** Jede Anfrage bekommt eine Request-ID, die access.log mit audit.log verknüpft.

**Empfehlung:** Server-Zeit per NTP synchronisieren (`chrony` oder `systemd-timesyncd`).

### 4. Datenkonsistenz

✅ **Erfüllt:** SQLAlchemy-Transaktionen – Änderungen werden nur bei Erfolg committed.  
✅ **Audit-Genauigkeit:** Vorher-/Nachher-Werte werden vor dem Commit erfasst.

### 5. Aufbewahrungsfrist

✅ **Erfüllt:** Log-Rotation mit konfigurierbarer Aufbewahrung (Standard: 10 × 10 MB).

**Empfehlung für GoBD-Konformität:**
- Aufbewahrungsfrist: **mindestens 6 Jahre** (§ 257 HGB) bzw. **10 Jahre** (§ 147 AO)
- Log-Dateien unveränderbar speichern (WORM, S3 Object Lock, oder schreibgeschützte Archive)
- Regelmäßige Backups der Log-Dateien + Prüfsummen (SHA-256)

### 6. Nachvollziehbarkeit

✅ **Erfüllt:** Jeder Eintrag enthält Benutzer, IP, Zeitstempel und geänderte Werte.

**Empfehlung:**
- Regelmäßige Stichproben zur Prüfung der Vollständigkeit
- Dokumentation der Logging-Konfiguration und Änderungsprotokolle
- Sicherstellen, dass niemand direkten DB-Zugriff ohne Logging hat

---

## Konfiguration

### Umgebungsvariablen

```bash
# Log-Verzeichnis (Standard: logs/ im App-Verzeichnis)
export VERTRAGSPLANER_LOG_DIR="/var/log/vertragsplaner"

# Log-Level: DEBUG, INFO, WARNING, ERROR
export VERTRAGSPLANER_LOG_LEVEL="INFO"

# Maximale Größe pro Log-Datei in Bytes (Standard: 10 MB)
export VERTRAGSPLANER_LOG_MAX_BYTES="10000000"

# Anzahl der aufbewahrten Backup-Dateien (Standard: 10)
export VERTRAGSPLANER_LOG_BACKUP_COUNT="20"
```

### Log-Verzeichnis sichern

```bash
# Backup der Logs mit Datum
tar -czf "logs-backup-$(date +%Y%m%d).tar.gz" logs/

# Prüfsumme für Integritätsnachweis
sha256sum "logs-backup-$(date +%Y%m%d).tar.gz" > "logs-backup-$(date +%Y%m%d).tar.gz.sha256"

# Auf schreibgeschütztes Medium kopieren
cp logs-backup-*.tar.gz* /mnt/backup/logs/
```

---

## Analyse-Beispiele

### Alle Änderungen an Verträgen

```bash
jq 'select(.resource_type == "Vertrag")' logs/audit.log
```

### Wer hat wann was gelöscht?

```bash
jq 'select(.action == "delete")' logs/audit.log
```

### Änderungen eines bestimmten Benutzers

```bash
jq 'select(.username == "arne")' logs/audit.log
```

### Requests mit Status >= 400

```bash
jq 'select(.status_code >= 400)' logs/access.log
```

### Langsame Requests (> 1 Sekunde)

```bash
jq 'select(.duration_ms > 1000)' logs/access.log
```

---

## Log-Dateien nicht im Git tracken

`.gitignore` sollte enthalten:

```gitignore
# Logs
logs/*.log
*.log
```

---

## Produktionsempfehlungen

1. **Log-Verzeichnis außerhalb des App-Verzeichnisses:** `/var/log/vertragsplaner/`
2. **Systemd Journal:** Optional zusätzlich `journald` für die App nutzen
3. **Log-Monitoring:** Tools wie `fail2ban` für wiederholte fehlgeschlagene Logins
4. **Zentrales Logging:** Für größere Umgebungen Logs an Syslog/ELK/Grafana Loki senden
5. **HTTPS:** In Produktion unbedingt HTTPS verwenden, sonst sind IP-Adressen und Daten unverschlüsselt
