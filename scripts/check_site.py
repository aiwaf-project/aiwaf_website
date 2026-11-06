"""Check the built Jekyll site's navigation, assets, search and deployment boundaries."""

import argparse
import ast
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_docs_search import entries


# Tags whose closing tag is required. A missing one can break the layout of the whole page.
STRUCTURAL_TAGS = {
    "a", "article", "aside", "blockquote", "body", "code", "div", "footer", "h1", "h2", "h3", "h4",
    "h5", "h6", "head", "header", "html", "main", "nav", "ol", "pre", "section", "table", "tbody",
    "thead", "title", "ul",
}


class Page(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links, self.ids = [], set()
        self.open_tags, self.structure_errors = [], []
        self.title = ""
        self.feed(markup)
        self.structure_errors.extend(f"<{tag}> is never closed" for tag in self.open_tags)

    def handle_data(self, data):
        if self.open_tags and self.open_tags[-1] == "title":
            self.title += data

    def handle_endtag(self, tag):
        if tag not in STRUCTURAL_TAGS:
            return
        if tag not in self.open_tags:
            self.structure_errors.append(f"</{tag}> has no opening tag (line {self.getpos()[0]})")
            return
        while self.open_tags:
            current = self.open_tags.pop()
            if current == tag:
                break
            self.structure_errors.append(f"<{current}> is closed by </{tag}> (line {self.getpos()[0]})")

    def handle_starttag(self, tag, attrs):
        if tag in STRUCTURAL_TAGS:
            self.open_tags.append(tag)
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag in {"script", "img", "link"}:
            link = attrs.get("src") or attrs.get("href")
            if link:
                self.links.append(link)


# Jekyll fills these in even when a page's front matter doesn't set them.
JEKYLL_PAGE_VARIABLES = {"content", "date", "dir", "excerpt", "name", "path", "url"}
JEKYLL_SITE_VARIABLES = {"data", "documents", "html_pages", "pages", "posts", "static_files", "time"}


def front_matter_keys(text):
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        return set()
    return set(re.findall(r"^([A-Za-z_]\w*):", parts[1], re.M))


def undefined_variables(text, site_keys):
    """Find page.x and site.x values that would silently render as blank."""
    keys = front_matter_keys(text)
    problems = []
    for tag in re.findall(r"\{\{.*?\}\}|\{%.*?%\}", text, re.S):
        for scope, name in re.findall(r"\b(page|site)\.([A-Za-z_]\w*)", tag):
            known = keys | JEKYLL_PAGE_VARIABLES if scope == "page" else site_keys | JEKYLL_SITE_VARIABLES
            if name not in known:
                problems.append(f"{scope}.{name}")
    return sorted(set(problems))


def check_source_variables():
    site_keys = front_matter_keys("---\n" + (ROOT / "_config.yml").read_text(encoding="utf-8") + "\n---\n")
    for source in sorted((ROOT / "site/pages").glob("*.html")):
        problems = undefined_variables(source.read_text(encoding="utf-8"), site_keys)
        assert not problems, (source, "Undefined variables", problems)


def check(baseurl=""):
    check_source_variables()
    output = ROOT / "_site"
    assert (output / "index.html").is_file(), "Run bundle exec jekyll build first"
    parsed_pages = {}
    for file in output.rglob("*.html"):
        markup = file.read_text(encoding="utf-8")
        assert "{%" not in markup and "{{" not in markup, f"Unrendered template: {file}"
        assert "beta-signup" not in markup and "beta_csrf" not in markup, file
        page = Page(markup)
        assert not page.structure_errors, (file, page.structure_errors[:5])
        assert page.title.strip(), f"Missing page title: {file}"
        parsed_pages[file] = page
    for file, page in parsed_pages.items():
        current = "/" + file.relative_to(output).as_posix()
        if current.endswith("index.html"):
            current = current[:-len("index.html")]
        for href in page.links:
            target = urlsplit(href)
            if target.scheme or target.netloc:
                continue
            path = urlsplit(urljoin(baseurl + current, href)).path
            assert not baseurl or path.startswith(baseurl + "/"), (file, href, "Missing baseurl")
            path = path.removeprefix(baseurl)
            destination = output / unquote(path).lstrip("/")
            if destination.is_dir():
                destination /= "index.html"
            assert destination.is_file(), (file, href, "Broken local link")
            if target.fragment and destination in parsed_pages:
                assert unquote(target.fragment) in parsed_pages[destination].ids, (file, href, "Missing fragment")
    index = json.loads((output / "static/docs-search-index.json").read_text(encoding="utf-8"))
    assert index == list(entries()), "Search index is stale: python scripts/build_docs_search.py"
    for page in index:
        assert (output / page["url"].strip("/") / "index.html").is_file(), page["url"]
    sitemap = ElementTree.parse(output / "sitemap.xml")
    locations = [node.text for node in sitemap.findall(".//{*}loc")]
    expected = {baseurl + "/"} | {baseurl + entry["url"] for entry in index}
    assert {urlsplit(loc).path for loc in locations} == expected, "Sitemap page coverage mismatch"
    assert len(locations) == len(expected), "Duplicate sitemap entries"
    assert not (output / "aiwaf").exists(), "Admin endpoints must not be published"
    for file in output.rglob("*"):
        assert not file.name.startswith(".env") and file.suffix not in {".py", ".db", ".sqlite"}, file
    for source in (ROOT / "site/pages").glob("*.html"):
        for name, block in re.findall(r'data-example="([^"]+)">([\s\S]*?)</code>', source.read_text(encoding="utf-8")):
            example = (ROOT / name).read_text(encoding="utf-8")
            assert html.unescape(block).strip() == example.strip(), (source, name)
            ast.parse(example)
    print(f"Verified {len(index)} documentation pages, {len(parsed_pages)} HTML files, links, assets, search, sitemap and code examples")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseurl", default="")
    check(parser.parse_args().baseurl.rstrip("/"))
