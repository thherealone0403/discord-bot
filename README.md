# discord-bot

Ein Python-Discord-Bot mit Ticket-System, Bewerbungen, Teamverwaltung und Moderationsfunktionen.

## Funktionen

- `/ticket-panel`: Erstellt ein Ticket-Panel mit Dropdown für Support, Meldungen und Sonstiges. Tickets sind privat und können vom Ersteller oder der Serververwaltung geschlossen werden.
- Automatische Rolle und Willkommensnachricht beim Serverbeitritt.
- Link-Blocker ausschließlich für die Rolle **Member** (per `MEMBER_ROLE_ID` oder Rollenname `Member`). Andere Rollen können weiterhin Links senden.
- TikTok-Live-Überwachung für `louis.hnvr157`: Wenn der Account live geht, postet der Bot im konfigurierten Channel eine Ankündigung mit Live-Link. Standard-Channel: `1570261943032479825`.
- Trial-Mod-Bewerbungen, Rangverwaltung, Verwarnungen sowie `/ping`, `/server` und `/user`.
- Docker-Unterstützung.

## Einrichtung

1. Python 3.10+ installieren.
2. Abhängigkeiten installieren: `pip install -r requirements.txt`.
3. `.env.example` nach `.env` kopieren und `DISCORD_TOKEN` eintragen. Prüfe bei Bedarf insbesondere `MEMBER_ROLE_ID`, `TIKTOK_USERNAME` und `TIKTOK_CHANNEL_ID`.
4. Im Discord Developer Portal unter **Bot → Privileged Gateway Intents** `Server Members Intent` und `Message Content Intent` aktivieren. Den Bot mit den Scopes `bot` und `applications.commands` einladen.
5. Bot starten: `python run_bot.py`.

Der Bot braucht im Ankündigungs-Channel die Berechtigung **Nachrichten senden**. Damit der Link-Blocker Nachrichten löschen kann, benötigt er außerdem **Nachrichten verwalten**. Aktivierte Rollen-IDs müssen aus demselben Discord-Server stammen.

## Ticket-Panel und Bewerbungen

Mit `/ticket-panel` wird das Ticket-Dropdown im aktuellen Channel veröffentlicht. Bewerbungs-Panel und Teamverwaltung verwenden die in `.env` konfigurierten Channel- und Rollen-IDs.

## Docker

```bash
docker compose up --build -d
```

Die `.env` wird über Docker Compose eingelesen. Niemals echte Bot-Tokens in Git committen.
