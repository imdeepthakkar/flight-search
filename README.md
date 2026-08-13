<div align="center">

# ✈️ Flight Search

### _Find the cheapest flights — right from your terminal_ 🖥️💸

> 🆓 **100% Free** &nbsp;·&nbsp; 🌍 **Worldwide** &nbsp;·&nbsp; ⚡ **Instant results** &nbsp;·&nbsp; 🤖 **AI-ready**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=flat-square)](https://python.org)
[![Travelpayouts](https://img.shields.io/badge/Powered%20by-Travelpayouts-FF6B35?style=flat-square)](https://www.travelpayouts.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-22C55E?style=flat-square)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-94A3B8?style=flat-square)](LICENSE)

<br/>

```
✈  CPH → LHR   [2026-09]

1.  DKK 929   SK   Oct 01 2026   Nonstop    3h 50m   ← cheapest 🏆
2.  DKK 948   SK   Sep 30 2026   Nonstop    3h 50m
3.  DKK 960   SK   Oct 07 2026   Nonstop    3h 50m
4.  DKK 965   SK   Sep 23 2026   Nonstop    3h 50m
```
_This is what it looks like in your terminal_ 👆

</div>

---

## 🌟 Why use this?

| Without flight-search | With flight-search |
|---|---|
| 😫 Open browser, wait for Skyscanner to load | ⚡ One command, results in seconds |
| 🍪 Ads, cookies, popups everywhere | 🧹 Clean terminal output, no distractions |
| 💸 Prices change while you browse | 📊 Cached real fares from the last 48h |
| 🤷 "Is this actually the cheapest?" | 🏆 Sorted by price, always |
| 🤖 Can't use with your AI assistant | 🤖 Works with AGY, Claude, Cursor & more via MCP |

---

## 🗺️ Table of Contents

- [⚡ Quickstart](#-quickstart-5-minutes)
- [💻 CLI Commands](#-cli-commands)
- [🤖 Use with AI Tools (MCP)](#-use-with-ai-tools-mcp)
- [⚙️ Configuration](#%EF%B8%8F-configuration)
- [📁 Project Structure](#-project-structure)
- [❓ FAQ](#-faq)

---

## ⚡ Quickstart (5 minutes)

### 🪙 Step 1 — Grab your FREE API token

1. 🌐 Visit **[travelpayouts.com](https://www.travelpayouts.com)** and sign up (free, 30 seconds)
2. 👤 Go to your **Profile → API token** tab
3. 📋 Copy your token — it's already generated, waiting for you!

> 💡 **No credit card. No approval. No waiting.** The token is yours the moment you register.

---

### 📦 Step 2 — Install

```bash
# 📥 Clone the repo
git clone https://github.com/imdeepthakkar/flight-search.git
cd flight-search

# 🔧 Install everything (Python 3.10+ required)
pip install -e .
```

🎉 This gives you **two new commands** on your machine:

| Command | What it does |
|---|---|
| `flight-search` | 🖥️ The CLI — search flights in your terminal |
| `flight-search-mcp` | 🤖 The MCP server — connects to your AI assistant |

---

### 🔑 Step 3 — Configure

```bash
# 📄 Copy the config template
cp .env.example .env
```

Open `.env` and fill it in:

```env
# 🔑 Required — paste your token from travelpayouts.com
TRAVELPAYOUTS_TOKEN=your_token_here

# 💱 Optional — your preferred currency (default: USD)
# Run `flight-search currencies` to see all options
TRAVELPAYOUTS_CURRENCY=DKK
```

---

### 🚀 Step 4 — Search your first flight!

```bash
flight-search search --from CPH --to LHR --date 2026-09
```

> 🎯 Replace `CPH` with your origin airport and `LHR` with your destination.
> Don't know the airport code? Run `flight-search airports` to look it up!

---

## 💻 CLI Commands

### 🔍 `search` — Find the cheapest fares

```bash
# 🛫 Basic: cheapest flights for a month
flight-search search --from CPH --to LHR --date 2026-09

# 🔄 Round-trip
flight-search search --from CPH --to LHR --date 2026-09 --return 2026-09 --trip round-trip

# 💱 Different currency
flight-search search --from JFK --to CDG --date 2026-10 --currency EUR

# 🌐 Any month (all cached results)
flight-search search --from CPH --to LHR

# 🧙 Interactive mode — answers questions one by one
flight-search search -i
```

**All flags:**

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--from` | `-f` | 🛫 Origin airport code (e.g. `CPH`) | required |
| `--to` | `-t` | 🛬 Destination airport code (e.g. `LHR`) | required |
| `--date` | `-d` | 📅 Month to search `YYYY-MM` | any month |
| `--return` | `-r` | 🔄 Return month for round-trip `YYYY-MM` | — |
| `--trip` | | 🎫 `one-way` or `round-trip` | `one-way` |
| `--currency` | `-c` | 💱 Currency code (e.g. `DKK`, `EUR`, `USD`) | from `.env` |
| `--interactive` | `-i` | 🧙 Guided prompt mode | off |

---

### 📅 `calendar` — Cheapest price per day

```bash
# 🗓️ See every day's cheapest price in September
flight-search calendar CPH LHR --month 2026-09

# ⚡ Default: shows next month automatically
flight-search calendar CPH LHR
```

> 💡 **Pro tip:** Use `calendar` when your travel dates are flexible!
> It highlights the cheapest day with a `← cheapest 🏆` tag so you spot it instantly.

---

### 🗺️ `airports` — Look up IATA codes

```bash
# 🔎 Not sure what CPH, LHR, CDG mean? Look them up!
flight-search airports
```

> ℹ️ IATA codes are 3-letter airport identifiers used worldwide.
> e.g. `CPH` = Copenhagen · `LHR` = London Heathrow · `CDG` = Paris Charles de Gaulle

---

### 💱 `currencies` — Supported currency codes

```bash
# 📋 Lists all currencies + shows which one is your default
flight-search currencies
```

---

## 🤖 Use with AI Tools (MCP)

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets your AI assistant search flights **directly from the chat** — no copy-pasting, no switching tabs.

Just say something like:

> 💬 _"Find the cheapest nonstop flight from Copenhagen to London in October"_
> 💬 _"What's the cheapest day to fly CPH → Paris in September?"_
> 💬 _"Show me flights under 1000 DKK from CPH to Amsterdam"_

...and your AI calls the right tool automatically! 🪄

### 🛠️ Available MCP Tools

| Tool | 🎯 Triggered by |
|------|----------------|
| 🔍 `search_flights` | "find flights", "cheap flights from X to Y", "flight prices" |
| 📅 `calendar_view` | "cheapest day to fly", "price calendar", "when is cheapest" |
| 🗺️ `list_airports` | "airport code for X", "what's the IATA for Copenhagen" |
| 💱 `list_currencies` | "what currencies are supported", "change currency" |

---

### 🟢 AGY / Antigravity — Zero config needed

Just **open this project folder in AGY** — everything connects automatically!

- 📡 MCP server auto-registers via `.agents/mcp_config.json`
- 🧙 Flight search wizard activates via `.agents/skills/flight-search/SKILL.md`
- 💬 Just ask: _"find me flights from CPH to London next month"_

---

### 🟤 Claude Code

Add this to **`~/.claude/claude_desktop_config.json`**:

```json
{
  "mcpServers": {
    "flight-search": {
      "command": "flight-search-mcp"
    }
  }
}
```

🔄 Restart Claude Code → look for `flight-search` in your tools list ✅

---

### 🔵 Cursor

Add this to **`~/.cursor/mcp.json`** (global) or **`.cursor/mcp.json`** (project only):

```json
{
  "mcpServers": {
    "flight-search": {
      "command": "flight-search-mcp"
    }
  }
}
```

---

### 🟣 Windsurf

Add this to **`~/.codeium/windsurf/mcp_config.json`**:

```json
{
  "mcpServers": {
    "flight-search": {
      "command": "flight-search-mcp"
    }
  }
}
```

---

### 🔧 Any other MCP-compatible tool

Run the server and connect via stdio transport:

```bash
flight-search-mcp
```

---

## ⚙️ Configuration

All config lives in your `.env` file (copied from `.env.example`):

```env
# 🔑 REQUIRED — Get your free token at travelpayouts.com
TRAVELPAYOUTS_TOKEN=your_token_here

# 💱 OPTIONAL — Default currency for all searches
# Supported: USD, EUR, GBP, DKK, SEK, NOK, INR, AED, AUD, CAD...
# Run `flight-search currencies` to see the full list
TRAVELPAYOUTS_CURRENCY=DKK
```

> 🔒 Your `.env` file is in `.gitignore` — your token is **never committed to Git**.

---

## 📁 Project Structure

```
✈️ flight-search/
│
├── 🐍 main.py              ← CLI app  →  the `flight-search` command
├── 🤖 mcp_server.py        ← MCP server  →  the `flight-search-mcp` command
│
├── 📦 pyproject.toml       ← Package config & entry points
├── 📋 requirements.txt     ← Python dependencies
├── 🔑 .env.example         ← Config template  →  copy to .env
├── 🔒 .gitignore           ← Keeps your .env token safe
├── 📖 SKILL.md             ← Full AGY skill documentation
│
└── 🤖 .agents/             ← AGY auto-discovery folder
    ├── 📡 mcp_config.json                ← Registers MCP server in AGY
    └── 🧙 skills/flight-search/
        └── 📄 SKILL.md                   ← AGY wizard instructions
```

---

## ❓ FAQ

<details>
<summary>🆓 <strong>Is this really free? What's the catch?</strong></summary>

<br/>

Yes, genuinely free. The Travelpayouts Data API endpoints used here (`/v1/prices/cheap` and `/v1/prices/calendar`) are available to all registered affiliate partners at no cost. Travelpayouts makes money when users book through their affiliate links — they share the price data freely to encourage integration.

No credit card. No paid tier. No catch.

</details>

<details>
<summary>⏱️ <strong>Are prices live / real-time?</strong></summary>

<br/>

Prices are **cached from the last 48 hours** of real user searches on Travelpayouts partner sites. They reflect genuine fares but may vary slightly when you click through to book (prices can change between searches). Think of it as a reliable price indicator rather than a live booking engine.

</details>

<details>
<summary>🐍 <strong>What Python version do I need?</strong></summary>

<br/>

**Python 3.10 or higher.** Check yours with:

```bash
python --version
```

No other system dependencies needed beyond what `pip install -e .` installs automatically.

</details>

<details>
<summary>🔤 <strong>What's an IATA code? I don't know mine.</strong></summary>

<br/>

IATA codes are 3-letter airport identifiers used worldwide. Examples:

| City | IATA Code |
|------|-----------|
| Copenhagen | `CPH` |
| London Heathrow | `LHR` |
| Paris | `CDG` |
| New York JFK | `JFK` |
| Dubai | `DXB` |

Run `flight-search airports` for a full reference list, or just Google _"[city name] airport IATA code"_.

</details>

<details>
<summary>💱 <strong>How do I change the default currency?</strong></summary>

<br/>

Add this line to your `.env` file:

```env
TRAVELPAYOUTS_CURRENCY=EUR
```

Run `flight-search currencies` to see all supported currency codes.

You can also override per-command with `--currency EUR`.

</details>

<details>
<summary>🪟 <strong>Does this work on Windows?</strong></summary>

<br/>

Yes! Works on Windows, Mac, and Linux. On Windows, if `flight-search` isn't recognized after install, use:

```bash
python main.py search --from CPH --to LHR --date 2026-09
```

Or activate your virtual environment first:
```bash
.\venv\Scripts\activate
flight-search search --from CPH --to LHR
```

</details>

<details>
<summary>🤖 <strong>The MCP server isn't showing up in my AI tool. Help?</strong></summary>

<br/>

1. Make sure `flight-search-mcp` is installed: run it in terminal — it should hang (waiting for input), which means it's working ✅
2. Double-check the config file path for your tool (each tool has a different location)
3. Fully restart your AI tool after editing the config
4. Make sure `flight-search-mcp` is accessible from your PATH — if not, use the full path: `"/path/to/venv/bin/flight-search-mcp"`

</details>

---

## 📝 Limitations

| | |
|---|---|
| ⏱️ | Prices cached from last **48 hours** — not live quotes |
| 🔤 | Requires **IATA codes** — use `flight-search airports` to find them |
| 📊 | Data shows **cheapest cached fare**, not all available flights |
| 🌐 | Best coverage for **major routes** — some niche routes may have no data |

---

<div align="center">

### Made with ❤️ + ☕ + ✈️

Powered by the [Travelpayouts Data API](https://www.travelpayouts.com) &nbsp;·&nbsp; Built for terminal lovers

[🐛 Report an issue](https://github.com/imdeepthakkar/flight-search/issues) &nbsp;·&nbsp; [⭐ Star on GitHub](https://github.com/imdeepthakkar/flight-search)

</div>