---
name: flight-search
description: Run the flight search wizard. Use this skill when the user wants to search for flights, find cheap fares, view a price calendar, or asks about flights between two cities.
---

# Flight Search Wizard

**Agent Instructions:**
Do NOT run `python main.py` interactively. Instead, YOU (the agent) must act as the wizard natively.
Ask the user the following questions ONE BY ONE in the chat. As soon as they answer one, immediately ask the next.

Questions to ask:
1. **From?** — origin airport or city (e.g. CPH, Copenhagen, JFK, New York)
2. **To?** — destination airport or city (e.g. LHR, London, CDG, Paris)
3. **Search type?** — `search` (cheapest fares) or `calendar` (price per day in a month)
4. **Month?** — travel month in `YYYY-MM` format (e.g. `2026-09`). Leave blank for any month.
5. **Currency?** — ISO-4217 code (default: DKK). Skip if happy with default.

Once all questions are answered, resolve any city names to IATA codes (use the airports command if unsure), then run the appropriate command:

## Commands

### Search cheapest fares
```bash
python main.py search --from <ORIGIN> --to <DESTINATION> --date <YYYY-MM> --currency <CODE>
```

### Calendar view (cheapest price per day)
```bash
python main.py calendar <ORIGIN> <DESTINATION> --month <YYYY-MM> --currency <CODE>
```

### Look up IATA codes
```bash
python main.py airports
```

### List supported currencies
```bash
python main.py currencies
```

## Key flags

| Flag | Description | Default |
|------|-------------|---------|
| `--from` / `-f` | Origin IATA code (e.g. CPH) | required |
| `--to` / `-t` | Destination IATA code (e.g. LHR) | required |
| `--date` / `-d` | Month to search `YYYY-MM` | any month |
| `--return` / `-r` | Return month for round-trip `YYYY-MM` | — |
| `--trip` | `one-way` or `round-trip` | one-way |
| `--currency` / `-c` | Currency code | DKK (from .env) |

## Notes
- All commands must be run from `C:\Users\deept\AIProjects\flight-search`
- Use `.\venv\Scripts\python.exe main.py` if `python` is not on PATH
- Prices are cached from the last 48 hours of user searches on Travelpayouts
- The `.env` file already contains the API token and default currency (DKK)
