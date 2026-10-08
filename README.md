# AIWAF Documentation Website

Flask documentation website for the [AIWAF monorepo](https://github.com/aiwaf-project/aiwaf). Python, Node.js, Java, and Rust/WASM are current runtimes; PHP pages are legacy reference. The upstream README is authoritative for package behavior and releases.

## Run locally

On Linux/macOS:

~~~bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python app.py
~~~

On Windows PowerShell:

~~~powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
~~~

Open http://localhost:5000. Set SECRET_KEY in the environment or a local .env file. app.py loads aiwaf_config.py before initializing protection and stores AIWAF data under aiwaf_data and request logs under logs. Flask-SQLAlchemy initializes a local SQLite URI; the primary runner does not use the alternate runner's MySQL analytics models.

## Generate routes

Run in this checkout with the same virtual environment used by the server:

~~~bash
aiwaf init --framework flask --app app:app
~~~

The target means the app object in app.py, not a filename. Use app:create_app for a factory. The output is .aiwaf/paths.json. Regenerate after changing registered routes. This command imports the live application and requires its dependencies and configuration.

## Documentation map

- /docs: runtime setup guides and source-version matrix.
- /docs/getting_started: learning paths and framework selection.
- /docs/tutorial/installation: a six-step first protected app tutorial with complete app and verification files.
- /docs/architecture: request lifecycle, policy, state, response observations, and training.
- /docs/configuration: runtime configuration, types, defaults, and precedence.
- /docs/migration: upgrades, npm package rename, blacklist and model migration.
- /docs/troubleshooting: import targets, manifests, block responses, training, and website routing.
- /docs/python/setup/flask, /docs/python/setup/django, /docs/python/setup/fastapi: Python guides.
- /docs/javascript, /docs/java, /docs/rust: other maintained runtimes.
- /health: HTTP liveness; /robots.txt and /sitemap.xml: crawler endpoints.

Both app.py and simple_app.py register documentation.py. Setup landing pages redirect to their default guide; short setup URLs redirect to canonical /docs URLs. simple_app.py is an alternate database/SSH-tunnel runner, not the production WSGI target.

## Production and verification

On a Linux host with Gunicorn:

~~~bash
gunicorn --config gunicorn.conf.py wsgi:application
~~~

See [DEPLOYMENT.md](DEPLOYMENT.md) for DigitalOcean and hosted WSGI setup. python app.py and python wsgi.py use Flask's development server.

~~~bash
python -m unittest discover -s tests -v
~~~

The documentation tests render templates and check routes and links without starting AIWAF or a database. They do not certify an installed package or live deployment. Verify the running application's /health and setup URLs after deploying.

## Maintenance

[COMPREHENSIVE_SETUP_GUIDE.md](COMPREHENSIVE_SETUP_GUIDE.md) covers installation and rollout across runtimes. [PROJECT_DETAILED_REFERENCE.md](PROJECT_DETAILED_REFERENCE.md) maps architecture to upstream sources. Keep these alongside the templates in version control. Runtime data, logs, .aiwaf manifests, virtual environments, local credentials, build outputs, and temporary release staging directories belong in .gitignore.

Configuration tables can be refreshed from a local monorepo checkout:

~~~bash
python scripts/build_configuration_reference.py ../aiwaf
~~~

The generated tables record the manifest versions and full source commit. Review changes to defaults and examples together before publishing. Source versions do not guarantee registry availability.

## Tutorial and search maintenance

The first-app tutorial has six linked chapters. Complete code snapshots live in examples/tutorial; data-example blocks in the templates must match those files. The smoke test installs no packages and starts no network server; run it in an environment with the Flask AIWAF extra:

~~~bash
python scripts/verify_flask_tutorial.py
~~~

It checks live route-manifest generation, three allowed requests followed by a 429, selective/full exemptions, and JSON log creation with temporary runtime state. Documentation CI checks the published Flask package separately from route/template tests.

Rebuild the search index after editing any documentation page or configuration-default include:

~~~bash
python scripts/build_docs_search.py
python -m unittest discover -s tests -v
~~~

The index is static and searches in the browser; queries are not sent to an external search service. Code-copy controls and section navigation are progressive enhancements; the tutorial and its previous/next links work without JavaScript. The route tests also detect stale search content and mismatched code snapshots.
