#!/usr/bin/env python3
"""
flight-search MCP Server
Exposes flight search tools via the Model Context Protocol (MCP).
Works with AGY, Claude Code, Cursor, Windsurf, and any MCP-compatible client.
Supports natural language city names — no need to know IATA codes!

Install: pip install -e .
Run:     flight-search-mcp
"""

import os
import sys
import asyncio
import datetime
import requests

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
    resolve_to_iata,
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

# ── City/Airport name → IATA resolution ──────────────────────────────────────

# Re-using resolve_to_iata from main.py

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

    Accepts city names OR IATA codes — e.g. 'Copenhagen' or 'CPH', 'London' or 'LHR'.

    Args:
        origin: Origin city name or IATA code (e.g. 'Copenhagen', 'CPH', 'New York', 'JFK')
        destination: Destination city name or IATA code (e.g. 'London', 'LHR', 'Paris', 'CDG')
        month: Travel month YYYY-MM (e.g. 2026-09). Leave blank for any month.
        return_month: Return month YYYY-MM for round-trip. Leave blank for one-way.
        currency: ISO-4217 currency code (e.g. USD, EUR, DKK). Defaults to configured default.
    """
    token    = get_token()
    currency = (currency.strip().upper() or DEFAULT_CURRENCY)

    try:
        origin_code, origin_name = resolve_to_iata(origin)
        dest_code,   dest_name   = resolve_to_iata(destination)
    except ValueError as e:
        return f"❌ {e}"

    resolved_note = ""
    if origin_code != origin.strip().upper() or dest_code != destination.strip().upper():
        resolved_note = f"📍 Resolved: {origin} → {origin_code} ({origin_name}), {destination} → {dest_code} ({dest_name})\n\n"

    tickets = fetch_cheap(
        token,
        origin=origin_code,
        destination=dest_code,
        depart_date=month or None,
        return_date=return_month or None,
        currency=currency,
    )

    if not tickets:
        return (
            resolved_note +
            f"No flights found for {origin_code} → {dest_code}"
            + (f" in {month}" if month else "") + ".\n"
            "Try a different month or leave month blank for any-month results."
        )

    tickets = sorted(tickets, key=lambda t: float(t.get("price", 0) or t.get("value", 0)))

    lines = [resolved_note + f"✈  {origin_code} ({origin_name}) → {dest_code} ({dest_name})" + (f"  [{month}]" if month else "") + "\n"]
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

    Accepts city names OR IATA codes — e.g. 'Copenhagen' or 'CPH', 'London' or 'LHR'.

    Args:
        origin: Origin city name or IATA code (e.g. 'Copenhagen', 'CPH')
        destination: Destination city name or IATA code (e.g. 'London', 'LHR')
        month: Month YYYY-MM (e.g. 2026-09). Defaults to next month.
        currency: ISO-4217 currency code. Defaults to configured default.
    """
    token    = get_token()
    currency = (currency.strip().upper() or DEFAULT_CURRENCY)
    month    = month or (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m")

    try:
        origin_code, origin_name = resolve_to_iata(origin)
        dest_code,   dest_name   = resolve_to_iata(destination)
    except ValueError as e:
        return f"❌ {e}"

    resolved_note = ""
    if origin_code != origin.strip().upper() or dest_code != destination.strip().upper():
        resolved_note = f"📍 Resolved: {origin} → {origin_code} ({origin_name}), {destination} → {dest_code} ({dest_name})\n\n"

    tickets = fetch_month_matrix(token, origin_code, dest_code, month, currency)

    if not tickets:
        return resolved_note + f"No calendar data found for {origin_code} → {dest_code} in {month}."

    tickets   = sorted(tickets, key=lambda t: t.get("departure_at", ""))
    min_price = min(float(t.get("price", 9999)) for t in tickets)

    lines = [resolved_note + f"📅 {origin_code} ({origin_name}) → {dest_code} ({dest_name})  [{month}]\n"]
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
def resolve_location(query: str) -> str:
    """
    Resolve any city name, airport name, or partial name to its IATA code.
    Use this when unsure of a code before calling search_flights or calendar_view.

    Args:
        query: City or airport name to look up (e.g. 'Copenhagen', 'Heathrow', 'New York')
    """
    try:
        code, display = resolve_to_iata(query)
        return f"✅ '{query}' → {code} ({display})"
    except ValueError as e:
        return f"❌ {e}"


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
