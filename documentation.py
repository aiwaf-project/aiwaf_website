"""Shared documentation routing for the production and alternate app runners."""

import os
from xml.etree.ElementTree import Element, SubElement, tostring

from flask import Blueprint, Response, abort, current_app, redirect, render_template, request
from jinja2 import TemplateNotFound

from documentation_catalog import documentation_path


documentation = Blueprint("documentation", __name__)

SETUP_DEFAULTS = {
    "python": "django",
    "javascript": "express",
    "php": "plain",
    "java": "servlet",
}
PYTHON_ALIASES = {"django", "flask", "fastapi", "fast"}


def site_url():
    return current_app.config.get("SITE_URL", os.environ.get("SITE_URL", "https://aiwaf.org")).rstrip("/")


@documentation.route("/robots.txt")
def robots():
    content = "User-agent: *\nAllow: /\nDisallow: /aiwaf/\n"
    content += f"Sitemap: {site_url()}/sitemap.xml\n"
    return Response(content, mimetype="text/plain")


@documentation.route("/sitemap.xml")
def sitemap():
    """Discover canonical documentation pages; omit aliases and operational routes."""
    paths = {"/"}
    paths.update(
        path for template in current_app.jinja_env.list_templates()
        if (path := documentation_path(template)) is not None
    )
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in sorted(paths):
        node = SubElement(root, "url")
        SubElement(node, "loc").text = site_url() + path
    # Omit lastmod until reliable content modification dates are available.
    return Response(tostring(root, encoding="utf-8", xml_declaration=True), mimetype="application/xml")


def render_documentation_template(template):
    """Return 404 for an absent page, without hiding errors inside existing pages."""
    try:
        current_app.jinja_env.loader.get_source(current_app.jinja_env, template)
    except TemplateNotFound:
        abort(404)
    return render_template(template)


@documentation.route("/docs/<framework>", strict_slashes=False)
def framework_docs(framework):
    if framework in PYTHON_ALIASES:
        return redirect("/docs/python", code=302)
    return render_documentation_template(f"docs_{framework}.html")


@documentation.route("/docs/<framework>/<page>", strict_slashes=False)
def doc_page(framework, page):
    if framework in PYTHON_ALIASES:
        if page in {"installation", "middleware", "commands", "setup"}:
            adapter = "fastapi" if framework == "fast" else framework
            return redirect(f"/docs/python/setup/{adapter}", code=302)
        if page in {"architecture", "reference"}:
            return redirect("/docs/python/architecture", code=302)
        if page in {"operations", "cli", "testing"}:
            return redirect("/docs/python/operations", code=302)
        return redirect("/docs/python/adapters", code=302)

    if page == "setup" and framework in SETUP_DEFAULTS:
        return redirect(f"/docs/{framework}/setup/{SETUP_DEFAULTS[framework]}", code=302)
    return render_documentation_template(f"docs_{framework}_{page}.html")


@documentation.route("/<language>/setup/<subframework>", strict_slashes=False)
@documentation.route("/docs/<language>/setup/<subframework>", strict_slashes=False)
def doc_setup_subframework(language, subframework):
    template = f"docs_{language}_setup_{subframework}.html"
    # Validate the destination before redirecting short URLs.
    try:
        current_app.jinja_env.loader.get_source(current_app.jinja_env, template)
    except TemplateNotFound:
        abort(404)
    if not request.path.startswith("/docs/"):
        return redirect(f"/docs/{language}/setup/{subframework}", code=302)
    return render_template(template)
