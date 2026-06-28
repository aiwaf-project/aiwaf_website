from flask import Flask, render_template, jsonify, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
# SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000").rstrip("/")
SITE_URL = "https://aiwaf.org/"
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

from aiwaf.flask import AIWAF

aiwaf = AIWAF(
    app,
    middlewares=[
        "logging",
        "header_validation",
        "ip_keyword_block",
        "rate_limit",
        "geo_block",
        "ai_anomaly",
        "uuid_tamper",
    ],
)


@app.context_processor
def inject_seo_defaults():
    """Inject SEO metadata defaults for all rendered pages."""
    path = request.path.rstrip("/") or "/"
    title_map = {
        "/": "AIWAF Documentation | Python, JavaScript, PHP, Java, and Rust Security Guides",
        "/docs": "AIWAF Documentation Hub | Comprehensive Deep Dives for All Languages",
        "/docs/python": "AIWAF Python Deep Dive | Architecture and Operations",
        "/docs/python/setup": "AIWAF Python Setup Guide | End-to-End Installation and Validation",
        "/docs/python/architecture": "AIWAF Python Architecture | Core Modules and Runtime Flow",
        "/docs/python/adapters": "AIWAF Python Adapters | Django, Flask, FastAPI Integration",
        "/docs/python/operations": "AIWAF Python Operations | CLI, Testing, Packaging",
        "/docs/javascript": "AIWAF-JS Deep Dive | Node.js Security Middleware Reference",
        "/docs/javascript/setup": "AIWAF-JS Setup Guide | Node.js End-to-End Integration",
        "/docs/javascript/architecture": "AIWAF-JS Architecture | Middleware Pipeline and Adapters",
        "/docs/javascript/operations": "AIWAF-JS Operations | CLI, Config, Testing, Packaging",
        "/docs/php": "AIWAF-PHP Deep Dive | PHP Security Integration Reference",
        "/docs/php/setup": "AIWAF-PHP Setup Guide | End-to-End PHP Integration",
        "/docs/php/architecture": "AIWAF-PHP Architecture | Runtime Flow and Core Modules",
        "/docs/php/operations": "AIWAF-PHP Operations | Config, Testing, Packaging",
        "/docs/java": "AIWAF-Java Deep Dive | Spring and Servlet Security Reference",
        "/docs/java/setup": "AIWAF-Java Setup Guide | End-to-End Java Integration",
        "/docs/java/architecture": "AIWAF-Java Architecture | Request Pipeline and Core Modules",
        "/docs/java/operations": "AIWAF-Java Operations | CLI, Config, Testing, Packaging",
        "/docs/rust": "aiwaf-rust Guide | PyO3 and WASM Accelerator Overview",
        "/docs/rust/bindings": "aiwaf-rust Bindings API | Python and WASM Functions",
        "/docs/rust/operations": "aiwaf-rust Build and Operations | Packaging and Validation",
    }
    description_map = {
        "/": "Official AIWAF documentation for Python, JavaScript, PHP, Java, and Rust integrations, setup guides, architecture, and operational best practices.",
        "/docs": "Browse AIWAF deep-dive documentation for all implementations, including setup, architecture, and operations.",
        "/docs/python": "Comprehensive Python reference for AIWAF covering architecture, adapters, storage, training lifecycle, and runtime behavior.",
        "/docs/python/setup": "End-to-end setup guide for AIWAF in Django, Flask, and FastAPI with production-ready configuration and troubleshooting.",
        "/docs/python/architecture": "Detailed architecture guide for AIWAF Python core modules, storage primitives, training pipeline, and security controls.",
        "/docs/python/adapters": "Framework execution details for AIWAF Python adapters across Django, Flask, and FastAPI.",
        "/docs/python/operations": "AIWAF Python operational guide with CLI, testing strategy, release surface, and production checklists.",
        "/docs/javascript": "Comprehensive Node.js reference for aiwaf-js covering middleware pipeline, framework adapters, and core runtime behavior.",
        "/docs/javascript/setup": "End-to-end setup guide for aiwaf-js across Express, Fastify, Hapi, Koa, NestJS, Next.js, AdonisJS, and Sails.",
        "/docs/javascript/architecture": "aiwaf-js architecture guide covering request flow, adapters, storage strategy, and model training lifecycle.",
        "/docs/javascript/operations": "aiwaf-js operations guide for CLI commands, AIWAF_* config, testing workflow, packaging, and operational notes.",
        "/docs/php": "Comprehensive PHP reference for aiwaf-php covering integration patterns, configuration model, runtime artifacts, and training workflow.",
        "/docs/php/setup": "End-to-end setup guide for aiwaf-php across plain PHP, Laravel, Symfony, and WordPress-style bootstraps.",
        "/docs/php/architecture": "Deep architecture reference for aiwaf-php including protect() flow, module responsibilities, persistence, and training lifecycle.",
        "/docs/php/operations": "Operational guide for aiwaf-php covering scripts, configuration layering, testing commands, packaging, and deployment notes.",
        "/docs/java": "Comprehensive Java reference for aiwaf-java covering Spring/Servlet integration, configuration model, runtime stores, and request pipeline behavior.",
        "/docs/java/setup": "End-to-end setup guide for aiwaf-java with Maven install, Spring/Servlet wiring, runtime storage setup, and validation steps.",
        "/docs/java/architecture": "Deep architecture reference for aiwaf-java including AiwafEngine flow, module responsibilities, path-rule behavior, and runtime layering.",
        "/docs/java/operations": "Operational guide for aiwaf-java covering CLI commands, AiwafConfig controls, test workflows, and production hardening notes.",
        "/docs/rust": "End-to-end aiwaf-rust guide for Rust core, PyO3 Python module, and WASM package workflows.",
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


@app.route('/robots.txt')
def robots():
    """Search engine crawl directives."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /aiwaf/admin\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return Response(content, mimetype="text/plain")


@app.route('/sitemap.xml')
def sitemap():
    """Basic XML sitemap for primary documentation pages."""
    routes = [
        "/",
        "/docs",
        "/docs/python",
        "/docs/python/setup",
        "/docs/python/architecture",
        "/docs/python/adapters",
        "/docs/python/operations",
        "/docs/javascript",
        "/docs/javascript/setup",
        "/docs/javascript/architecture",
        "/docs/javascript/operations",
        "/docs/php",
        "/docs/php/setup",
        "/docs/php/architecture",
        "/docs/php/operations",
        "/docs/java",
        "/docs/java/setup",
        "/docs/java/architecture",
        "/docs/java/operations",
        "/docs/rust",
        "/docs/rust/bindings",
        "/docs/rust/operations",
    ]
    now = datetime.utcnow().strftime("%Y-%m-%d")
    url_nodes = "".join(
        (
            "<url>"
            f"<loc>{SITE_URL}{path}</loc>"
            f"<lastmod>{now}</lastmod>"
            "<changefreq>weekly</changefreq>"
            "<priority>0.8</priority>"
            "</url>"
        )
        for path in routes
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{url_nodes}"
        "</urlset>"
    )
    return Response(xml, mimetype="application/xml")

@app.route('/docs/<framework>')
def framework_docs(framework):
    """Framework-specific documentation overview"""
    if framework in {'django', 'flask', 'fastapi', 'fast'}:
        return redirect('/docs/python', code=302)
    return render_template(f'docs_{framework}.html')

@app.route('/docs/<framework>/<page>')
def doc_page(framework, page):
    """Specific documentation pages"""
    if framework in {'django', 'flask', 'fastapi', 'fast'}:
        if page in {'installation', 'middleware', 'commands', 'setup'}:
            return redirect('/docs/python/setup', code=302)
        if page in {'architecture', 'reference'}:
            return redirect('/docs/python/architecture', code=302)
        if page in {'operations', 'cli', 'testing'}:
            return redirect('/docs/python/operations', code=302)
        return redirect('/docs/python/adapters', code=302)
    return render_template(f'docs_{framework}_{page}.html')

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
            from aiwaf_flask.storage import add_ip_whitelist
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
            from aiwaf_flask.storage import add_ip_blacklist
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
            from aiwaf_flask.storage import add_keyword
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
    
    print(f"🚀 Starting AIWAF Documentation on port {port}")
    print(f"Debug mode: {debug_mode}")
    
    # Run the app
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode
    )
