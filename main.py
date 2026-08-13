#!/usr/bin/env python3
"""
flight-search -- terminal utility for searching flights via Travelpayouts API
Free, no credit card required. Sign up at https://www.travelpayouts.com
"""

import sys
import io
import os
import datetime
from typing import Optional

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box
from rich.align import Align
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.padding import Padding
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    name="flight-search",
    help="Search flights via Travelpayouts API (100%% free, no credit card)",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

BASE_URL = "https://api.travelpayouts.com"
SEAT_CHOICES = ["economy", "business", "first"]
TRIP_CHOICES  = ["one-way", "round-trip"]

SUPPORTED_CURRENCIES = [
    ("USD", "US Dollar",          "$"),
    ("EUR", "Euro",               "€"),
    ("GBP", "British Pound",      "£"),
    ("DKK", "Danish Krone",       "kr"),
    ("SEK", "Swedish Krona",      "kr"),
    ("NOK", "Norwegian Krone",    "kr"),
    ("INR", "Indian Rupee",       "₹"),
    ("AED", "UAE Dirham",         "د.إ"),
    ("AUD", "Australian Dollar",  "A$"),
    ("CAD", "Canadian Dollar",    "C$"),
    ("CHF", "Swiss Franc",        "Fr"),
    ("JPY", "Japanese Yen",       "¥"),
    ("SGD", "Singapore Dollar",   "S$"),
    ("THB", "Thai Baht",          "฿"),
    ("BRL", "Brazilian Real",     "R$"),
    ("ZAR", "South African Rand", "R"),
    ("MXN", "Mexican Peso",       "$"),
    ("HKD", "Hong Kong Dollar",   "HK$"),
    ("NZD", "New Zealand Dollar", "NZ$"),
    ("PLN", "Polish Zloty",       "zł"),
]

DEFAULT_CURRENCY = os.getenv("TRAVELPAYOUTS_CURRENCY", "USD").strip().upper()

BANNER = """
[bold cyan]  >>  F L I G H T   S E A R C H[/bold cyan]
[dim]  Powered by Travelpayouts Data API -- 100% free[/dim]
"""


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_token() -> str:
    token = os.getenv("TRAVELPAYOUTS_TOKEN", "").strip()
    if not token or token == "your_token_here":
        console.print(
            Panel(
                "[bold yellow]No Travelpayouts token found![/bold yellow]\n\n"
                "1. Sign up free (no credit card) at "
                "[link=https://www.travelpayouts.com]travelpayouts.com[/link]\n"
                "2. Go to [bold]Profile -> Developers -> API[/bold] and copy your token\n"
                "3. Create a [bold].env[/bold] file:\n\n"
                "   [dim]cp .env.example .env[/dim]\n\n"
                "   Then set [bold]TRAVELPAYOUTS_TOKEN=your_actual_token[/bold]",
                title="[bold red]Setup Required[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)
    return token


# ── API calls ─────────────────────────────────────────────────────────────────

def fetch_cheap(token: str, origin: str, destination: str,
                depart_date: Optional[str], return_date: Optional[str],
                currency: str) -> list[dict]:
    """
    GET /v1/prices/cheap
    Returns cheapest tickets found in the last 48 hours per direction/stops.
    """
    params = {
        "origin":      origin,
        "destination": destination,
        "currency":    currency,
        "token":       token,
    }
    if depart_date:
        params["depart_date"] = depart_date[:7]   # YYYY-MM  (month granularity)
    if return_date:
        params["return_date"] = return_date[:7]

    r = requests.get(
        f"{BASE_URL}/v1/prices/cheap",
        params=params,
        headers={"Accept-Encoding": "gzip"},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()

    if not body.get("success", True):
        raise RuntimeError(body.get("error", "API returned an error"))

    raw = body.get("data", {})
    results = []
    for dest_code, stops_map in raw.items():
        for stops_key, ticket in stops_map.items():
            ticket["_destination"] = dest_code
            ticket["_stops_key"]   = stops_key
            results.append(ticket)
    return results


def fetch_latest(token: str, origin: str, destination: str,
                 depart_date: Optional[str], currency: str,
                 trip_duration: Optional[int]) -> list[dict]:
    """
    GET /v2/prices/latest
    Returns a list of cheapest prices from the last 48 hours, sortable.
    """
    params = {
        "origin":      origin,
        "destination": destination,
        "currency":    currency,
        "token":       token,
        "limit":       30,
        "sorting":     "price",
        "unique":      False,
    }
    if depart_date:
        params["beginning_of_period"] = depart_date[:7] + "-01"
        params["period_type"] = "month"
    if trip_duration:
        params["trip_duration"] = trip_duration

    r = requests.get(
        f"{BASE_URL}/v2/prices/latest",
        params=params,
        headers={"Accept-Encoding": "gzip"},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()

    if not body.get("success", True):
        raise RuntimeError(body.get("error", "API returned an error"))

    return body.get("data", [])


def fetch_month_matrix(token: str, origin: str, destination: str,
                       month: str, currency: str) -> list[dict]:
    """
    GET /v1/prices/calendar
    Returns cheapest price for each day in a month.
    """
    params = {
        "origin":       origin,
        "destination":  destination,
        "depart_date":  month,      # YYYY-MM
        "currency":     currency,
        "token":        token,
        "calendar_type": "departure_date",
    }
    r = requests.get(
        f"{BASE_URL}/v1/prices/calendar",
        params=params,
        headers={"Accept-Encoding": "gzip"},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    if not body.get("success", True):
        raise RuntimeError(body.get("error", "API returned an error"))
    raw = body.get("data", {})
    return list(raw.values())


# ── Formatting ────────────────────────────────────────────────────────────────

def fmt_stops(n: int) -> str:
    if n == 0:
        return "[bold green]Nonstop[/bold green]"
    return f"[yellow]{n} stop{'s' if n != 1 else ''}[/yellow]"


def fmt_price(amount, currency: str) -> str:
    try:
        return f"[bold green]{currency} {float(amount):,.0f}[/bold green]"
    except Exception:
        return f"[bold green]{currency} {amount}[/bold green]"


def fmt_date(d: str) -> str:
    try:
        return datetime.datetime.fromisoformat(d).strftime("%b %d %Y")
    except Exception:
        return d or "—"


def print_banner():
    console.print(Align.center(BANNER))
    console.print(Rule(style="dim cyan"))
    console.print()


def print_results_table(tickets: list[dict], currency: str, origin: str, destination: str):
    if not tickets:
        console.print(
            "[yellow]  No flights found for that route/period.\n"
            "  Try a different month or leave the date blank for any-month results.[/yellow]"
        )
        return

    # Sort by price
    tickets = sorted(tickets, key=lambda t: float(t.get("price", 0) or t.get("value", 0)))

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
        title=f"[bold cyan]{origin} -> {destination}[/bold cyan]  [dim]cheapest fares (last 48 h)[/dim]",
        title_style="bold",
    )
    table.add_column("#",           style="dim",         width=3)
    table.add_column("Price",       style="bold green",  min_width=12)
    table.add_column("Airline",     style="bold",        width=8)
    table.add_column("Depart",      style="cyan",        min_width=12)
    table.add_column("Return",      style="magenta",     min_width=12)
    table.add_column("Duration",    style="yellow",      width=10)
    table.add_column("Stops",       min_width=10)
    table.add_column("Transfers",   style="dim",         min_width=8)

    for i, t in enumerate(tickets, 1):
        price     = t.get("price") or t.get("value", "?")
        airline   = t.get("airline", "—")
        depart    = fmt_date(t.get("departure_at", t.get("depart_date", "")))
        ret       = fmt_date(t.get("return_at",    t.get("return_date", "")))
        transfers = t.get("transfers", t.get("number_of_changes", 0))
        # duration in minutes (v1) or hours (v2 has flight_number quirks)
        dur_raw   = t.get("duration", t.get("duration_to", 0)) or 0
        if dur_raw:
            h, m = divmod(int(dur_raw), 60)
            dur_str = f"{h}h {m:02d}m" if h else f"{m}m"
        else:
            dur_str = "—"

        table.add_row(
            str(i),
            fmt_price(price, currency),
            airline,
            depart,
            ret if ret and ret != "—" else "[dim]—[/dim]",
            dur_str,
            fmt_stops(transfers),
            str(transfers),
        )

    console.print()
    console.print(Align.center(table))
    console.print()
    console.print(f"  [dim]Showing [bold]{len(tickets)}[/bold] fares. "
                  "Prices are cached from the last 48 hours of user searches.[/dim]\n")


def print_calendar(tickets: list[dict], currency: str, origin: str,
                   destination: str, month: str):
    """Print a mini day-price calendar view."""
    if not tickets:
        console.print("[yellow]  No calendar data found for that month.[/yellow]")
        return

    tickets = sorted(tickets, key=lambda t: t.get("departure_at", ""))
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        title=f"[bold cyan]{origin} -> {destination}[/bold cyan]  [dim]{month} prices[/dim]",
        title_style="bold",
    )
    table.add_column("Date",        style="cyan",       width=14)
    table.add_column("Price",       style="bold green", min_width=12)
    table.add_column("Airline",     style="bold",       width=8)
    table.add_column("Stops",       min_width=10)
    table.add_column("Duration",    style="yellow",     width=10)

    min_price = min(float(t.get("price", 9999)) for t in tickets)

    for t in tickets:
        price     = float(t.get("price", 0))
        airline   = t.get("airline", "—")
        depart    = fmt_date(t.get("departure_at", ""))
        transfers = t.get("transfers", 0)
        dur_raw   = t.get("duration", 0) or 0
        h, m      = divmod(int(dur_raw), 60)
        dur_str   = f"{h}h {m:02d}m" if h else ("—" if not dur_raw else f"{m}m")

        # Highlight cheapest
        price_str = f"[bold green]{currency} {price:,.0f}[/bold green]"
        if price == min_price:
            price_str += " [bold yellow]<-- cheapest[/bold yellow]"

        table.add_row(depart, price_str, airline, fmt_stops(transfers), dur_str)

    console.print()
    console.print(Align.center(table))
    console.print()


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command()
def search(
    from_airport: Optional[str] = typer.Option(None, "--from", "-f",
        help="Origin IATA code (e.g. JFK)"),
    to_airport:   Optional[str] = typer.Option(None, "--to",   "-t",
        help="Destination IATA code (e.g. LHR)"),
    date:         Optional[str] = typer.Option(None, "--date", "-d",
        help="Month to search (YYYY-MM). Leave blank for any month."),
    return_date:  Optional[str] = typer.Option(None, "--return", "-r",
        help="Return month for round-trip (YYYY-MM)."),
    trip:         str           = typer.Option("one-way",  "--trip",
        help="one-way / round-trip"),
    currency:     str           = typer.Option(None, "--currency", "-c",
        help=f"Currency code (USD, EUR, GBP, DKK…). Default: {DEFAULT_CURRENCY} (set TRAVELPAYOUTS_CURRENCY in .env to change)."),
    interactive:  bool          = typer.Option(False, "--interactive", "-i",
        is_flag=True, help="Guided prompt mode"),
):
    """
    [bold cyan]Search cheapest flights via Travelpayouts (100% free, no credit card).[/bold cyan]

    Shows the cheapest fares found in the last 48 hours for a given route.
    Dates use YYYY-MM format (month-level granularity).

    [dim]Examples:[/dim]

      [green]python main.py search --from JFK --to LHR --date 2026-09[/green]

      [green]python main.py search --from BOM --to DEL --date 2026-10 --currency INR[/green]

      [green]python main.py search -i[/green]
    """
    print_banner()
    currency = (currency or DEFAULT_CURRENCY).strip().upper()

    # ── Interactive ───────────────────────────────────────────────────────────
    if interactive or not from_airport:
        console.print("[bold]  Let's find your flight![/bold]\n")
        from_airport = (Prompt.ask("  [cyan]From[/cyan] airport (IATA)", default=from_airport or "")).upper()
        to_airport   = (Prompt.ask("  [cyan]To[/cyan] airport (IATA)",   default=to_airport   or "")).upper()
        default_month = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m")
        date = Prompt.ask(
            "  [cyan]Month[/cyan] (YYYY-MM, or leave blank for any)",
            default=date or default_month,
        )
        trip = Prompt.ask("  [cyan]Trip type[/cyan]", choices=TRIP_CHOICES, default=trip)
        if trip == "round-trip":
            default_ret = (datetime.date.today() + datetime.timedelta(days=37)).strftime("%Y-%m")
            return_date = Prompt.ask(
                "  [cyan]Return month[/cyan] (YYYY-MM)",
                default=return_date or default_ret,
            )
        currency = Prompt.ask("  [cyan]Currency[/cyan]", default=currency or DEFAULT_CURRENCY)
        console.print()

    # ── Validate ──────────────────────────────────────────────────────────────
    if not from_airport or not to_airport:
        console.print("[bold red]  Provide --from and --to (or use -i for interactive).[/bold red]")
        raise typer.Exit(1)

    from_airport = from_airport.strip().upper()
    to_airport   = to_airport.strip().upper()

    token = get_token()

    console.print(
        Panel(
            f"[bold]{from_airport}[/bold] [cyan]->[/cyan] [bold]{to_airport}[/bold]"
            + (f" [cyan]->[/cyan] [bold]{from_airport}[/bold]" if trip == "round-trip" else "")
            + (f"   [dim]{date}[/dim]" if date else "  [dim]any month[/dim]"),
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()

    with Live(
        Spinner("dots", text="  Fetching from Travelpayouts…", style="cyan"),
        refresh_per_second=10,
        console=console,
        transient=True,
    ):
        try:
            tickets = fetch_cheap(
                token,
                origin=from_airport,
                destination=to_airport,
                depart_date=date or None,
                return_date=return_date if trip == "round-trip" else None,
                currency=currency,
            )
        except requests.HTTPError as e:
            console.print(f"\n[bold red]  HTTP error:[/bold red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[bold red]  Error:[/bold red] {e}")
            raise typer.Exit(1)

    print_results_table(tickets, currency, from_airport, to_airport)


@app.command()
def calendar(
    from_airport: str           = typer.Argument(..., help="Origin IATA code (e.g. JFK)"),
    to_airport:   str           = typer.Argument(..., help="Destination IATA code (e.g. LHR)"),
    month:        Optional[str] = typer.Option(None, "--month", "-m",
        help="Month to view (YYYY-MM). Defaults to next month."),
    currency:     str           = typer.Option(None, "--currency", "-c",
        help=f"Currency code. Default: {DEFAULT_CURRENCY} (set TRAVELPAYOUTS_CURRENCY in .env to change)."),
):
    """
    Show cheapest price for each day in a month (calendar view).

    [dim]Example:[/dim]

      [green]python main.py calendar JFK LHR --month 2026-09[/green]
    """
    print_banner()
    currency = (currency or DEFAULT_CURRENCY).strip().upper()

    token = get_token()
    month = month or (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m")
    from_airport = from_airport.upper()
    to_airport   = to_airport.upper()

    console.print(f"  [dim]Loading calendar for [bold]{from_airport} -> {to_airport}[/bold] in [bold]{month}[/bold]...[/dim]\n")

    with Live(
        Spinner("dots", text="  Fetching calendar…", style="cyan"),
        refresh_per_second=10,
        console=console,
        transient=True,
    ):
        try:
            tickets = fetch_month_matrix(token, from_airport, to_airport, month, currency)
        except Exception as e:
            console.print(f"\n[bold red]  Error:[/bold red] {e}")
            raise typer.Exit(1)

    print_calendar(tickets, currency, from_airport, to_airport, month)


@app.command()
def currencies():
    """List all supported currency codes."""
    print_banner()

    table = Table(
        title="Supported Currencies",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
        title_style="bold cyan",
    )
    table.add_column("Code",     style="bold yellow", width=6)
    table.add_column("Currency", style="white")
    table.add_column("Symbol",   style="bold green",  width=6)
    table.add_column("Default",  style="dim",         width=8)

    for code, name, symbol in SUPPORTED_CURRENCIES:
        is_default = "[bold cyan]✓ default[/bold cyan]" if code == DEFAULT_CURRENCY else ""
        table.add_row(code, name, symbol, is_default)

    console.print(Align.center(table))
    console.print(
        f"\n  [dim]Current default: [bold cyan]{DEFAULT_CURRENCY}[/bold cyan]. "
        "To change, add [bold]TRAVELPAYOUTS_CURRENCY=DKK[/bold] (or any code) to your [bold].env[/bold] file.[/dim]\n"
    )


@app.command()
def airports():
    """Show common airport IATA codes for quick reference."""
    print_banner()

    table = Table(
        title="Common Airport Codes",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
        title_style="bold cyan",
    )
    table.add_column("Code",          style="bold yellow", width=6)
    table.add_column("Airport",       style="white")
    table.add_column("City/Country",  style="dim")

    COMMON = [
        ("JFK", "John F. Kennedy International",     "New York, USA"),
        ("LAX", "Los Angeles International",          "Los Angeles, USA"),
        ("ORD", "O'Hare International",               "Chicago, USA"),
        ("LHR", "Heathrow",                           "London, UK"),
        ("CDG", "Charles de Gaulle",                  "Paris, France"),
        ("FRA", "Frankfurt Airport",                  "Frankfurt, Germany"),
        ("AMS", "Amsterdam Airport Schiphol",         "Amsterdam, Netherlands"),
        ("DXB", "Dubai International",                "Dubai, UAE"),
        ("SIN", "Singapore Changi",                   "Singapore"),
        ("HKG", "Hong Kong International",            "Hong Kong"),
        ("NRT", "Narita International",               "Tokyo, Japan"),
        ("SYD", "Sydney Kingsford Smith",             "Sydney, Australia"),
        ("BOM", "Chhatrapati Shivaji Maharaj Intl",   "Mumbai, India"),
        ("DEL", "Indira Gandhi International",        "Delhi, India"),
        ("GRU", "Sao Paulo-Guarulhos",                "Sao Paulo, Brazil"),
        ("ICN", "Incheon International",              "Seoul, South Korea"),
        ("PEK", "Beijing Capital",                    "Beijing, China"),
        ("YYZ", "Toronto Pearson",                    "Toronto, Canada"),
        ("MEX", "Mexico City International",          "Mexico City, Mexico"),
        ("CPT", "Cape Town International",            "Cape Town, South Africa"),
    ]

    for code, name, city in COMMON:
        table.add_row(code, name, city)

    console.print(Align.center(table))
    console.print("\n  [dim]Use any IATA code with [bold]search[/bold] or [bold]calendar[/bold].[/dim]\n")


if __name__ == "__main__":
    app()
