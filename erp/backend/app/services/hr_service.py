"""
HR Service - Employees, Payroll, Payslips
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from decimal import Decimal
from datetime import date
from app.models import Employee, PayrollConfig, Payslip, PayFrequency, LedgerEntry, Account
from app.schemas import EmployeeCreate, EmployeeUpdate, PayrollConfigCreate


class EmployeeService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, employee_id: int, business_id: int) -> Optional[Employee]:
        return self.db.query(Employee).options(
            joinedload(Employee.payroll_config)
        ).filter(
            Employee.id == employee_id,
            Employee.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int, include_inactive: bool = False) -> List[Employee]:
        query = self.db.query(Employee).filter(
            Employee.branch_id == branch_id,
            Employee.business_id == business_id
        )
        if not include_inactive:
            query = query.filter(Employee.is_active == True)
        return query.order_by(Employee.full_name).all()
    
    def get_all_by_business(self, business_id: int) -> List[Employee]:
        return self.db.query(Employee).options(
            joinedload(Employee.payroll_config)
        ).filter(
            Employee.business_id == business_id
        ).order_by(Employee.full_name).all()
    
    def create(self, employee_data: EmployeeCreate, business_id: int) -> Employee:
        employee = Employee(
            full_name=employee_data.full_name,
            email=employee_data.email,
            phone_number=employee_data.phone_number,
            address=employee_data.address,
            hire_date=employee_data.hire_date,
            department=employee_data.department,
            position=employee_data.position,
            branch_id=employee_data.branch_id,
            business_id=business_id
        )
        self.db.add(employee)
        self.db.flush()
        
        # Create payroll config if provided
        if employee_data.payroll_config:
            payroll_config = PayrollConfig(
                gross_salary=employee_data.payroll_config.gross_salary,
                pay_frequency=employee_data.payroll_config.pay_frequency,
                paye_rate=employee_data.payroll_config.paye_rate,
                pension_employee_rate=employee_data.payroll_config.pension_employee_rate,
                pension_employer_rate=employee_data.payroll_config.pension_employer_rate,
                employee_id=employee.id
            )
            self.db.add(payroll_config)
        
        self.db.flush()
        return employee
    
    def update(self, employee_id: int, business_id: int, employee_data: EmployeeUpdate) -> Optional[Employee]:
        employee = self.get_by_id(employee_id, business_id)
        if not employee:
            return None
        
        update_data = employee_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(employee, key, value)
        
        self.db.flush()
        return employee
    
    def terminate(self, employee_id: int, business_id: int, termination_date: date) -> Optional[Employee]:
        employee = self.get_by_id(employee_id, business_id)
        if not employee:
            return None
        
        employee.termination_date = termination_date
        employee.is_active = False
        
        self.db.flush()
        return employee
    
    def delete(self, employee_id: int, business_id: int) -> bool:
        employee = self.get_by_id(employee_id, business_id)
        if not employee:
            return False
        
        # Check for payslips
        has_payslips = self.db.query(Payslip).filter(
            Payslip.employee_id == employee_id
        ).first()
        
        if has_payslips:
            employee.is_active = False
        else:
            self.db.delete(employee)
        
        return True


class PayrollConfigService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_employee(self, employee_id: int) -> Optional[PayrollConfig]:
        return self.db.query(PayrollConfig).filter(
            PayrollConfig.employee_id == employee_id
        ).first()
    
    def create(self, config_data: PayrollConfigCreate, employee_id: int) -> PayrollConfig:
        config = PayrollConfig(
            gross_salary=config_data.gross_salary,
            pay_frequency=config_data.pay_frequency,
            paye_rate=config_data.paye_rate,
            pension_employee_rate=config_data.pension_employee_rate,
            pension_employer_rate=config_data.pension_employer_rate,
            employee_id=employee_id
        )
        self.db.add(config)
        self.db.flush()
        return config
    
    def update(self, employee_id: int, config_data: dict) -> Optional[PayrollConfig]:
        config = self.get_by_employee(employee_id)
        if not config:
            return None
        
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.db.flush()
        return config


class PayslipService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, payslip_id: int, business_id: int) -> Optional[Payslip]:
        return self.db.query(Payslip).options(
            joinedload(Payslip.employee)
        ).filter(
            Payslip.id == payslip_id,
            Payslip.business_id == business_id
        ).first()
    
    def get_by_employee(self, employee_id: int) -> List[Payslip]:
        return self.db.query(Payslip).filter(
            Payslip.employee_id == employee_id
        ).order_by(Payslip.pay_period_start.desc()).all()
    
    def get_by_business(self, business_id: int, pay_period_start: date = None, pay_period_end: date = None) -> List[Payslip]:
        query = self.db.query(Payslip).options(
            joinedload(Payslip.employee)
        ).filter(
            Payslip.business_id == business_id
        )
        
        if pay_period_start:
            query = query.filter(Payslip.pay_period_start >= pay_period_start)
        if pay_period_end:
            query = query.filter(Payslip.pay_period_end <= pay_period_end)
        
        return query.order_by(Payslip.pay_period_start.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        last_payslip = self.db.query(Payslip).filter(
            Payslip.business_id == business_id
        ).order_by(Payslip.id.desc()).first()
        
        if last_payslip:
            try:
                num = int(last_payslip.payslip_number.replace("PS-", ""))
                return f"PS-{num + 1:05d}"
            except ValueError:
                pass
        
        return "PS-00001"
    
    def calculate_deductions(self, gross_salary: Decimal, paye_rate: Decimal, 
                           pension_employee_rate: Decimal) -> Dict[str, Decimal]:
        """Calculate tax and pension deductions"""
        paye_deduction = gross_salary * (paye_rate / 100) if paye_rate else Decimal("0")
        pension_deduction = gross_salary * (pension_employee_rate / 100) if pension_employee_rate else Decimal("0")
        
        return {
            "paye_deduction": paye_deduction,
            "pension_deduction": pension_deduction
        }
    
    def create_payslip(self, employee: Employee, pay_period_start: date, pay_period_end: date, 
                      business_id: int, additional_deductions: Decimal = Decimal("0"),
                      additional_allowances: Decimal = Decimal("0")) -> Payslip:
        """Generate payslip for an employee"""
        if not employee.payroll_config:
            raise ValueError("Employee has no payroll configuration")
        
        config = employee.payroll_config
        
        # Calculate deductions
        deductions = self.calculate_deductions(
            config.gross_salary,
            config.paye_rate or Decimal("0"),
            config.pension_employee_rate or Decimal("0")
        )
        
        paye_deduction = deductions["paye_deduction"]
        pension_deduction = deductions["pension_deduction"]
        other_deductions = config.other_deductions or Decimal("0")
        other_allowances = config.other_allowances or Decimal("0")
        
        total_deductions = paye_deduction + pension_deduction + other_deductions + additional_deductions
        net_salary = config.gross_salary + other_allowances + additional_allowances - total_deductions
        
        payslip = Payslip(
            payslip_number=self.get_next_number(business_id),
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            gross_salary=config.gross_salary + other_allowances + additional_allowances,
            paye_deduction=paye_deduction,
            pension_deduction=pension_deduction,
            other_deductions=other_deductions + additional_deductions,
            total_deductions=total_deductions,
            net_salary=net_salary,
            employee_id=employee.id,
            business_id=business_id
        )
        self.db.add(payslip)
        self.db.flush()
        
        return payslip
    
    def run_payroll(self, business_id: int, branch_id: int, pay_period_start: date, 
                   pay_period_end: date) -> List[Payslip]:
        """Run payroll for all active employees in a branch"""
        employees = self.db.query(Employee).options(
            joinedload(Employee.payroll_config)
        ).filter(
            Employee.business_id == business_id,
            Employee.branch_id == branch_id,
            Employee.is_active == True
        ).all()
        
        payslips = []
        for employee in employees:
            if employee.payroll_config:
                payslip = self.create_payslip(
                    employee, pay_period_start, pay_period_end, business_id
                )
                payslips.append(payslip)
        
        return payslips
    
    def mark_as_paid(self, payslip_id: int, business_id: int, paid_date: date = None) -> Optional[Payslip]:
        """Mark payslip as paid"""
        payslip = self.get_by_id(payslip_id, business_id)
        if not payslip:
            return None
        
        payslip.is_paid = True
        payslip.paid_date = paid_date or date.today()
        
        self.db.flush()
        return payslip
    
    def get_payroll_summary(self, business_id: int, pay_period_start: date, pay_period_end: date) -> Dict:
        """Get payroll summary for a period"""
        payslips = self.get_by_business(business_id, pay_period_start, pay_period_end)
        
        total_gross = sum(p.gross_salary for p in payslips)
        total_paye = sum(p.paye_deduction for p in payslips)
        total_pension = sum(p.pension_deduction for p in payslips)
        total_deductions = sum(p.total_deductions for p in payslips)
        total_net = sum(p.net_salary for p in payslips)
        
        return {
            "period_start": pay_period_start,
            "period_end": pay_period_end,
            "employee_count": len(payslips),
            "total_gross": total_gross,
            "total_paye": total_paye,
            "total_pension": total_pension,
            "total_deductions": total_deductions,
            "total_net": total_net,
            "payslips": payslips
        }
