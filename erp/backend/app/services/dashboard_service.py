"""
Dashboard Service - Analytics and Reporting
"""
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from decimal import Decimal
from datetime import date, timedelta
from app.models import (
    SalesInvoice, PurchaseBill, Expense, Customer, Vendor, Product,
    LedgerEntry, Account, AccountType
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_stats(self, business_id: int, branch_id: int) -> Dict:
        """Get main dashboard statistics"""
        
        # Total Sales (this month)
        today = date.today()
        month_start = today.replace(day=1)
        
        sales_result = self.db.query(func.sum(SalesInvoice.total_amount)).filter(
            SalesInvoice.business_id == business_id,
            SalesInvoice.branch_id == branch_id,
            SalesInvoice.invoice_date >= month_start
        ).scalar() or Decimal("0")
        
        # Total Purchases (this month)
        purchases_result = self.db.query(func.sum(PurchaseBill.total_amount)).filter(
            PurchaseBill.business_id == business_id,
            PurchaseBill.branch_id == branch_id,
            PurchaseBill.bill_date >= month_start
        ).scalar() or Decimal("0")
        
        # Total Expenses (this month)
        expenses_result = self.db.query(func.sum(Expense.amount)).filter(
            Expense.business_id == business_id,
            Expense.branch_id == branch_id,
            Expense.expense_date >= month_start
        ).scalar() or Decimal("0")
        
        # Total Receivables
        receivables_result = self.db.query(func.sum(SalesInvoice.total_amount - SalesInvoice.paid_amount)).filter(
            SalesInvoice.business_id == business_id,
            SalesInvoice.branch_id == branch_id,
            SalesInvoice.status.in_(["Unpaid", "Partial", "Overdue"])
        ).scalar() or Decimal("0")
        
        # Total Payables
        payables_result = self.db.query(func.sum(PurchaseBill.total_amount - PurchaseBill.paid_amount)).filter(
            PurchaseBill.business_id == business_id,
            PurchaseBill.branch_id == branch_id,
            PurchaseBill.status.in_(["Unpaid", "Partial", "Overdue"])
        ).scalar() or Decimal("0")
        
        # Cash Balance
        cash_accounts = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.type == AccountType.ASSET,
            Account.name.in_(["Cash", "Bank"])
        ).all()
        
        cash_balance = Decimal("0")
        for account in cash_accounts:
            balance = self._get_account_balance(account.id)
            cash_balance += balance
        
        # Counts
        total_customers = self.db.query(Customer).filter(
            Customer.business_id == business_id,
            Customer.branch_id == branch_id,
            Customer.is_active == True
        ).count()
        
        total_vendors = self.db.query(Vendor).filter(
            Vendor.business_id == business_id,
            Vendor.branch_id == branch_id,
            Vendor.is_active == True
        ).count()
        
        total_products = self.db.query(Product).filter(
            Product.branch_id == branch_id,
            Product.is_active == True
        ).count()
        
        # Low stock products
        low_stock = self.db.query(Product).filter(
            Product.branch_id == branch_id,
            Product.is_active == True,
            Product.stock_quantity <= Product.reorder_level
        ).count()
        
        return {
            "total_sales": sales_result,
            "total_purchases": purchases_result,
            "total_expenses": expenses_result,
            "total_receivables": receivables_result,
            "total_payables": payables_result,
            "cash_balance": cash_balance,
            "total_customers": total_customers,
            "total_vendors": total_vendors,
            "total_products": total_products,
            "low_stock_products": low_stock
        }
    
    def _get_account_balance(self, account_id: int) -> Decimal:
        """Calculate account balance from ledger entries"""
        result = self.db.query(
            func.sum(LedgerEntry.debit - LedgerEntry.credit)
        ).filter(LedgerEntry.account_id == account_id).scalar()
        
        return result or Decimal("0")
    
    def get_sales_chart(self, business_id: int, branch_id: int, days: int = 30) -> Dict:
        """Get sales data for chart"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        results = self.db.query(
            SalesInvoice.invoice_date,
            func.sum(SalesInvoice.total_amount)
        ).filter(
            SalesInvoice.business_id == business_id,
            SalesInvoice.branch_id == branch_id,
            SalesInvoice.invoice_date >= start_date
        ).group_by(SalesInvoice.invoice_date).all()
        
        # Fill in missing dates
        date_dict = {r[0]: r[1] for r in results}
        labels = []
        values = []
        
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime("%Y-%m-%d"))
            values.append(date_dict.get(current_date, Decimal("0")))
            current_date += timedelta(days=1)
        
        return {"labels": labels, "values": values}
    
    def get_expense_chart(self, business_id: int, branch_id: int, days: int = 30) -> Dict:
        """Get expense data for chart"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        results = self.db.query(
            Expense.expense_date,
            func.sum(Expense.amount)
        ).filter(
            Expense.business_id == business_id,
            Expense.branch_id == branch_id,
            Expense.expense_date >= start_date
        ).group_by(Expense.expense_date).all()
        
        date_dict = {r[0]: r[1] for r in results}
        labels = []
        values = []
        
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime("%Y-%m-%d"))
            values.append(date_dict.get(current_date, Decimal("0")))
            current_date += timedelta(days=1)
        
        return {"labels": labels, "values": values}
    
    def get_receivables_aging(self, business_id: int, branch_id: int) -> Dict:
        """Get accounts receivable aging report"""
        today = date.today()
        
        invoices = self.db.query(SalesInvoice).filter(
            SalesInvoice.business_id == business_id,
            SalesInvoice.branch_id == branch_id,
            SalesInvoice.status.in_(["Unpaid", "Partial", "Overdue"])
        ).all()
        
        aging = {
            "current": Decimal("0"),
            "1_30": Decimal("0"),
            "31_60": Decimal("0"),
            "61_90": Decimal("0"),
            "over_90": Decimal("0")
        }
        
        for invoice in invoices:
            days_overdue = (today - invoice.due_date).days if invoice.due_date else 0
            outstanding = invoice.total_amount - invoice.paid_amount
            
            if days_overdue <= 0:
                aging["current"] += outstanding
            elif days_overdue <= 30:
                aging["1_30"] += outstanding
            elif days_overdue <= 60:
                aging["31_60"] += outstanding
            elif days_overdue <= 90:
                aging["61_90"] += outstanding
            else:
                aging["over_90"] += outstanding
        
        return aging
    
    def get_payables_aging(self, business_id: int, branch_id: int) -> Dict:
        """Get accounts payable aging report"""
        today = date.today()
        
        bills = self.db.query(PurchaseBill).filter(
            PurchaseBill.business_id == business_id,
            PurchaseBill.branch_id == branch_id,
            PurchaseBill.status.in_(["Unpaid", "Partial", "Overdue"])
        ).all()
        
        aging = {
            "current": Decimal("0"),
            "1_30": Decimal("0"),
            "31_60": Decimal("0"),
            "61_90": Decimal("0"),
            "over_90": Decimal("0")
        }
        
        for bill in bills:
            days_overdue = (today - bill.due_date).days if bill.due_date else 0
            outstanding = bill.total_amount - bill.paid_amount
            
            if days_overdue <= 0:
                aging["current"] += outstanding
            elif days_overdue <= 30:
                aging["1_30"] += outstanding
            elif days_overdue <= 60:
                aging["31_60"] += outstanding
            elif days_overdue <= 90:
                aging["61_90"] += outstanding
            else:
                aging["over_90"] += outstanding
        
        return aging
    
    def get_full_dashboard(self, business_id: int, branch_id: int) -> Dict:
        """Get all dashboard data"""
        return {
            "stats": self.get_stats(business_id, branch_id),
            "sales_chart": self.get_sales_chart(business_id, branch_id),
            "expense_chart": self.get_expense_chart(business_id, branch_id),
            "receivables_aging": self.get_receivables_aging(business_id, branch_id),
            "payables_aging": self.get_payables_aging(business_id, branch_id)
        }
