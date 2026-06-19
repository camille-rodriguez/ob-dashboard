"""Tests for the Orangebox Dashboard application."""

import sys
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# network_utils tests
# ---------------------------------------------------------------------------
class TestIsHostReachable(unittest.TestCase):
    def setUp(self):
        # Ensure fresh import for each test
        if "network_utils" in sys.modules:
            del sys.modules["network_utils"]

    def _import(self):
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "network_utils",
            pathlib.Path(__file__).parent.parent / "network_utils.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_returns_true_when_ping_succeeds(self):
        mod = self._import()
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            self.assertTrue(mod.is_host_reachable("10.0.0.1"))

    def test_returns_false_when_ping_fails(self):
        mod = self._import()
        mock_result = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            self.assertFalse(mod.is_host_reachable("10.0.0.1"))

    def test_returns_false_on_timeout(self):
        import subprocess
        mod = self._import()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ping", 2)):
            self.assertFalse(mod.is_host_reachable("10.0.0.1"))

    def test_is_port_open_true(self):
        mod = self._import()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=None)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        with patch("socket.create_connection", return_value=mock_ctx):
            self.assertTrue(mod.is_port_open("10.0.0.1", 5240))

    def test_is_port_open_false(self):
        mod = self._import()
        with patch("socket.create_connection", side_effect=OSError):
            self.assertFalse(mod.is_port_open("10.0.0.1", 9999))


# ---------------------------------------------------------------------------
# maas_client tests
# ---------------------------------------------------------------------------
class TestGetMaasStatus(unittest.TestCase):
    def _import(self):
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "maas_client",
            pathlib.Path(__file__).parent.parent / "maas_client.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_no_url_returns_error(self):
        mod = self._import()
        result = mod.get_maas_status(maas_url="", api_key="")
        self.assertFalse(result["reachable"])
        self.assertIsNotNone(result["error"])

    def test_connection_error(self):
        import requests as req
        mod = self._import()
        with patch("requests.get", side_effect=req.exceptions.ConnectionError("refused")):
            result = mod.get_maas_status(
                maas_url="http://10.0.0.1:5240/MAAS", api_key=""
            )
        self.assertFalse(result["reachable"])
        self.assertIn("Cannot connect", result["error"])

    def test_timeout_error(self):
        import requests as req
        mod = self._import()
        with patch("requests.get", side_effect=req.exceptions.Timeout):
            result = mod.get_maas_status(
                maas_url="http://10.0.0.1:5240/MAAS", api_key=""
            )
        self.assertFalse(result["reachable"])
        self.assertIn("timed out", result["error"])

    def test_successful_response_counts_machines(self):
        mod = self._import()
        machines_json = [
            {"status_name": "Ready"},
            {"status_name": "ready"},
            {"status_name": "Deployed"},
            {"status_name": "Broken"},
            {"status_name": "Commissioning"},  # should be ignored
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = machines_json
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = mod.get_maas_status(
                maas_url="http://10.0.0.1:5240/MAAS", api_key=""
            )
        self.assertTrue(result["reachable"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["machine_counts"]["ready"], 2)
        self.assertEqual(result["machine_counts"]["deployed"], 1)
        self.assertEqual(result["machine_counts"]["broken"], 1)

    def test_http_error_marks_reachable(self):
        import requests as req
        mod = self._import()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("403")
        with patch("requests.get", return_value=mock_resp):
            result = mod.get_maas_status(
                maas_url="http://10.0.0.1:5240/MAAS", api_key=""
            )
        # Server responded → reachable, but error message set
        self.assertTrue(result["reachable"])
        self.assertIsNotNone(result["error"])


# ---------------------------------------------------------------------------
# Flask app tests
# ---------------------------------------------------------------------------
class TestFlaskApp(unittest.TestCase):
    def _make_app(self, powered_on=True, maas_status=None):
        if maas_status is None:
            maas_status = {
                "reachable": True,
                "error": None,
                "machine_counts": {"ready": 3, "deployed": 2, "broken": 0},
            }
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "app",
            pathlib.Path(__file__).parent.parent / "app.py",
        )
        mod = importlib.util.module_from_spec(spec)
        with (
            patch("network_utils.is_host_reachable", return_value=powered_on),
            patch("maas_client.get_maas_status", return_value=maas_status),
        ):
            spec.loader.exec_module(mod)
        return mod.app

    def test_index_returns_200(self):
        app = self._make_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            with (
                patch("network_utils.is_host_reachable", return_value=True),
                patch(
                    "maas_client.get_maas_status",
                    return_value={
                        "reachable": True,
                        "error": None,
                        "machine_counts": {"ready": 1, "deployed": 0, "broken": 0},
                    },
                ),
                patch.dict("os.environ", {"OB_HOST": "10.0.0.1"}),
            ):
                rv = client.get("/")
        self.assertEqual(rv.status_code, 200)

    def test_healthz_returns_ok(self):
        app = self._make_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            rv = client.get("/healthz")
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data["status"], "ok")

    def test_index_shows_powered_on(self):
        app = self._make_app(powered_on=True)
        app.config["TESTING"] = True
        with app.test_client() as client:
            with (
                patch("network_utils.is_host_reachable", return_value=True),
                patch(
                    "maas_client.get_maas_status",
                    return_value={
                        "reachable": True,
                        "error": None,
                        "machine_counts": {"ready": 0, "deployed": 0, "broken": 0},
                    },
                ),
                patch.dict("os.environ", {"OB_HOST": "10.0.0.1"}),
            ):
                rv = client.get("/")
        self.assertIn(b"ON", rv.data)

    def test_index_shows_powered_off(self):
        app = self._make_app(powered_on=False)
        app.config["TESTING"] = True
        with app.test_client() as client:
            with (
                patch("network_utils.is_host_reachable", return_value=False),
                patch(
                    "maas_client.get_maas_status",
                    return_value={
                        "reachable": False,
                        "error": "Cannot connect",
                        "machine_counts": {"ready": 0, "deployed": 0, "broken": 0},
                    },
                ),
                patch.dict("os.environ", {"OB_HOST": "10.0.0.1"}),
            ):
                rv = client.get("/")
        self.assertIn(b"OFF", rv.data)

    def test_index_shows_machine_counts(self):
        maas_status = {
            "reachable": True,
            "error": None,
            "machine_counts": {"ready": 5, "deployed": 3, "broken": 1},
        }
        app = self._make_app(maas_status=maas_status)
        app.config["TESTING"] = True
        with app.test_client() as client:
            with (
                patch("network_utils.is_host_reachable", return_value=True),
                patch("maas_client.get_maas_status", return_value=maas_status),
            ):
                rv = client.get("/")
        self.assertIn(b"5", rv.data)
        self.assertIn(b"3", rv.data)
        self.assertIn(b"1", rv.data)


if __name__ == "__main__":
    unittest.main()
