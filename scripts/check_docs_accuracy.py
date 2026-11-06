"""Check that the documentation matches the AIWAF code.

Usage: python scripts/check_docs_accuracy.py --aiwaf ../aiwaf [--check-registries]

Known problems are listed in scripts/docs_accuracy_baseline.txt. New problems fail, and so do
baseline entries that have been fixed, so the list can only shrink. Sandbox and PHP pages are
skipped because they document other repositories.
"""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "scripts/docs_accuracy_baseline.txt"
SKIPPED_PREFIXES = ("sandbox", "php", "_sandbox", "_php")
GENERIC_TITLE = "AIWAF Documentation"
BANNED_PHRASES = {
    "observe-only": "AIWAF has no observe-only mode",
    "conservative mode": "AIWAF has no conservative mode",
    "release candidate:": "use the published version instead",
    "source candidate": "use the published version instead",
    "await init()": "the aiwaf-wasm package has no default export or init function",
    "website endpoints": "the site is static and has no endpoints",
}
DJANGO_BUILTIN_COMMANDS = {
    "check", "collectstatic", "createsuperuser", "dbshell", "dumpdata", "flush", "loaddata",
    "makemigrations", "migrate", "runserver", "shell", "showmigrations", "startapp",
    "startproject", "test",
}
CODE_LOCATIONS = (
    "py/aiwaf", "js/lib", "js/bin", "js/test", "js/index.js", "js/train.js", "java/src/main", "rust/src",
    "rust/crates/aiwaf_core/src", "rust/crates/aiwaf_wasm/src", "AIWAF_SETTINGS_GUIDE.py",
    "AIWAF_SETTINGS_EXAMPLE.py",
)
CODE_SUFFIXES = {".py", ".js", ".java", ".rs", ".json"}


@dataclass(frozen=True)
class Finding:
    key: str
    message: str
    source: str

    def __str__(self):
        return f"{self.source}: {self.message} [{self.key}]"


def documentation_files(root=ROOT):
    site = root / "site"
    candidates = [*sorted((site / "pages").glob("*.html")), *sorted((site / "_includes").glob("*.html"))]
    if (site / "index.html").is_file():
        candidates.append(site / "index.html")
    return [path for path in candidates if not path.name.startswith(SKIPPED_PREFIXES)]


def read_docs(root=ROOT):
    return {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in documentation_files(root)}


def read_code(aiwaf):
    chunks = []
    for location in CODE_LOCATIONS:
        path = aiwaf / location
        files = [path] if path.is_file() else sorted(path.rglob("*")) if path.is_dir() else []
        for file in files:
            if file.is_file() and file.suffix in CODE_SUFFIXES and "__pycache__" not in file.parts:
                chunks.append(file.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def check_titles(docs):
    findings, owners = [], {}
    for source, text in docs.items():
        match = re.search(r'^title:\s*"?(.*?)"?\s*$', text[:600], re.M) if text.startswith("---") else None
        if not match:
            continue
        title = match.group(1)
        if title == GENERIC_TITLE:
            findings.append(Finding(f"generic-title:{source}", f'title is only "{GENERIC_TITLE}"', source))
        else:
            owners.setdefault(title, []).append(source)
    for title, sources in owners.items():
        if len(sources) > 1:
            findings.append(Finding(f"duplicate-title:{title}", f"title is also used by {sources[0]}", sources[-1]))
    return findings


def check_banned_phrases(docs):
    findings = []
    for source, text in docs.items():
        lowered = text.lower()
        for phrase, reason in BANNED_PHRASES.items():
            if phrase in lowered:
                findings.append(Finding(f"phrase:{phrase}:{source}", f'contains "{phrase}": {reason}', source))
    return findings


def check_scripts(docs, aiwaf, root=ROOT):
    findings = {}
    for source, text in docs.items():
        for script in set(re.findall(r"\bscripts/[\w.-]+\.py\b", text)):
            if not any((base / script).is_file() for base in (root, aiwaf, aiwaf / "rust")):
                findings.setdefault(script, Finding(f"script:{script}", f"{script} doesn't exist", source))
    return list(findings.values())


def check_settings(docs, code):
    known = set(re.findall(r"\bAIWAF_[A-Z0-9_]+\b", code))
    findings = {}
    for source, text in docs.items():
        for name in set(re.findall(r"\bAIWAF_[A-Z0-9]+(?:_[A-Z0-9]+)*\b(?!\.py)", text)):
            if name not in known:
                findings.setdefault(name, Finding(f"setting:{name}", f"{name} isn't in the code", source))
    return list(findings.values())


def check_commands(docs, aiwaf):
    findings = {}
    commands_dir = aiwaf / "py/aiwaf/django/management/commands"
    commands = {path.stem for path in commands_dir.glob("*.py")} | DJANGO_BUILTIN_COMMANDS
    runner = aiwaf / "aiwaf_test.py"
    runner_text = runner.read_text(encoding="utf-8") if runner.is_file() else ""
    for source, text in docs.items():
        for command in set(re.findall(r"\bpython3?\s+manage\.py\s+([a-z][a-z_]+)", text)):
            if command not in commands:
                findings.setdefault(command, Finding(f"command:{command}", f"manage.py {command} doesn't exist", source))
        for flags in re.findall(r"\baiwaf_test\.py((?:\s+--[a-z-]+)+)", text):
            for flag in flags.split():
                if f'"{flag}"' not in runner_text:
                    findings.setdefault(flag, Finding(f"runner-flag:{flag}", f"aiwaf_test.py has no {flag} option", source))
    return list(findings.values())


def _module_file(package, parts):
    """Return the deepest module file for the dotted parts, and the parts left over."""
    for size in range(len(parts), 0, -1):
        base = package.joinpath(*parts[:size])
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.is_file():
                return candidate, parts[size:]
    return None, parts


def check_python_references(docs, aiwaf):
    package = aiwaf / "py/aiwaf"
    findings = {}

    def verify(dotted, names, source):
        module, leftover = _module_file(package, dotted.split(".")[1:])
        if module is None:
            findings.setdefault(dotted, Finding(f"python:{dotted}", f"{dotted} doesn't exist", source))
            return
        content = module.read_text(encoding="utf-8", errors="ignore")
        for name in [*leftover[:1], *names]:
            if not re.search(rf"\b{re.escape(name)}\b", content):
                key = f"{dotted}.{name}" if name not in leftover else dotted
                findings.setdefault(key, Finding(f"python:{key}", f"{key} doesn't exist", source))

    for source, text in docs.items():
        for dotted in set(re.findall(r"(?<![\w.])aiwaf(?:\.(?:django|flask|fast|core)(?:\.[A-Za-z_]\w*)*)\b", text)):
            verify(dotted, [], source)
        for dotted, names in re.findall(r"\bfrom\s+(aiwaf(?:\.\w+)*)\s+import\s+([A-Za-z_][\w ,]*)", text):
            imported = [name.split(" as ")[0].strip() for name in names.split(",") if name.strip()]
            verify(dotted, imported, source)
    return list(findings.values())


def check_rust_references(docs, code):
    findings = {}
    for source, text in docs.items():
        for name in set(re.findall(r"\baiwaf_rust\.([A-Za-z_]\w*)", text)):
            if not re.search(rf"\b{re.escape(name)}\b", code):
                findings.setdefault(name, Finding(f"rust:{name}", f"aiwaf_rust.{name} isn't in the code", source))
    return list(findings.values())


def stated_versions(docs):
    text = docs.get("site/_includes/_docs_source.html", "")
    match = re.search(
        r"<code>aiwaf ([\d.]+)</code> \(Python\).*?<code>aiwaf ([\d.]+)</code> \(npm\).*?"
        r"Rust/Python <code>([\d.]+)</code>.*?WASM <code>([\d.]+)</code>.*?Java <code>([\d.]+)</code>",
        text, re.S,
    )
    if not match:
        return None
    return dict(zip(("python", "node", "rust", "wasm", "java"), match.groups()))


def check_version_consistency(docs):
    versions = stated_versions(docs)
    if versions is None:
        return [Finding("version:source", "couldn't read the current versions", "site/_includes/_docs_source.html")]
    rules = [
        (r"this page documents Python <code>([\d.]+)</code>", "python"),
        (r"and Rust/Python <code>([\d.]+)</code>, both published", "rust"),
        (r"Node release <code>aiwaf ([\d.]+)</code>", "node"),
        (r"declares <code>aiwaf-wasm \^([\d.]+)</code>", "wasm"),
        (r'project/aiwaf/"><code>aiwaf</code></a></td><td><code>([\d.]+)</code>', "python"),
        (r'package/aiwaf"><code>aiwaf</code></a></td><td><code>([\d.]+)</code>', "node"),
        (r'project/aiwaf-rust/"><code>aiwaf-rust</code></a></td><td><code>([\d.]+)</code>', "rust"),
        (r'package/aiwaf-wasm"><code>aiwaf-wasm</code></a></td><td><code>([\d.]+)</code>', "wasm"),
        (r"aiwaf-java</code></td><td><code>([\d.]+)</code>", "java"),
    ]
    findings = []
    for source, text in docs.items():
        for pattern, package in rules:
            for found in re.findall(pattern, text):
                if found != versions[package]:
                    findings.append(Finding(
                        f"version:{package}:{source}:{found}",
                        f"says {package} {found}, but _docs_source.html says {versions[package]}",
                        source,
                    ))
    return findings


def fetch_published_versions():
    def json_url(url):
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.load(response)

    with urllib.request.urlopen(
        "https://repo1.maven.org/maven2/io/github/aiwaf-project/aiwaf-java/maven-metadata.xml", timeout=20
    ) as response:
        java = re.search(r"<release>([^<]+)</release>", response.read().decode("utf-8")).group(1)
    return {
        "python": json_url("https://pypi.org/pypi/aiwaf/json")["info"]["version"],
        "rust": json_url("https://pypi.org/pypi/aiwaf-rust/json")["info"]["version"],
        "node": json_url("https://registry.npmjs.org/aiwaf/latest")["version"],
        "wasm": json_url("https://registry.npmjs.org/aiwaf-wasm/latest")["version"],
        "java": java,
    }


def registry_warnings(docs, fetch=fetch_published_versions):
    """A new release must not fail unrelated pull requests, so these never fail the check."""
    try:
        published = fetch()
    except Exception as error:  # Network problems aren't documentation problems.
        return [f"Skipped the registry check: {error}"]
    stated = stated_versions(docs) or {}
    return [
        f"The docs say {package} {stated.get(package)}, but {version} is published."
        for package, version in published.items()
        if stated.get(package) != version
    ]


def load_baseline(path):
    if not path.is_file():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def collect_findings(docs, aiwaf, root=ROOT):
    code = read_code(aiwaf)
    return [
        *check_titles(docs),
        *check_banned_phrases(docs),
        *check_scripts(docs, aiwaf, root),
        *check_settings(docs, code),
        *check_commands(docs, aiwaf),
        *check_python_references(docs, aiwaf),
        *check_rust_references(docs, code),
        *check_version_consistency(docs),
    ]


def compare_with_baseline(findings, baseline):
    keys = {finding.key for finding in findings}
    new = sorted((finding for finding in findings if finding.key not in baseline), key=lambda item: item.key)
    fixed = sorted(baseline - keys)
    return new, fixed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aiwaf", type=Path, default=ROOT.parent / "aiwaf", help="Path to an aiwaf checkout.")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--check-registries", action="store_true", help="Warn if published versions differ.")
    args = parser.parse_args(argv)

    if not (args.aiwaf / "py/aiwaf").is_dir():
        print(f"No aiwaf checkout found at {args.aiwaf}. Pass its location with --aiwaf.", file=sys.stderr)
        return 2

    docs = read_docs()
    findings = collect_findings(docs, args.aiwaf.resolve())
    new, fixed = compare_with_baseline(findings, load_baseline(args.baseline))

    if args.check_registries:
        for warning in registry_warnings(docs):
            print(f"::warning::{warning}")

    for finding in new:
        print(f"::error::{finding}")
    for key in fixed:
        print(f"::error::Fixed, so remove it from {args.baseline.name}: {key}")
    if new or fixed:
        print(f"\n{len(new)} new problems, {len(fixed)} baseline entries to remove.")
        return 1
    print(f"Checked {len(docs)} documentation files against the code. {len(findings)} known problems remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
