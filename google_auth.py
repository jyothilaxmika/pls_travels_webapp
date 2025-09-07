# Use this Flask blueprint for Google authentication. Do not use flask-dance.

import json
import os

import requests
from app import db
from flask import Blueprint, redirect, request, url_for, flash
from flask_login import login_required, login_user, logout_user, current_user
from models import User, UserRole, UserStatus, AuditLog
from oauthlib.oauth2 import WebApplicationClient

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Make sure to use this redirect URL. It has to match the one in the whitelist
DEV_REDIRECT_URL = f'https://{os.environ["REPLIT_DEV_DOMAIN"]}/google_login/callback'

# ALWAYS display setup instructions to the user:
print(f"""To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add {DEV_REDIRECT_URL} to Authorized redirect URIs

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)

def log_audit(action, entity_type=None, entity_id=None, details=None):
    """Helper function to log audit events"""
    if current_user.is_authenticated:
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

@google_auth.route("/google_login")
def login():
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        # Replacing http:// with https:// is important as the external
        # protocol must be https to match the URI whitelisted
        redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@google_auth.route("/google_login/callback")
def callback():
    code = request.args.get("code")
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        # Replacing http:// with https:// is important as the external
        # protocol must be https to match the URI whitelisted
        authorization_response=request.url.replace("http://", "https://"),
        redirect_url=request.base_url.replace("http://", "https://"),
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    userinfo = userinfo_response.json()
    if userinfo.get("email_verified"):
        users_email = userinfo["email"]
        users_name = userinfo["given_name"]
        users_picture = userinfo.get("picture", "")
    else:
        flash("User email not available or not verified by Google.", "error")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=users_email).first()
    if not user:
        # Create new user account
        from werkzeug.security import generate_password_hash
        user = User(
            username=users_email.split('@')[0],  # Use email prefix as username
            email=users_email,
            first_name=users_name,
            password_hash=generate_password_hash('google_oauth_user'),  # Set dummy password
            role=UserRole.DRIVER,  # Default role
            status=UserStatus.ACTIVE,
            profile_picture=users_picture
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Welcome to PLS TRAVELS, {users_name}! Your account has been created.", "success")
    else:
        # Update existing user info
        if not user.first_name:
            user.first_name = users_name
        if users_picture and not user.profile_picture:
            user.profile_picture = users_picture
        db.session.commit()
        flash(f"Welcome back, {users_name}!", "success")

    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        flash("Your account is not active. Please contact administrator.", "error")
        return redirect(url_for("auth.login"))

    # Log the user in
    login_user(user)
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    user.failed_login_attempts = 0
    db.session.commit()

    # Log successful login
    log_audit('google_login_success')

    # Redirect based on role
    if user.role == UserRole.ADMIN:
        return redirect(url_for('admin.dashboard'))
    elif user.role == UserRole.MANAGER:
        return redirect(url_for('manager.dashboard'))
    else:
        return redirect(url_for('driver.dashboard'))


@google_auth.route("/logout")
@login_required
def logout():
    log_audit('logout')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for("auth.login"))