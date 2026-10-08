"""Documentation route regressions without WAF or database initialization."""

from pathlib import Path
import ast
import html
from html.parser import HTMLParser
import json
import re
import unittest
from urllib.parse import urlsplit

from flask import Flask, render_template
from jinja2 import DictLoader, TemplateNotFound

from documentation import documentation
from scripts.build_docs_search import entries


ROOT = Path(__file__).resolve().parents[1]


class DocumentationHTML(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])


class DocumentationRoutesTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"))
        self.app.config["TESTING"] = True
        self.app.register_blueprint(documentation)
        self.app.add_url_rule("/docs", "docs", lambda: render_template("docs.html"))
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

    def test_all_documentation_pages_and_internal_links(self):
        paths = {"/docs"}
        for template in (ROOT / "templates").glob("docs_*.html"):
            parts = template.stem.removeprefix("docs_").split("_")
            paths.add("/docs/" + "/".join(parts))
        rendered = {}
        for path in sorted(paths):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                rendered[path] = DocumentationHTML(response.get_data(as_text=True))
        # Validate links across pages, including fragments after redirects.
        for path, page in rendered.items():
            for href in page.links:
                target = urlsplit(href)
                if target.scheme or target.netloc:
                    continue
                destination = target.path or path
                if not destination.startswith("/docs"):
                    continue
                with self.subTest(page=path, href=href):
                    response = self.client.get(destination, follow_redirects=True)
                    self.assertEqual(response.status_code, 200)
                    if target.fragment:
                        self.assertIn(target.fragment, DocumentationHTML(response.get_data(as_text=True)).ids)

    def test_reference_pages_include_key_diagnostics(self):
        cases = {
            "/docs/configuration": (b"AIWAF_RATE_CACHE_BACKEND", b"storageRedisFailureMode", b"WINDOW_SEC"),
            "/docs/migration": (b"npm install aiwaf", b"aiwaf blacklist migrate", b"JSON"),
            "/docs/troubleshooting": (b"--app app:app", b"documentation.py", b"/docs/python/setup/django"),
        }
        for path, expected in cases.items():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            for text in expected:
                with self.subTest(path=path, text=text):
                    self.assertIn(text, response.data)

    def test_documented_code_matches_runnable_examples(self):
        examples = set()
        for template in (ROOT / "templates").glob("docs*.html"):
            source = template.read_text(encoding="utf-8")
            for name, block in re.findall(r'data-example="([^"]+)">([\s\S]*?)</code>', source):
                with self.subTest(template=template.name, example=name):
                    path = ROOT / name
                    self.assertTrue(path.is_file())
                    self.assertEqual(html.unescape(block).strip(), path.read_text(encoding="utf-8").strip())
                    ast.parse(path.read_text(encoding="utf-8"))
                    examples.add(name)
        self.assertEqual(examples, {
            "examples/tutorial/first_app.py", "examples/tutorial/app.py", "examples/tutorial/verify.py",
            "examples/testing/test_flask_protection.py", "examples/testing/django_test_settings.py",
            "examples/testing/test_django_protection.py",
        })

    def test_search_is_visible_above_documentation_layout(self):
        for entry in entries():
            markup = self.client.get(entry["url"], follow_redirects=True).get_data(as_text=True)
            with self.subTest(url=entry["url"]):
                self.assertEqual(markup.count('id="docs-search-input"'), 1)
                self.assertLess(markup.index('data-docs-search'), markup.index('class="main-content"'))
                self.assertNotIn('<details class="docs-search"', markup)

    def test_search_index_matches_templates_and_resolves(self):
        actual = json.loads((ROOT / "static/docs-search-index.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, list(entries()), "Run python scripts/build_docs_search.py after editing docs")
        for page in actual:
            with self.subTest(url=page["url"]):
                self.assertTrue(page["title"])
                self.assertEqual(self.client.get(page["url"], follow_redirects=True).status_code, 200)

    def test_contents_covers_every_documentation_page(self):
        page = DocumentationHTML(self.client.get("/docs/contents").get_data(as_text=True))
        self.assertTrue({"tutorials", "topics", "howto", "reference", "legacy"}.issubset(page.ids))
        destinations = {urlsplit(link).path for link in page.links}
        expected = {entry["url"] for entry in entries()} - {"/docs/contents"}
        self.assertTrue(expected.issubset(destinations), f"Missing contents links: {expected - destinations}")

    def test_missing_include_in_existing_page_is_not_hidden(self):
        self.app.jinja_loader = DictLoader({"docs_python.html": "{% include 'missing.html' %}"})
        with self.assertRaises(TemplateNotFound):
            self.client.get("/docs/python")


if __name__ == "__main__":
    unittest.main()
