from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from documentation import documentation

# Load environment variables
load_dotenv()

app = Flask(__name__)
SITE_URL = os.environ.get("SITE_URL", "https://aiwaf.org").rstrip("/")
app.config["SITE_URL"] = SITE_URL
# Load optional AIWAF-specific config overrides.
app.config.from_pyfile("aiwaf_config.py", silent=True)

# Basic Flask configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aiwaf-docs-secret-key')

# Configure SQLAlchemy (required by aiwaf-flask even for CSV mode)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aiwaf_temp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# AIWAF Configuration - CSV Storage (no database needed!)
app.config['AIWAF_USE_CSV'] = True
app.config['AIWAF_DATA_DIR'] = 'aiwaf_data'  # Directory for CSV files
app.config['AIWAF_ENABLE_LOGGING'] = True       # Enable logging
app.config['AIWAF_LOG_DIR'] = 'logs'            # Log directory
app.config['AIWAF_LOG_FORMAT'] = 'common'     # Format: combined, common, csv, json
app.config["AIWAF_USE_RUST"] = True
# AIWAF Protection Settings
app.config['AIWAF_RATE_WINDOW'] = 60     # 60 seconds window
app.config['AIWAF_RATE_MAX'] = 100       # 100 requests per minute
app.config['AIWAF_RATE_FLOOD'] = 200     # Auto-block at 200 requests
app.config['AIWAF_MIN_FORM_TIME'] = 2.0  # Minimum form submission time

# Initialize AIWAF protection

from aiwaf.flask import AIWAF, aiwaf_exempt

aiwaf = AIWAF(app)


@app.context_processor
def inject_seo_defaults():
    """Inject SEO metadata defaults for all rendered pages."""
    path = request.path.rstrip("/") or "/"
    title_map = {
        "/": "AIWAF Documentation | Python, Node.js, Java, and Rust/WASM Security Guides",
        "/docs": "AIWAF Documentation Hub | Comprehensive Deep Dives for All Languages",
        "/docs/contents": "AIWAF Documentation Contents | Tutorials, Topics, How-to Guides, and Reference",
        "/docs/testing": "Testing AIWAF Applications | Flask, Django, and Protection Integration Tests",
        "/docs/getting_started": "Getting Started with AIWAF | Tutorials and Framework Guides",
        "/docs/tutorial/installation": "AIWAF Tutorial | Prepare Your Environment",
        "/docs/tutorial/application": "AIWAF Tutorial | Create Your First Protected App",
        "/docs/tutorial/routes": "AIWAF Tutorial | Discover Live Routes",
        "/docs/tutorial/verification": "AIWAF Tutorial | Verify a Rate Limit",
        "/docs/tutorial/policies": "AIWAF Tutorial | Add a Route Policy",
        "/docs/tutorial/logging": "AIWAF Tutorial | Read Logs and Plan Training",
        "/docs/architecture": "How AIWAF Works | System Architecture and Request Lifecycle",
        "/docs/configuration": "AIWAF Configuration Reference | Runtime Defaults and Precedence",
        "/docs/migration": "AIWAF Upgrade Guide | Package, State, and Model Migration",
        "/docs/troubleshooting": "AIWAF Troubleshooting | CLI, Routes, Training, and Verification",
        "/docs/python": "AIWAF Python Deep Dive | Architecture and Operations",
        "/docs/python/setup/django": "AIWAF Django Setup Guide | End-to-End Installation",
        "/docs/python/setup/flask": "AIWAF Flask Setup Guide | End-to-End Installation",
        "/docs/python/setup/fastapi": "AIWAF FastAPI Setup Guide | End-to-End Installation",
        "/docs/javascript/setup": "AIWAF Node.js Setup Guide | Node.js End-to-End Integration",
        "/docs/javascript/setup/express": "AIWAF Express Setup Guide | Node.js Integration",
        "/docs/javascript/setup/fastify": "AIWAF Fastify Setup Guide | Node.js Integration",
        "/docs/javascript/setup/hapi": "AIWAF Hapi Setup Guide | Node.js Integration",
        "/docs/javascript/setup/koa": "AIWAF Koa Setup Guide | Node.js Integration",
        "/docs/javascript/setup/nestjs": "AIWAF NestJS Setup Guide | Node.js Integration",
        "/docs/javascript/setup/nextjs": "AIWAF Next.js Setup Guide | Node.js Integration",
        "/docs/javascript/setup/adonis": "AIWAF AdonisJS Setup Guide | Node.js Integration",
        "/docs/javascript/setup/sails": "AIWAF Sails Setup Guide | Node.js Integration",
        "/docs/javascript/architecture": "AIWAF Node.js Architecture | Middleware Pipeline and Adapters",
        "/docs/javascript/operations": "AIWAF Node.js Operations | CLI, Config, Testing, Packaging",
        "/docs/php": "AIWAF PHP | Legacy Integration Reference",
        "/docs/php/setup": "AIWAF PHP Setup | Legacy Reference",
        "/docs/php/setup/plain": "AIWAF Plain PHP | Legacy Setup Reference",
        "/docs/php/setup/laravel": "AIWAF Laravel | Legacy Setup Reference",
        "/docs/php/setup/symfony": "AIWAF Symfony | Legacy Setup Reference",
        "/docs/php/setup/wordpress": "AIWAF WordPress | Legacy Setup Reference",
        "/docs/php/architecture": "AIWAF PHP Architecture | Legacy Reference",
        "/docs/php/operations": "AIWAF PHP Operations | Legacy Reference",
        "/docs/java": "AIWAF-Java Deep Dive | Spring and Servlet Security Reference",
        "/docs/java/setup": "AIWAF-Java Setup Guide | End-to-End Java Integration",
        "/docs/java/setup/servlet": "AIWAF Java Servlet Setup Guide | Core Integration",
        "/docs/java/setup/spring": "AIWAF Spring Setup Guide | Java Integration",
        "/docs/java/architecture": "AIWAF-Java Architecture | Request Pipeline and Core Modules",
        "/docs/java/operations": "AIWAF-Java Operations | CLI, Config, Testing, Packaging",
        "/docs/rust": "aiwaf-rust Guide | PyO3 and WASM Accelerator Overview",
        "/docs/rust/architecture": "AIWAF Rust and WASM Architecture | Bindings, Features, and Forests",
        "/docs/rust/bindings": "aiwaf-rust Bindings API | Python and WASM Functions",
        "/docs/rust/operations": "aiwaf-rust Build and Operations | Packaging and Validation",
    }
    description_map = {
        "/": "Official AIWAF documentation for Python, Node.js, Java, and Rust/WASM integrations, setup guides, architecture, and operational best practices.",
        "/docs": "Browse AIWAF deep-dive documentation for all implementations, including setup, architecture, and operations.",
        "/docs/architecture": "Understand AIWAF request processing, route policies, runtime state, response-aware decisions, and the offline learning loop across Python, Node.js, Java, and Rust/WASM.",
        "/docs/configuration": "Runtime-specific AIWAF settings, types, source defaults, configuration precedence, exemptions, and shared state.",
        "/docs/migration": "Upgrade AIWAF packages, migrate reputation state, regenerate route manifests and models, and plan compatible rollbacks.",
        "/docs/troubleshooting": "Diagnose AIWAF import targets, missing routes, website errors, proxy addresses, shared counters, and training failures.",
        "/docs/python": "Comprehensive Python reference for AIWAF covering architecture, adapters, storage, training lifecycle, and runtime behavior.",
        "/docs/python/setup": "End-to-end setup guide for AIWAF in Python with production-ready configuration and troubleshooting.",
        "/docs/python/setup/django": "End-to-end setup guide for AIWAF in Django with production-ready configuration and troubleshooting.",
        "/docs/python/setup/flask": "End-to-end setup guide for AIWAF in Flask with production-ready configuration and troubleshooting.",
        "/docs/python/setup/fastapi": "End-to-end setup guide for AIWAF in FastAPI with production-ready configuration and troubleshooting.",
        "/docs/python/architecture": "Detailed architecture guide for AIWAF Python core modules, storage primitives, training pipeline, and security controls.",
        "/docs/python/adapters": "Framework execution details for AIWAF Python adapters across Django, Flask, and FastAPI.",
        "/docs/python/operations": "AIWAF Python operational guide with CLI, testing strategy, release surface, and production checklists.",
        "/docs/javascript": "Comprehensive Node.js reference for aiwaf covering middleware pipeline, framework adapters, and core runtime behavior.",
        "/docs/javascript/setup": "End-to-end setup guide for aiwaf across all Node frameworks.",
        "/docs/javascript/setup/express": "End-to-end setup guide for aiwaf in Express.",
        "/docs/javascript/setup/fastify": "End-to-end setup guide for aiwaf in Fastify.",
        "/docs/javascript/setup/hapi": "End-to-end setup guide for aiwaf in Hapi.",
        "/docs/javascript/setup/koa": "End-to-end setup guide for aiwaf in Koa.",
        "/docs/javascript/setup/nestjs": "End-to-end setup guide for aiwaf in NestJS.",
        "/docs/javascript/setup/nextjs": "End-to-end setup guide for aiwaf in Next.js.",
        "/docs/javascript/setup/adonis": "End-to-end setup guide for aiwaf in AdonisJS.",
        "/docs/javascript/setup/sails": "End-to-end setup guide for aiwaf in Sails.",
        "/docs/javascript/architecture": "aiwaf architecture guide covering request flow, adapters, storage strategy, and model training lifecycle.",
        "/docs/javascript/operations": "aiwaf operations guide for CLI commands, AIWAF_* config, testing workflow, packaging, and operational notes.",
        "/docs/php": "Legacy PHP reference. The current AIWAF monorepo supports Python, Node.js, Java, and Rust/WASM; PHP is absent from the current source tree.",
        "/docs/php/setup": "Legacy setup reference for aiwaf-php across plain PHP and frameworks.",
        "/docs/php/setup/plain": "Legacy setup reference for aiwaf-php for Plain PHP.",
        "/docs/php/setup/laravel": "Legacy setup reference for aiwaf-php for Laravel.",
        "/docs/php/setup/symfony": "Legacy setup reference for aiwaf-php for Symfony.",
        "/docs/php/setup/wordpress": "Legacy setup reference for aiwaf-php for WordPress.",
        "/docs/php/architecture": "Legacy architecture reference for aiwaf-php. PHP is absent from the current AIWAF monorepo.",
        "/docs/php/operations": "Legacy operations reference for aiwaf-php. PHP is absent from the current AIWAF monorepo.",
        "/docs/java": "Comprehensive Java reference for aiwaf-java covering Spring/Servlet integration, configuration model, runtime stores, and request pipeline behavior.",
        "/docs/java/setup": "End-to-end setup guide for aiwaf-java with Maven install.",
        "/docs/java/setup/servlet": "End-to-end setup guide for aiwaf-java with Servlet integration.",
        "/docs/java/setup/spring": "End-to-end setup guide for aiwaf-java with Spring Boot integration.",
        "/docs/java/architecture": "Deep architecture reference for aiwaf-java including AiwafEngine flow, module responsibilities, path-rule behavior, and runtime layering.",
        "/docs/java/operations": "Operational guide for aiwaf-java covering CLI commands, AiwafConfig controls, test workflows, and production hardening notes.",
        "/docs/rust": "End-to-end aiwaf-rust guide for Rust core, PyO3 Python module, and WASM package workflows.",
        "/docs/rust/architecture": "Explain AIWAF Rust core and host bindings, reusable matchers, stateful feature extraction, Isolation Forest scoring, JSON artifacts, and acceleration boundaries.",
        "/docs/rust/bindings": "Function-level aiwaf-rust API reference for PyO3 and wasm-bindgen exports, including IsolationForest semantics.",
        "/docs/rust/operations": "Build, package, troubleshoot, and validate aiwaf-rust Python and WASM artifacts.",
    }
    seo_title = title_map.get(path, "AIWAF Documentation")
    seo_description = description_map.get(
        path,
        "AIWAF security documentation and framework integration guides.",
    )
    canonical_url = f"{SITE_URL}{request.path}"
    return {
        "site_url": SITE_URL,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "canonical_url": canonical_url,
        "seo_image": f"{SITE_URL}/static/og-image.png",
    }

@app.route('/')
def home():
    """Homepage with hero section and framework overview"""
    return render_template('home.html')

@app.route('/health')
def health():
    """Simple health check endpoint for deployment"""
    return jsonify({
        "status": "healthy", 
        "message": "AIWAF Documentation is running",
        "version": "1.0.0"
    })

@app.route('/docs')
def docs():
    """Main documentation landing page"""
    return render_template('docs.html')


app.register_blueprint(documentation)
# Keep crawler discovery public even if the optional path-exemption config is absent.
for crawler_endpoint in ("documentation.sitemap", "documentation.robots"):
    app.view_functions[crawler_endpoint] = aiwaf_exempt(app.view_functions[crawler_endpoint])

@app.route('/aiwaf/admin')
def aiwaf_admin():
    """AIWAF Administration Interface"""
    return render_template('aiwaf_admin.html')

# AIWAF Management Routes
@app.route('/aiwaf/status')
def aiwaf_status():
    """AIWAF protection status and statistics"""
    try:
        # Get basic status information
        data_dir = app.config.get('AIWAF_DATA_DIR', 'aiwaf_data')
        
        status = {
            'protection_enabled': True,
            'storage_type': 'CSV',
            'data_directory': data_dir,
            'configuration': {
                'rate_window': app.config.get('AIWAF_RATE_WINDOW', 60),
                'rate_max': app.config.get('AIWAF_RATE_MAX', 100),
                'rate_flood': app.config.get('AIWAF_RATE_FLOOD', 200),
                'min_form_time': app.config.get('AIWAF_MIN_FORM_TIME', 2.0)
            }
        }
        
        # Check if CSV files exist
        import os
        if os.path.exists(data_dir):
            files = os.listdir(data_dir)
            status['csv_files'] = files
        else:
            status['csv_files'] = []
            
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e), 'protection_enabled': False}), 500

@app.route('/aiwaf/whitelist', methods=['GET', 'POST'])
def aiwaf_whitelist():
    """Manage IP whitelist"""
    if request.method == 'POST':
        try:
            from aiwaf.flask.storage import add_ip_whitelist
            ip = request.json.get('ip')
            if ip:
                add_ip_whitelist(ip)
                return jsonify({'success': True, 'message': f'IP {ip} added to whitelist'})
            else:
                return jsonify({'success': False, 'message': 'IP address required'}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET request - return current whitelist
    try:
        data_dir = app.config.get('AIWAF_DATA_DIR', 'aiwaf_data')
        whitelist_file = os.path.join(data_dir, 'whitelist.csv')
        whitelist = []
        
        if os.path.exists(whitelist_file):
            import csv
            with open(whitelist_file, 'r') as f:
                reader = csv.DictReader(f)
                whitelist = list(reader)
        
        return jsonify({'whitelist': whitelist})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/aiwaf/blacklist', methods=['GET', 'POST'])
def aiwaf_blacklist():
    """Manage IP blacklist"""
    if request.method == 'POST':
        try:
            from aiwaf.flask.storage import add_ip_blacklist
            ip = request.json.get('ip')
            reason = request.json.get('reason', 'Manual block')
            
            if ip:
                add_ip_blacklist(ip, reason=reason)
                return jsonify({'success': True, 'message': f'IP {ip} added to blacklist'})
            else:
                return jsonify({'success': False, 'message': 'IP address required'}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET request - return current blacklist
    try:
        data_dir = app.config.get('AIWAF_DATA_DIR', 'aiwaf_data')
        blacklist_file = os.path.join(data_dir, 'blacklist.csv')
        blacklist = []
        
        if os.path.exists(blacklist_file):
            import csv
            with open(blacklist_file, 'r') as f:
                reader = csv.DictReader(f)
                blacklist = list(reader)
        
        return jsonify({'blacklist': blacklist})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/aiwaf/keywords', methods=['GET', 'POST'])
def aiwaf_keywords():
    """Manage blocked keywords"""
    if request.method == 'POST':
        try:
            from aiwaf.flask.storage import add_keyword
            keyword = request.json.get('keyword')
            
            if keyword:
                add_keyword(keyword)
                return jsonify({'success': True, 'message': f'Keyword "{keyword}" added to blocklist'})
            else:
                return jsonify({'success': False, 'message': 'Keyword required'}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET request - return current keywords
    try:
        data_dir = app.config.get('AIWAF_DATA_DIR', 'aiwaf_data')
        keywords_file = os.path.join(data_dir, 'keywords.csv')
        keywords = []
        
        if os.path.exists(keywords_file):
            import csv
            with open(keywords_file, 'r') as f:
                reader = csv.DictReader(f)
                keywords = list(reader)
        
        return jsonify({'keywords': keywords})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Custom 404 page"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 page"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Get port from environment variable (for deployment platforms)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting AIWAF Documentation on port {port}")
    print(f"Debug mode: {debug_mode}")
    
    # Run the app
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode
    )
