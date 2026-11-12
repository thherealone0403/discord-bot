# discord-bot

Ein Python-Discord-Bot mit Ticket-System, Bewerbungen, Teamverwaltung und Moderationsfunktionen.

## Funktionen

- `/ticket-panel`: Erstellt ein Ticket-Panel mit Dropdown für Support, Meldungen und Sonstiges. Tickets sind privat; Ersteller können sie mit `/close-ticket` oder dem Button im Ticket schließen.
- Automatische Rolle und Willkommensnachricht beim Serverbeitritt.
- Link-Blocker: Nachrichten mit URLs/Discord-Einladungen werden gelöscht.
- Trial-Mod-Bewerbungen mit Formular, Annahme/Ablehnung und automatischer Rollenvergabe.
- `/uprank`, `/downrank` und `/warn` mit Rollenprüfung und Rangänderungs-Log.
- `/ping`, `/server` und `/user`.
- Docker-Unterstützung.

## Einrichtung

1. Python 3.10+ installieren.
2. Abhängigkeiten installieren: `pip install -r requirements.txt`.
3. `.env.example` nach `.env` kopieren und `DISCORD_TOKEN` sowie Channel-/Rollen-IDs prüfen.
4. Im Discord Developer Portal unter **Bot → Privileged Gateway Intents** `Server Members Intent` und `Message Content Intent` aktivieren. Den Bot mit den Scopes `bot` und `applications.commands` einladen. Er braucht je nach Funktionen mindestens `Manage Channels`, `Manage Roles`, `Send Messages`, `View Channels`, `Read Message History` und `Manage Messages`.
5. Bot starten: `python main.py`.

## Ticket-Panel

Mit `/ticket-panel` in einem Server-Channel wird das Dropdown-Panel dort veröffentlicht. Der Befehl ist für Mitglieder mit **Server verwalten**. Beim Auswählen erstellt der Bot einen privaten Ticket-Channel und sendet dort einen Schließen-Button. Optional lässt sich `TICKET_CATEGORY_ID` setzen; andernfalls nutzt/erstellt der Bot eine Kategorie mit `TICKET_CATEGORY_NAME`.

## Bewerbungen und Teamverwaltung

Die Channel- und Rollen-IDs der Fynnis-Systeme sind als Standardwerte hinterlegt und können in `.env` überschrieben werden. Reviewer mit einer der konfigurierten Review-Rollen können `/apply-panel`, `/apply-on` und `/apply-off` verwenden. Management-Rollen können `/uprank`, `/downrank` und `/warn` verwenden. Die Teamrollen-Hierarchie ist in `main.py` festgelegt.

## Docker

```bash
docker compose up --build -d
```

Die `.env` wird über Docker Compose eingelesen. Niemals echte Bot-Tokens in Git committen.
