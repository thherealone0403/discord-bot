# discord-bot

Ein fertiges Discord-Bot-Projekt in Python mit:
- Slash-Commands
- Ticket-System
- Auto-Role beim Join
- Welcome-Nachricht in einem konfigurierten Channel
- Link-Blocker für Nachrichten
- Docker-Unterstützung

## Features

- `/ticket <grund>`: Erstellt ein Ticket
- `/closeticket`: Schließt das aktuelle Ticket
- Auto-Rolle bei Join: Rolle mit ID `1570262416502030356`
- Welcome-Nachricht in Channel `1570259898690961591`
- Nachricht mit Links wird gelöscht und der User bekommt eine Warnung

## Schnellstart

1. Python 3.10+ installieren
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env.example` kopieren und anpassen:
   ```bash
   cp .env.example .env
   ```
4. Token und IDs in `.env` setzen
5. Bot starten:
   ```bash
   python main.py
   ```

## Docker

```bash
docker build -t discord-bot .
docker run --env-file .env discord-bot
```

Oder mit Docker Compose:

```bash
docker compose up --build
```

## Environment Variablen

```env
DISCORD_TOKEN=YOUR_BOT_TOKEN
WELCOME_CHANNEL_ID=1570259898690961591
AUTO_ROLE_ID=1570262416502030356
```

## Wichtiger Hinweis

Die Bot-IDs sind bereits als Standardwerte im Code hinterlegt. Für den Einsatz im eigenen Server kannst du sie natürlich in der `.env` überschreiben.
