import unittest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from main import app, print_unified_results_table
from live_search import UnifiedFlight

runner = CliRunner()

class TestCLI(unittest.TestCase):
    def test_search_cli_help_includes_source_option(self):
        result = runner.invoke(app, ["search", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--source", result.output)
        self.assertIn("--depart", result.output)
        self.assertIn("--date", result.output)
        self.assertIn("--return", result.output)

    @patch("main.search_flights")
    @patch("main.resolve_to_iata")
    def test_search_cli_live_source_badge(self, mock_resolve, mock_search):
        mock_resolve.side_effect = lambda code: (code, f"{code} Airport")
        flight = UnifiedFlight(
            airline="SAS",
            flight_number="SK123",
            price=3200.0,
            currency="DKK",
            depart_at="2026-11-20 08:30",
            return_at=None,
            duration="7h 15m",
            stops=0,
            layovers=[],
            source="Google Flights (Live)",
        )
        mock_search.return_value = ([flight], "Google Flights (Live)")

        result = runner.invoke(app, [
            "search",
            "--from", "CPH",
            "--to", "LHR",
            "--depart", "2026-11-20",
            "--source", "live",
        ])

        self.assertEqual(result.exit_code, 0)
        mock_search.assert_called_once_with(
            origin="CPH",
            destination="LHR",
            depart_date="2026-11-20",
            return_date=None,
            trip_type="one-way",
            currency="DKK",
            source="live",
        )
        self.assertIn("LIVE FARES (Google Flights)", result.output)
        self.assertIn("SAS", result.output)
        self.assertIn("3,200", result.output)

    @patch("main.search_flights")
    @patch("main.resolve_to_iata")
    def test_search_cli_cached_source_badge(self, mock_resolve, mock_search):
        mock_resolve.side_effect = lambda code: (code, f"{code} Airport")
        flight = UnifiedFlight(
            airline="BA",
            flight_number="BA811",
            price=2800.0,
            currency="DKK",
            depart_at="2026-11-20",
            return_at=None,
            duration="2h 00m",
            stops=0,
            layovers=[],
            source="Travelpayouts (Cached)",
        )
        mock_search.return_value = ([flight], "Travelpayouts (Cached)")

        result = runner.invoke(app, [
            "search",
            "--from", "CPH",
            "--to", "LHR",
            "--depart", "2026-11-20",
            "--source", "cached",
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("CACHED FARES (Travelpayouts)", result.output)
        self.assertIn("BA", result.output)
        self.assertIn("2,800", result.output)

    @patch("main.search_flights")
    @patch("main.resolve_to_iata")
    def test_search_cli_backward_compatibility_date_flag(self, mock_resolve, mock_search):
        mock_resolve.side_effect = lambda code: (code, f"{code} Airport")
        mock_search.return_value = ([], "Travelpayouts (Cached)")

        result = runner.invoke(app, [
            "search",
            "--from", "JFK",
            "--to", "LHR",
            "--date", "2026-12",
        ])

        self.assertEqual(result.exit_code, 0)
        mock_search.assert_called_once()
        _, kwargs = mock_search.call_args
        self.assertEqual(kwargs["depart_date"], "2026-12")

    @patch("main.search_flights")
    @patch("main.resolve_to_iata")
    def test_search_cli_no_results(self, mock_resolve, mock_search):
        mock_resolve.side_effect = lambda code: (code, f"{code} Airport")
        mock_search.return_value = ([], "Live Search (No results found)")

        result = runner.invoke(app, [
            "search",
            "--from", "CPH",
            "--to", "LHR",
            "--depart", "2026-11-20",
            "--source", "live",
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("No flights found", result.output)

if __name__ == "__main__":
    unittest.main()
