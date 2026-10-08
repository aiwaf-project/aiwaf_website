"""Smoke-test the exact tutorial app with installed AIWAF and Flask.

Run: python scripts/verify_flask_tutorial.py
Uses isolated temporary runtime storage and starts no network server.
"""

import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    original = Path.cwd()
    with tempfile.TemporaryDirectory(prefix=".ci-tutorial-validation-", dir=ROOT) as directory:
        try:
            os.chdir(directory)
            spec = importlib.util.spec_from_file_location("tutorial_app", ROOT / "examples/tutorial/app.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            from aiwaf.flask.path_manifest import generate_flask_manifest
            generate_flask_manifest(module.app, ".aiwaf/paths.json")
            manifest = json.loads(Path(".aiwaf/paths.json").read_text(encoding="utf-8"))
            assert "/api/message" in json.dumps(manifest), "Protected route missing from manifest"
            client = module.app.test_client()
            statuses = [client.get("/api/message").status_code for _ in range(4)]
            assert statuses == [200, 200, 200, 429], statuses
            assert client.get("/api/message").json == {"error": "too_many_requests"}
            assert client.get("/health").json == {"ok": True}
            preview = [client.get("/api/preview").status_code for _ in range(5)]
            assert preview == [200] * 5, preview
            logs = Path("aiwaf_logs/access.log")
            assert logs.exists(), "Access log missing"
            entries = [json.loads(line) for line in logs.read_text(encoding="utf-8").splitlines()]
            assert len(entries) >= 4, "Expected request observations in JSON log"
            print("Tutorial passed: live route manifest; three 200 responses, then 429; exempt routes pass; JSON logs exist.")
        finally:
            os.chdir(original)


if __name__ == "__main__":
    main()
