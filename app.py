import os
import logging
from flask import Flask, send_from_directory, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_compress import Compress
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_socketio import SocketIO
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
socketio = SocketIO()
csrf = CSRFProtect()
jwt = JWTManager()
compress = Compress()

def create_app():
    # Create the app
    app = Flask(__name__)
    # Enforce SESSION_SECRET requirement
    app.secret_key = os.environ.get("SESSION_SECRET")
    if not app.secret_key:
        raise RuntimeError("SESSION_SECRET environment variable is required but not set")
    # Configure ProxyFix for proper client IP detection in production
    # x_for=1: Trust one proxy for X-Forwarded-For header (client IP)
    # x_proto=1: Trust one proxy for X-Forwarded-Proto header (HTTPS detection)
    # x_host=1: Trust one proxy for X-Forwarded-Host header (hostname)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # CORS Configuration for production (restricted origins for security)
    production_origins = os.environ.get('ALLOWED_ORIGINS', '').split(',')
    allowed_origins = [origin.strip() for origin in production_origins if origin.strip()]
    
    # Fallback to localhost for development only if no production origins set
    if not allowed_origins:
        allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        
    CORS(app, origins=allowed_origins, 
         supports_credentials=False,
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Configure compression for better performance
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml', 'text/plain',
        'application/json', 'application/javascript', 'application/xml',
        'application/rss+xml', 'application/atom+xml', 'image/svg+xml'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Balance between compression ratio and speed
    app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress files larger than 500 bytes
    
    # Initialize compression
    compress.init_app(app)

    # Configure the database - use PostgreSQL in production, SQLite for development
    database_url = os.environ.get("DATABASE_URL") or "sqlite:///pls_travels.db"
    
    # Configure for PostgreSQL production database
    if database_url.startswith(("postgresql://", "postgres://")):
        # Ensure psycopg2 driver is specified
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
        # Log connection info (without password) for debugging
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        print(f"🔌 Connecting to PostgreSQL: host={parsed.hostname}, db={parsed.path[1:]}, user={parsed.username}, password_present={'*' * len(parsed.password or '')}")
        
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 10,
            "pool_recycle": 280,  # Slightly less than 5 minutes to prevent stale connections
            "pool_pre_ping": True,
            "max_overflow": 15,
            "pool_timeout": 20,  # Maximum time to wait for connection from pool
            "connect_args": {
                "sslmode": "require",
                "connect_timeout": 10,  # Reduced from 30 to 10 seconds
                "application_name": "pls_travels",
                "keepalives_idle": 600,  # Keep connections alive
                "keepalives_interval": 30,
                "keepalives_count": 3
            }
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
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max file size for camera captures
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'  # type: ignore
    login_manager.login_message = 'Please log in to access this page.'
    
    # Initialize SocketIO with proper security and extended configuration
    # For development, allow all Replit domains with proper wildcard matching
    allowed_origins = [
        "https://*.replit.app", 
        "https://*.replit.dev", 
        "https://*.pike.replit.dev",
        "https://*-*.pike.replit.dev",  # More specific pattern for complex Replit domains
        "https://*.*.*replit.dev",      # Even more permissive for development
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ]
    # WebSocket/SocketIO is DISABLED for stability
    # Real-time features temporarily unavailable
    # To re-enable: uncomment socketio.init_app() and websocket routes below

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Add template functions
    from datetime import datetime, timedelta
    import pytz
    
    # Configure IST timezone for the application
    IST = pytz.timezone('Asia/Kolkata')
    
    # SocketIO configuration (disabled for stability)
    app.config['SOCKETIO_ENABLED'] = False
    
    def get_ist_time():
        """Get current time in IST timezone"""
        return datetime.now(IST)
    
    def get_ist_time_naive():
        """Get current IST time as naive datetime for database storage"""
        return datetime.now(IST).replace(tzinfo=None)
    
    def convert_to_ist(dt):
        """Convert datetime to IST timezone"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = pytz.utc.localize(dt)
        return dt.astimezone(IST)
    
    # JWT Configuration (after imports to avoid scope issues)
    app.config['JWT_SECRET_KEY'] = app.secret_key  # Use same secret as Flask session
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config['JWT_ALGORITHM'] = 'HS256'

    # Make datetime and timedelta available in templates
    app.jinja_env.globals['datetime'] = datetime
    app.jinja_env.globals['timedelta'] = timedelta
    app.jinja_env.globals['get_ist_time'] = get_ist_time
    app.jinja_env.globals['get_ist_time_naive'] = get_ist_time_naive
    app.jinja_env.globals['convert_to_ist'] = convert_to_ist
    
    @app.template_global()
    def moment(dt=None):
        class MomentJS:
            def __init__(self, datetime_obj=None):
                if datetime_obj is None:
                    self.dt = get_ist_time()
                else:
                    self.dt = convert_to_ist(datetime_obj)
            
            def format(self, format_str):
                if not self.dt:
                    return ''
                
                format_mapping = {
                    'DD/MM/YYYY': self.dt.strftime('%d/%m/%Y'),
                    'MMMM DD, YYYY': self.dt.strftime('%B %d, %Y'),
                    'MMM DD, YYYY': self.dt.strftime('%b %d, %Y'), 
                    'YYYY-MM-DD': self.dt.strftime('%Y-%m-%d'),
                    'YYYY-MM-DD HH:mm:ss': self.dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'HH:mm:ss': self.dt.strftime('%H:%M:%S'),
                    'HH:mm': self.dt.strftime('%H:%M'),
                    'DD MMM': self.dt.strftime('%d %b'),
                }
                return format_mapping.get(format_str, self.dt.strftime('%Y-%m-%d'))
            
            def fromNow(self):
                if not self.dt:
                    return ''
                now = get_ist_time()
                diff = now - self.dt
                if diff.days > 0:
                    return f"{diff.days} days ago"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    return f"{hours} hours ago"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    return f"{minutes} minutes ago"
                else:
                    return "Just now"
            
            def date(self):
                return self.dt.date() if self.dt else None
        
        return MomentJS(dt)
    
    # Add context processor for pending duties notifications
    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        from models import UserRole, DutyStatus, Duty
        
        if current_user.is_authenticated:
            pending_duties_count = 0
            if current_user.role == UserRole.ADMIN:
                pending_duties_count = Duty.query.filter_by(status=DutyStatus.PENDING_APPROVAL).count()
            
            return dict(pending_duties_count=pending_duties_count)
        return dict(pending_duties_count=0)

    # JWT token blacklist checker
    from mobile_auth import check_if_token_revoked as check_token_blacklist
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return check_token_blacklist(jwt_header, jwt_payload)

    # Register blueprints
    from auth import auth_bp
    from otp_routes import otp_bp
    from mobile_auth import mobile_auth_bp
    from mobile_api import mobile_api_bp
    from admin_routes import admin_bp
    from manager_routes import manager_bp
    from driver_routes import driver_bp
    from storage_routes import storage_bp
    from vehicle_tracking_routes import tracking_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(otp_bp, url_prefix='/otp')
    app.register_blueprint(mobile_auth_bp)  # Mobile auth includes /api/v1/auth/*
    app.register_blueprint(mobile_api_bp)   # Mobile API includes /api/v1/driver/*
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(storage_bp)
    app.register_blueprint(tracking_bp, url_prefix='/tracking')
    
    # Make session permanent and handle database timeouts
    @app.before_request
    def make_session_permanent():
        session.permanent = True
        # Removed redundant SELECT 1 ping - pool_pre_ping=True handles connection validation automatically

    # Create tables
    # Check OTP system configuration on startup
    from utils.config_validator import get_otp_config_status
    print(f"OTP Configuration: {get_otp_config_status()}")
    
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        
        # Import models needed for checks
        from models import User, Branch
        from werkzeug.security import generate_password_hash
        
        # Only create demo data if explicitly enabled (SECURITY RISK IN PRODUCTION)
        demo_mode = os.environ.get('DEMO_SEED', 'false').lower() == 'true'
        
        if demo_mode:
            
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                from models import UserRole, UserStatus
                admin = User()
                admin.username = 'admin'
                admin.email = 'admin@plstravels.com'
                admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')
                if not admin_password:
                    raise RuntimeError("ADMIN_INITIAL_PASSWORD environment variable is required for demo mode but not set")
                admin.password_hash = generate_password_hash(admin_password)
                admin.role = UserRole.ADMIN
                admin.status = UserStatus.ACTIVE
                admin.first_name = 'System'
                admin.last_name = 'Administrator'
                db.session.add(admin)
            
            # Create default branches only in demo mode
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
            
            # Create active driver profile for admin user only in demo mode
            from models import Driver, DriverStatus
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user and not admin_user.driver_profile:
                # Check if a driver with employee_id 'EMP000001' already exists
                existing_admin_driver = Driver.query.filter_by(employee_id='EMP000001').first()
                if existing_admin_driver:
                    # Link existing driver to admin user if not already linked
                    if not existing_admin_driver.user_id:
                        existing_admin_driver.user_id = admin_user.id
                        existing_admin_driver.status = DriverStatus.ACTIVE
                        existing_admin_driver.approved_by = admin_user.id
                        existing_admin_driver.approved_at = datetime.utcnow()
                else:
                    # Get default branch and create new driver
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
        
            # Note: Pending driver auto-activation removed for production security
        
        # Always commit changes (even if no demo data created)
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

    # Health check endpoint for deployment
    @app.route('/health')
    def health():
        """Simple health check endpoint for deployment readiness"""
        return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}, 200

    # Root route
    @app.route('/')
    def index():
        from flask import redirect, url_for, render_template
        from flask_login import current_user
        from forms import LoginForm
        
        if current_user.is_authenticated:
            from models import UserRole
            if current_user.role == UserRole.ADMIN:
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == UserRole.MANAGER:
                return redirect(url_for('manager.dashboard'))
            elif current_user.role == UserRole.DRIVER:
                return redirect(url_for('driver.dashboard'))
        
        # Show landing page with login form for unauthenticated users
        form = LoginForm()
        return render_template('landing.html', form=form)
    
    # Add direct /login route for convenience
    @app.route('/login')
    def login_redirect():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    # Route to serve uploaded files with authentication
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        """Serve uploaded files from the uploads directory with authentication"""
        from flask_login import login_required, current_user
        from models import UserRole
        
        # Require authentication
        if not current_user.is_authenticated:
            return "Authentication required", 401
            
        # Allow admin and manager full access
        if current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
            upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
            return send_from_directory(upload_folder, filename)
            
        # Drivers cannot access uploads directly for security
        # TODO: Implement proper file ownership verification for drivers
        
        return "Access denied - contact administrator", 403

    # SEO routes
    @app.route('/robots.txt')
    def robots_txt():
        """Serve robots.txt for search engine crawlers"""
        return send_from_directory('static', 'robots.txt')

    @app.route('/sitemap.xml')
    def sitemap_xml():
        """Generate sitemap.xml for search engines"""
        from flask import render_template, make_response
        from datetime import datetime
        
        response = make_response(render_template('sitemap.xml', 
                                               current_date=datetime.now().strftime('%Y-%m-%d')))
        response.headers['Content-Type'] = 'application/xml'
        return response

    return app

app = create_app()

# WebSocket event handlers DISABLED (SocketIO temporarily disabled for stability)
# @socketio.on('connect')
# def handle_connect():
#     from flask_login import current_user
#     from flask_socketio import emit
#     if current_user.is_authenticated:
#         emit('status', {'msg': f'User {current_user.username} connected'})

# @socketio.on('disconnect')
# def handle_disconnect():
#     from flask_login import current_user
#     if current_user.is_authenticated:
#         print(f'User {current_user.username} disconnected')

# @socketio.on('join_tracking')
# def handle_join_tracking(data):
#     from flask_socketio import join_room, emit
#     from flask_login import current_user
#     from models import UserRole
#     if current_user.is_authenticated:
#         # Join user-specific room
#         user_room = f"tracking_{current_user.id}"
#         join_room(user_room)
#         
#         # Join global tracking room for real-time updates
#         join_room("tracking_global")
#         
#         # Join branch-specific rooms for managers/admins
#         if current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
#             if current_user.role == UserRole.ADMIN:
#                 # Admin can see all branches
#                 from models import Branch
#                 branches = Branch.query.all()
#                 for branch in branches:
#                     join_room(f"tracking_branch_{branch.id}")
#             else:
#                 # Manager sees only their branches
#                 for branch in current_user.managed_branches:
#                     join_room(f"tracking_branch_{branch.id}")
#         
#         emit('status', {'msg': f'Joined tracking rooms successfully'})

# @socketio.on('request_vehicle_update')
# def handle_vehicle_update_request():
#     from flask_socketio import emit
#     from flask_login import current_user
#     if current_user.is_authenticated:
#         # Trigger vehicle location update
#         emit('vehicle_update_requested', broadcast=True)

# @socketio.on('location_update')
# def handle_driver_location_update(data):
#     from flask_socketio import emit
#     from flask_login import current_user
#     from models import Driver, VehicleTracking, Duty, DutyStatus, db
#     from timezone_utils import get_ist_time_naive
#     
#     if not current_user.is_authenticated:
#         return
#     
#     # Get driver profile
#     driver = Driver.query.filter_by(user_id=current_user.id).first()
#     if not driver:
#         return
#     
#     # Get active duty
#     active_duty = Duty.query.filter(
#         Duty.driver_id == driver.id,
#         Duty.status == DutyStatus.ACTIVE
#     ).first()
#     
#     if not active_duty:
#         return
#     
#     # Create tracking record
#     try:
#         tracking = VehicleTracking()
#         tracking.vehicle_id = active_duty.vehicle_id
#         tracking.duty_id = active_duty.id
#         tracking.driver_id = driver.id
#         tracking.recorded_at = get_ist_time_naive()
#         tracking.odometer_reading = 0  # Will be updated by driver later
#         tracking.odometer_type = 'gps'
#         tracking.latitude = data.get('latitude')
#         tracking.longitude = data.get('longitude')
#         tracking.location_accuracy = data.get('accuracy', 0)
#         tracking.location_name = 'GPS Location'
#         tracking.source = 'mobile_gps'
#         tracking.notes = 'Real-time GPS update from mobile device'
#         
#         db.session.add(tracking)
#         db.session.commit()
#         
#         # Broadcast to tracking room
#         broadcast_data = {
#             'vehicle_id': active_duty.vehicle_id,
#             'vehicle_number': active_duty.vehicle.number if active_duty.vehicle else 'Unknown',
#             'driver_name': driver.full_name,
#             'latitude': data.get('latitude'),
#             'longitude': data.get('longitude'),
#             'accuracy': data.get('accuracy', 0),
#             'timestamp': tracking.recorded_at.isoformat(),
#             'is_significant_move': True,
#             'location_name': 'GPS Location'
#         }
#         
#         # Broadcast to appropriate rooms
#         from flask_socketio import emit
#         emit('vehicle_location_update', broadcast_data, to='tracking_global')
#         
#         # Also broadcast to branch-specific room
#         if active_duty.vehicle and active_duty.vehicle.branch_id:
#             emit('vehicle_location_update', broadcast_data, to=f'tracking_branch_{active_duty.vehicle.branch_id}')
#         
#     except Exception as e:
#         print(f"Error handling location update: {e}")
#         db.session.rollback()
