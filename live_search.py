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
