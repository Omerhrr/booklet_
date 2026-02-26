"""
Banking Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import api_request, login_required, permission_required

bp = Blueprint('banking', __name__, url_prefix='/banking')


@bp.route('/accounts')
@login_required
@permission_required('banking:view')
def list_accounts():
    """List all bank accounts"""
    accounts, status = api_request('GET', '/banking/accounts')
    
    if status != 200:
        accounts = []
    
    return render_template('banking/accounts.html', title='Bank Accounts', accounts=accounts)


@bp.route('/accounts/new', methods=['GET', 'POST'])
@login_required
@permission_required('banking:create')
def new_account():
    """Create new bank account"""
    if request.method == 'GET':
        coa_accounts, _ = api_request('GET', '/accounting/accounts')
        return render_template('banking/account_form.html', title='New Bank Account', coa_accounts=coa_accounts or [])
    
    data = {
        'account_name': request.form.get('account_name'),
        'bank_name': request.form.get('bank_name'),
        'account_number': request.form.get('account_number'),
        'currency': request.form.get('currency', 'USD'),
        'chart_of_account_id': request.form.get('chart_of_account_id')
    }
    
    response, status = api_request('POST', '/banking/accounts', data=data)
    
    if status == 200:
        flash('Bank account created', 'success')
        return redirect(url_for('banking.list_accounts'))
    
    error = response.get('detail', 'Failed to create bank account') if response else 'Failed'
    flash(error, 'error')
    return render_template('banking/account_form.html', title='New Bank Account')


@bp.route('/accounts/<int:account_id>')
@login_required
@permission_required('banking:view')
def view_account(account_id):
    """View bank account details"""
    account, status = api_request('GET', f'/banking/accounts/{account_id}')
    
    if status != 200:
        flash('Account not found', 'error')
        return redirect(url_for('banking.list_accounts'))
    
    return render_template('banking/account_detail.html',
                          title=account.get('account_name', 'Bank Account'),
                          account=account)


@bp.route('/transfers')
@login_required
@permission_required('banking:view')
def transfers():
    """Fund transfers"""
    transfers, status = api_request('GET', '/banking/transfers')
    accounts, _ = api_request('GET', '/banking/accounts')
    
    if status != 200:
        transfers = []
    
    return render_template('banking/transfers.html', title='Fund Transfers', transfers=transfers, accounts=accounts or [])


@bp.route('/transfers/new', methods=['POST'])
@login_required
@permission_required('banking:create')
def new_transfer():
    """Create fund transfer"""
    data = {
        'transfer_date': request.form.get('transfer_date'),
        'amount': request.form.get('amount'),
        'from_account_id': request.form.get('from_account_id'),
        'to_account_id': request.form.get('to_account_id'),
        'description': request.form.get('description'),
        'reference': request.form.get('reference')
    }
    
    response, status = api_request('POST', '/banking/transfers', data=data)
    
    if status == 200:
        flash('Transfer completed', 'success')
        return redirect(url_for('banking.transfers'))
    
    error = response.get('detail', 'Failed to create transfer') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('banking.transfers'))


@bp.route('/reconciliation')
@login_required
@permission_required('banking:view')
def reconciliation():
    """Bank Reconciliation"""
    accounts, status = api_request('GET', '/banking/accounts')
    
    return render_template('banking/reconciliation.html', title='Bank Reconciliation', accounts=accounts or [])
