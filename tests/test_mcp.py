import unittest
from unittest.mock import patch
from live_search import UnifiedFlight
import mcp_server

class TestMCP(unittest.TestCase):
    @patch("mcp_server.run_live_search")
    def test_mcp_server_search_flights_returns_structured_dicts(self, mock_search):
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
        flights = mcp_server.search_flights(
            origin="CPH",
            destination="BOM",
            depart_date="2026-12-16",
            return_date="2027-01-07",
            currency="DKK",
        )
        mock_search.assert_called_once_with(
            origin="CPH",
            destination="BOM",
            depart_date="2026-12-16",
            return_date="2027-01-07",
            trip_type="round-trip",
            currency="DKK",
            source="auto",
        )
        self.assertIsInstance(flights, list)
        self.assertEqual(len(flights), 1)
        flight_dict = flights[0]
        self.assertIsInstance(flight_dict, dict)
        self.assertEqual(flight_dict["airline"], "Emirates")
        self.assertEqual(flight_dict["flight_number"], "EK152")
        self.assertEqual(flight_dict["price"], 5500.0)
        self.assertEqual(flight_dict["currency"], "DKK")
        self.assertEqual(flight_dict["stops"], 1)
        self.assertEqual(flight_dict["layovers"], ["DXB"])
        self.assertEqual(flight_dict["source"], "Google Flights (Live)")

    @patch("mcp_server.run_live_search")
    def test_mcp_server_search_flights_city_resolution_and_month(self, mock_search):
        mock_search.return_value = ([], "Travelpayouts (Cached)")
        flights = mcp_server.search_flights(
            origin="Copenhagen",
            destination="Mumbai",
            month="2026-12",
            return_month="2027-01",
        )
        mock_search.assert_called_once_with(
            origin="CPH",
            destination="BOM",
            depart_date="2026-12",
            return_date="2027-01",
            trip_type="round-trip",
            currency="DKK",
            source="auto",
        )
        self.assertEqual(flights, [])

    def test_mcp_server_search_flights_invalid_airport(self):
        with self.assertRaises(ValueError):
            mcp_server.search_flights(
                origin="INVALID_XYZ_AIRPORT",
                destination="BOM",
            )


if __name__ == "__main__":
    unittest.main()
