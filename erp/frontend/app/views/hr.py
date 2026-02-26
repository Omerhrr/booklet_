"""
HR Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import api_request, login_required
import json

bp = Blueprint('hr', __name__, url_prefix='/hr')


@bp.route('/employees')
@login_required
def list_employees():
    """List all employees"""
    employees, status = api_request('GET', '/hr/employees')
    
    if status != 200:
        employees = []
    
    return render_template('hr/employees.html', title='Employees', employees=employees)


@bp.route('/employees/new', methods=['GET', 'POST'])
@login_required
def new_employee():
    """Create new employee"""
    if request.method == 'GET':
        return render_template('hr/employee_form.html', title='New Employee')
    
    payroll_config = None
    if request.form.get('gross_salary'):
        payroll_config = {
            'gross_salary': request.form.get('gross_salary'),
            'pay_frequency': request.form.get('pay_frequency', 'Monthly'),
            'paye_rate': request.form.get('paye_rate'),
            'pension_employee_rate': request.form.get('pension_employee_rate'),
            'pension_employer_rate': request.form.get('pension_employer_rate')
        }
    
    data = {
        'full_name': request.form.get('full_name'),
        'email': request.form.get('email'),
        'phone_number': request.form.get('phone_number'),
        'address': request.form.get('address'),
        'hire_date': request.form.get('hire_date'),
        'department': request.form.get('department'),
        'position': request.form.get('position'),
        'branch_id': session.get('selected_branch_id', 1),
        'payroll_config': payroll_config
    }
    
    response, status = api_request('POST', '/hr/employees', data=data)
    
    if status == 200:
        flash('Employee created successfully', 'success')
        return redirect(url_for('hr.view_employee', employee_id=response.get('id')))
    
    error = response.get('detail', 'Failed to create employee') if response else 'Failed'
    flash(error, 'error')
    return render_template('hr/employee_form.html', title='New Employee', error=error)


@bp.route('/employees/<int:employee_id>')
@login_required
def view_employee(employee_id):
    """View employee details"""
    employee, status = api_request('GET', f'/hr/employees/{employee_id}')
    
    if status != 200:
        flash('Employee not found', 'error')
        return redirect(url_for('hr.list_employees'))
    
    return render_template('hr/employee_detail.html',
                          title=employee.get('full_name', 'Employee'),
                          employee=employee)


@bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    """Edit employee"""
    if request.method == 'GET':
        employee, status = api_request('GET', f'/hr/employees/{employee_id}')
        if status != 200:
            flash('Employee not found', 'error')
            return redirect(url_for('hr.list_employees'))
        return render_template('hr/employee_form.html', title='Edit Employee', employee=employee)
    
    data = {k: v for k, v in request.form.items() if k != 'csrf_token'}
    
    response, status = api_request('PUT', f'/hr/employees/{employee_id}', data=data)
    
    if status == 200:
        flash('Employee updated', 'success')
        return redirect(url_for('hr.view_employee', employee_id=employee_id))
    
    error = response.get('detail', 'Failed to update employee') if response else 'Failed'
    flash(error, 'error')
    return redirect(url_for('hr.edit_employee', employee_id=employee_id))


@bp.route('/payroll')
@login_required
def run_payroll():
    """Run Payroll"""
    employees, _ = api_request('GET', '/hr/employees')
    return render_template('hr/run_payroll.html', title='Run Payroll', employees=employees or [])


@bp.route('/payslips')
@login_required
def payslips():
    """Payslip History"""
    payslips, status = api_request('GET', '/hr/payslips')
    
    if status != 200:
        payslips = []
    
    return render_template('hr/payslips.html', title='Payslips', payslips=payslips)


@bp.route('/payslips/<int:payslip_id>')
@login_required
def view_payslip(payslip_id):
    """View payslip details"""
    payslip, status = api_request('GET', f'/hr/payslips/{payslip_id}')
    
    if status != 200:
        flash('Payslip not found', 'error')
        return redirect(url_for('hr.payslips'))
    
    return render_template('hr/payslip_detail.html', title='Payslip', payslip=payslip)
