import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    # Create the app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Configure the database
    database_url = os.environ.get("DATABASE_URL") or "sqlite:///pls_travels.db"
    
    # Configure for PostgreSQL production database
    if database_url.startswith("postgresql://"):
        # Use connection pooling for PostgreSQL
        database_url = database_url.replace('.us-east-2', '-pooler.us-east-2')
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 5,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 30,
            "max_overflow": 10
        }
    else:
        # Fallback to SQLite for local development
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    
    # File upload configuration
    app.config["UPLOAD_FOLDER"] = "uploads"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # type: ignore
    login_manager.login_message = 'Please log in to access this page.'

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Add template functions
    from datetime import datetime
    
    @app.template_global()
    def moment():
        class MomentJS:
            def format(self, format_str):
                now = datetime.now()
                format_mapping = {
                    'MMMM DD, YYYY': now.strftime('%B %d, %Y'),
                    'MMM DD, YYYY': now.strftime('%b %d, %Y'), 
                    'YYYY-MM-DD': now.strftime('%Y-%m-%d'),
                }
                return format_mapping.get(format_str, now.strftime('%Y-%m-%d'))
            
            def date(self):
                return datetime.now().date()
        
        return MomentJS()

    # Register blueprints
    from auth import auth_bp
    from admin_routes import admin_bp
    from manager_routes import manager_bp
    from driver_routes import driver_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(driver_bp, url_prefix='/driver')

    # Create tables
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        
        # Create initial admin user if doesn't exist
        from models import User, Branch
        from werkzeug.security import generate_password_hash
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            from models import UserRole, UserStatus
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@plstravels.com'
            admin.password_hash = generate_password_hash('admin123')
            admin.role = UserRole.ADMIN
            admin.status = UserStatus.ACTIVE
            admin.first_name = 'System'
            admin.last_name = 'Administrator'
            db.session.add(admin)
            
        # Create default branches
        if not Branch.query.first():
            from models import Region
            # Create a default region first
            region = Region()
            region.name = 'South India'
            region.code = 'SI'
            region.state = 'Tamil Nadu'
            region.country = 'India'
            db.session.add(region)
            db.session.flush()  # Get the ID
            
            chennai = Branch()
            chennai.name = 'Chennai HQ'
            chennai.code = 'CHN'
            chennai.region_id = region.id
            chennai.city = 'Chennai'
            chennai.address = 'Chennai, Tamil Nadu'
            chennai.target_revenue_monthly = 500000.0
            
            bangalore = Branch()
            bangalore.name = 'Bangalore Office'
            bangalore.code = 'BLR'
            bangalore.region_id = region.id
            bangalore.city = 'Bangalore'
            bangalore.address = 'Bangalore, Karnataka'
            bangalore.target_revenue_monthly = 400000.0
            db.session.add(chennai)
            db.session.add(bangalore)
            
        # Create active driver profile for admin user
        from models import Driver, DriverStatus
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user and not admin_user.driver_profile:
            # Get default branch
            default_branch = Branch.query.first()
            if default_branch:
                admin_driver = Driver()
                admin_driver.user_id = admin_user.id
                admin_driver.branch_id = default_branch.id
                admin_driver.employee_id = 'EMP000001'  # Special ID for admin
                admin_driver.full_name = f"{admin_user.first_name} {admin_user.last_name}"
                admin_driver.status = DriverStatus.ACTIVE  # Make active so they can access duty management
                admin_driver.approved_by = admin_user.id  # Self-approved
                admin_driver.approved_at = datetime.utcnow()
                db.session.add(admin_driver)
        
        # Activate any pending drivers (for demo/testing purposes)
        pending_drivers = Driver.query.filter_by(status=DriverStatus.PENDING).all()
        for driver in pending_drivers:
            driver.status = DriverStatus.ACTIVE
            driver.approved_by = admin_user.id if admin_user else None
            driver.approved_at = datetime.utcnow()
            
        db.session.commit()

    # API routes
    @app.route('/api/calculate-salary', methods=['POST'])
    def calculate_salary():
        from flask import request, jsonify
        from utils import calculate_tripsheet
        
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No input provided"}), 400

        # Handle single row or multiple rows
        if isinstance(data, dict):
            result = calculate_tripsheet(data)
        elif isinstance(data, list):
            result = [calculate_tripsheet(row) for row in data]
        else:
            return jsonify({"error": "Invalid input format"}), 400

        return jsonify(result)

    # Root route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        
        if current_user.is_authenticated:
            from models import UserRole
            if current_user.role == UserRole.ADMIN:
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == UserRole.MANAGER:
                return redirect(url_for('manager.dashboard'))
            elif current_user.role == UserRole.DRIVER:
                return redirect(url_for('driver.dashboard'))
        
        return redirect(url_for('auth.login'))
    
    # Add direct /login route for convenience
    @app.route('/login')
    def login_redirect():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    return app

app = create_app()
