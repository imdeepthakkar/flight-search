"""
live_search.py -- Unified flight search engine supporting Google Flights,
Amadeus GDS, and Travelpayouts cached fallback.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

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
            
        stops = int(ticket.get("_stops_key") or 0)
        
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
            dep_date = getattr(first_seg.departure, "date", None) or [2026, 1, 1]
            dep_time = getattr(first_seg.departure, "time", None) or [0, 0]
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
                try:
                    from fast_flights.exceptions import FlightsNotFound
                    parsed = parse_js(script.text())
                    return self._convert_result(parsed, currency)
                except (FlightsNotFound, Exception):
                    return []
                
        return []


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



