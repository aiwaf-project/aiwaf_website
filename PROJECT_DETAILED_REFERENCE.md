# AIWAF architecture and source reference

The source of truth is the single [AIWAF monorepo](https://github.com/aiwaf-project/aiwaf), including its README and manifests. This document maps the website's explanations to code. Source versions and registry releases are independent.

## Request lifecycle

1. A framework adapter converts the incoming method, path, headers, address, and parameters into runtime inputs.
2. Middleware selection and route policy determine which checks apply. Exemptions, manifests, and path overrides are part of policy evaluation.
3. Deterministic checks consult configuration and runtime state: IP/reputation, geo policy, headers, methods, keywords, timing, UUID signals, and rate counters.
4. A permitted request reaches the handler. The adapter records actual status and timing where supported.
5. Response observations update behavior state and logs. Offline training derives features and produces the next runtime model.

A request-only integration cannot supply actual response information. See /docs/architecture and each runtime architecture page for ordering and enforcement differences.

## Sources by responsibility

All paths are relative to the monorepo root.

| Responsibility | Sources |
| --- | --- |
| Python import-target CLI | py/aiwaf/cli.py |
| Python runtime configuration | py/aiwaf/core/runtime_config.py |
| Shared Python policy planning | py/aiwaf/core/middleware_plan.py, py/aiwaf/core/exemptions.py |
| Flask initialization | py/aiwaf/flask/flask_integration.py |
| Flask rate cache | py/aiwaf/flask/rate_limit_middleware.py |
| Python adapters | py/aiwaf/django, py/aiwaf/flask, py/aiwaf/fast |
| Node exports and adapters | js/index.js, js/lib |
| Node normalized options | js/lib/settingsCompat.js |
| Java engine/configuration | java/src/main/java/com/aiwaf/core/AiwafEngine.java, AiwafConfig.java |
| Java Spring integration | java/src/main/java/com/aiwaf/spring |
| Java Servlet integration | java/src/main/java/com/aiwaf/servlet |
| Rust core and bindings | rust/crates, rust/src |
| Releases and tests | .github/workflows, tests, js/test, java/src/test |

## Configuration boundaries

Flask uses app.config before registration; Django uses settings.py. FastAPI's runtime orchestrator accepts nested options backed by AIWAFConfig. The nested manager applies defaults, JSON file values, then recognized environment variables; explicit runtime options can override configuration afterward. These are different input surfaces, not identical parameter names.

Node settingsCompat resolves supported aliases, legacy AIWAF_SETTINGS, recognized environment variables, and defaults. Java exposes typed AiwafConfig fields and JSON/environment/Spring-property mappings. /docs/configuration records source defaults and links to the loaders. Proxy and private-address behavior are adapter-specific.

## State ownership

Configuration defines policy. Runtime storage contains mutable blacklist/exemption/keyword state; counters and recent history may use a separate cache. Model artifacts are another lifecycle, written by training and loaded for inference. Persisting one store does not make every worker share every other store.

Python Flask/FastAPI can use a shared rate cache. Node accepts a shared cache instead of its process-local fallback. Java's scoped per-engine storage context and Redis backend support distributed rate, timing, UUID, and anomaly history. Java 1.3 bounds Redis connection/pool waits and supports fail-open or fail-closed policy, with standalone Redis and state-schema guards.

## Models and response observations

The shared training intent uses six behavior features, but runtimes retain native implementations. Python models persist as JSON; old pickle/joblib artifacts are unsupported. Java also has explicit portable-model conversion paths; only use those when schema, feature order, and artifact validation match. General cross-runtime file copying is not a supported migration strategy.

Response-aware adapters can use actual status/duration. Java evaluateBeforeResponse/evaluateAfterResponse supplies these observations; evaluate(request) uses provisional response values. Once a response is committed, recording observations cannot retract sent bytes.

## Website routing and verification

The website is a separate Flask repository. documentation.py owns documentation routes. app.py and simple_app.py register the same blueprint. /docs/python/setup redirects to Django; /python/setup/django redirects to /docs/python/setup/django. A missing top-level page returns 404, while errors inside an existing template remain application errors.

Tests in tests/test_documentation_routes.py exercise routes and template rendering without WAF/database initialization. Their success does not verify a real package installation, training lifecycle, Redis deployment, or public website. Use DEPLOYMENT.md and /docs/troubleshooting to verify those separately.
