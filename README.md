# discord-bot

Ein Python-Discord-Bot mit privatem Ticket-System, TikTok-Live-Ankündigung, Member-Linkfilter und Team-Rangverwaltung.

## Funktionen und Slash-Commands

- `/ticket-panel`: Erstellt ein Ticket-Panel mit Dropdown für Support, Meldungen und Sonstiges (Serververwaltung).
- `/close-ticket`: Schließt ein Ticket und speichert zuvor ein Transcript.
- `/ping`: Zeigt Latenz und Online-Status.
- `/server`: Zeigt Serverinformationen.
- `/user`: Zeigt Informationen über dich oder einen angegebenen Benutzer.
- `/hilfe`: Listet die wichtigsten Befehle auf.
- `/uprank` und `/downrank`: Team-Rang ändern, mit Rollen-Hierarchieprüfung.
- Nur Mitglieder mit der Rolle **Member** dürfen keine Links senden; andere Rollen sind vom Linkfilter ausgenommen.
- TikTok-Live-Überwachung für den in `TIKTOK_USERNAME` angegebenen Account, standardmäßig `louis.hnvr157`.
- Bot-Aktivität: **Schaut Louis‘s Stream**.

Die Bewerbungs-/`apply`-Befehle und `/warn` wurden entfernt. Beim Start werden die registrierten Slash-Commands synchronisiert, wodurch alte globale Bot-Commands entfernt werden sollten.

## Einrichtung

1. Python 3.10+ installieren.
2. Abhängigkeiten installieren: `pip install -r requirements.txt`.
3. `.env.example` nach `.env` kopieren und `DISCORD_TOKEN` eintragen. Prüfe die Rollen- und Channel-IDs, insbesondere `MEMBER_ROLE_ID`, `TIKTOK_CHANNEL_ID` und optional `TICKET_LOG_CHANNEL_ID`.
4. Im Discord Developer Portal unter **Bot → Privileged Gateway Intents** `Server Members Intent` und `Message Content Intent` aktivieren. Den Bot mit den Scopes `bot` und `applications.commands` einladen.
5. Bot starten: `python run_bot.py`.

Der Bot benötigt Nachrichten- und Channel-Berechtigungen für Tickets, **Nachrichten verwalten** für den Linkfilter und im TikTok-Ankündigungs-Channel **Nachrichten senden**. Für ein Transcript-Log benötigt er dort ebenfalls **Dateien anhängen**. Der Bot kann nur Rollen verwalten, die in der Discord-Rollenhierarchie unter seiner eigenen Rolle liegen.

## Ticket-Transcripts

Vor dem Löschen eines Tickets wird die Nachrichtenhistorie als UTF-8-Textdatei gespeichert. Lokal landen die Dateien in `transcripts/`. Mit Docker Compose ist dieses Verzeichnis als Volume eingebunden, sodass die Dateien Container-Neustarts überstehen. Optional kann `TICKET_LOG_CHANNEL_ID` auf einen Text-Channel gesetzt werden; dann wird das Transcript zusätzlich dort hochgeladen.

## TikTok

Beim Wechsel des konfigurierten TikTok-Accounts zu live sendet der Bot eine Ankündigung mit Live-Link in `TIKTOK_CHANNEL_ID`. TikTok kann seine Schnittstellen ändern oder Anfragen begrenzen; bei temporären Fehlern protokolliert der Monitor den Fehler und versucht es beim nächsten Poll erneut. Die Live-Erkennung kann daher nicht garantiert werden.

## Docker

```bash
docker compose up --build -d
```

Die `.env` wird über Docker Compose eingelesen. Niemals echte Bot-Tokens in Git committen.
