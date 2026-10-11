"""Copy to /var/www/aiwaf_org_wsgi.py to serve the protected website."""

import sys

project_home = "/home/aayushgauba/aiwaf_website"
sys.path.insert(0, project_home)

from wsgi import application
