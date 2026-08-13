#!/usr/bin/env python3
"""
flight-search MCP Server
Exposes flight search tools via the Model Context Protocol (MCP).
Works with AGY, Claude Code, Cursor, Windsurf, and any MCP-compatible client.

Install: pip install -e .
Run:     flight-search-mcp
"""

import os
import sys
import asyncio
import datetime

from dotenv import load_dotenv
from mcp.server.mcpserver.server import MCPServer

load_dotenv()

# ── Re-use API functions from main.py ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from main import (
    fetch_cheap,
    fetch_month_matrix,
    get_token,
    SUPPORTED_CURRENCIES,
    DEFAULT_CURRENCY,
)

COMMON_AIRPORTS = [
    ("CPH", "Copenhagen Airport",                 "Copenhagen, Denmark"),
    ("JFK", "John F. Kennedy International",      "New York, USA"),
    ("LAX", "Los Angeles International",           "Los Angeles, USA"),
    ("ORD", "O'Hare International",                "Chicago, USA"),
    ("LHR", "Heathrow",                            "London, UK"),
    ("CDG", "Charles de Gaulle",                   "Paris, France"),
    ("FRA", "Frankfurt Airport",                   "Frankfurt, Germany"),
    ("AMS", "Amsterdam Airport Schiphol",          "Amsterdam, Netherlands"),
    ("DXB", "Dubai International",                 "Dubai, UAE"),
    ("SIN", "Singapore Changi",                    "Singapore"),
    ("HKG", "Hong Kong International",             "Hong Kong"),
    ("NRT", "Narita International",                "Tokyo, Japan"),
    ("SYD", "Sydney Kingsford Smith",              "Sydney, Australia"),
    ("BOM", "Chhatrapati Shivaji Maharaj Intl",    "Mumbai, India"),
    ("DEL", "Indira Gandhi International",         "Delhi, India"),
    ("GRU", "Sao Paulo-Guarulhos",                 "Sao Paulo, Brazil"),
    ("ICN", "Incheon International",               "Seoul, South Korea"),
    ("YYZ", "Toronto Pearson",                     "Toronto, Canada"),
    ("MEX", "Mexico City International",           "Mexico City, Mexico"),
    ("CPT", "Cape Town International",             "Cape Town, South Africa"),
]

# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = MCPServer(
    name="flight-search",
    description="Search for cheap flights worldwide via Travelpayouts (free, no credit card).",
)


@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    month: str = "",
    return_month: str = "",
    currency: str = "",
) -> str:
    """
    Search for the cheapest flights between two airports for a given month.
    Returns cached prices from the last 48 hours.
    Use for: 'find flights', 'cheap flights from X to Y', 'flight prices', 'search flights'.

    Args:
        origin: Origin airport IATA code (e.g. CPH, JFK, LHR)
        destination: Destination airport IATA code (e.g. LHR, CDG, DXB)
        month: Travel month YYYY-MM (e.g. 2026-09). Leave blank for any month.
        return_month: Return month YYYY-MM for round-trip. Leave blank for one-way.
        currency: ISO-4217 currency code (e.g. USD, EUR, DKK). Defaults to configured default.
    """
    token    = get_token()
    origin   = origin.strip().upper()
    dest     = destination.strip().upper()
    currency = (currency.strip().upper() or DEFAULT_CURRENCY)

    tickets = fetch_cheap(
        token,
        origin=origin,
        destination=dest,
        depart_date=month or None,
        return_date=return_month or None,
        currency=currency,
    )

    if not tickets:
        return (
            f"No flights found for {origin} → {dest}"
            + (f" in {month}" if month else "") + ".\n"
            "Try a different month or leave month blank for any-month results."
        )

    tickets = sorted(tickets, key=lambda t: float(t.get("price", 0) or t.get("value", 0)))

    lines = [f"✈  {origin} → {dest}" + (f"  [{month}]" if month else "") + "\n"]
    for i, t in enumerate(tickets, 1):
        price     = t.get("price") or t.get("value", "?")
        airline   = t.get("airline", "—")
        depart    = (t.get("departure_at") or t.get("depart_date") or "")[:10] or "—"
        ret       = (t.get("return_at") or t.get("return_date") or "")[:10] or "—"
        transfers = t.get("transfers", t.get("number_of_changes", 0))
        stops     = "Nonstop" if transfers == 0 else f"{transfers} stop(s)"
        dur_raw   = t.get("duration", t.get("duration_to", 0)) or 0
        if dur_raw:
            h, m = divmod(int(dur_raw), 60)
            dur = f"{h}h {m:02d}m" if h else f"{m}m"
        else:
            dur = "—"
        lines.append(
            f"{i}. {currency} {float(price):,.0f}  |  {airline}  |  {depart} → {ret}  |  {stops}  |  {dur}"
        )

    lines.append(f"\nShowing {len(tickets)} fare(s). Prices cached from last 48h.")
    return "\n".join(lines)


@mcp.tool()
def calendar_view(
    origin: str,
    destination: str,
    month: str = "",
    currency: str = "",
) -> str:
    """
    Show the cheapest flight price for each day in a month between two airports.
    Great for finding the cheapest day to fly.
    Use for: 'cheapest day to fly', 'calendar view', 'price per day', 'when is cheapest flight'.

    Args:
        origin: Origin airport IATA code (e.g. CPH)
        destination: Destination airport IATA code (e.g. LHR)
        month: Month YYYY-MM (e.g. 2026-09). Defaults to next month.
        currency: ISO-4217 currency code. Defaults to configured default.
    """
    token    = get_token()
    origin   = origin.strip().upper()
    dest     = destination.strip().upper()
    currency = (currency.strip().upper() or DEFAULT_CURRENCY)
    month    = month or (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m")

    tickets = fetch_month_matrix(token, origin, dest, month, currency)

    if not tickets:
        return f"No calendar data found for {origin} → {dest} in {month}."

    tickets   = sorted(tickets, key=lambda t: t.get("departure_at", ""))
    min_price = min(float(t.get("price", 9999)) for t in tickets)

    lines = [f"📅 {origin} → {dest}  [{month}]\n"]
    for t in tickets:
        price     = float(t.get("price", 0))
        airline   = t.get("airline", "—")
        depart    = (t.get("departure_at") or "")[:10] or "—"
        transfers = t.get("transfers", 0)
        stops     = "Nonstop" if transfers == 0 else f"{transfers} stop(s)"
        tag       = "  ← cheapest" if price == min_price else ""
        lines.append(f"{depart}  {currency} {price:,.0f}{tag}  |  {airline}  |  {stops}")

    lines.append(f"\nCheapest: {currency} {min_price:,.0f}  |  {len(tickets)} dates found.")
    return "\n".join(lines)


@mcp.tool()
def list_airports() -> str:
    """
    List common airport IATA codes with city and country.
    Use to resolve city names to IATA codes before searching for flights.
    """
    lines = ["Common Airport IATA Codes:\n"]
    for code, name, city in COMMON_AIRPORTS:
        lines.append(f"{code}  {name}  ({city})")
    return "\n".join(lines)


@mcp.tool()
def list_currencies() -> str:
    """
    List all supported currency codes for flight price searches.
    """
    lines = [f"Supported Currencies  (default: {DEFAULT_CURRENCY})\n"]
    for code, name, symbol in SUPPORTED_CURRENCIES:
        tag = "  ← default" if code == DEFAULT_CURRENCY else ""
        lines.append(f"{code}  {symbol}  {name}{tag}")
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
