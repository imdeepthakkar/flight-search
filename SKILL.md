---
name: flight-search
version: 1.0.0
description: >
  Use this skill to search for cheap flights worldwide using cached Travelpayouts
  pricing data. Trigger phrases: find flights, search flights, cheap flights from
  <city>, flights to <city>, show me flights, flight prices, calendar view flights,
  cheapest day to fly, when is the cheapest flight.
context: fork
enabled: true
allowed-tools: Bash(python main.py *)
---

# Flight Search Skill

Search for real-time cached flight prices worldwide using the **[Travelpayouts Data API](https://www.travelpayouts.com)**
— 100% free, no credit card required. Prices reflect the cheapest fares found in
the last 48 hours of user searches.

> **One API token required.** Register free at [travelpayouts.com](https://www.travelpayouts.com)
> and set `TRAVELPAYOUTS_TOKEN` in your `.env`. Already set up ✅

## ⚙️ Setup (one-time)

```bash
# 1. Register free at https://www.travelpayouts.com
# 2. Copy your token from Profile → API token tab
cp .env.example .env
# 3. Set your token and optional default currency
# TRAVELPAYOUTS_TOKEN=your_token
# TRAVELPAYOUTS_CURRENCY=DKK   ← optional, defaults to USD
```

## When to use this skill

- Find cheapest flights between two cities for a given month
- View a calendar of prices for each day in a month
- Look up IATA airport codes by city name
- Compare prices across currencies

## Commands

### 1. Search cheapest fares

```bash
python main.py search --from CPH --to LHR --date 2026-09
python main.py search --from CPH --to LHR --date 2026-09 --currency EUR
python main.py search --from JFK --to CDG --trip round-trip --date 2026-10 --return 2026-10
python main.py search -i   # interactive/guided mode
```

### 2. Calendar view — cheapest price per day

```bash
python main.py calendar CPH LHR --month 2026-09
python main.py calendar CPH LHR --month 2026-09 --currency USD
```

### 3. Airport IATA codes reference

```bash
python main.py airports
```

### 4. Supported currencies

```bash
python main.py currencies
```

## Key flags

| Flag | Description | Default |
|------|-------------|---------|
| `--from` / `-f` | Origin IATA code (e.g. `CPH`) | required |
| `--to` / `-t` | Destination IATA code (e.g. `LHR`) | required |
| `--date` / `-d` | Month `YYYY-MM` | any month |
| `--return` / `-r` | Return month for round-trip `YYYY-MM` | — |
| `--trip` | `one-way` or `round-trip` | `one-way` |
| `--currency` / `-c` | Currency code | from `.env` or `USD` |
| `--interactive` / `-i` | Guided prompt mode | false |

## Notes

- **Prices are cached** — data reflects searches from the last 48 hours, not live booking prices.
- **IATA codes required** — use city names as hints but pass 3-letter IATA codes to the CLI.
- **Default currency** is set via `TRAVELPAYOUTS_CURRENCY` in `.env` (currently `DKK`).
- All errors print to stderr and exit with code `1`.
