"""
Flask Frontend Application
"""
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# Initialize app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['BACKEND_URL'] = os.getenv('BACKEND_URL', 'http://localhost:8000')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CSRF Protection
csrf = CSRFProtect(app)


# ==================== HELPERS ====================

def get_backend_url(endpoint):
    """Get full backend URL"""
    return f"{app.config['BACKEND_URL']}/api/v1{endpoint}"


def api_request(method, endpoint, data=None, params=None, include_auth=True):
    """Make request to backend API"""
    url = get_backend_url(endpoint)
    headers = {'Content-Type': 'application/json'}
    
    if include_auth and 'access_token' in session:
        headers['Authorization'] = f"Bearer {session['access_token']}"
    
    cookies = {'access_token': session.get('access_token')} if include_auth and 'access_token' in session else None
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, cookies=cookies)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, cookies=cookies)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers, cookies=cookies)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, cookies=cookies)
        else:
            return None, "Invalid method"
        
        return response.json() if response.content else {}, response.status_code
    except requests.exceptions.ConnectionError:
        return None, "Backend connection error"
    except Exception as e:
        return None, str(e)


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current user from session/API"""
    if 'access_token' not in session:
        return None
    
    # Cache user in session
    if 'user_data' in session:
        return session['user_data']
    
    user_data, status = api_request('GET', '/auth/me')
    if status == 200:
        session['user_data'] = user_data
        return user_data
    return None


@app.context_processor
def inject_globals():
    """Inject global variables into templates"""
    return {
        'current_user': get_current_user(),
        'app_name': 'Booklet ERP',
        'current_year': __import__('datetime').datetime.now().year
    }


@app.template_filter('currency')
def currency_filter(value, symbol='$'):
    """Format number as currency"""
    try:
        return f"{symbol}{float(value):,.2f}"
    except (ValueError, TypeError):
        return f"{symbol}0.00"


@app.template_filter('date')
def date_filter(value, format='%Y-%m-%d'):
    """Format date"""
    try:
        if value:
            return __import__('datetime').datetime.strptime(str(value), '%Y-%m-%d').strftime(format)
    except ValueError:
        pass
    return value


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('shared/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('shared/500.html'), 500


@app.errorhandler(403)
def forbidden(error):
    return render_template('shared/403.html'), 403


# ==================== REGISTER BLUEPRINTS ====================

from app.views import auth, dashboard, crm, inventory, sales, purchases, accounting, hr, banking, reports, settings

app.register_blueprint(auth.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(crm.bp)
app.register_blueprint(inventory.bp)
app.register_blueprint(sales.bp)
app.register_blueprint(purchases.bp)
app.register_blueprint(accounting.bp)
app.register_blueprint(hr.bp)
app.register_blueprint(banking.bp)
app.register_blueprint(reports.bp)
app.register_blueprint(settings.bp)


# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    """Root route"""
    if 'access_token' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
