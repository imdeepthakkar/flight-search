# Design Specification: Live Flight Search Integration

**Date:** 2026-09-30  
**Status:** Approved  
**Topic:** Real-Time Live Flight Search with Automatic Fallback  

---

## 1. Overview & Goals

Currently, the `flight-search` CLI relies exclusively on the Travelpayouts Free Data API, which serves cached fare searches recorded over the preceding 48 hours. While fast and free, it cannot search arbitrary exact dates or guarantee real-time seat availability.

This feature introduces a **live search engine** with dual provider support (Google Flights zero-config engine and official Amadeus GDS API), coupled with an **automatic fallback mechanism** to Travelpayouts cached data.

### Success Criteria
- Support live searches for exact dates (`YYYY-MM-DD`) and month-level estimates (`YYYY-MM`).
- Default to live search automatically across CLI commands and MCP server tools.
- Zero-config live search out of the box using Google Flights (handling EU/EEA GDPR consent automatically).
- Seamless opt-in to Amadeus API if credentials (`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`) are present in `.env`.
- Graceful, automatic fallback to Travelpayouts cached API if live queries fail, timeout, or hit rate limits.
- Clear visual indication in the terminal (`[LIVE]` vs `[CACHED]`).

---

## 2. Architecture & Modules

```
                    ┌─────────────────────────┐
                    │  CLI (main.py) / MCP    │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │     live_search.py      │
                    │  (Unified Orchestrator) │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   Amadeus GDS     │ │   Google Flights  │ │   Travelpayouts   │
│   (if in .env)    │ │   (Live Default)  │ │ (Cached Fallback) │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

### 2.1 Unified Data Model (`live_search.py`)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class UnifiedFlight:
    airline: str
    flight_number: str
    price: float
    currency: str
    depart_at: str          # e.g. "2026-12-16 14:05"
    return_at: Optional[str] # e.g. "2027-01-07 21:40"
    duration: str           # e.g. "12h 45m"
    stops: int              # 0, 1, 2...
    layovers: list[str]     # e.g. ["IST"]
    source: str             # "Google Flights (Live)" | "Amadeus (Live)" | "Travelpayouts (Cached)"
    booking_url: Optional[str] = None
```

### 2.2 Orchestration Logic

```python
def search_flights(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: Optional[str] = None,
    trip_type: str = "one-way",
    currency: str = "DKK",
    source: str = "auto",  # "auto" | "live" | "cached"
) -> tuple[list[UnifiedFlight], str]:
    """
    Coordinates flight searches according to the configured source:
    1. If source in ("auto", "live"):
       a. If AMADEUS credentials configured -> query Amadeus live.
       b. Otherwise -> query Google Flights live.
       c. If live search succeeds -> return (flights, live_provider_name).
       d. If live search fails and source == "auto" -> fallback to step 2.
    2. If source in ("auto", "cached") or fallback triggered:
       Query Travelpayouts cached API -> return (flights, "Travelpayouts (Cached)").
    """
```

---

## 3. Provider Implementations

### 3.1 Google Flights Engine (`GoogleFlightsProvider`)
- Utilizes `primp` client with browser fingerprinting.
- Automatically injects consent cookie (`SOCS=CAISHAgBEhJnd3NfMjAyNDA5MjQtMF9SQzIaAmVuIAEaBgiA_L22Bg`) to bypass European GDPR redirection (`consent.google.com`).
- Builds protobuf query parameters via `fast_flights` and parses the `ds:1` payload.
- Extracts airline names, prices, durations, stops, and layover airport codes.

### 3.2 Amadeus GDS Provider (`AmadeusProvider`)
- Checks for `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` in `.env`.
- Authenticates via OAuth2 token endpoint.
- Queries `v2/shopping/flight-offers` with exact origin, destination, departure date, return date, and currency.
- Parses itinerary segments into `UnifiedFlight` instances.

### 3.3 Travelpayouts Fallback Provider (`TravelpayoutsProvider`)
- Wraps existing `fetch_cheap` and `fetch_latest` functions.
- Formats results into `UnifiedFlight` objects so downstream tables and MCP tools consume a uniform interface.

---

## 4. User Interface & CLI Updates (`main.py`)

### 4.1 CLI Arguments
- `--depart` / `-d`: Exact date `YYYY-MM-DD` or month `YYYY-MM`.
- `--return` / `-r`: Return date `YYYY-MM-DD` or month `YYYY-MM`.
- `--source` / `-s`: `auto` (default), `live`, or `cached`.
- Deprecate `--date` as an alias to `--depart` for backward compatibility.

### 4.2 Terminal Output
- Table header reflects the data source:
  - `🟢 LIVE FARES (Google Flights)` or `🟢 LIVE FARES (Amadeus)`
  - `🟡 CACHED FARES (Travelpayouts - past 48h)` (with explanatory tip if fallen back)
- Table displays: `#`, `Price`, `Airline`, `Depart`, `Return`, `Duration`, `Stops / Layovers`.

---

## 5. MCP Server Updates (`mcp_server.py`)

- Update `search_flights` tool in `mcp_server.py` to call `search_flights(..., source="auto")`.
- Expose clear indications of whether returned results are live or cached.

---

## 6. Error Handling & Edge Cases

1. **No Live Availability on Specific Date:**
   - Detect empty result sets and report cleanly; if `--source auto`, check cached database for nearby alternatives.
2. **Network / Scraper Failure:**
   - Log warning and gracefully fall back to cache when `source="auto"`.
3. **Currency Conversion:**
   - Google Flights and Amadeus both accept standard ISO currency codes (`DKK`, `EUR`, `USD`, `INR`).
4. **GDPR / Region Redirection:**
   - Handled via persistent `SOCS` header in the request pipeline.

---

## 7. Testing & Verification

1. **Unit Tests (`tests/test_live_search.py`):**
   - Test `GoogleFlightsProvider` for one-way and round-trip queries.
   - Test `AmadeusProvider` authentication and mock/live calls.
   - Test `search_flights` fallback logic when live queries fail.
2. **Integration Verification:**
   - Run live CLI search: `python main.py search --from CPH --to BOM --depart 2026-12-16 --return 2027-01-07 --currency DKK`.
   - Verify table output and source indicator.
   - Run fallback test with simulated offline live provider to verify smooth downgrade to Travelpayouts cache.
