"""
AIWAF runtime configuration for this docs website.
"""

# Skip AIWAF checks for liveness and crawler endpoints.
AIWAF_EXEMPT_PATHS = [
    "/health",
    "/robots.txt",
    "/sitemap.xml",
]
