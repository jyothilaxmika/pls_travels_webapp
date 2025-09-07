import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, render_template, url_for, flash
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

from flask import current_app
from models import OAuth, User, UserRole, UserStatus, AuditLog
import json

def log_audit(action, entity_type=None, entity_id=None, details=None):
    """Helper function to log audit events"""
    if current_user.is_authenticated:
        from app import db
        audit = AuditLog()
        audit.user_id = current_user.id
        audit.action = action
        audit.entity_type = entity_type
        audit.entity_id = entity_id
        audit.new_values = json.dumps(details) if details else None
        audit.ip_address = request.remote_addr
        audit.user_agent = request.headers.get('User-Agent', '')[:255]
        db.session.add(audit)
        db.session.commit()

class UserSessionStorage(BaseStorage):

    def get(self, blueprint):
        try:
            from app import db
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        from app import db
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name,
        ).delete()
        new_model = OAuth()
        new_model.user_id = current_user.get_id()
        new_model.browser_session_key = g.browser_session_key
        new_model.provider = blueprint.name
        new_model.token = token
        db.session.add(new_model)
        db.session.commit()

    def delete(self, blueprint):
        from app import db
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name).delete()
        db.session.commit()


def make_replit_blueprint():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("the REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        del replit_bp.token
        logout_user()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id":
            repl_id,
            "post_logout_redirect_uri":
            request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return replit_bp


def save_user(user_claims):
    from app import db
    user = User.query.filter_by(email=user_claims.get('email')).first()
    
    if not user:
        # Create new user
        from werkzeug.security import generate_password_hash
        user = User()
        user.username = user_claims.get('email', '').split('@')[0] or f"user_{user_claims['sub']}"
        user.email = user_claims.get('email')
        user.first_name = user_claims.get('first_name')
        user.last_name = user_claims.get('last_name')
        user.profile_picture = user_claims.get('profile_image_url')
        user.password_hash = generate_password_hash('replit_oauth_user')  # Set dummy password
        user.role = UserRole.DRIVER  # Default role
        user.status = UserStatus.ACTIVE
        db.session.add(user)
        db.session.commit()
        flash(f"Welcome to PLS TRAVELS! Your account has been created.", "success")
    else:
        # Update existing user info
        if not user.first_name and user_claims.get('first_name'):
            user.first_name = user_claims.get('first_name')
        if not user.last_name and user_claims.get('last_name'):
            user.last_name = user_claims.get('last_name')
        if not user.profile_picture and user_claims.get('profile_image_url'):
            user.profile_picture = user_claims.get('profile_image_url')
        db.session.commit()
    
    return user


@oauth_authorized.connect
def logged_in(blueprint, token):
    from app import db
    user_claims = jwt.decode(token['id_token'],
                             options={"verify_signature": False})
    user = save_user(user_claims)
    
    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        flash("Your account is not active. Please contact administrator.", "error")
        return redirect(url_for("auth.login"))
    
    login_user(user)
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    user.failed_login_attempts = 0
    db.session.commit()
    
    # Log successful login
    log_audit('replit_login_success')
    
    flash(f"Welcome back, {user.first_name or user.username}!", "success")
    
    # Redirect based on role
    if user.role == UserRole.ADMIN:
        return redirect(url_for('admin.dashboard'))
    elif user.role == UserRole.MANAGER:
        return redirect(url_for('manager.dashboard'))
    else:
        return redirect(url_for('driver.dashboard'))


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    return redirect(url_for('replit_auth.error'))


def require_login(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))

        expires_in = replit.token.get('expires_in', 0)
        if expires_in < 0:
            refresh_token_url = issuer_url + "/token"
            try:
                token = replit.refresh_token(token_url=refresh_token_url,
                                             client_id=os.environ['REPL_ID'])
            except InvalidGrantError:
                # If the refresh token is invalid, the users needs to re-login.
                session["next_url"] = get_next_navigation_url(request)
                return redirect(url_for('replit_auth.login'))
            replit.token_updater(token)

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    is_navigation_url = request.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and request.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


replit = LocalProxy(lambda: g.flask_dance_replit)