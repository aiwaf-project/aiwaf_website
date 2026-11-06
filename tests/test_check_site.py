"""The built-site checker must catch pages that build but are broken."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_site import Page, front_matter_keys, undefined_variables  # noqa: E402


def page(body, title="Title"):
    return Page(f"<!doctype html><html><head><title>{title}</title></head><body>{body}</body></html>")


class PageStructureTest(unittest.TestCase):
    def test_balanced_page_has_no_errors(self):
        result = page("<main><section><p>Text<br><img src='x.png'></p><ul><li>a<li>b</ul></section></main>")
        self.assertEqual(result.structure_errors, [])
        self.assertEqual(result.title, "Title")

    def test_unclosed_tags_are_reported(self):
        self.assertIn("<section> is closed by </body> (line 1)", page("<section><p>oops").structure_errors)

    def test_stray_closing_tags_are_reported(self):
        self.assertEqual(page("</div>").structure_errors, ["</div> has no opening tag (line 1)"])

    def test_wrongly_nested_tags_are_reported(self):
        self.assertTrue(page("<div><section></div></section>").structure_errors)

    def test_truncated_page_is_reported(self):
        self.assertIn("<main> is never closed", Page("<html><body><main>").structure_errors)

    def test_tags_shown_as_code_are_not_treated_as_markup(self):
        self.assertEqual(page("<pre><code>&lt;div&gt;</code></pre>").structure_errors, [])

    def test_scripts_are_not_parsed_as_markup(self):
        self.assertEqual(page("<script>const a = '<div>';</script>").structure_errors, [])

    def test_blank_title_is_detectable(self):
        self.assertEqual(page("", title="  ").title.strip(), "")


class SourceVariableTest(unittest.TestCase):
    SITE = {"title", "url", "baseurl"}

    def test_front_matter_keys_are_read(self):
        self.assertEqual(front_matter_keys('---\ntitle: "A: B"\ndescription: C\n---\nBody: text'), {"title", "description"})

    def test_defined_variables_pass(self):
        text = '---\ntitle: A\n---\n{{ page.title | escape }} {{ page.url }} {{ site.url }} {% if page.title %}x{% endif %}'
        self.assertEqual(undefined_variables(text, self.SITE), [])

    def test_undefined_page_variable_is_reported(self):
        self.assertEqual(undefined_variables("---\ntitle: A\n---\n{{ page.description }}", self.SITE), ["page.description"])

    def test_undefined_site_variable_is_reported(self):
        self.assertEqual(undefined_variables("---\ntitle: A\n---\n{{ site.nope }}", self.SITE), ["site.nope"])

    def test_text_outside_liquid_tags_is_ignored(self):
        self.assertEqual(undefined_variables("---\ntitle: A\n---\nSee page.nope and site.nope", self.SITE), [])


if __name__ == "__main__":
    unittest.main()
