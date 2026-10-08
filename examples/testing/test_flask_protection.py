"""Run with: python -m unittest discover -s examples/testing -p test_flask_protection.py -v"""

from pathlib import Path
import tempfile
import unittest

from flask import Flask
from aiwaf.flask import AIWAF, aiwaf_exempt, aiwaf_exempt_from


class ProtectionTests(unittest.TestCase):
    def setUp(self):
        # A new application and state directory for every test.
        directory = tempfile.TemporaryDirectory(prefix=".ci-protection-validation-", dir=Path.cwd())
        self.addCleanup(directory.cleanup)
        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            AIWAF_USE_CSV=True,
            AIWAF_DATA_DIR=directory.name,
            AIWAF_RATE_CACHE_BACKEND="memory",
            AIWAF_PATH_MANIFEST=str(Path(directory.name) / "paths.json"),
            AIWAF_RATE_WINDOW=60,
            AIWAF_RATE_MAX=3,
            AIWAF_RATE_FLOOD=100,
            AIWAF_PATH_RULES=[
                {"PREFIX": path, "RATE_LIMIT": {"WINDOW": 60, "MAX": 3, "FLOOD": 100}}
                for path in ("/api/message", "/api/preview")
            ],
        )

        @app.get("/api/message")
        def message():
            return {"message": "Protected"}

        @app.get("/health")
        @aiwaf_exempt
        def health():
            return {"ok": True}

        @app.get("/api/preview")
        @aiwaf_exempt_from("rate_limit")
        def preview():
            return {"message": "Preview"}

        AIWAF(app, middlewares=["rate_limit"])
        self.client = app.test_client()

    def test_protected_route_throttles(self):
        for _ in range(3):
            response = self.client.get("/api/message")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"message": "Protected"})
        response = self.client.get("/api/message")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json, {"error": "too_many_requests"})

    def test_health_stays_available_after_throttling(self):
        for _ in range(4):
            self.client.get("/api/message")
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"ok": True})

    def test_selective_exemption_bypasses_rate_limit(self):
        self.assertEqual(
            [self.client.get("/api/preview").status_code for _ in range(5)],
            [200] * 5,
        )


if __name__ == "__main__":
    unittest.main()
