"""
Dashboard Views
"""
from flask import Blueprint, render_template, request, session, jsonify
from app import api_request, login_required

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@bp.route('')
@login_required
def index():
    """Main dashboard"""
    # Get dashboard data
    dashboard_data, status = api_request('GET', '/dashboard/full')
    
    if status != 200:
        dashboard_data = {}
    
    return render_template('dashboard/index.html', title='Dashboard', dashboard=dashboard_data)


@bp.route('/stats')
@login_required
def stats():
    """Get dashboard stats (HTMX partial)"""
    stats_data, status = api_request('GET', '/dashboard/stats')
    
    if status != 200:
        stats_data = {}
    
    return render_template('dashboard/partials/stats.html', stats=stats_data)


@bp.route('/charts/sales')
@login_required
def sales_chart():
    """Get sales chart data"""
    days = request.args.get('days', 30, type=int)
    chart_data, status = api_request('GET', f'/dashboard/sales-chart?days={days}')
    return jsonify(chart_data) if status == 200 else jsonify({})


@bp.route('/charts/expenses')
@login_required
def expenses_chart():
    """Get expenses chart data"""
    days = request.args.get('days', 30, type=int)
    chart_data, status = api_request('GET', f'/dashboard/expense-chart?days={days}')
    return jsonify(chart_data) if status == 200 else jsonify({})
