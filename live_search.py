"""
live_search.py -- Unified flight search engine supporting Google Flights,
Amadeus GDS, and Travelpayouts cached fallback.
"""

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

