import unittest
from unittest.mock import patch, MagicMock
from live_search import UnifiedFlight, TravelpayoutsProvider, GoogleFlightsProvider

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

    def test_google_flights_multi_segment(self):
        fake_flight = MagicMock()
        fake_flight.price = 5200
        fake_flight.airlines = ["Emirates", "flydubai"]
        seg1 = MagicMock()
        seg1.from_airport.code = "CPH"
        seg1.to_airport.code = "DXB"
        seg1.departure.date = [2026, 12, 16]
        seg1.departure.time = [14, 20]
        seg1.duration = 380

        seg2 = MagicMock()
        seg2.from_airport.code = "DXB"
        seg2.to_airport.code = "BOM"
        seg2.departure.date = [2026, 12, 17]
        seg2.departure.time = [2, 10]
        seg2.duration = 190

        fake_flight.flights = [seg1, seg2]

        provider = GoogleFlightsProvider()
        flights = provider._convert_result([fake_flight], "DKK")
        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0].airline, "Emirates / flydubai")
        self.assertEqual(flights[0].stops, 1)
        self.assertEqual(flights[0].layovers, ["DXB"])
        self.assertEqual(flights[0].duration, "9h 30m")

    @patch("fast_flights.parser.parse_js")
    @patch("live_search.GoogleFlightsProvider._fetch_html")
    def test_search_extracts_ds1_script(self, mock_fetch, mock_parse_js):
        mock_fetch.return_value = '<html><body><script class="ds:1">AF_initDataCallback({});</script></body></html>'
        fake_flight = MagicMock()
        fake_flight.price = 3000
        fake_flight.airlines = ["SAS"]
        seg = MagicMock()
        seg.from_airport.code = "CPH"
        seg.to_airport.code = "LHR"
        seg.departure.date = [2026, 11, 15]
        seg.departure.time = [8, 0]
        seg.duration = 120
        fake_flight.flights = [seg]
        mock_parse_js.return_value = [fake_flight]

        provider = GoogleFlightsProvider()
        flights = provider.search("CPH", "LHR", "2026-11", trip_type="one-way", currency="DKK")
        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0].airline, "SAS")
        self.assertEqual(flights[0].price, 3000.0)

    @patch("live_search.GoogleFlightsProvider._fetch_html")
    def test_search_returns_empty_when_no_ds1(self, mock_fetch):
        mock_fetch.return_value = '<html><body><div>No data</div></body></html>'
        provider = GoogleFlightsProvider()
        flights = provider.search("CPH", "LHR", "2026-11-15", trip_type="one-way", currency="DKK")
        self.assertEqual(flights, [])


if __name__ == "__main__":
    unittest.main()

