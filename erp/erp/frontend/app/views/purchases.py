"""
Purchases Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import api_request, login_required, permission_required
import json

bp = Blueprint('purchases', __name__, url_prefix='/purchases')


@bp.route('/bills')
@login_required
@permission_required('bills:view')
def list_bills():
    """List all purchase bills"""
    status_filter = request.args.get('status')
    params = {'status': status_filter} if status_filter else {}
    
    bills, status = api_request('GET', '/purchases/bills', params=params)
    
    if status != 200:
        bills = []
    
    return render_template('purchases/bills.html', title='Purchase Bills', bills=bills)


@bp.route('/bills/new', methods=['GET', 'POST'])
@login_required
@permission_required('bills:create')
def new_bill():
    """Create new purchase bill"""
    if request.method == 'GET':
        vendors, _ = api_request('GET', '/crm/vendors')
        products, _ = api_request('GET', '/inventory/products')
        
        return render_template('purchases/bill_form.html',
                              title='New Purchase Bill',
                              vendors=vendors or [],
                              products=products or [])
    
    # POST
    items_json = request.form.get('items_json', '[]')
    
    data = {
        'vendor_id': request.form.get('vendor_id'),
        'bill_date': request.form.get('bill_date'),
        'due_date': request.form.get('due_date'),
        'bill_number': request.form.get('bill_number'),
        'notes': request.form.get('notes'),
        'items': json.loads(items_json)
    }
    
    response, status = api_request('POST', '/purchases/bills', data=data)
    
    if status == 200:
        flash('Purchase bill created successfully', 'success')
        return redirect(url_for('purchases.view_bill', bill_id=response.get('id')))
    
    error = response.get('detail', 'Failed to create bill') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('purchases.new_bill'))


@bp.route('/bills/<int:bill_id>')
@login_required
@permission_required('bills:view')
def view_bill(bill_id):
    """View purchase bill"""
    bill, status = api_request('GET', f'/purchases/bills/{bill_id}')
    
    if status != 200:
        flash('Bill not found', 'error')
        return redirect(url_for('purchases.list_bills'))
    
    return render_template('purchases/bill_detail.html',
                          title=f"Bill {bill.get('bill_number', '')}",
                          bill=bill)


@bp.route('/bills/<int:bill_id>/payment', methods=['POST'])
@login_required
@permission_required('bills:edit')
def record_payment(bill_id):
    """Record payment for bill"""
    data = {
        'bill_id': bill_id,
        'payment_date': request.form.get('payment_date'),
        'amount': request.form.get('amount'),
        'payment_account_id': request.form.get('payment_account_id'),
        'reference': request.form.get('reference')
    }
    
    response, status = api_request('POST', f'/purchases/bills/{bill_id}/payment', data=data)
    
    if status == 200:
        flash('Payment recorded successfully', 'success')
        return redirect(url_for('purchases.view_bill', bill_id=bill_id))
    
    error = response.get('detail', 'Failed to record payment') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('purchases.view_bill', bill_id=bill_id))


# ==================== DEBIT NOTES ====================

@bp.route('/debit-notes')
@login_required
@permission_required('debit_notes:view')
def list_debit_notes():
    """List all debit notes"""
    debit_notes, status = api_request('GET', '/purchases/debit-notes')
    
    if status != 200:
        debit_notes = []
    
    return render_template('purchases/debit_notes.html', title='Debit Notes', debit_notes=debit_notes)
