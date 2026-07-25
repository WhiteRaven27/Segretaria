# Segretaria
Bot Discord creato con discord.py.

## Features
- Embed editor
- Pulsanti
- Modals
- Hex colors
- Conferma invio
- Messaggi ephemeral

## Installazione

1. **Clona il repository:**
```bash
git clone <repository-url>
cd Segretaria
```

2. **Crea un ambiente virtuale (consigliato):**
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

3. **Installa le dipendenze:**
```bash
pip install -r requirements.txt
```

4. **Configura il bot:**
   - Copia `.env.example` a `.env`:
   ```bash
   cp .env.example .env  # Su Windows: copy .env.example .env
   ```
   - Apri `.env` e sostituisci `your_discord_bot_token_here` con il tuo token Discord

5. **Avvia il bot:**
```bash
python bot.py
```

## Ottenere un token Discord

1. Vai su [Discord Developer Portal](https://discord.com/developers/applications)
2. Clicca su "New Application"
3. Vai nella sezione "Bot" e clicca "Add Bot"
4. Copia il token sotto "TOKEN"
5. Assicurati che i "Message Content Intent" siano abilitati in "Privileged Gateway Intents"

## Sicurezza

⚠️ **Non commitare mai il file `.env`** - Contiene informazioni sensibili come il token del bot!
Il file `.env` è già inserito in `.gitignore` per proteggerti da incidenti.
