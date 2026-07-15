# Track-A-Bet TabHelper

A local CLI + Web UI helper for logging bets to [Track-A-Bet](https://track-a-bet.bettingiscool.com).

## Features

- **CLI tool** — log bets quickly from the terminal
- **Web UI** — local Flask server with a clean form for logging bets
- **Auto-detection** — parses common bet strings (e.g. "Man Utd -1.5 @ 2.10 $50") 
- **Local storage** — SQLite database caches your bets locally
- **Session tracking** — view recent bets, stats, and performance
- **Sync to Track-A-Bet** — push bets to the live dashboard

## Setup

```bash
# Install
pip install -r requirements.txt

# Run the web UI
python run.py web

# Log a bet from the CLI
python run.py log "Man Utd vs Liverpool" --sport football --selection "Man Utd -1.5" --odds 2.10 --stake 50

# Log with natural syntax
python run.py log "Arsenal -0.5 @ 1.95 $100"

# View bet history
python run.py list

# Show stats
python run.py stats
```
