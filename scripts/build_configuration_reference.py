"""Refresh source-default tables without importing or starting an application.

Usage: python scripts/build_configuration_reference.py ../aiwaf
Requires Python and Node.js; only reads the supplied source checkout.
"""

import ast
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def table(rows):
    body = "".join(
        "<tr>" + "".join(f"<td><code>{html.escape(str(value))}</code></td>" for value in row) + "</tr>\n"
        for row in rows
    )
    return '<div class="table-wrap"><table><thead><tr><th>Setting</th><th>Type</th><th>Source default</th></tr></thead><tbody>\n' + body + "</tbody></table></div>\n"


def flatten(values, prefix=""):
    for key, value in values.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from flatten(value, name)
        else:
            kind = "null or string" if value is None else type(value).__name__
            yield name, kind, json.dumps(value, ensure_ascii=True)


def build(repo):
    tree = ast.parse((repo / "py/aiwaf/core/runtime_config.py").read_text(encoding="utf-8"))
    defaults_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_get_default_config")
    defaults = ast.literal_eval(next(n.value for n in defaults_fn.body if isinstance(n, ast.Return)))
    node_code = """const { normalizeSettings } = require(process.argv[1]);
const defaults = normalizeSettings();
console.log(JSON.stringify(Object.entries(defaults).map(([k,v]) => [k,
  v === undefined ? 'optional' : Array.isArray(v) ? 'array' : typeof v,
  v === undefined ? 'unset (resolved by consumer)' : JSON.stringify(v)])));"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("AIWAF_") and k != "NODE_LOG_PATH"}
    node_rows = json.loads(subprocess.check_output(
        ["node", "-e", node_code, str(repo / "js/lib/settingsCompat.js")], env=env, text=True
    ))
    java = (repo / "java/src/main/java/com/aiwaf/core/AiwafConfig.java").read_text(encoding="utf-8")
    java = java[java.index("    public boolean headerValidationEnabled"):]
    java_rows = [
        (name, kind, " ".join(value.split()))
        for kind, name, value in re.findall(r"^    public ([\w<> ,]+) (\w+) = ([\s\S]*?);", java, re.MULTILINE)
    ]
    # Read versions as source metadata, without importing package code.
    python_version = re.search(r'^version\s*=\s*"([^"]+)"', (repo / "pyproject.toml").read_text(), re.MULTILINE).group(1)
    node_version = json.loads((repo / "js/package.json").read_text())["version"]
    pom = ET.parse(repo / "java/pom.xml").getroot()
    java_version = pom.find("{http://maven.apache.org/POM/4.0.0}version").text
    revision = subprocess.check_output(
        ["git", "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    content = f'<p>Source snapshot: Python {python_version}, Node.js {node_version}, Java {java_version}; commit <code>{revision}</code>. These are source defaults, not a registry availability check. Runtime configuration and route policies can change effective values.</p>\n'
    content += '<h3>Python nested configuration defaults</h3>\n' + table(flatten(defaults))
    content += '<h3>Node.js normalized option defaults</h3>\n' + table(node_rows)
    content += '<h3>Java AiwafConfig field defaults</h3>\n<p>Java expressions are shown as declared in source. Collection constructors describe initial values; constants are resolved by the Java implementation.</p>\n' + table(java_rows)
    (ROOT / "templates/_configuration_defaults.html").write_text(content, encoding="utf-8")
    print(f"Wrote defaults: {len(list(flatten(defaults)))} Python, {len(node_rows)} Node.js, {len(java_rows)} Java settings")


if __name__ == "__main__":
    build(Path(sys.argv[1]).resolve())
