"""
Accounting Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import api_request, login_required, permission_required
import json

bp = Blueprint('accounting', __name__, url_prefix='/accounting')


@bp.route('/chart-of-accounts')
@login_required
@permission_required('accounts:view')
def chart_of_accounts():
    """Chart of Accounts"""
    accounts, status = api_request('GET', '/accounting/accounts')
    
    if status != 200:
        accounts = []
    
    return render_template('accounting/chart_of_accounts.html', title='Chart of Accounts', accounts=accounts)


@bp.route('/accounts/new', methods=['POST'])
@login_required
@permission_required('accounts:create')
def create_account():
    """Create new account"""
    data = {
        'name': request.form.get('name'),
        'code': request.form.get('code'),
        'type': request.form.get('type'),
        'description': request.form.get('description'),
        'parent_id': request.form.get('parent_id')
    }
    
    response, status = api_request('POST', '/accounting/accounts', data=data)
    
    if status == 200:
        flash('Account created', 'success')
        return redirect(url_for('accounting.chart_of_accounts'))
    
    error = response.get('detail', 'Failed to create account') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('accounting.chart_of_accounts'))


@bp.route('/journal')
@login_required
@permission_required('journal:view')
def journal():
    """Journal entries list"""
    journals, status = api_request('GET', '/accounting/journal')
    
    if status != 200:
        journals = []
    
    return render_template('accounting/journal_list.html', title='Journal Entries', journals=journals)


@bp.route('/journal/new', methods=['GET', 'POST'])
@login_required
@permission_required('journal:create')
def new_journal():
    """Create journal entry"""
    if request.method == 'GET':
        accounts, _ = api_request('GET', '/accounting/accounts')
        return render_template('accounting/journal_form.html', title='New Journal Entry', accounts=accounts or [])
    
    lines_json = request.form.get('lines_json', '[]')
    
    data = {
        'transaction_date': request.form.get('transaction_date'),
        'description': request.form.get('description'),
        'reference': request.form.get('reference'),
        'lines': json.loads(lines_json)
    }
    
    response, status = api_request('POST', '/accounting/journal', data=data)
    
    if status == 200:
        flash('Journal entry created', 'success')
        return redirect(url_for('accounting.journal'))
    
    error = response.get('detail', 'Failed to create journal entry') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('accounting.new_journal'))


@bp.route('/ledger')
@login_required
@permission_required('accounts:view')
def general_ledger():
    """General Ledger"""
    return render_template('accounting/general_ledger.html', title='General Ledger')


@bp.route('/balance-sheet')
@login_required
@permission_required('reports:view')
def balance_sheet():
    """Balance Sheet Report"""
    return render_template('accounting/balance_sheet.html', title='Balance Sheet')


@bp.route('/profit-loss')
@login_required
@permission_required('reports:view')
def profit_loss():
    """Profit & Loss Report"""
    return render_template('accounting/profit_loss.html', title='Profit & Loss')


@bp.route('/trial-balance')
@login_required
@permission_required('reports:view')
def trial_balance():
    """Trial Balance Report"""
    return render_template('accounting/trial_balance.html', title='Trial Balance')
