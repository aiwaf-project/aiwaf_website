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


class Page(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links, self.ids = [], set()
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag in {"script", "img", "link"}:
            link = attrs.get("src") or attrs.get("href")
            if link:
                self.links.append(link)


def check(baseurl=""):
    output = ROOT / "_site"
    assert (output / "index.html").is_file(), "Run bundle exec jekyll build first"
    parsed_pages = {}
    for file in output.rglob("*.html"):
        markup = file.read_text(encoding="utf-8")
        assert "{%" not in markup and "{{" not in markup, f"Unrendered template: {file}"
        assert "beta-signup" not in markup and "beta_csrf" not in markup, file
        parsed_pages[file] = Page(markup)
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
