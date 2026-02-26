"""
Authentication Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import api_request

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'GET':
        if 'access_token' in session:
            return redirect(url_for('dashboard.index'))
        return render_template('auth/login.html', title='Login')
    
    # POST - Process login
    data = {
        'username': request.form.get('username'),
        'password': request.form.get('password')
    }
    
    response, status = api_request('POST', '/auth/login', data=data, include_auth=False)
    
    if status == 200 and 'access_token' in response:
        session['access_token'] = response['access_token']
        session['username'] = data['username']
        
        # Fetch user data and branches
        user_data, _ = api_request('GET', '/auth/me')
        if user_data:
            session['user_data'] = user_data
            session['is_superuser'] = user_data.get('is_superuser', False)
        
        # Fetch user permissions
        perms_data, _ = api_request('GET', '/auth/permissions')
        if perms_data:
            session['permissions'] = perms_data.get('permissions', [])
        
        # Fetch branches for branch selector
        branches, _ = api_request('GET', '/settings/branches')
        if branches and isinstance(branches, list):
            session['branches'] = branches
            # Set default branch
            default_branch = next((b for b in branches if b.get('is_default')), branches[0] if branches else None)
            if default_branch:
                session['selected_branch_id'] = default_branch.get('id')
                session['selected_branch_name'] = default_branch.get('name')
        
        # Handle HTMX request
        if request.headers.get('HX-Request'):
            response_obj = jsonify({'success': True})
            response_obj.headers['HX-Redirect'] = url_for('dashboard.index')
            return response_obj
        
        return redirect(url_for('dashboard.index'))
    
    error_msg = response.get('detail', 'Login failed') if response else 'Login failed'
    
    if request.headers.get('HX-Request'):
        return render_template('auth/partials/login_error.html', error=error_msg)
    
    flash(error_msg, 'error')
    return render_template('auth/login.html', title='Login', error=error_msg)


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if request.method == 'GET':
        if 'access_token' in session:
            return redirect(url_for('dashboard.index'))
        return render_template('auth/signup.html', title='Sign Up')
    
    # POST - Process signup
    data = {
        'business_name': request.form.get('business_name'),
        'email': request.form.get('email'),
        'username': request.form.get('username'),
        'password': request.form.get('password')
    }
    
    response, status = api_request('POST', '/auth/signup', data=data, include_auth=False)
    
    if status == 200 and 'access_token' in response:
        session['access_token'] = response['access_token']
        session['username'] = data['username']
        
        # Fetch user data and branches
        user_data, _ = api_request('GET', '/auth/me')
        if user_data:
            session['user_data'] = user_data
            session['is_superuser'] = user_data.get('is_superuser', False)
        
        # Fetch user permissions
        perms_data, _ = api_request('GET', '/auth/permissions')
        if perms_data:
            session['permissions'] = perms_data.get('permissions', [])
        
        # Fetch branches for branch selector
        branches, _ = api_request('GET', '/settings/branches')
        if branches and isinstance(branches, list):
            session['branches'] = branches
            # Set default branch
            default_branch = next((b for b in branches if b.get('is_default')), branches[0] if branches else None)
            if default_branch:
                session['selected_branch_id'] = default_branch.get('id')
                session['selected_branch_name'] = default_branch.get('name')
        
        if request.headers.get('HX-Request'):
            response_obj = jsonify({'success': True})
            response_obj.headers['HX-Redirect'] = url_for('dashboard.index')
            return response_obj
        
        return redirect(url_for('dashboard.index'))
    
    error_msg = response.get('detail', 'Signup failed') if response else 'Signup failed'
    
    if request.headers.get('HX-Request'):
        return render_template('auth/partials/signup_error.html', error=error_msg)
    
    flash(error_msg, 'error')
    return render_template('auth/signup.html', title='Sign Up', error=error_msg)


@bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('auth.login'))


@bp.route('/refresh-permissions', methods=['POST'])
def refresh_permissions():
    """Refresh permissions in session"""
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))
    
    # Fetch user permissions
    perms_data, status = api_request('GET', '/auth/permissions')
    
    # Debug: Log what we got
    print(f"\n[DEBUG] ====== REFRESH PERMISSIONS ======")
    print(f"[DEBUG] API Status: {status}")
    print(f"[DEBUG] Full response: {perms_data}")
    
    if perms_data:
        session['permissions'] = perms_data.get('permissions', [])
        session.modified = True
        
        print(f"[DEBUG] User: {session.get('username')}")
        print(f"[DEBUG] Permissions count: {len(session.get('permissions', []))}")
        print(f"[DEBUG] Permissions: {session.get('permissions')}")
        
        # Check for debug info
        if 'debug' in perms_data:
            print(f"[DEBUG] API Debug info: {perms_data['debug']}")
    else:
        print(f"[DEBUG] No data received from API!")
    
    # Redirect back to the same page
    return redirect(request.referrer or url_for('dashboard.index'))


@bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password"""
    if request.method == 'GET':
        return render_template('auth/change_password.html', title='Change Password')
    
    data = {
        'current_password': request.form.get('current_password'),
        'new_password': request.form.get('new_password'),
        'confirm_password': request.form.get('confirm_password')
    }
    
    response, status = api_request('POST', '/settings/users/change-password', data=data)
    
    if status == 200:
        if request.headers.get('HX-Request'):
            return render_template('auth/partials/password_changed.html')
        flash('Password changed successfully', 'success')
        return redirect(url_for('settings.index'))
    
    error_msg = response.get('detail', 'Failed to change password') if response else 'Failed to change password'
    
    if request.headers.get('HX-Request'):
        return render_template('auth/partials/password_error.html', error=error_msg)
    
    flash(error_msg, 'error')
    return render_template('auth/change_password.html', title='Change Password', error=error_msg)
