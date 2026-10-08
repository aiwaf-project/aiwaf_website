"""Canonical documentation URLs shared by search and crawler discovery."""

from pathlib import PurePosixPath


def documentation_path(template):
    """Return the public URL for a maintained documentation template."""
    name = PurePosixPath(template).name
    if name == "docs.html":
        return "/docs"
    if not name.startswith("docs_") or not name.endswith(".html"):
        return None
    slug = name[len("docs_"):-len(".html")]
    return "/docs/" + (slug if slug == "getting_started" else slug.replace("_", "/"))
