"""
Reports Views
"""
from flask import Blueprint, render_template, request
from app import api_request, login_required, permission_required

bp = Blueprint('reports', __name__, url_prefix='/reports')


@bp.route('')
@login_required
@permission_required('reports:view')
def index():
    """Reports index"""
    return render_template('reports/index.html', title='Reports')


@bp.route('/sales')
@login_required
@permission_required('reports:view')
def sales_report():
    """Sales Report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    params = {}
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    
    report, status = api_request('GET', '/reports/sales', params=params)
    
    if status != 200:
        report = {}
    
    return render_template('reports/sales_report.html', title='Sales Report', report=report)


@bp.route('/purchases')
@login_required
@permission_required('reports:view')
def purchases_report():
    """Purchases Report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    params = {}
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    
    report, status = api_request('GET', '/reports/purchases', params=params)
    
    if status != 200:
        report = {}
    
    return render_template('reports/purchase_report.html', title='Purchases Report', report=report)


@bp.route('/expenses')
@login_required
@permission_required('reports:view')
def expenses_report():
    """Expenses Report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    params = {}
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    
    report, status = api_request('GET', '/reports/expenses', params=params)
    
    if status != 200:
        report = {}
    
    return render_template('reports/expense_report.html', title='Expenses Report', report=report)


@bp.route('/inventory')
@login_required
@permission_required('reports:view')
def inventory_report():
    """Inventory Report"""
    report, status = api_request('GET', '/reports/inventory')
    
    if status != 200:
        report = {}
    
    return render_template('reports/inventory_report.html', title='Inventory Report', report=report)


@bp.route('/aging')
@login_required
@permission_required('reports:view')
def aging_report():
    """Aging Report"""
    aging, status = api_request('GET', '/dashboard/aging')
    
    if status != 200:
        aging = {'receivables': {}, 'payables': {}}
    
    return render_template('reports/aging_report.html', title='Aging Report', aging=aging)


@bp.route('/trial-balance')
@login_required
@permission_required('reports:view')
def trial_balance():
    """Trial Balance"""
    report, status = api_request('GET', '/reports/trial-balance')
    
    if status != 200:
        report = {}
    
    return render_template('reports/trial_balance.html', title='Trial Balance', report=report)


@bp.route('/vat')
@login_required
@permission_required('reports:view')
def vat_report():
    """VAT Report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    params = {}
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    
    report, status = api_request('GET', '/reports/vat', params=params)
    
    if status != 200:
        report = {}
    
    return render_template('reports/vat_report.html', title='VAT Report', report=report)
