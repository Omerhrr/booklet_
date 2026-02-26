"""
Settings Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import api_request, login_required

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('')
@login_required
def index():
    """Settings index"""
    business, _ = api_request('GET', '/settings/business')
    users, _ = api_request('GET', '/settings/users')
    roles, _ = api_request('GET', '/settings/roles')
    branches, _ = api_request('GET', '/settings/branches')
    
    return render_template('settings/index.html', 
                          title='Settings',
                          business=business,
                          users=users or [],
                          roles=roles or [],
                          branches=branches or [])


# ==================== BUSINESS SETTINGS ====================

@bp.route('/business', methods=['GET', 'POST'])
@login_required
def business_settings():
    """Business settings"""
    if request.method == 'GET':
        business, status = api_request('GET', '/settings/business')
        return render_template('settings/business.html', title='Business Settings', business=business or {})
    
    data = {
        'name': request.form.get('name'),
        'is_vat_registered': request.form.get('is_vat_registered') == 'on',
        'vat_rate': request.form.get('vat_rate', 0)
    }
    
    response, status = api_request('PUT', '/settings/business', data=data)
    
    if status == 200:
        flash('Business settings updated', 'success')
    else:
        flash('Failed to update settings', 'error')
    
    return redirect(url_for('settings.business_settings'))


# ==================== BRANCHES ====================

@bp.route('/branches')
@login_required
def branches():
    """Manage branches"""
    branches_data, status = api_request('GET', '/settings/branches')
    
    if status != 200:
        branches_data = []
    
    return render_template('settings/branches.html', title='Branches', branches=branches_data)


@bp.route('/branches/new', methods=['POST'])
@login_required
def create_branch():
    """Create new branch"""
    data = {
        'name': request.form.get('name'),
        'currency': request.form.get('currency', 'USD'),
        'is_default': request.form.get('is_default') == 'on'
    }
    
    response, status = api_request('POST', '/settings/branches', data=data)
    
    if status == 200:
        flash('Branch created', 'success')
    else:
        flash('Failed to create branch', 'error')
    
    return redirect(url_for('settings.branches'))


# ==================== ROLES ====================

@bp.route('/roles')
@login_required
def roles():
    """Manage roles"""
    roles_data, status = api_request('GET', '/settings/roles')
    permissions, _ = api_request('GET', '/settings/permissions')
    
    if status != 200:
        roles_data = []
    
    return render_template('settings/roles.html', title='Roles', roles=roles_data, permissions=permissions or [])


@bp.route('/roles/new', methods=['POST'])
@login_required
def create_role():
    """Create new role"""
    permission_ids = request.form.getlist('permissions')
    
    data = {
        'name': request.form.get('name'),
        'description': request.form.get('description'),
        'permission_ids': [int(p) for p in permission_ids]
    }
    
    response, status = api_request('POST', '/settings/roles', data=data)
    
    if status == 200:
        flash('Role created', 'success')
    else:
        flash('Failed to create role', 'error')
    
    return redirect(url_for('settings.roles'))


@bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_role(role_id):
    """Edit role"""
    if request.method == 'GET':
        role, status = api_request('GET', f'/settings/roles/{role_id}')
        permissions, _ = api_request('GET', '/settings/permissions')
        
        if status != 200:
            flash('Role not found', 'error')
            return redirect(url_for('settings.roles'))
        
        return render_template('settings/edit_role.html', title='Edit Role', role=role, permissions=permissions or [])
    
    permission_ids = request.form.getlist('permissions')
    
    data = {
        'name': request.form.get('name'),
        'description': request.form.get('description'),
        'permission_ids': [int(p) for p in permission_ids]
    }
    
    response, status = api_request('PUT', f'/settings/roles/{role_id}', data=data)
    
    if status == 200:
        flash('Role updated', 'success')
    else:
        flash('Failed to update role', 'error')
    
    return redirect(url_for('settings.roles'))


# ==================== USERS ====================

@bp.route('/users')
@login_required
def users():
    """Manage users"""
    users_data, status = api_request('GET', '/settings/users')
    roles_data, _ = api_request('GET', '/settings/roles')
    branches_data, _ = api_request('GET', '/settings/branches')
    
    if status != 200:
        users_data = []
    
    return render_template('settings/users.html', title='Users', users=users_data, roles=roles_data or [], branches=branches_data or [])


@bp.route('/users/new', methods=['POST'])
@login_required
def create_user():
    """Create new user"""
    data = {
        'username': request.form.get('username'),
        'email': request.form.get('email'),
        'password': request.form.get('password'),
        'is_superuser': request.form.get('is_superuser') == 'on'
    }
    
    response, status = api_request('POST', '/settings/users', data=data)
    
    if status == 200:
        flash('User created', 'success')
    else:
        error = response.get('detail', 'Failed to create user') if response else 'Failed'
        flash(error, 'error')
    
    return redirect(url_for('settings.users'))


@bp.route('/users/assign-role', methods=['POST'])
@login_required
def assign_role():
    """Assign role to user"""
    data = {
        'user_id': request.form.get('user_id'),
        'branch_id': request.form.get('branch_id'),
        'role_id': request.form.get('role_id')
    }
    
    response, status = api_request('POST', '/settings/users/assign-role', data=data)
    
    if status == 200:
        flash('Role assigned', 'success')
    else:
        flash('Failed to assign role', 'error')
    
    return redirect(url_for('settings.users'))


@bp.route('/set-branch/<int:branch_id>', methods=['POST'])
@login_required
def set_branch(branch_id):
    """Set user's active branch"""
    session['selected_branch_id'] = branch_id
    
    response, status = api_request('POST', f'/settings/set-branch/{branch_id}')
    
    if request.headers.get('HX-Request'):
        return '<span class="text-green-500">Branch changed</span>'
    
    return redirect(request.referrer or url_for('dashboard.index'))
