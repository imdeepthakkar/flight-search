import unittest
from unittest.mock import patch, MagicMock
from live_search import UnifiedFlight, TravelpayoutsProvider, GoogleFlightsProvider, AmadeusProvider, search_flights

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

    @patch("fast_flights.parser.parse_js")
    @patch("live_search.GoogleFlightsProvider._fetch_html")
    def test_search_returns_empty_on_flights_not_found(self, mock_fetch, mock_parse_js):
        from fast_flights.exceptions import FlightsNotFound
        mock_fetch.return_value = '<html><body><script class="ds:1">AF_initDataCallback({});</script></body></html>'
        mock_parse_js.side_effect = FlightsNotFound("No flights found")
        provider = GoogleFlightsProvider()
        flights = provider.search("CPH", "XYZ", "2026-11-15", trip_type="one-way", currency="DKK")
        self.assertEqual(flights, [])

    def test_convert_result_with_none_departure_date_or_time(self):
        fake_flight = MagicMock()
        fake_flight.price = 1000
        fake_flight.airlines = ["SAS"]
        seg = MagicMock()
        seg.departure.date = None
        seg.departure.time = None
        seg.duration = 60
        fake_flight.flights = [seg]

        provider = GoogleFlightsProvider()
        flights = provider._convert_result([fake_flight], "DKK")
        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0].depart_at, "2026-01-01 00:00")


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

    @patch("amadeus.Client")
    def test_search_calls_flight_offers_search(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.data = [
            {
                "price": {"grandTotal": "3000.0", "currency": "DKK"},
                "itineraries": [
                    {
                        "duration": "PT2H00M",
                        "segments": [
                            {
                                "carrierCode": "SK",
                                "number": "100",
                                "departure": {"iataCode": "CPH", "at": "2026-12-01T10:00:00"},
                                "arrival": {"iataCode": "LHR", "at": "2026-12-01T11:00:00"},
                            }
                        ],
                    }
                ],
            }
        ]
        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        provider = AmadeusProvider(client_id="id", client_secret="sec")
        results = provider.search("CPH", "LHR", "2026-12", return_date="2026-12", currency="DKK")

        mock_client.shopping.flight_offers_search.get.assert_called_once_with(
            originLocationCode="CPH",
            destinationLocationCode="LHR",
            departureDate="2026-12-15",
            adults=1,
            currencyCode="DKK",
            max=15,
            returnDate="2026-12-15",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].airline, "SK")
        self.assertEqual(results[0].flight_number, "SK100")
        self.assertEqual(results[0].price, 3000.0)

    @patch("amadeus.Client")
    def test_search_raises_runtime_error_on_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.shopping.flight_offers_search.get.side_effect = Exception("API rate limit")

        provider = AmadeusProvider(client_id="id", client_secret="sec")
        with self.assertRaises(RuntimeError) as ctx:
            provider.search("CPH", "LHR", "2026-12-01")
        self.assertIn("Amadeus search failed: API rate limit", str(ctx.exception))

    def test_convert_round_trip_offer(self):
        raw_offer = {
            "price": {"grandTotal": "5000", "currency": "EUR"},
            "itineraries": [
                {
                    "duration": "PT8H00M",
                    "segments": [
                        {
                            "carrierCode": "BA",
                            "number": "123",
                            "departure": {"iataCode": "CPH", "at": "2026-12-01T08:00:00"},
                            "arrival": {"iataCode": "LHR", "at": "2026-12-01T09:00:00"},
                        }
                    ],
                },
                {
                    "duration": "PT8H00M",
                    "segments": [
                        {
                            "carrierCode": "BA",
                            "number": "124",
                            "departure": {"iataCode": "LHR", "at": "2026-12-10T14:00:00"},
                            "arrival": {"iataCode": "CPH", "at": "2026-12-10T17:00:00"},
                        }
                    ],
                },
            ],
        }
        provider = AmadeusProvider(client_id="k", client_secret="s")
        flight = provider._convert_offer(raw_offer)
        self.assertEqual(flight.airline, "BA")
        self.assertEqual(flight.currency, "EUR")
        self.assertEqual(flight.depart_at, "2026-12-01 08:00")
        self.assertEqual(flight.return_at, "2026-12-10 14:00")


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

    @patch("live_search.TravelpayoutsProvider.search")
    def test_orchestrator_source_cached(self, mock_cached):
        mock_cached.return_value = [
            UnifiedFlight(
                airline="SK",
                flight_number="",
                price=2000.0,
                currency="DKK",
                depart_at="2026-11-20 10:00",
                return_at=None,
                duration="2h",
                stops=0,
                source="Travelpayouts (Cached)",
            )
        ]
        flights, src = search_flights("CPH", "LHR", "2026-11-20", source="cached")
        self.assertEqual(len(flights), 1)
        self.assertEqual(src, "Travelpayouts (Cached)")
        mock_cached.assert_called_once_with("CPH", "LHR", "2026-11-20", None, "DKK")

    @patch("live_search.GoogleFlightsProvider.search", side_effect=Exception("Timeout"))
    def test_orchestrator_source_live_failure(self, mock_google):
        flights, src = search_flights("CPH", "BOM", "2026-12-16", source="live")
        self.assertEqual(flights, [])
        self.assertEqual(src, "Live Search (No results found)")

    @patch("live_search.AmadeusProvider.is_configured", return_value=True)
    @patch("live_search.AmadeusProvider.search")
    def test_orchestrator_amadeus_priority(self, mock_amadeus_search, mock_is_conf):
        mock_amadeus_search.return_value = [
            UnifiedFlight(
                airline="LH",
                flight_number="LH820",
                price=4000.0,
                currency="DKK",
                depart_at="2026-12-16 06:00",
                return_at=None,
                duration="14h",
                stops=1,
                source="Amadeus (Live)",
            )
        ]
        flights, src = search_flights("CPH", "BOM", "2026-12-16", source="auto")
        self.assertEqual(len(flights), 1)
        self.assertEqual(src, "Amadeus (Live)")
        mock_amadeus_search.assert_called_once_with("CPH", "BOM", "2026-12-16", None, "DKK")

    @patch("live_search.AmadeusProvider.is_configured", return_value=True)
    @patch("live_search.AmadeusProvider.search", side_effect=Exception("API Error"))
    @patch("live_search.GoogleFlightsProvider.search")
    def test_orchestrator_amadeus_failure_falls_to_google(self, mock_google, mock_amadeus_search, mock_is_conf):
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


if __name__ == "__main__":
    unittest.main()



