"""Verify production crawler routes through AIWAF, with disposable local state."""

import importlib
import os
from pathlib import Path
import sys
import tempfile
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    original = Path.cwd()
    with tempfile.TemporaryDirectory(prefix=".ci-crawler-validation-", dir=ROOT) as directory:
        try:
            os.chdir(directory)
            app = importlib.import_module("app").app
            app.config.update(
                TESTING=True,
                SITE_URL="https://aiwaf.org",
                AIWAF_EXEMPT_PATHS=[],
                AIWAF_REQUIRED_HEADERS=["X-Required-Test-Header"],
                AIWAF_RATE_MAX=1,
                AIWAF_RATE_FLOOD=2,
            )
            app.add_url_rule("/crawler-test-control", "crawler_test_control", lambda: {"ok": True})
            client = app.test_client()
            for endpoint in ("documentation.sitemap", "documentation.robots"):
                assert getattr(app.view_functions[endpoint], "_aiwaf_exempt", False), endpoint
            for agent in ("", "Googlebot"):
                for method in ("GET", "HEAD"):
                    for path in ("/sitemap.xml", "/robots.txt"):
                        for _ in range(4):
                            response = client.open(path, method=method, headers={"User-Agent": agent},
                                                   environ_overrides={"REMOTE_ADDR": "203.0.113.91"})
                            assert response.status_code == 200, (path, method, agent, response.status_code)
                            if path == "/sitemap.xml":
                                assert response.mimetype == "application/xml"
                                if method == "GET":
                                    root = ElementTree.fromstring(response.data)
                                    assert root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
                            elif method == "GET":
                                assert b"Sitemap: https://aiwaf.org/sitemap.xml" in response.data
            control = client.get("/crawler-test-control", headers={"User-Agent": ""},
                                 environ_overrides={"REMOTE_ADDR": "203.0.113.91"})
            assert control.status_code == 403, ("Non-exempt control should be blocked", control.status_code)
            print("Crawler endpoints passed with AIWAF enabled: GET/HEAD, sparse headers, repeated requests, valid XML.")
        finally:
            os.chdir(original)


if __name__ == "__main__":
    main()
