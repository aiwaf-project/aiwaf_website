"""
Simple Flask app runner that can work with or without SSH tunnel
"""
import os

# Try to import required modules, use fallbacks if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment variables")

try:
    from flask import Flask, render_template, jsonify, request, redirect
    print("✅ Flask imported successfully")
except ImportError:
    print("❌ Flask not available. Please install: pip install Flask")
    exit(1)

try:
    from flask_sqlalchemy import SQLAlchemy
    print("✅ Flask-SQLAlchemy imported successfully")
except ImportError:
    print("❌ Flask-SQLAlchemy not available. Please install: pip install Flask-SQLAlchemy")
    exit(1)

try:
    import pymysql
    pymysql.install_as_MySQLdb()
    print("✅ PyMySQL imported successfully")
except ImportError:
    print("❌ PyMySQL not available. Please install: pip install PyMySQL")
    exit(1)

# Create Flask app
app = Flask(__name__)

# Database configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# For production deployment, use direct connection
db_user = os.environ.get('DB_USER', 'aayushgauba')
db_password = os.environ.get('DB_PASSWORD', 'sykpon-bovtY9-vykbez')
db_host = os.environ.get('DB_HOST', 'aayushgauba.mysql.pythonanywhere-services.com')
db_port = os.environ.get('DB_PORT', '3306')
db_name = os.environ.get('DB_NAME', 'aayushgauba$aiwaf')

# Use direct DATABASE_URL for production (DigitalOcean, etc.)
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    database_url = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"Database URL: mysql+pymysql://{db_user}:***@{db_host}:{db_port}/{db_name}")

# Initialize database
db = SQLAlchemy(app)

# Database Models
class PageView(db.Model):
    """Track page views for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    page_path = db.Column(db.String(255), nullable=False)
    user_ip = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class UserFeedback(db.Model):
    """Store user feedback on documentation"""
    id = db.Column(db.Integer, primary_key=True)
    page_path = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    email = db.Column(db.String(120))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class DownloadStats(db.Model):
    """Track AIWAF downloads and installations"""
    id = db.Column(db.Integer, primary_key=True)
    framework = db.Column(db.String(50), nullable=False)
    version = db.Column(db.String(20))
    user_ip = db.Column(db.String(45))
    country = db.Column(db.String(2))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/health')
def health():
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy", 
        "message": "AIWAF Documentation is running",
        "database": db_status
    })

@app.route('/docs')
def docs():
    return render_template('docs.html')

@app.route('/docs/<framework>')
def framework_docs(framework):
    return render_template(f'docs_{framework}.html')

@app.route('/docs/<framework>/<page>')
def doc_page(framework, page):
    return render_template(f'docs_{framework}_{page}.html')

@app.route('/<language>/setup/<subframework>', strict_slashes=False)
@app.route('/docs/<language>/setup/<subframework>', strict_slashes=False)
def doc_setup_subframework(language, subframework):
    """Serve setup guides and redirect short URLs to their documentation URL."""
    if not request.path.startswith('/docs/'):
        return redirect(f'/docs/{language}/setup/{subframework}', code=302)
    return render_template(f'docs_{language}_setup_{subframework}.html')

if __name__ == '__main__':
    print("Initializing database...")
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            print("This is expected if connecting to external database without SSH tunnel")

    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Flask app on port {port}...")
    print(f"🌐 Access your app at: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
