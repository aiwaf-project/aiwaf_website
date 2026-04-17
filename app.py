from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

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

@app.route('/docs/<framework>')
def framework_docs(framework):
    """Framework-specific documentation overview"""
    return render_template(f'docs_{framework}.html')

@app.route('/docs/<framework>/<page>')
def doc_page(framework, page):
    """Specific documentation pages"""
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
