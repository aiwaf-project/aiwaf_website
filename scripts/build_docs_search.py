"""Build the local documentation search index from maintained templates."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main = False
        self.in_title = False
        self.body = []
        self.title = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main = True
        if tag == "h1" and self.in_main:
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False
        if tag == "h1":
            self.in_title = False

    def handle_data(self, text):
        if self.in_main:
            self.body.append(text)
        if self.in_title:
            self.title.append(text)


def entries():
    for template in sorted((ROOT / "templates").glob("docs*.html")):
        source = template.read_text(encoding="utf-8")
        source = source.replace("{% include '_configuration_defaults.html' %}",
                                (ROOT / "templates/_configuration_defaults.html").read_text(encoding="utf-8"))
        parser = PageText()
        parser.feed(re.sub(r"\{%[\s\S]*?%\}|\{\{[\s\S]*?\}\}", "", source))
        slug = template.stem.removeprefix("docs_")
        url = "/docs" if template.stem == "docs" else "/docs/" + (slug if slug == "getting_started" else slug.replace("_", "/"))
        yield {"title": " ".join(" ".join(parser.title).split()), "url": url,
               "text": " ".join(" ".join(parser.body).split())}


if __name__ == "__main__":
    pages = list(entries())
    (ROOT / "static/docs-search-index.json").write_text(
        json.dumps(pages, ensure_ascii=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"Indexed {len(pages)} documentation pages")
