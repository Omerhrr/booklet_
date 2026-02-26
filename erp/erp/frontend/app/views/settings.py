"""
Settings Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import api_request, login_required, permission_required

bp = Blueprint('settings', __name__, url_prefix='/settings')


def refresh_branches_in_session():
    """Refresh branches in session for branch selector"""
    branches, status = api_request('GET', '/settings/branches')
    if branches and isinstance(branches, list):
        session['branches'] = branches
        session.modified = True


@bp.route('')
@login_required
@permission_required('users:view', 'roles:view', 'branches:view')
def index():
    """Settings index"""
    business, business_status = api_request('GET', '/settings/business')
    users, users_status = api_request('GET', '/settings/users')
    roles, roles_status = api_request('GET', '/settings/roles')
    branches, branches_status = api_request('GET', '/settings/branches')
    
    # Ensure we have proper list objects, not error dicts
    if users_status != 200 or not isinstance(users, list):
        users = []
    if roles_status != 200 or not isinstance(roles, list):
        roles = []
    if branches_status != 200 or not isinstance(branches, list):
        branches = []
    if business_status != 200 or not isinstance(business, dict):
        business = None
    
    return render_template('settings/index.html', 
                          title='Settings',
                          business=business,
                          users=users,
                          roles=roles,
                          branches=branches)


# ==================== BUSINESS SETTINGS ====================

@bp.route('/business', methods=['GET', 'POST'])
@login_required
@permission_required('settings:edit')
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


@bp.route('/business/update', methods=['POST'])
@login_required
@permission_required('settings:edit')
def update_business():
    """Update business settings from settings page"""
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
    
    return redirect(url_for('settings.index'))


# ==================== BRANCHES ====================

@bp.route('/branches')
@login_required
@permission_required('branches:view')
def branches():
    """Manage branches - redirect to settings index"""
    return redirect(url_for('settings.index'))


@bp.route('/branches/new', methods=['GET', 'POST'])
@login_required
@permission_required('branches:create')
def new_branch():
    """Create new branch"""
    if request.method == 'GET':
        return render_template('settings/branch_form.html', title='New Branch')
    
    data = {
        'name': request.form.get('name'),
        'currency': request.form.get('currency', 'USD'),
        'is_default': request.form.get('is_default') == 'on'
    }
    
    response, status = api_request('POST', '/settings/branches', data=data)
    
    if status == 200:
        # Refresh branches in session so the selector shows the new branch
        refresh_branches_in_session()
        flash('Branch created', 'success')
    else:
        error_msg = response.get('detail', 'Failed to create branch') if response else 'Failed to create branch'
        flash(error_msg, 'error')
    
    return redirect(url_for('settings.index'))


@bp.route('/branches/<int:branch_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('branches:edit')
def edit_branch(branch_id):
    """Edit branch"""
    if request.method == 'GET':
        branch, status = api_request('GET', f'/settings/branches/{branch_id}')
        
        if status != 200:
            flash('Branch not found', 'error')
            return redirect(url_for('settings.index'))
        
        return render_template('settings/branch_form.html', title='Edit Branch', branch=branch)
    
    data = {
        'name': request.form.get('name'),
        'currency': request.form.get('currency', 'USD')
    }
    
    response, status = api_request('PUT', f'/settings/branches/{branch_id}', data=data)
    
    if status == 200:
        flash('Branch updated', 'success')
    else:
        flash('Failed to update branch', 'error')
    
    return redirect(url_for('settings.index'))


@bp.route('/branches/<int:branch_id>/set-default', methods=['POST'])
@login_required
@permission_required('branches:edit')
def set_default_branch(branch_id):
    """Set branch as default"""
    response, status = api_request('POST', f'/settings/branches/{branch_id}/set-default')
    
    if status == 200:
        refresh_branches_in_session()
        flash('Default branch updated', 'success')
    else:
        flash('Failed to set default branch', 'error')
    
    return redirect(url_for('settings.index'))


# ==================== ROLES ====================

@bp.route('/roles')
@login_required
@permission_required('roles:view')
def roles():
    """Manage roles - redirect to settings index"""
    return redirect(url_for('settings.index'))


@bp.route('/roles/new', methods=['GET', 'POST'])
@login_required
@permission_required('roles:create')
def new_role():
    """Create new role"""
    if request.method == 'GET':
        permissions, _ = api_request('GET', '/settings/permissions')
        return render_template('settings/role_form.html', title='New Role', permissions=permissions or [])
    
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
    
    return redirect(url_for('settings.index'))


@bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('roles:edit')
def edit_role(role_id):
    """Edit role"""
    if request.method == 'GET':
        role, status = api_request('GET', f'/settings/roles/{role_id}')
        permissions, _ = api_request('GET', '/settings/permissions')
        
        if status != 200:
            flash('Role not found', 'error')
            return redirect(url_for('settings.index'))
        
        return render_template('settings/role_form.html', title='Edit Role', role=role, permissions=permissions or [])
    
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
    
    return redirect(url_for('settings.index'))


@bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@permission_required('roles:delete')
def delete_role(role_id):
    """Delete role"""
    response, status = api_request('DELETE', f'/settings/roles/{role_id}')
    
    if status == 200:
        flash('Role deleted', 'success')
    else:
        error_msg = response.get('detail', 'Failed to delete role') if response else 'Failed to delete role'
        flash(error_msg, 'error')
    
    return redirect(url_for('settings.index'))


# ==================== USERS ====================

@bp.route('/users')
@login_required
@permission_required('users:view')
def users():
    """Manage users - redirect to settings index"""
    return redirect(url_for('settings.index'))


@bp.route('/users/<int:user_id>')
@login_required
@permission_required('users:view')
def view_user(user_id):
    """View user details"""
    user, status = api_request('GET', f'/settings/users/{user_id}/details')
    
    if status != 200:
        flash('User not found', 'error')
        return redirect(url_for('settings.index'))
    
    return render_template('settings/user_detail.html', title=f"{user.get('username', 'User')} - Details", user=user)


@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@permission_required('users:create')
def new_user():
    """Create new user"""
    if request.method == 'GET':
        roles_data, _ = api_request('GET', '/settings/roles')
        branches_data, _ = api_request('GET', '/settings/branches')
        return render_template('settings/user_form.html', title='New User', roles=roles_data or [], branches=branches_data or [])
    
    data = {
        'username': request.form.get('username'),
        'email': request.form.get('email'),
        'password': request.form.get('password'),
        'is_superuser': request.form.get('is_superuser') == 'on'
    }
    
    response, status = api_request('POST', '/settings/users', data=data)
    
    if status == 200:
        # If role and branch are selected, assign the role
        role_id = request.form.get('role_id')
        branch_id = request.form.get('branch_id')
        if role_id and branch_id:
            user_id = response.get('id')
            assign_data = {
                'user_id': user_id,
                'branch_id': int(branch_id),
                'role_id': int(role_id)
            }
            assign_response, assign_status = api_request('POST', '/settings/users/assign-role', data=assign_data)
            print(f"[DEBUG] Role assignment response: {assign_response}, status: {assign_status}")
        else:
            print(f"[DEBUG] No role/branch selected - role_id: {role_id}, branch_id: {branch_id}")
        flash('User created', 'success')
    else:
        error = response.get('detail', 'Failed to create user') if response else 'Failed'
        flash(error, 'error')
    
    return redirect(url_for('settings.index'))


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('users:edit')
def edit_user(user_id):
    """Edit user"""
    if request.method == 'GET':
        user, status = api_request('GET', f'/settings/users/{user_id}')
        roles_data, _ = api_request('GET', '/settings/roles')
        branches_data, _ = api_request('GET', '/settings/branches')
        
        if status != 200:
            flash('User not found', 'error')
            return redirect(url_for('settings.index'))
        
        return render_template('settings/user_form.html', title='Edit User', user=user, roles=roles_data or [], branches=branches_data or [])
    
    # Update user basic info
    data = {
        'username': request.form.get('username'),
        'email': request.form.get('email'),
        'is_superuser': request.form.get('is_superuser') == 'on',
        'is_active': request.form.get('is_active') == 'on'
    }
    
    response, status = api_request('PUT', f'/settings/users/{user_id}', data=data)
    
    if status == 200:
        # If role and branch are selected, assign the role
        role_id = request.form.get('role_id')
        branch_id = request.form.get('branch_id')
        if role_id and branch_id:
            assign_data = {
                'user_id': user_id,
                'branch_id': int(branch_id),
                'role_id': int(role_id)
            }
            api_request('POST', '/settings/users/assign-role', data=assign_data)
        flash('User updated', 'success')
    else:
        flash('Failed to update user', 'error')
    
    return redirect(url_for('settings.index'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@permission_required('users:delete')
def delete_user(user_id):
    """Delete user"""
    response, status = api_request('DELETE', f'/settings/users/{user_id}')
    
    if status == 200:
        flash('User deleted successfully', 'success')
    else:
        error_msg = response.get('detail', 'Failed to delete user') if response else 'Failed to delete user'
        flash(error_msg, 'error')
    
    return redirect(url_for('settings.index'))


@bp.route('/users/assign-role', methods=['POST'])
@login_required
@permission_required('users:assign-roles')
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
    
    return redirect(url_for('settings.index'))


@bp.route('/set-branch/<int:branch_id>', methods=['POST'])
@login_required
def set_branch(branch_id):
    """Set user's active branch"""
    # Find the branch name from session branches
    branches = session.get('branches', [])
    branch_name = next((b.get('name') for b in branches if b.get('id') == branch_id), 'Unknown')
    
    session['selected_branch_id'] = branch_id
    session['selected_branch_name'] = branch_name
    
    response, status = api_request('POST', f'/settings/set-branch/{branch_id}')
    
    # Always redirect to refresh the page with new branch data
    return redirect(request.referrer or url_for('dashboard.index'))


@bp.route('/permissions/seed', methods=['POST'])
@login_required
@permission_required('settings:edit')
def seed_permissions():
    """Seed missing permissions - admin only"""
    response, status = api_request('POST', '/settings/permissions/seed')
    
    if status == 200:
        flash('Permissions synced successfully. Admin role updated with all permissions.', 'success')
    else:
        error_msg = response.get('detail', 'Failed to seed permissions') if response else 'Failed to seed permissions'
        flash(error_msg, 'error')
    
    return redirect(url_for('settings.index'))
