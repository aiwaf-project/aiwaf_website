"""Documentation route regressions without WAF or database initialization."""

from pathlib import Path
import unittest

from flask import Flask
from jinja2 import DictLoader, TemplateNotFound

from documentation import documentation


ROOT = Path(__file__).resolve().parents[1]


class DocumentationRoutesTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"))
        self.app.config["TESTING"] = True
        self.app.register_blueprint(documentation)
        self.client = self.app.test_client()

    def test_setup_landing_pages_redirect_to_existing_guides(self):
        defaults = {"python": "django", "javascript": "express", "java": "servlet", "php": "plain"}
        for language, adapter in defaults.items():
            for suffix in ("", "/"):
                with self.subTest(language=language, suffix=suffix):
                    path = f"/docs/{language}/setup{suffix}"
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(response.headers["Location"], f"/docs/{language}/setup/{adapter}")
                    page = self.client.get(path, follow_redirects=True)
                    self.assertEqual(page.status_code, 200)
                    self.assertIn(b"One AIWAF repository.", page.data)

    def test_every_setup_guide_and_short_url_renders(self):
        for template in (ROOT / "templates").glob("docs_*_setup_*.html"):
            language, _, adapter = template.stem.removeprefix("docs_").split("_", 2)
            for prefix in ("", "/docs"):
                for suffix in ("", "/"):
                    path = f"{prefix}/{language}/setup/{adapter}{suffix}"
                    with self.subTest(path=path):
                        self.assertEqual(self.client.get(path, follow_redirects=True).status_code, 200)

    def test_legacy_python_routes_redirect(self):
        for adapter in ("django", "flask", "fastapi", "fast"):
            with self.subTest(adapter=adapter):
                destination = "fastapi" if adapter == "fast" else adapter
                response = self.client.get(f"/docs/{adapter}/setup")
                self.assertEqual(response.headers["Location"], f"/docs/python/setup/{destination}")
                self.assertEqual(self.client.get(f"/docs/{adapter}/setup", follow_redirects=True).status_code, 200)

    def test_unknown_documentation_returns_404(self):
        for path in ("/docs/unknown", "/docs/python/unknown", "/docs/python/setup/unknown", "/python/setup/unknown"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_missing_include_in_existing_page_is_not_hidden(self):
        self.app.jinja_loader = DictLoader({"docs_python.html": "{% include 'missing.html' %}"})
        with self.assertRaises(TemplateNotFound):
            self.client.get("/docs/python")


if __name__ == "__main__":
    unittest.main()
