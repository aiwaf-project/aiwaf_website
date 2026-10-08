# Deploy the documentation website

The primary application is app.py, exported as application by wsgi.py. It uses AIWAF CSV state in aiwaf_data, request logs in logs, and a local SQLite URI initialized through Flask-SQLAlchemy. MySQL analytics and SSH tunneling belong to simple_app.py; they are not required by the primary WSGI application. /health reports liveness, not database or Redis readiness.

## Install and start

Use a Python environment compatible with requirements.txt. Several pinned numerical dependencies require a newer interpreter than AIWAF's own minimum; runtime.txt records this website's requested runtime.

~~~bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY='replace-with-a-generated-secret'
export PORT=8080
gunicorn --config gunicorn.conf.py wsgi:application
~~~

Run from the repository root. gunicorn.conf.py uses two sync workers, a 30-second timeout, stdout/stderr logging, and PORT (default 8080). Its /dev/shm worker temporary directory is intended for Linux deployments. Set a suitable worker_tmp_dir if your host lacks it. python wsgi.py and python app.py start Flask's development server; use the WSGI export for hosting.

app.py reads SECRET_KEY, PORT, and SITE_URL (default https://aiwaf.org). Set SITE_URL to the public staging domain when applicable; trailing slashes are normalized. Configure AIWAF through app.config before AIWAF(app), including aiwaf_config.py. The primary app does not consume DB_USER, DB_PASSWORD, DB_HOST, or DATABASE_URL. The .env.example file also contains settings for the alternate runner; select only the settings your runner uses.

## DigitalOcean App Platform

Use .do/app.yaml with the actual website repository and branch. Its run command is Gunicorn with gunicorn.conf.py and wsgi:application; its health check is /health. Set SECRET_KEY as a platform secret and PORT to the service port. Procfile uses the same Gunicorn entrypoint.

Provide writable locations for runtime state and logs. Ephemeral filesystem state may disappear during replacement or redeployment. Persist state outside the disposable application filesystem when it must survive. CSV files alone do not make rate-limit counters shared across workers: configure and verify a shared rate cache separately. The Flask rate cache can fall back to memory if Redis initialization fails, so test behavior across workers rather than assuming that setting a URL is enough.

## Hosted WSGI, including PythonAnywhere

Select the website virtual environment in the host's web application settings. In the host's WSGI configuration, add the checkout to sys.path and import the export:

~~~python
import sys

checkout = '/home/YOUR_USERNAME/aiwaf_website'
if checkout not in sys.path:
    sys.path.insert(0, checkout)
from wsgi import application
~~~

Replace the username and checkout path. Ensure the worker can read templates/static files and write runtime state. The host controls its WSGI process; do not launch Gunicorn from the host's WSGI file. Reload the web application after updating source or dependencies.

Before reloading, check imports in the same virtual environment and checkout:

~~~bash
python -c "from wsgi import application; print(application.url_map)"
aiwaf init --framework flask --app app:app
~~~

Importing wsgi starts the actual application's initialization. This can create runtime state and expose missing dependencies; documentation-only tests intentionally do not perform this check.

## Verify after deployment

~~~bash
curl -i https://aiwaf.org/health
# Match the site's header policy when probing protected documentation.
probe_docs() {
  curl -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36' \
    -H 'Accept: text/html' -H 'Accept-Language: en-US' -H 'Accept-Encoding: identity' "$@"
}
probe_docs -i https://aiwaf.org/docs/python/setup
probe_docs -i https://aiwaf.org/python/setup/django
probe_docs -fL https://aiwaf.org/docs/python/setup/django
probe_docs -f https://aiwaf.org/docs/configuration
probe_docs -f https://aiwaf.org/docs/migration
probe_docs -f https://aiwaf.org/docs/troubleshooting
~~~

The explicit /health exemption permits plain health probes. Protected documentation can reject curl default headers; use the browser-style probe or a browser for those pages. Expect /health to return 200; the setup landing and short URL to redirect to the canonical Django guide; and the final pages to return 200. Replace the domain for staging. Unknown documentation pages should return 404. Inspect canonical tags and sitemap locations for the deployed domain.

A 500 requires the server error log/traceback: verify that documentation.py and the templates are deployed together, that the active worker imports the expected checkout, and that the host was reloaded. A 403 can originate from AIWAF or an upstream proxy; inspect response details and logs before changing policy. See /docs/troubleshooting for package and route diagnostics.

## Rollback

Keep the previous code revision, dependency versions, configuration, and backups of writable state/model files. Restore compatible code and state together, then reload workers and repeat the HTTP checks. A successful template test does not establish that production has been updated.
