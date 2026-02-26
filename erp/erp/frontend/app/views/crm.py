"""
CRM Views - Customers and Vendors
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import api_request, login_required, permission_required

bp = Blueprint('crm', __name__, url_prefix='/crm')


# ==================== CUSTOMERS ====================

@bp.route('/customers')
@login_required
@permission_required('customers:view')
def list_customers():
    """List all customers"""
    customers, status = api_request('GET', '/crm/customers')
    
    if status != 200:
        customers = []
    
    return render_template('crm/customers.html', title='Customers', customers=customers)


@bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
@permission_required('customers:create')
def new_customer():
    """Create new customer"""
    if request.method == 'GET':
        return render_template('crm/customer_form.html', title='New Customer')
    
    data = {
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'address': request.form.get('address'),
        'tax_id': request.form.get('tax_id'),
        'credit_limit': request.form.get('credit_limit', 0)
    }
    
    response, status = api_request('POST', '/crm/customers', data=data)
    
    if status == 200:
        if request.headers.get('HX-Request'):
            return render_template('crm/partials/customer_row.html', customer=response)
        flash('Customer created successfully', 'success')
        return redirect(url_for('crm.list_customers'))
    
    error = response.get('detail', 'Failed to create customer') if response else 'Failed to create customer'
    
    if request.headers.get('HX-Request'):
        return render_template('shared/partials/error_alert.html', error=error)
    
    flash(error, 'error')
    return render_template('crm/customer_form.html', title='New Customer', error=error)


@bp.route('/customers/<int:customer_id>')
@login_required
@permission_required('customers:view')
def view_customer(customer_id):
    """View customer details"""
    customer, status = api_request('GET', f'/crm/customers/{customer_id}')
    balance, _ = api_request('GET', f'/crm/customers/{customer_id}/balance')
    
    if status != 200:
        flash('Customer not found', 'error')
        return redirect(url_for('crm.list_customers'))
    
    return render_template('crm/customer_detail.html', title=customer.get('name', 'Customer'), customer=customer, balance=balance)


@bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('customers:edit')
def edit_customer(customer_id):
    """Edit customer"""
    if request.method == 'GET':
        customer, status = api_request('GET', f'/crm/customers/{customer_id}')
        if status != 200:
            flash('Customer not found', 'error')
            return redirect(url_for('crm.list_customers'))
        return render_template('crm/customer_form.html', title='Edit Customer', customer=customer)
    
    data = {k: v for k, v in request.form.items() if k != 'csrf_token'}
    
    response, status = api_request('PUT', f'/crm/customers/{customer_id}', data=data)
    
    if status == 200:
        if request.headers.get('HX-Request'):
            return render_template('crm/partials/customer_row.html', customer=response)
        flash('Customer updated successfully', 'success')
        return redirect(url_for('crm.view_customer', customer_id=customer_id))
    
    error = response.get('detail', 'Failed to update customer') if response else 'Failed to update customer'
    flash(error, 'error')
    return render_template('crm/customer_form.html', title='Edit Customer', error=error)


@bp.route('/customers/<int:customer_id>/delete', methods=['DELETE'])
@login_required
@permission_required('customers:delete')
def delete_customer(customer_id):
    """Delete customer"""
    response, status = api_request('DELETE', f'/crm/customers/{customer_id}')
    
    if status == 200:
        return ''
    
    return jsonify({'error': 'Failed to delete customer'}), 400


# ==================== VENDORS ====================

@bp.route('/vendors')
@login_required
@permission_required('vendors:view')
def list_vendors():
    """List all vendors"""
    vendors, status = api_request('GET', '/crm/vendors')
    
    if status != 200:
        vendors = []
    
    return render_template('crm/vendors.html', title='Vendors', vendors=vendors)


@bp.route('/vendors/new', methods=['GET', 'POST'])
@login_required
@permission_required('vendors:create')
def new_vendor():
    """Create new vendor"""
    if request.method == 'GET':
        return render_template('crm/vendor_form.html', title='New Vendor')
    
    data = {
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'address': request.form.get('address'),
        'tax_id': request.form.get('tax_id')
    }
    
    response, status = api_request('POST', '/crm/vendors', data=data)
    
    if status == 200:
        if request.headers.get('HX-Request'):
            return render_template('crm/partials/vendor_row.html', vendor=response)
        flash('Vendor created successfully', 'success')
        return redirect(url_for('crm.list_vendors'))
    
    error = response.get('detail', 'Failed to create vendor') if response else 'Failed to create vendor'
    flash(error, 'error')
    return render_template('crm/vendor_form.html', title='New Vendor', error=error)


@bp.route('/vendors/<int:vendor_id>')
@login_required
@permission_required('vendors:view')
def view_vendor(vendor_id):
    """View vendor details"""
    vendor, status = api_request('GET', f'/crm/vendors/{vendor_id}')
    balance, _ = api_request('GET', f'/crm/vendors/{vendor_id}/balance')
    
    if status != 200:
        flash('Vendor not found', 'error')
        return redirect(url_for('crm.list_vendors'))
    
    return render_template('crm/vendor_detail.html', title=vendor.get('name', 'Vendor'), vendor=vendor, balance=balance)
