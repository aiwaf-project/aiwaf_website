"""Each rule in the documentation checker must catch the problem it exists for."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import check_docs_accuracy as checker  # noqa: E402

VERSIONS = (
    "<code>aiwaf 1.1.8</code> (Python) and <code>aiwaf 1.1.5</code> (npm), with Rust/Python "
    "<code>0.2.7</code> and WASM <code>0.2.5</code> and Java <code>1.3.5</code>."
)


class CheckerTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / "website"
        self.aiwaf = Path(folder.name) / "aiwaf"
        self.write(self.aiwaf / "py/aiwaf/core/logs.py", "def parse_log_line():\n    return 'AIWAF_REAL_SETTING'\n")
        self.write(self.aiwaf / "py/aiwaf/core/__init__.py", "")
        self.write(self.aiwaf / "py/aiwaf/django/__init__.py", "def aiwaf_exempt():\n    pass\n")
        self.write(self.aiwaf / "py/aiwaf/django/management/commands/detect_and_train.py", "")
        self.write(self.aiwaf / "rust/src/lib.rs", "fn training_parse_lines() {}\n")
        self.write(self.aiwaf / "scripts/real_script.py", "")
        self.write(self.aiwaf / "rust/scripts/rust_script.py", "")
        self.write(self.aiwaf / "aiwaf_test.py", 'add_argument("--rust-only")\n')
        self.code = checker.read_code(self.aiwaf)

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def keys(self, findings):
        return {finding.key for finding in findings}

    def test_generic_and_duplicate_titles_are_reported(self):
        docs = {
            "a.html": '---\ntitle: "AIWAF Documentation"\n---\n',
            "b.html": '---\ntitle: "Same"\n---\n',
            "c.html": '---\ntitle: "Same"\n---\n',
            "d.html": '---\ntitle: "Unique"\n---\n',
        }
        self.assertEqual(self.keys(checker.check_titles(docs)), {"generic-title:a.html", "duplicate-title:Same"})

    def test_banned_claims_are_reported_in_any_case(self):
        findings = checker.check_banned_phrases({"a.html": "Start in Observe-Only mode", "b.html": "Normal text"})
        self.assertEqual(self.keys(findings), {"phrase:observe-only:a.html"})

    def test_missing_scripts_are_reported(self):
        docs = {"a.html": "python scripts/real_script.py\npython scripts/rust_script.py\npython scripts/gone.py"}
        self.assertEqual(self.keys(checker.check_scripts(docs, self.aiwaf, self.root)), {"script:scripts/gone.py"})

    def test_unknown_settings_are_reported(self):
        docs = {"a.html": "AIWAF_REAL_SETTING AIWAF_MADE_UP see AIWAF_REAL_FILE.py"}
        self.assertEqual(self.keys(checker.check_settings(docs, self.code)), {"setting:AIWAF_MADE_UP"})

    def test_unknown_commands_and_runner_flags_are_reported(self):
        docs = {"a.html": (
            "python manage.py detect_and_train\npython manage.py migrate\npython manage.py made_up\n"
            "needs manage.py and a settings module\n"
            "python aiwaf_test.py --rust-only\npython aiwaf_test.py --made-up"
        )}
        self.assertEqual(self.keys(checker.check_commands(docs, self.aiwaf)), {"command:made_up", "runner-flag:--made-up"})

    def test_unknown_python_names_are_reported(self):
        docs = {"a.html": (
            "aiwaf.core.logs.parse_log_line\naiwaf.core.logs.gone\naiwaf.core.missing\n"
            "from aiwaf.django import aiwaf_exempt, aiwaf_gone\n"
            "com.aiwaf.core.JavaClass\naiwaf.log\n"
        )}
        self.assertEqual(
            self.keys(checker.check_python_references(docs, self.aiwaf)),
            {"python:aiwaf.core.logs.gone", "python:aiwaf.core.missing", "python:aiwaf.django.aiwaf_gone"},
        )

    def test_unknown_rust_names_are_reported(self):
        docs = {"a.html": "aiwaf_rust.training_parse_lines aiwaf_rust.gone"}
        self.assertEqual(self.keys(checker.check_rust_references(docs, self.code)), {"rust:gone"})

    def test_old_version_numbers_are_reported(self):
        docs = {
            "site/_includes/_docs_source.html": VERSIONS,
            "good.html": "this page documents Python <code>1.1.8</code>",
            "bad.html": 'package/aiwaf-wasm"><code>aiwaf-wasm</code></a></td><td><code>0.2.4</code>',
        }
        self.assertEqual(self.keys(checker.check_version_consistency(docs)), {"version:wasm:bad.html:0.2.4"})

    def test_unreadable_version_source_is_reported(self):
        self.assertEqual(self.keys(checker.check_version_consistency({})), {"version:source"})

    def test_new_release_only_warns(self):
        docs = {"site/_includes/_docs_source.html": VERSIONS}
        published = lambda: {"python": "1.1.9", "node": "1.1.5", "rust": "0.2.7", "wasm": "0.2.5", "java": "1.3.5"}
        self.assertEqual(checker.registry_warnings(docs, published), ["The docs say python 1.1.8, but 1.1.9 is published."])

    def test_network_problems_only_warn(self):
        def offline():
            raise OSError("offline")

        self.assertEqual(checker.registry_warnings({}, offline), ["Skipped the registry check: offline"])

    def test_baseline_allows_known_problems_and_requires_removal_when_fixed(self):
        known = checker.Finding("known", "known", "a.html")
        added = checker.Finding("added", "added", "a.html")
        new, fixed = checker.compare_with_baseline([known, added], {"known", "fixed"})
        self.assertEqual([finding.key for finding in new], ["added"])
        self.assertEqual(fixed, ["fixed"])

    def test_sandbox_and_php_pages_are_skipped(self):
        for name in ("docs.html", "sandbox_start.html", "php_setup.html"):
            self.write(self.root / "site/pages" / name, "text")
        names = {path.name for path in checker.documentation_files(self.root)}
        self.assertEqual(names, {"docs.html"})

    def test_main_returns_nonzero_without_an_aiwaf_checkout(self):
        self.assertEqual(checker.main(["--aiwaf", str(self.root / "missing")]), 2)


if __name__ == "__main__":
    unittest.main()
