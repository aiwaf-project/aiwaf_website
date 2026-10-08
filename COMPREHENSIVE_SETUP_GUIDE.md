# AIWAF setup and rollout guide

All packages now live in https://github.com/aiwaf-project/aiwaf. The upstream README and package manifests are authoritative; this is the website's maintained walkthrough, not a separate Java repository manual. PHP integration pages remain legacy reference.

## Choose a runtime

| Application | Installation / source | Website guide |
| --- | --- | --- |
| Flask | pip install "aiwaf[flask]"; py/aiwaf/flask | /docs/python/setup/flask |
| Django | pip install "aiwaf[django]"; py/aiwaf/django | /docs/python/setup/django |
| FastAPI | pip install "aiwaf[fastapi]"; py/aiwaf/fast | /docs/python/setup/fastapi |
| Node.js | npm install aiwaf; js | /docs/javascript/setup/express |
| Java | java/pom.xml; java/src/main/java/com/aiwaf | /docs/java/setup/spring |
| Rust/Python | pip install aiwaf-rust; rust | /docs/rust/bindings |
| WASM | npm install aiwaf-wasm; rust/crates/aiwaf_wasm | /docs/rust/bindings |

The repository has independent package versions. For Java, select a published Maven version or build java with Maven; the version in java/pom.xml is not proof of registry availability. Java targets Java 17. It uses a native MaxMind DB reader, with no external GeoIP lookup process required.

## Minimal Flask application

Install the Flask extra and save as app.py:

~~~python
from flask import Flask
from aiwaf.flask import AIWAF

app = Flask(__name__)
app.config.update(AIWAF_RATE_WINDOW=10, AIWAF_RATE_MAX=20, AIWAF_RATE_FLOOD=40)
AIWAF(app, middlewares=['all'])

@app.get('/')
def home():
    return {'protected': True}
~~~

Run from its directory:

~~~bash
aiwaf init --framework flask --app app:app
flask --app app:app run
~~~

The CLI imports a module and application object. app.py is a filename; app:app is the import target. A factory uses app:create_app. Add all routes before generating .aiwaf/paths.json. Local/private client traffic may be exempt and is not evidence that public blocking policy was exercised.

## Other Python adapters

Django adds aiwaf.django to INSTALLED_APPS and aiwaf.django.middleware.all to MIDDLEWARE. Generate routes with:

~~~bash
aiwaf init --framework django --settings project.settings
~~~

FastAPI imports AIWAF from aiwaf.fast and uses nested constructor settings such as rate_limiting and storage. Generate routes with:

~~~bash
aiwaf init --framework fastapi --app app:app
~~~

Flask reads flat app.config values; Django reads settings.py values. Do not copy FastAPI constructor dictionaries into the Flask constructor. Follow the adapter-specific setup page for middleware ordering and settings.

## Node.js and Java

Replace old npm package imports with require('aiwaf') or the equivalent ES module import. Install middleware before the routes it protects. Choose the actual framework adapter; the website has separate Express, Fastify, Hapi, Koa, NestJS, Next.js, AdonisJS, and Sails guides.

Spring Boot auto-configuration registers the AIWAF filter and discovers live MVC mappings. Plain Servlet applications register AiwafServletFilter explicitly. Avoid running the filter and interceptor as two independent enforcement layers. Java's two-stage API uses actual response status and duration for anomaly features; streaming or committed responses cannot be replaced after bytes are sent.

## Configure and verify

Read /docs/configuration for defaults, option types, adapter differences, and precedence. Inspect enabled middleware and exemption policies. Test a normal public request, an intentionally blocked request, a rate-limit boundary, and the intended exempt health endpoint. Record the response and reason from logs. Test client IP resolution through your real proxy chain.

Use shared state when workers must enforce one policy. Verify which state the selected backend shares: a persisted blacklist does not automatically share rate counters. Java Redis 1.3 supports standalone mode and explicit failure policy; review namespace/schema compatibility before a rolling upgrade.

## Collect, train, and reload

Enable request logging, collect representative responses, and run the trainer for the selected runtime. /docs/python/operations, /docs/javascript/operations, /docs/java/operations, and /docs/rust/operations contain runtime commands. Confirm training thresholds, input paths, feature schema, output path, and model load diagnostics. Regenerate Python's old executable model artifacts using the current trainer; persisted Python state is JSON. Do not assume language-specific model artifacts are interchangeable.

Deploy the model and restart or reload through the runtime's documented mechanism. Retest normal traffic and blocking behavior. Keep compatible state/configuration/model backups for rollback. /docs/migration contains the upgrade sequence; /docs/troubleshooting covers common failures.

## This website

For the website itself, install requirements.txt, use app:app for route discovery, and host wsgi:application. See DEPLOYMENT.md. The shared documentation blueprint serves both application runners, but their database and initialization behavior differ.
