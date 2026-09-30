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
