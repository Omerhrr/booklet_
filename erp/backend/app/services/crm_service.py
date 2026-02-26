"""
CRM Service - Business Logic for Customers and Vendors
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from app.models import Customer, Vendor, SalesInvoice, PurchaseBill, LedgerEntry
from app.schemas import CustomerCreate, CustomerUpdate, VendorCreate, VendorUpdate


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, customer_id: int, business_id: int) -> Optional[Customer]:
        return self.db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int, include_inactive: bool = False) -> List[Customer]:
        query = self.db.query(Customer).filter(
            Customer.business_id == business_id,
            Customer.branch_id == branch_id
        )
        if not include_inactive:
            query = query.filter(Customer.is_active == True)
        return query.all()
    
    def get_all_by_business(self, business_id: int) -> List[Customer]:
        return self.db.query(Customer).filter(Customer.business_id == business_id).all()
    
    def create(self, customer_data: CustomerCreate, business_id: int) -> Customer:
        customer = Customer(
            name=customer_data.name,
            email=customer_data.email,
            phone=customer_data.phone,
            address=customer_data.address,
            tax_id=customer_data.tax_id,
            credit_limit=customer_data.credit_limit,
            branch_id=customer_data.branch_id,
            business_id=business_id
        )
        self.db.add(customer)
        self.db.flush()
        return customer
    
    def update(self, customer_id: int, business_id: int, customer_data: CustomerUpdate) -> Optional[Customer]:
        customer = self.get_by_id(customer_id, business_id)
        if not customer:
            return None
        
        update_data = customer_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(customer, key, value)
        
        self.db.flush()
        return customer
    
    def delete(self, customer_id: int, business_id: int) -> bool:
        customer = self.get_by_id(customer_id, business_id)
        if not customer:
            return False
        
        # Check for related invoices
        has_invoices = self.db.query(SalesInvoice).filter(
            SalesInvoice.customer_id == customer_id
        ).first()
        
        if has_invoices:
            # Soft delete instead
            customer.is_active = False
        else:
            self.db.delete(customer)
        
        return True
    
    def get_balance(self, customer_id: int) -> Decimal:
        """Calculate customer's outstanding balance"""
        result = self.db.query(LedgerEntry).filter(
            LedgerEntry.customer_id == customer_id
        ).all()
        
        balance = Decimal("0.00")
        for entry in result:
            balance += entry.debit - entry.credit
        
        return balance
    
    def get_with_balance(self, customer_id: int, business_id: int) -> dict:
        customer = self.get_by_id(customer_id, business_id)
        if not customer:
            return None
        
        balance = self.get_balance(customer_id)
        
        return {
            **customer.__dict__,
            "total_outstanding": balance
        }


class VendorService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, vendor_id: int, business_id: int) -> Optional[Vendor]:
        return self.db.query(Vendor).filter(
            Vendor.id == vendor_id,
            Vendor.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int, include_inactive: bool = False) -> List[Vendor]:
        query = self.db.query(Vendor).filter(
            Vendor.business_id == business_id,
            Vendor.branch_id == branch_id
        )
        if not include_inactive:
            query = query.filter(Vendor.is_active == True)
        return query.all()
    
    def get_all_by_business(self, business_id: int) -> List[Vendor]:
        return self.db.query(Vendor).filter(Vendor.business_id == business_id).all()
    
    def create(self, vendor_data: VendorCreate, business_id: int) -> Vendor:
        vendor = Vendor(
            name=vendor_data.name,
            email=vendor_data.email,
            phone=vendor_data.phone,
            address=vendor_data.address,
            tax_id=vendor_data.tax_id,
            branch_id=vendor_data.branch_id,
            business_id=business_id
        )
        self.db.add(vendor)
        self.db.flush()
        return vendor
    
    def update(self, vendor_id: int, business_id: int, vendor_data: VendorUpdate) -> Optional[Vendor]:
        vendor = self.get_by_id(vendor_id, business_id)
        if not vendor:
            return None
        
        update_data = vendor_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(vendor, key, value)
        
        self.db.flush()
        return vendor
    
    def delete(self, vendor_id: int, business_id: int) -> bool:
        vendor = self.get_by_id(vendor_id, business_id)
        if not vendor:
            return False
        
        # Check for related bills
        has_bills = self.db.query(PurchaseBill).filter(
            PurchaseBill.vendor_id == vendor_id
        ).first()
        
        if has_bills:
            vendor.is_active = False
        else:
            self.db.delete(vendor)
        
        return True
    
    def get_balance(self, vendor_id: int) -> Decimal:
        """Calculate vendor's outstanding balance"""
        result = self.db.query(LedgerEntry).filter(
            LedgerEntry.vendor_id == vendor_id
        ).all()
        
        balance = Decimal("0.00")
        for entry in result:
            balance += entry.credit - entry.debit
        
        return balance
