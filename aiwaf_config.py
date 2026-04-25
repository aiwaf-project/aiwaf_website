"""
AIWAF runtime configuration for this docs website.
"""

# Skip AIWAF checks for crawler endpoints.
AIWAF_EXEMPT_PATHS = [
    "/robots.txt",
    "/sitemap.xml",
]
