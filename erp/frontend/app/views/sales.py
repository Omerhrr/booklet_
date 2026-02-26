"""
Sales Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import date
from app import api_request, login_required
import json

bp = Blueprint('sales', __name__, url_prefix='/sales')


@bp.route('/invoices')
@login_required
def list_invoices():
    """List all sales invoices"""
    status_filter = request.args.get('status')
    params = {'status': status_filter} if status_filter else {}
    
    invoices, status = api_request('GET', '/sales/invoices', params=params)
    
    if status != 200:
        invoices = []
    
    return render_template('sales/invoices.html', title='Sales Invoices', invoices=invoices)


@bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
def new_invoice():
    """Create new sales invoice"""
    if request.method == 'GET':
        customers, _ = api_request('GET', '/crm/customers')
        products, _ = api_request('GET', '/inventory/products')
        next_number, _ = api_request('GET', '/sales/next-number')
        business, _ = api_request('GET', '/settings/business')
        
        return render_template('sales/invoice_form.html', 
                              title='New Sales Invoice',
                              customers=customers or [],
                              products=products or [],
                              next_number=next_number.get('next_number', 'INV-00001'),
                              today=date.today().isoformat(),
                              vat_rate=business.get('vat_rate', 0) if business else 0)
    
    # POST - Process items from form
    items = []
    item_index = 0
    while f'items[{item_index}][product_id]' in request.form:
        items.append({
            'product_id': int(request.form.get(f'items[{item_index}][product_id]')),
            'quantity': float(request.form.get(f'items[{item_index}][quantity]', 0)),
            'price': float(request.form.get(f'items[{item_index}][price]', 0))
        })
        item_index += 1
    
    data = {
        'customer_id': int(request.form.get('customer_id')),
        'invoice_date': request.form.get('invoice_date'),
        'due_date': request.form.get('due_date') or None,
        'notes': request.form.get('notes'),
        'items': items
    }
    
    response, status = api_request('POST', '/sales/invoices', data=data)
    
    if status == 200:
        flash('Invoice created successfully', 'success')
        return redirect(url_for('sales.view_invoice', invoice_id=response.get('id')))
    
    error = response.get('detail', 'Failed to create invoice') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('sales.new_invoice'))


@bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View sales invoice"""
    invoice, status = api_request('GET', f'/sales/invoices/{invoice_id}')
    
    if status != 200:
        flash('Invoice not found', 'error')
        return redirect(url_for('sales.list_invoices'))
    
    return render_template('sales/invoice_detail.html', 
                          title=f"Invoice {invoice.get('invoice_number', '')}",
                          invoice=invoice)


@bp.route('/invoices/<int:invoice_id>/payment', methods=['POST'])
@login_required
def record_payment(invoice_id):
    """Record payment for invoice"""
    data = {
        'invoice_id': invoice_id,
        'payment_date': request.form.get('payment_date'),
        'amount': request.form.get('amount'),
        'payment_account_id': request.form.get('payment_account_id'),
        'reference': request.form.get('reference')
    }
    
    response, status = api_request('POST', f'/sales/invoices/{invoice_id}/payment', data=data)
    
    if status == 200:
        flash('Payment recorded successfully', 'success')
        return redirect(url_for('sales.view_invoice', invoice_id=invoice_id))
    
    error = response.get('detail', 'Failed to record payment') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('sales.view_invoice', invoice_id=invoice_id))


@bp.route('/invoices/<int:invoice_id>/write-off', methods=['POST'])
@login_required
def write_off_invoice(invoice_id):
    """Write off invoice"""
    data = {
        'write_off_date': request.form.get('write_off_date')
    }
    
    response, status = api_request('POST', f'/sales/invoices/{invoice_id}/write-off', data=data)
    
    if status == 200:
        flash('Invoice written off', 'success')
        return redirect(url_for('sales.view_invoice', invoice_id=invoice_id))
    
    error = response.get('detail', 'Failed to write off invoice') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('sales.view_invoice', invoice_id=invoice_id))


# ==================== CREDIT NOTES ====================

@bp.route('/credit-notes')
@login_required
def list_credit_notes():
    """List all credit notes"""
    credit_notes, status = api_request('GET', '/sales/credit-notes')
    
    if status != 200:
        credit_notes = []
    
    return render_template('sales/credit_notes.html', title='Credit Notes', credit_notes=credit_notes)


@bp.route('/credit-notes/<int:credit_note_id>')
@login_required
def view_credit_note(credit_note_id):
    """View credit note"""
    credit_note, status = api_request('GET', f'/sales/credit-notes/{credit_note_id}')
    
    if status != 200:
        flash('Credit note not found', 'error')
        return redirect(url_for('sales.list_credit_notes'))
    
    return render_template('sales/credit_note_detail.html',
                          title=f"Credit Note {credit_note.get('credit_note_number', '')}",
                          credit_note=credit_note)
