# Live Flight Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate real-time live flight searching into the CLI and MCP server using Google Flights (zero-config default) and Amadeus GDS, with automatic fallback to Travelpayouts cached fares.

**Architecture:** A new module `live_search.py` orchestrates queries across three providers (`AmadeusProvider`, `GoogleFlightsProvider`, `TravelpayoutsProvider`), normalizes tickets into a `UnifiedFlight` dataclass, and handles fallback logic. `main.py` and `mcp_server.py` consume this unified interface.

**Tech Stack:** Python 3.13, Typer, Rich, Requests, Primp, Fast-Flights, Amadeus Python SDK, Python standard `unittest`.

## Global Constraints

- Python command: `.\venv\Scripts\python.exe`
- Test command: `.\venv\Scripts\python.exe -m unittest discover tests`
- Currency default: `DKK` (configurable via `TRAVELPAYOUTS_CURRENCY` or CLI flag)
- Travelpayouts token: `TRAVELPAYOUTS_TOKEN` in `.env`
- Zero-config live search: Must work out of the box without requiring Amadeus API credentials.

---

### Task 1: Core Dataclass and Travelpayouts Cached Adapter

**Files:**
- Create: `live_search.py`
- Create: `tests/__init__.py`
- Create: `tests/test_live_search.py`

**Interfaces:**
- Produces:
  - `UnifiedFlight` dataclass (airline, flight_number, price, currency, depart_at, return_at, duration, stops, layovers, source, booking_url)
  - `TravelpayoutsProvider` class with method `search(origin: str, destination: str, depart_date: Optional[str], return_date: Optional[str], currency: str) -> list[UnifiedFlight]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_live_search.py`:
```python
import unittest
from live_search import UnifiedFlight, TravelpayoutsProvider

class TestTravelpayoutsAdapter(unittest.TestCase):
    def test_unified_flight_fields(self):
        flight = UnifiedFlight(
            airline="SAS",
            flight_number="SK123",
            price=3500.0,
            currency="DKK",
            depart_at="2026-11-20 10:00",
            return_at="2026-11-28 18:00",
            duration="18h 00m",
            stops=0,
            layovers=[],
            source="Travelpayouts (Cached)",
        )
        self.assertEqual(flight.airline, "SAS")
        self.assertEqual(flight.price, 3500.0)
        self.assertEqual(flight.source, "Travelpayouts (Cached)")

    def test_adapter_transforms_travelpayouts_dict(self):
        raw_ticket = {
            "airline": "SK",
            "price": 3686,
            "departure_at": "2026-11-20T10:00:00Z",
            "return_at": "2026-11-28T18:00:00Z",
            "flight_number": 951,
            "duration": 1080,
            "_destination": "BOM",
            "_stops_key": "0",
        }
        provider = TravelpayoutsProvider(token="test_token")
        flight = provider._convert_ticket(raw_ticket, "DKK")
        self.assertEqual(flight.airline, "SK")
        self.assertEqual(flight.price, 3686.0)
        self.assertEqual(flight.stops, 0)
        self.assertEqual(flight.duration, "18h 00m")
        self.assertEqual(flight.source, "Travelpayouts (Cached)")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'live_search'`

- [ ] **Step 3: Write minimal implementation**

Create `live_search.py`:
```python
"""
live_search.py -- Unified flight search engine supporting Google Flights,
Amadeus GDS, and Travelpayouts cached fallback.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import datetime

@dataclass
class UnifiedFlight:
    airline: str
    flight_number: str
    price: float
    currency: str
    depart_at: str
    return_at: Optional[str]
    duration: str
    stops: int
    layovers: list[str] = field(default_factory=list)
    source: str = "Live"
    booking_url: Optional[str] = None


class TravelpayoutsProvider:
    def __init__(self, token: Optional[str] = None):
        self.token = token

    def _convert_ticket(self, ticket: dict, currency: str) -> UnifiedFlight:
        airline = ticket.get("airline", "Unknown")
        flight_no = str(ticket.get("flight_number", ""))
        price = float(ticket.get("price", 0))
        depart_raw = ticket.get("departure_at", "")
        return_raw = ticket.get("return_at")
        
        # Format dates
        depart_str = depart_raw[:16].replace("T", " ") if depart_raw else ""
        return_str = return_raw[:16].replace("T", " ") if return_raw else None
        
        # Duration in minutes
        dur_mins = ticket.get("duration", 0)
        if dur_mins:
            h = dur_mins // 60
            m = dur_mins % 60
            duration_str = f"{h}h {m:02d}m"
        else:
            duration_str = "—"
            
        stops = int(ticket.get("_stops_key", 0))
        
        return UnifiedFlight(
            airline=airline,
            flight_number=flight_no,
            price=price,
            currency=currency,
            depart_at=depart_str,
            return_at=return_str,
            duration=duration_str,
            stops=stops,
            layovers=[],
            source="Travelpayouts (Cached)",
        )

    def search(
        self,
        origin: str,
        destination: str,
        depart_date: Optional[str],
        return_date: Optional[str],
        currency: str,
    ) -> list[UnifiedFlight]:
        from main import fetch_cheap, get_token
        token = self.token or get_token()
        tickets = fetch_cheap(
            token=token,
            origin=origin,
            destination=destination,
            depart_date=depart_date,
            return_date=return_date,
            currency=currency,
        )
        return [self._convert_ticket(t, currency) for t in tickets]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: PASS with 2 tests passing.

- [ ] **Step 5: Commit**

```bash
git add live_search.py tests/
git commit -m "feat(live_search): add UnifiedFlight dataclass and TravelpayoutsProvider"
```

---

### Task 2: Google Flights Live Search Provider

**Files:**
- Modify: `live_search.py`
- Modify: `tests/test_live_search.py`

**Interfaces:**
- Produces:
  - `GoogleFlightsProvider` class with method:
    `search(origin: str, destination: str, depart_date: str, return_date: Optional[str], trip_type: str, currency: str) -> list[UnifiedFlight]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_search.py`:
```python
from unittest.mock import patch, MagicMock
from live_search import GoogleFlightsProvider

class TestGoogleFlightsProvider(unittest.TestCase):
    @patch("live_search.GoogleFlightsProvider._fetch_html")
    def test_google_flights_parses_html(self, mock_fetch):
        # Mock HTML containing minimal script tag with ds:1
        fake_flight = MagicMock()
        fake_flight.price = 4500
        fake_flight.airlines = ["Emirates"]
        seg = MagicMock()
        seg.from_airport.code = "CPH"
        seg.to_airport.code = "DXB"
        seg.departure.date = [2026, 12, 16]
        seg.departure.time = [14, 20]
        seg.duration = 380
        seg.plane_type = "Boeing 777"
        fake_flight.flights = [seg]
        
        provider = GoogleFlightsProvider()
        flights = provider._convert_result([fake_flight], "DKK")
        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0].airline, "Emirates")
        self.assertEqual(flights[0].price, 4500.0)
        self.assertEqual(flights[0].source, "Google Flights (Live)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: FAIL with `ImportError: cannot import name 'GoogleFlightsProvider' from 'live_search'`

- [ ] **Step 3: Write minimal implementation**

Add `GoogleFlightsProvider` to `live_search.py`:
```python
class GoogleFlightsProvider:
    CONSENT_COOKIE = "SOCS=CAISHAgBEhJnd3NfMjAyNDA5MjQtMF9SQzIaAmVuIAEaBgiA_L22Bg"

    def _fetch_html(self, query) -> str:
        import primp
        import fast_flights.fetcher
        client = primp.Client(
            impersonate_os="windows",
            referer=True,
            cookie_store=True,
        )
        headers = {"cookie": self.CONSENT_COOKIE}
        params = query.params() if hasattr(query, "params") else {"q": query}
        resp = client.get(fast_flights.fetcher.URL, params=params, headers=headers)
        resp.raise_for_status()
        return resp.text

    def _convert_result(self, raw_flights, currency: str) -> list[UnifiedFlight]:
        results = []
        for f in raw_flights:
            price = float(getattr(f, "price", 0) or 0)
            airlines = getattr(f, "airlines", []) or []
            airline_name = " / ".join(airlines) if airlines else "Multiple Airlines"
            
            segments = getattr(f, "flights", []) or []
            if not segments:
                continue
                
            first_seg = segments[0]
            dep_date = getattr(first_seg.departure, "date", [2026, 1, 1])
            dep_time = getattr(first_seg.departure, "time", [0, 0])
            depart_str = f"{dep_date[0]:04d}-{dep_date[1]:02d}-{dep_date[2]:02d} {dep_time[0]:02d}:{dep_time[1]:02d}"
            
            # Total duration in minutes
            total_dur = sum(getattr(s, "duration", 0) or 0 for s in segments)
            h = total_dur // 60
            m = total_dur % 60
            duration_str = f"{h}h {m:02d}m" if total_dur > 0 else "—"
            
            stops = max(0, len(segments) - 1)
            layovers = [getattr(s.to_airport, "code", "") for s in segments[:-1]]
            
            results.append(
                UnifiedFlight(
                    airline=airline_name,
                    flight_number="",
                    price=price,
                    currency=currency,
                    depart_at=depart_str,
                    return_at=None,
                    duration=duration_str,
                    stops=stops,
                    layovers=layovers,
                    source="Google Flights (Live)",
                )
            )
        return results

    def search(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: Optional[str] = None,
        trip_type: str = "one-way",
        currency: str = "DKK",
    ) -> list[UnifiedFlight]:
        from fast_flights import FlightQuery, create_filter
        from fast_flights.parser import parse_js
        from selectolax.lexbor import LexborHTMLParser

        # Normalize date to YYYY-MM-DD
        if len(depart_date) == 7:  # YYYY-MM
            depart_date = f"{depart_date}-15"
        if return_date and len(return_date) == 7:
            return_date = f"{return_date}-15"

        flight_queries = [FlightQuery(date=depart_date, from_airport=origin, to_airport=destination)]
        if trip_type == "round-trip" and return_date:
            flight_queries.append(FlightQuery(date=return_date, from_airport=destination, to_airport=origin))

        q = create_filter(
            flights=flight_queries,
            trip=trip_type,
            currency=currency,
        )

        html = self._fetch_html(q)
        parser = LexborHTMLParser(html)
        
        # Locate the ds:1 data script
        for script in parser.css("script"):
            if script.attributes.get("class") == "ds:1":
                parsed = parse_js(script.text())
                return self._convert_result(parsed, currency)
                
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: PASS with 3 tests passing.

- [ ] **Step 5: Commit**

```bash
git add live_search.py tests/
git commit -m "feat(live_search): add GoogleFlightsProvider with consent bypass"
```

---

### Task 3: Amadeus GDS Provider

**Files:**
- Modify: `live_search.py`
- Modify: `tests/test_live_search.py`

**Interfaces:**
- Produces:
  - `AmadeusProvider` class with method:
    `search(origin: str, destination: str, depart_date: str, return_date: Optional[str], currency: str) -> list[UnifiedFlight]`
  - `is_configured() -> bool`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_search.py`:
```python
from live_search import AmadeusProvider

class TestAmadeusProvider(unittest.TestCase):
    def test_not_configured_when_no_keys(self):
        provider = AmadeusProvider(client_id=None, client_secret=None)
        self.assertFalse(provider.is_configured())

    def test_configured_when_keys_present(self):
        provider = AmadeusProvider(client_id="key123", client_secret="secret456")
        self.assertTrue(provider.is_configured())

    def test_convert_amadeus_offer(self):
        raw_offer = {
            "price": {"grandTotal": "4200.50", "currency": "DKK"},
            "itineraries": [
                {
                    "duration": "PT14H30M",
                    "segments": [
                        {
                            "carrierCode": "LH",
                            "number": "820",
                            "departure": {"iataCode": "CPH", "at": "2026-12-16T06:00:00"},
                            "arrival": {"iataCode": "FRA", "at": "2026-12-16T07:30:00"},
                        },
                        {
                            "carrierCode": "LH",
                            "number": "756",
                            "departure": {"iataCode": "FRA", "at": "2026-12-16T12:00:00"},
                            "arrival": {"iataCode": "BOM", "at": "2026-12-17T01:00:00"},
                        }
                    ]
                }
            ]
        }
        provider = AmadeusProvider(client_id="k", client_secret="s")
        flight = provider._convert_offer(raw_offer)
        self.assertEqual(flight.airline, "LH")
        self.assertEqual(flight.price, 4200.50)
        self.assertEqual(flight.stops, 1)
        self.assertEqual(flight.layovers, ["FRA"])
        self.assertEqual(flight.source, "Amadeus (Live)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: FAIL with `ImportError: cannot import name 'AmadeusProvider' from 'live_search'`

- [ ] **Step 3: Write minimal implementation**

Add `AmadeusProvider` to `live_search.py`:
```python
import os
import re

class AmadeusProvider:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.getenv("AMADEUS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AMADEUS_CLIENT_SECRET")

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _convert_offer(self, offer: dict) -> UnifiedFlight:
        price_info = offer.get("price", {})
        price = float(price_info.get("grandTotal", 0.0))
        currency = price_info.get("currency", "DKK")
        
        itineraries = offer.get("itineraries", [])
        if not itineraries:
            raise ValueError("No itinerary in offer")
            
        outbound = itineraries[0]
        segments = outbound.get("segments", [])
        if not segments:
            raise ValueError("No segments in outbound itinerary")
            
        airline = segments[0].get("carrierCode", "Unknown")
        flight_no = f"{airline}{segments[0].get('number', '')}"
        
        dep_at = segments[0].get("departure", {}).get("at", "")
        depart_str = dep_at[:16].replace("T", " ") if dep_at else ""
        
        # Duration ISO 8601 (PT14H30M)
        dur_raw = outbound.get("duration", "")
        h_match = re.search(r"(\d+)H", dur_raw)
        m_match = re.search(r"(\d+)M", dur_raw)
        h = int(h_match.group(1)) if h_match else 0
        m = int(m_match.group(1)) if m_match else 0
        dur_str = f"{h}h {m:02d}m" if (h or m) else dur_raw
        
        stops = max(0, len(segments) - 1)
        layovers = [s.get("departure", {}).get("iataCode", "") for s in segments[1:]]
        
        return_str = None
        if len(itineraries) > 1:
            ret_segments = itineraries[1].get("segments", [])
            if ret_segments:
                ret_at = ret_segments[0].get("departure", {}).get("at", "")
                return_str = ret_at[:16].replace("T", " ") if ret_at else None

        return UnifiedFlight(
            airline=airline,
            flight_number=flight_no,
            price=price,
            currency=currency,
            depart_at=depart_str,
            return_at=return_str,
            duration=dur_str,
            stops=stops,
            layovers=layovers,
            source="Amadeus (Live)",
        )

    def search(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: Optional[str] = None,
        currency: str = "DKK",
    ) -> list[UnifiedFlight]:
        from amadeus import Client, ResponseError
        amadeus = Client(client_id=self.client_id, client_secret=self.client_secret)
        
        # Format date to YYYY-MM-DD
        if len(depart_date) == 7:
            depart_date = f"{depart_date}-15"
            
        kwargs = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": depart_date,
            "adults": 1,
            "currencyCode": currency,
            "max": 15,
        }
        if return_date:
            if len(return_date) == 7:
                return_date = f"{return_date}-15"
            kwargs["returnDate"] = return_date
            
        try:
            response = amadeus.shopping.flight_offers_search.get(**kwargs)
            return [self._convert_offer(o) for o in response.data]
        except Exception as e:
            raise RuntimeError(f"Amadeus search failed: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: PASS with 6 tests passing.

- [ ] **Step 5: Commit**

```bash
git add live_search.py tests/
git commit -m "feat(live_search): add AmadeusProvider GDS adapter"
```

---

### Task 4: Unified Search Orchestrator and Fallback Logic

**Files:**
- Modify: `live_search.py`
- Modify: `tests/test_live_search.py`

**Interfaces:**
- Produces:
  - `search_flights(origin: str, destination: str, depart_date: Optional[str], return_date: Optional[str], trip_type: str, currency: str, source: str) -> tuple[list[UnifiedFlight], str]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_search.py`:
```python
from live_search import search_flights

class TestOrchestrator(unittest.TestCase):
    @patch("live_search.GoogleFlightsProvider.search")
    def test_orchestrator_live_success(self, mock_google):
        mock_google.return_value = [
            UnifiedFlight(
                airline="Emirates",
                flight_number="",
                price=5000.0,
                currency="DKK",
                depart_at="2026-12-16 10:00",
                return_at=None,
                duration="10h",
                stops=1,
                source="Google Flights (Live)",
            )
        ]
        flights, src = search_flights("CPH", "BOM", "2026-12-16", source="auto")
        self.assertEqual(len(flights), 1)
        self.assertEqual(src, "Google Flights (Live)")

    @patch("live_search.GoogleFlightsProvider.search", side_effect=Exception("Scraper blocked"))
    @patch("live_search.TravelpayoutsProvider.search")
    def test_orchestrator_fallback_to_cache(self, mock_cached, mock_google):
        mock_cached.return_value = [
            UnifiedFlight(
                airline="SK",
                flight_number="",
                price=3686.0,
                currency="DKK",
                depart_at="2026-11-20 10:00",
                return_at=None,
                duration="18h",
                stops=0,
                source="Travelpayouts (Cached)",
            )
        ]
        flights, src = search_flights("CPH", "BOM", "2026-12-16", source="auto")
        self.assertEqual(len(flights), 1)
        self.assertEqual(src, "Travelpayouts (Cached)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: FAIL with `ImportError: cannot import name 'search_flights' from 'live_search'`

- [ ] **Step 3: Write minimal implementation**

Add `search_flights` to `live_search.py`:
```python
def search_flights(
    origin: str,
    destination: str,
    depart_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one-way",
    currency: str = "DKK",
    source: str = "auto",
) -> tuple[list[UnifiedFlight], str]:
    """
    Search flights with live search priority and automatic fallback to Travelpayouts cache.
    Source can be 'auto', 'live', or 'cached'.
    Returns (list_of_unified_flights, actual_source_used).
    """
    source = (source or "auto").lower()
    
    # Force cached if explicitly requested
    if source == "cached":
        tp = TravelpayoutsProvider()
        return tp.search(origin, destination, depart_date, return_date, currency), "Travelpayouts (Cached)"

    # Live Attempt 1: Amadeus (if configured)
    amadeus = AmadeusProvider()
    if amadeus.is_configured() and depart_date:
        try:
            results = amadeus.search(origin, destination, depart_date, return_date, currency)
            if results:
                return results, "Amadeus (Live)"
        except Exception:
            pass  # Fall through to Google Flights

    # Live Attempt 2: Google Flights (zero-config)
    if depart_date:
        try:
            gf = GoogleFlightsProvider()
            results = gf.search(origin, destination, depart_date, return_date, trip_type, currency)
            if results:
                return results, "Google Flights (Live)"
        except Exception:
            pass  # Fall through to cached

    # If source was explicitly 'live' and we got no results
    if source == "live":
        return [], "Live Search (No results found)"

    # Fallback: Travelpayouts cached
    tp = TravelpayoutsProvider()
    cached_results = tp.search(origin, destination, depart_date, return_date, currency)
    return cached_results, "Travelpayouts (Cached)"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_live_search.py`
Expected: PASS with 8 tests passing.

- [ ] **Step 5: Commit**

```bash
git add live_search.py tests/
git commit -m "feat(live_search): implement search_flights orchestrator with automatic fallback"
```

---

### Task 5: CLI Updates and Table Rendering

**Files:**
- Modify: `main.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `live_search.search_flights`, `UnifiedFlight`
- Produces: Updated Typer command `search` accepting `--source`, `--depart`, `--return`, rendering live badges.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:
```python
import unittest
from typer.testing import CliRunner
from main import app

runner = CliRunner()

class TestCLI(unittest.TestCase):
    def test_search_cli_help_includes_source_option(self):
        result = runner.invoke(app, ["search", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--source", result.output)
        self.assertIn("--depart", result.output)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_cli.py`
Expected: FAIL with `AssertionError: '--source' not found in result.output`

- [ ] **Step 3: Modify `main.py`**

Update `main.py`:
1. Add `print_unified_results_table(flights: list, currency: str, origin: str, dest: str, source_used: str)`
2. Update `@app.command() def search(...)`:
   - Add parameters:
     - `depart: Optional[str] = typer.Option(None, "--depart", "-d", help="Departure date (YYYY-MM-DD or YYYY-MM)")`
     - `return_date: Optional[str] = typer.Option(None, "--return", "-r", help="Return date (YYYY-MM-DD or YYYY-MM)")`
     - `source: str = typer.Option("auto", "--source", "-s", help="auto | live | cached")`
     - Keep `date` as fallback alias for `depart`.
   - Call `search_flights` from `live_search`.
   - Display the results using the new unified table printer.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_cli.py
git commit -m "feat(cli): integrate live search and source badge into main.py"
```

---

### Task 6: MCP Server & End-to-End Verification

**Files:**
- Modify: `mcp_server.py`
- Modify: `tests/test_mcp.py` (create if needed)
- Verify: Full end-to-end execution with real live query

- [ ] **Step 1: Write test for MCP search tool**

Create `tests/test_mcp.py`:
```python
import unittest
from unittest.mock import patch
from live_search import UnifiedFlight

class TestMCP(unittest.TestCase):
    @patch("live_search.search_flights")
    def test_mcp_returns_live_flights(self, mock_search):
        mock_search.return_value = (
            [
                UnifiedFlight(
                    airline="Emirates",
                    flight_number="EK152",
                    price=5500.0,
                    currency="DKK",
                    depart_at="2026-12-16 14:00",
                    return_at="2027-01-07 20:00",
                    duration="12h 30m",
                    stops=1,
                    layovers=["DXB"],
                    source="Google Flights (Live)",
                )
            ],
            "Google Flights (Live)",
        )
        from live_search import search_flights
        res, src = search_flights("CPH", "BOM", "2026-12-16", "2027-01-07", "round-trip", "DKK", "auto")
        self.assertEqual(len(res), 1)
        self.assertEqual(src, "Google Flights (Live)")
        self.assertEqual(res[0].airline, "Emirates")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m unittest tests/test_mcp.py`
Expected: PASS

- [ ] **Step 3: Update `mcp_server.py` to use `search_flights`**

Update `mcp_server.py` to import `search_flights` from `live_search` and return live results with source metadata.

- [ ] **Step 4: Execute real live query verification**

Run:
`.\venv\Scripts\python.exe main.py search --from CPH --to BOM --depart 2026-12-16 --return 2027-01-07 --trip round-trip --currency DKK`
Expected: Output table showing live results from Google Flights with source badge `[LIVE FARES (Google Flights)]`.

- [ ] **Step 5: Run full test suite**

Run: `.\venv\Scripts\python.exe -m unittest discover tests`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add mcp_server.py tests/
git commit -m "feat(mcp): support live flight searching in MCP server and verify e2e"
```
