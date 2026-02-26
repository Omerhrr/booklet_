"""
HR API Routes - Employees, Payroll, Payslips
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    PayrollConfigCreate, Payslip
)
from app.services.hr_service import EmployeeService, PayrollConfigService, PayslipService

router = APIRouter(prefix="/hr", tags=["HR"])


# ==================== EMPLOYEES ====================

@router.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all employees"""
    employee_service = EmployeeService(db)
    return employee_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id,
        include_inactive
    )


@router.post("/employees", response_model=EmployeeResponse, dependencies=[Depends(PermissionChecker(["hr:create"]))])
async def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new employee"""
    employee_service = EmployeeService(db)
    employee = employee_service.create(employee_data, current_user.business_id)
    db.commit()
    return employee


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get employee by ID"""
    employee_service = EmployeeService(db)
    employee = employee_service.get_by_id(employee_id, current_user.business_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.put("/employees/{employee_id}", response_model=EmployeeResponse, dependencies=[Depends(PermissionChecker(["hr:edit"]))])
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update employee"""
    employee_service = EmployeeService(db)
    employee = employee_service.update(employee_id, current_user.business_id, employee_data)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.commit()
    return employee


@router.post("/employees/{employee_id}/terminate", dependencies=[Depends(PermissionChecker(["hr:edit"]))])
async def terminate_employee(
    employee_id: int,
    termination_date: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Terminate employee"""
    employee_service = EmployeeService(db)
    employee = employee_service.terminate(employee_id, current_user.business_id, termination_date)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.commit()
    return {"message": "Employee terminated", "employee": EmployeeResponse.model_validate(employee)}


@router.delete("/employees/{employee_id}", dependencies=[Depends(PermissionChecker(["hr:delete"]))])
async def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete employee"""
    employee_service = EmployeeService(db)
    if not employee_service.delete(employee_id, current_user.business_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    db.commit()
    return {"message": "Employee deleted"}


# ==================== PAYROLL CONFIG ====================

@router.get("/employees/{employee_id}/payroll-config")
async def get_payroll_config(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get employee's payroll configuration"""
    payroll_service = PayrollConfigService(db)
    config = payroll_service.get_by_employee(employee_id)
    if not config:
        raise HTTPException(status_code=404, detail="Payroll configuration not found")
    return config


@router.post("/employees/{employee_id}/payroll-config", dependencies=[Depends(PermissionChecker(["hr:edit"]))])
async def create_payroll_config(
    employee_id: int,
    config_data: PayrollConfigCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create payroll configuration for employee"""
    payroll_service = PayrollConfigService(db)
    config = payroll_service.create(config_data, employee_id)
    db.commit()
    return config


@router.put("/employees/{employee_id}/payroll-config", dependencies=[Depends(PermissionChecker(["hr:edit"]))])
async def update_payroll_config(
    employee_id: int,
    config_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update payroll configuration"""
    payroll_service = PayrollConfigService(db)
    config = payroll_service.update(employee_id, config_data)
    if not config:
        raise HTTPException(status_code=404, detail="Payroll configuration not found")
    db.commit()
    return config


# ==================== PAYSLIPS ====================

@router.get("/payslips")
async def list_payslips(
    pay_period_start: date = None,
    pay_period_end: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all payslips"""
    payslip_service = PayslipService(db)
    return payslip_service.get_by_business(
        current_user.business_id, pay_period_start, pay_period_end
    )


@router.get("/employees/{employee_id}/payslips")
async def list_employee_payslips(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List payslips for an employee"""
    payslip_service = PayslipService(db)
    return payslip_service.get_by_employee(employee_id)


@router.post("/payslips/generate", dependencies=[Depends(PermissionChecker(["hr:run_payroll"]))])
async def generate_payslip(
    employee_id: int,
    pay_period_start: date,
    pay_period_end: date,
    additional_deductions: float = 0,
    additional_allowances: float = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Generate payslip for an employee"""
    from decimal import Decimal
    
    employee_service = EmployeeService(db)
    payslip_service = PayslipService(db)
    
    employee = employee_service.get_by_id(employee_id, current_user.business_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        payslip = payslip_service.create_payslip(
            employee,
            pay_period_start,
            pay_period_end,
            current_user.business_id,
            Decimal(str(additional_deductions)),
            Decimal(str(additional_allowances))
        )
        db.commit()
        return payslip
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payroll/run", dependencies=[Depends(PermissionChecker(["hr:run_payroll"]))])
async def run_payroll(
    pay_period_start: date,
    pay_period_end: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Run payroll for all employees in branch"""
    payslip_service = PayslipService(db)
    payslips = payslip_service.run_payroll(
        current_user.business_id,
        current_user.selected_branch.id,
        pay_period_start,
        pay_period_end
    )
    db.commit()
    return {
        "message": f"Payroll completed for {len(payslips)} employees",
        "payslips": payslips
    }


@router.get("/payslips/{payslip_id}")
async def get_payslip(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get payslip by ID"""
    payslip_service = PayslipService(db)
    payslip = payslip_service.get_by_id(payslip_id, current_user.business_id)
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    return payslip


@router.post("/payslips/{payslip_id}/mark-paid", dependencies=[Depends(PermissionChecker(["hr:run_payroll"]))])
async def mark_payslip_paid(
    payslip_id: int,
    paid_date: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Mark payslip as paid"""
    payslip_service = PayslipService(db)
    payslip = payslip_service.mark_as_paid(payslip_id, current_user.business_id, paid_date)
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    db.commit()
    return {"message": "Payslip marked as paid"}


@router.get("/payroll/summary")
async def get_payroll_summary(
    pay_period_start: date,
    pay_period_end: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get payroll summary for a period"""
    payslip_service = PayslipService(db)
    return payslip_service.get_payroll_summary(
        current_user.business_id, pay_period_start, pay_period_end
    )
