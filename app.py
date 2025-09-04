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
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pls_travels.db")
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
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@plstravels.com'
            admin.password_hash = generate_password_hash('admin123')
            admin.role = 'admin'
            admin.is_active = True
            db.session.add(admin)
            
        # Create default branches
        if not Branch.query.first():
            chennai = Branch()
            chennai.name = 'Chennai HQ'
            chennai.city = 'Chennai'
            chennai.address = 'Chennai, Tamil Nadu'
            chennai.target_revenue = 500000.0
            
            bangalore = Branch()
            bangalore.name = 'Bangalore Office'
            bangalore.city = 'Bangalore'
            bangalore.address = 'Bangalore, Karnataka'
            bangalore.target_revenue = 400000.0
            db.session.add(chennai)
            db.session.add(bangalore)
            
        db.session.commit()

    # Root route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'manager':
                return redirect(url_for('manager.dashboard'))
            elif current_user.role == 'driver':
                return redirect(url_for('driver.dashboard'))
        
        return redirect(url_for('auth.login'))

    return app

app = create_app()
