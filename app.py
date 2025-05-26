import time
import os
import json
import ssl
import asyncio
import inspect
import hashlib
import socket
import aiodns
import ipaddress

from flask import Flask, render_template, redirect, url_for, abort, jsonify, session, request
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import CSRFError
from flask_session import Session
from flask_caching import Cache
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from redis import Redis
from urllib.parse import urlparse
from ldap3 import Server, Connection, ALL, SUBTREE, Tls
from functools import wraps
from dataclasses import dataclass, field, asdict
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Cisco DNAC backend
DNAC_HOST = os.environ.get("DNAC_HOST")
DNAC_USERNAME = os.environ.get("DNAC_USERNAME")
DNAC_PASSWORD = os.environ.get("DNAC_PASSWORD")

# Redis backend for Celery / Server side sessions / Caching
REDIS_URL = os.environ.get("REDIS_URL")

# LDAP backend for authentication / authorization
LDAP_HOST = f"ldaps://{os.environ.get("LDAP_HOST")}"
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN")
LDAP_USERNAME = os.environ.get("LDAP_USERNAME")
LDAP_PASSWORD = os.environ.get("LDAP_PASSWORD")

# Application roles to LDAP groups mappings
ROLES = json.loads(os.environ.get("LDAP_ROLES"))

# Session timeout
SESSION_TIMEOUT_SECONDS = 3600*12

# DNS resolution
DNS_SERVERS = json.loads(os.environ.get("DNS_SERVERS"))
DNS_SUFFIXES = json.loads(os.environ.get("DNS_SUFFIXES"))

# Init Flask app
app = Flask(__name__)

# Caching
app.config['CACHE_TYPE'] = 'redis'
app.config['CACHE_REDIS_HOST'] = urlparse(REDIS_URL).hostname
app.config['CACHE_REDIS_PORT'] = 6379
app.config['CACHE_REDIS_DB'] = 0
cache = Cache(app)
# Custom cache key function
# usage: @cache.cached(timeout=300, key_prefix=make_key)
def make_key(*args, **kwargs):
    path = request.path
    query_params = request.args.to_dict(flat=True)
    # Convert to sorted JSON to ensure consistent key generation
    query_string = json.dumps(query_params, sort_keys=True)
    base_key = f"{path}?{query_string}"
    # Hash the key
    return "cache:" + hashlib.sha256(base_key.encode()).hexdigest()

# Server side sessions
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis.from_url(f"{REDIS_URL}/1")
Session(app)

if os.environ['FLASK_ENV'] == 'development':
    app.secret_key = 'REPLACE_WITH_SECURE_SECRET'
    app.debug = True
else:
    app.secret_key = os.urandom(24).hex()

# Attach Celery app
celery_app = Celery('celery', broker=f"{REDIS_URL}/2", result_backend=f"{REDIS_URL}/2", task_ignore_result=False)
celery_app.set_default()
app.extensions["celery"] = celery_app

# Refresh session timeout
@app.before_request
def refresh_session():
    # set default theme
    if "theme" not in session:
        session["theme"] = "dark"
    # Check session expired
    if 'username' in session:
        now = int(time.time())
        if session.get('expires_at', 0) < now:
            session.clear()
        else:
            # Refresh timeout
            session['expires_at'] = now + SESSION_TIMEOUT_SECONDS

# CSRF token timeout
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return redirect(url_for("login"))

# Enable CSRF protection
csrf = CSRFProtect(app)

# User class
@dataclass
class User:
    username: str
    password: str = None
    dn: str = None
    firstname: str = None
    fullname: str = None
    email: str = None
    authenticated: bool = False
    roles: list = field(default_factory = list)

# Utility function to read user data from session
def read_user_from_session(session)->User:
    return User(
        username = session.get("username"),
        password = session.get("password"),
        fullname = session.get("fullname"),
        firstname = session.get("firstname"),
        email = session.get("email"),
        roles = session.get("roles")
    )

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Login required decorator (supports sync and async functions)
def login_required(f):
    @wraps(f)
    def sync_wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    @wraps(f)
    async def async_wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for('login'))
        return await f(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper

# Roles required decorator
def roles_required(allowed_roles:list[str]):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_roles = session.get("roles", [])
            if not any(role in allowed_roles for role in user_roles):
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# LDAP login function
def ldap_login(username: str, password: str) -> User:
    tls_config = Tls(validate=ssl.CERT_NONE)
    server = Server(
        LDAP_HOST,
        get_info = ALL,
        port = 636,
        use_ssl = True,
        tls = tls_config
    )

    # Use service account to search for user's DN
    try:
        conn = Connection(
            server,
            user = LDAP_USERNAME,
            password = LDAP_PASSWORD,
            auto_bind = True
        )
    except Exception as e:
        print(f"[ERROR] Failed to bind with service account: {e}")
        return User(username=username)

    # Search for the user's DN using sAMAccountName
    search_filter = f"(sAMAccountName={username})"
    conn.search(
        search_base = LDAP_BASE_DN,
        search_filter = search_filter,
        search_scope = SUBTREE,
        attributes = ["distinguishedName", "memberOf", "displayName", "givenName", "mail"]
    )

    if not conn.entries:
        return User(username=username)

    user_dn = conn.entries[0].entry_dn
    member_of = conn.entries[0].memberOf.values if 'memberOf' in conn.entries[0] else []
    fullname = conn.entries[0].displayName.value
    firstname = conn.entries[0].givenName.value
    email = conn.entries[0].mail.value

    # Now try binding with the user's actual credentials
    try:
        Connection(server, user=user_dn, password=password, auto_bind=True)
    except Exception:
        return User(username=username)

    # User role mapping
    user_roles = set()
    for role_name,role_groups in ROLES.items():
        for role_group in role_groups:
            for user_group in member_of:
                if user_group.startswith(role_group):
                    user_roles.add(role_name)


    return User(
        authenticated = True,
        username = username,
        password = password,
        dn = user_dn,
        fullname = fullname,
        firstname = firstname,
        email = email,
        roles = list(user_roles)
    )

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error = None

    # Avoid LDAP bind if already authenticated
    if "username" in session:
        return redirect(url_for('home'))
    
    # Authenticate
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = ldap_login(username, password)
        if user.authenticated:
            app.session_interface.regenerate(session)
            session["username"] = user.username
            session["password"] = user.password
            session["roles"] = user.roles
            session["fullname"] = user.fullname
            session["firstname"] = user.firstname
            session["email"] = user.email
            session['expires_at'] = int(time.time()) + SESSION_TIMEOUT_SECONDS
            return redirect(url_for('home'))
        else:
            error = "Access denied"

    return render_template("login.html", form=form, error=error, theme=session["theme"])

# Logout route
@app.route('/logout', methods=['GET'])
@login_required
def logout():
    del session["username"]
    del session["password"]
    del session["roles"]
    del session["fullname"]
    del session["firstname"]
    del session["email"]
    del session['expires_at']
    #session.clear()
    return redirect(url_for('login'))

# About route
@app.route('/about', methods=['GET'])
@login_required
def about():
    user = read_user_from_session(session)
    return render_template("about.html", user=user, theme=session["theme"])

# Dark/Light theme route
@app.route("/theme", methods=["POST"])
@csrf.exempt
def toggle_theme():
    new_theme = request.form.get("theme")
    if new_theme in ["light", "dark"]:
        session["theme"] = new_theme
    return redirect(request.referrer or url_for("home"))

# simple DNS resolver
@app.route("/resolve", methods=["POST"])
@login_required
@csrf.exempt
async def resolve():
    payload = request.get_json()
    name = payload.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400

    # Check if it's already a valid IP address
    try:
        ip = str(ipaddress.ip_address(name))
        return jsonify({"ip": ip})
    except ValueError:
        pass  # not an IP, try DNS resolution

    resolver = aiodns.DNSResolver()
    resolver.nameservers = DNS_SERVERS
    
    for suffix in DNS_SUFFIXES:
        fqdn = name if suffix == "" else f"{name}.{suffix}"
        
        try:
            print(f"try resolving {fqdn}")
            result = await resolver.gethostbyname(fqdn, socket.AF_INET)
            print(result)
            if result and result.addresses:
                return jsonify({"ip": result.addresses[0], "fqdn": fqdn})
        except Exception as e:
            print(e)
            continue  # try next suffix

    return jsonify({"error": f"Could not resolve {name}"}), 404
    
# Home route
@app.route('/', methods=['GET'])
@login_required
def home():
    user = read_user_from_session(session)
    link_map = {
        "LAN": {
            "text": "View and operate LAN switches",
            "url": url_for('ui_lan.index')
        }

    }
    return render_template("home.html", user=user, link_map=link_map, theme=session["theme"])

# API Tasks blueprint
import api_tasks
app.register_blueprint(api_tasks.bp)

# API DNAC blueprint
import api_dnac
app.register_blueprint(api_dnac.bp)


# UI Base blueprint
import ui_lan
app.register_blueprint(ui_lan.bp)








if __name__ == '__main__':
    app.run(debug=True)
