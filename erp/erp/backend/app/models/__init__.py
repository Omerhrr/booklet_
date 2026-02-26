"""
SQLAlchemy Models for ERP System
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Numeric,
    ForeignKey, Enum, Table, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import enum

from app.core.database import Base


# ==================== ENUMS ====================

class AccountType(enum.Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class InvoiceStatus(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PayFrequency(enum.Enum):
    MONTHLY = "Monthly"
    WEEKLY = "Weekly"
    BI_WEEKLY = "Bi-Weekly"


class PlanType(enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# ==================== ASSOCIATION TABLES ====================

class RolePermission(Base):
    """Association table for Role-Permission many-to-many"""
    __tablename__ = 'role_permissions'
    
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")
    
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )


class UserBranchRole(Base):
    """Association table for User-Branch-Role many-to-many"""
    __tablename__ = 'user_branch_roles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="roles")
    branch = relationship("Branch", back_populates="user_assignments")
    role = relationship("Role", back_populates="user_assignments")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'branch_id', 'role_id', name='uq_user_branch_role'),
    )


# ==================== CORE MODELS ====================

class Business(Base):
    """Business/Company entity"""
    __tablename__ = 'businesses'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default=PlanType.FREE.value)
    is_vat_registered = Column(Boolean, default=False)
    vat_rate = Column(Numeric(5, 2), default=Decimal("0.00"))
    logo_url = Column(String(500), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    tax_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="business", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="business", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="business", cascade="all, delete-orphan")
    vendors = relationship("Vendor", back_populates="business", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="business", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="business", cascade="all, delete-orphan")
    sales_invoices = relationship("SalesInvoice", back_populates="business", cascade="all, delete-orphan")
    purchase_bills = relationship("PurchaseBill", back_populates="business", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="business", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="business", cascade="all, delete-orphan")
    bank_accounts = relationship("BankAccount", back_populates="business", cascade="all, delete-orphan")
    journal_vouchers = relationship("JournalVoucher", back_populates="business", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="business", cascade="all, delete-orphan")
    fixed_assets = relationship("FixedAsset", back_populates="business", cascade="all, delete-orphan")


class User(Base):
    """User account"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_superuser = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="users")
    roles = relationship("UserBranchRole", back_populates="user", cascade="all, delete-orphan")
    stock_adjustments = relationship("StockAdjustment", back_populates="user")
    created_invoices = relationship("SalesInvoice", back_populates="created_by_user")
    created_bills = relationship("PurchaseBill", back_populates="created_by_user")
    journal_vouchers = relationship("JournalVoucher", back_populates="created_by_user")
    
    @property
    def accessible_branches(self):
        return [assignment.branch for assignment in self.roles]
    
    @property
    def selected_branch(self):
        """Return the user's selected branch, or default/first accessible branch.
        
        Priority:
        1. _selected_branch set by get_current_active_user (admin-selected via cookie)
        2. Default branch from accessible branches
        3. First accessible branch
        """
        # Check if a branch was explicitly selected (for admin branch switching)
        if hasattr(self, '_selected_branch') and self._selected_branch is not None:
            return self._selected_branch
        
        branches = self.accessible_branches
        if not branches:
            return None
        # Return default branch if exists, otherwise first accessible
        for branch in branches:
            if branch.is_default:
                return branch
        return branches[0]


class Branch(Base):
    """Business branch/location"""
    __tablename__ = 'branches'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    currency = Column(String(10), default="USD")
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="branches")
    user_assignments = relationship("UserBranchRole", back_populates="branch", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="branch")
    vendors = relationship("Vendor", back_populates="branch")
    categories = relationship("Category", back_populates="branch")
    products = relationship("Product", back_populates="branch")
    sales_invoices = relationship("SalesInvoice", back_populates="branch")
    purchase_bills = relationship("PurchaseBill", back_populates="branch")
    expenses = relationship("Expense", back_populates="branch")
    employees = relationship("Employee", back_populates="branch")
    bank_accounts = relationship("BankAccount", back_populates="branch")
    journal_vouchers = relationship("JournalVoucher", back_populates="branch")
    
    __table_args__ = (
        Index('ix_branches_business_id', 'business_id'),
    )


class Permission(Base):
    """System permission"""
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    role_links = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class Role(Base):
    """User role"""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="roles")
    permission_links = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_assignments = relationship("UserBranchRole", back_populates="role", cascade="all, delete-orphan")
    
    @property
    def permissions(self):
        return [link.permission for link in self.permission_links]
    
    @property
    def permission_ids(self):
        return [link.permission_id for link in self.permission_links]


# ==================== ACCOUNTING MODELS ====================

class Account(Base):
    """Chart of Accounts"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(20), nullable=True)
    type = Column(Enum(AccountType), nullable=False)
    description = Column(Text, nullable=True)
    is_system_account = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="accounts")
    parent = relationship("Account", remote_side=[id], backref="children")
    bank_accounts = relationship("BankAccount", back_populates="chart_of_account")
    ledger_entries = relationship("LedgerEntry", back_populates="account")
    budget_items = relationship("BudgetItem", back_populates="account")
    
    __table_args__ = (
        Index('ix_accounts_business_id', 'business_id'),
        Index('ix_accounts_code', 'code'),
    )


class JournalVoucher(Base):
    """Journal voucher for manual journal entries"""
    __tablename__ = 'journal_vouchers'
    
    id = Column(Integer, primary_key=True)
    voucher_number = Column(String(50), nullable=False)
    transaction_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)
    is_posted = Column(Boolean, default=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="journal_vouchers")
    business = relationship("Business", back_populates="journal_vouchers")
    created_by_user = relationship("User", back_populates="journal_vouchers")
    ledger_entries = relationship("LedgerEntry", back_populates="journal_voucher", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('voucher_number', 'business_id', name='uq_journal_voucher_number'),
    )


class LedgerEntry(Base):
    """General ledger entry"""
    __tablename__ = 'ledger_entries'
    
    id = Column(Integer, primary_key=True)
    transaction_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)
    debit = Column(Numeric(15, 2), default=Decimal("0.00"))
    credit = Column(Numeric(15, 2), default=Decimal("0.00"))
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    journal_voucher_id = Column(Integer, ForeignKey('journal_vouchers.id', ondelete='CASCADE'), nullable=True)
    sales_invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='SET NULL'), nullable=True)
    purchase_bill_id = Column(Integer, ForeignKey('purchase_bills.id', ondelete='SET NULL'), nullable=True)
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='SET NULL'), nullable=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="ledger_entries")
    journal_voucher = relationship("JournalVoucher", back_populates="ledger_entries")
    sales_invoice = relationship("SalesInvoice", back_populates="ledger_entries")
    purchase_bill = relationship("PurchaseBill", back_populates="ledger_entries")
    customer = relationship("Customer", back_populates="ledger_entries")
    vendor = relationship("Vendor", back_populates="ledger_entries")
    branch = relationship("Branch")
    
    __table_args__ = (
        Index('ix_ledger_entries_account_id', 'account_id'),
        Index('ix_ledger_entries_transaction_date', 'transaction_date'),
    )


# ==================== CRM MODELS ====================

class Customer(Base):
    """Customer"""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    tax_id = Column(String(50), nullable=True)
    credit_limit = Column(Numeric(15, 2), default=Decimal("0.00"))
    is_active = Column(Boolean, default=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="customers")
    business = relationship("Business", back_populates="customers")
    sales_invoices = relationship("SalesInvoice", back_populates="customer")
    ledger_entries = relationship("LedgerEntry", back_populates="customer")
    
    __table_args__ = (
        Index('ix_customers_business_id', 'business_id'),
    )


class Vendor(Base):
    """Vendor/Supplier"""
    __tablename__ = 'vendors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    tax_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="vendors")
    business = relationship("Business", back_populates="vendors")
    purchase_bills = relationship("PurchaseBill", back_populates="vendor")
    ledger_entries = relationship("LedgerEntry", back_populates="vendor")
    
    __table_args__ = (
        Index('ix_vendors_business_id', 'business_id'),
    )


# ==================== INVENTORY MODELS ====================

class Category(Base):
    """Product category"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="categories")
    business = relationship("Business", back_populates="categories")
    products = relationship("Product", back_populates="category")
    
    __table_args__ = (
        Index('ix_categories_business_id', 'business_id'),
    )


class Product(Base):
    """Product/Item"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    unit = Column(String(20), default="pcs")
    purchase_price = Column(Numeric(15, 2), default=Decimal("0.00"))
    sales_price = Column(Numeric(15, 2), default=Decimal("0.00"))
    opening_stock = Column(Numeric(15, 2), default=Decimal("0.00"))
    stock_quantity = Column(Numeric(15, 2), default=Decimal("0.00"))
    reorder_level = Column(Numeric(15, 2), default=Decimal("0.00"))
    is_active = Column(Boolean, default=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    branch = relationship("Branch", back_populates="products")
    business = relationship("Business", back_populates="products")
    stock_adjustments = relationship("StockAdjustment", back_populates="product")
    sales_invoice_items = relationship("SalesInvoiceItem", back_populates="product")
    purchase_bill_items = relationship("PurchaseBillItem", back_populates="product")
    
    __table_args__ = (
        Index('ix_products_business_id', 'business_id'),
        Index('ix_products_sku', 'sku'),
    )


class StockAdjustment(Base):
    """Stock adjustment record"""
    __tablename__ = 'stock_adjustments'
    
    id = Column(Integer, primary_key=True)
    quantity_change = Column(Numeric(15, 2), nullable=False)
    reason = Column(Text, nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="stock_adjustments")
    user = relationship("User", back_populates="stock_adjustments")


# ==================== SALES MODELS ====================

class SalesInvoice(Base):
    """Sales Invoice"""
    __tablename__ = 'sales_invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    sub_total = Column(Numeric(15, 2), default=Decimal("0.00"))
    vat_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    paid_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    status = Column(String(20), default=InvoiceStatus.PENDING.value)
    notes = Column(Text, nullable=True)
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="sales_invoices")
    branch = relationship("Branch", back_populates="sales_invoices")
    business = relationship("Business", back_populates="sales_invoices")
    created_by_user = relationship("User", back_populates="created_invoices")
    items = relationship("SalesInvoiceItem", back_populates="sales_invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sales_invoice", cascade="all, delete-orphan")
    credit_notes = relationship("CreditNote", back_populates="sales_invoice", cascade="all, delete-orphan")
    ledger_entries = relationship("LedgerEntry", back_populates="sales_invoice")
    
    __table_args__ = (
        UniqueConstraint('invoice_number', 'business_id', name='uq_sales_invoice_number'),
        Index('ix_sales_invoices_business_id', 'business_id'),
    )


class SalesInvoiceItem(Base):
    """Sales Invoice Line Item"""
    __tablename__ = 'sales_invoice_items'
    
    id = Column(Integer, primary_key=True)
    quantity = Column(Numeric(15, 2), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    returned_quantity = Column(Numeric(15, 2), default=Decimal("0.00"))
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    sales_invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="sales_invoice_items")
    sales_invoice = relationship("SalesInvoice", back_populates="items")
    
    @property
    def total(self):
        return self.quantity * self.price


class Payment(Base):
    """Payment received"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    payment_number = Column(String(50), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    reference = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="cash")
    sales_invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sales_invoice = relationship("SalesInvoice", back_populates="payments")
    account = relationship("Account")


class CreditNote(Base):
    """Credit Note for sales returns"""
    __tablename__ = 'credit_notes'
    
    id = Column(Integer, primary_key=True)
    credit_note_number = Column(String(50), nullable=False)
    credit_note_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    reason = Column(Text, nullable=True)
    sales_invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sales_invoice = relationship("SalesInvoice", back_populates="credit_notes")
    branch = relationship("Branch")
    business = relationship("Business")
    items = relationship("CreditNoteItem", back_populates="credit_note", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('credit_note_number', 'business_id', name='uq_credit_note_number'),
    )


class CreditNoteItem(Base):
    """Credit Note Line Item"""
    __tablename__ = 'credit_note_items'
    
    id = Column(Integer, primary_key=True)
    quantity = Column(Numeric(15, 2), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    credit_note_id = Column(Integer, ForeignKey('credit_notes.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    credit_note = relationship("CreditNote", back_populates="items")
    
    @property
    def total(self):
        return self.quantity * self.price


# ==================== PURCHASES MODELS ====================

class PurchaseBill(Base):
    """Purchase Bill"""
    __tablename__ = 'purchase_bills'
    
    id = Column(Integer, primary_key=True)
    bill_number = Column(String(50), nullable=False)
    vendor_bill_number = Column(String(100), nullable=True)
    bill_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    sub_total = Column(Numeric(15, 2), default=Decimal("0.00"))
    vat_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    paid_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    status = Column(String(20), default=InvoiceStatus.PENDING.value)
    notes = Column(Text, nullable=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="purchase_bills")
    branch = relationship("Branch", back_populates="purchase_bills")
    business = relationship("Business", back_populates="purchase_bills")
    created_by_user = relationship("User", back_populates="created_bills")
    items = relationship("PurchaseBillItem", back_populates="purchase_bill", cascade="all, delete-orphan")
    debit_notes = relationship("DebitNote", back_populates="purchase_bill", cascade="all, delete-orphan")
    ledger_entries = relationship("LedgerEntry", back_populates="purchase_bill")
    
    __table_args__ = (
        UniqueConstraint('bill_number', 'business_id', name='uq_purchase_bill_number'),
        Index('ix_purchase_bills_business_id', 'business_id'),
    )


class PurchaseBillItem(Base):
    """Purchase Bill Line Item"""
    __tablename__ = 'purchase_bill_items'
    
    id = Column(Integer, primary_key=True)
    quantity = Column(Numeric(15, 2), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    returned_quantity = Column(Numeric(15, 2), default=Decimal("0.00"))
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    purchase_bill_id = Column(Integer, ForeignKey('purchase_bills.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="purchase_bill_items")
    purchase_bill = relationship("PurchaseBill", back_populates="items")
    
    @property
    def total(self):
        return self.quantity * self.price


class DebitNote(Base):
    """Debit Note for purchase returns"""
    __tablename__ = 'debit_notes'
    
    id = Column(Integer, primary_key=True)
    debit_note_number = Column(String(50), nullable=False)
    debit_note_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    reason = Column(Text, nullable=True)
    purchase_bill_id = Column(Integer, ForeignKey('purchase_bills.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_bill = relationship("PurchaseBill", back_populates="debit_notes")
    branch = relationship("Branch")
    business = relationship("Business")
    items = relationship("DebitNoteItem", back_populates="debit_note", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('debit_note_number', 'business_id', name='uq_debit_note_number'),
    )


class DebitNoteItem(Base):
    """Debit Note Line Item"""
    __tablename__ = 'debit_note_items'
    
    id = Column(Integer, primary_key=True)
    quantity = Column(Numeric(15, 2), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    debit_note_id = Column(Integer, ForeignKey('debit_notes.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    debit_note = relationship("DebitNote", back_populates="items")
    
    @property
    def total(self):
        return self.quantity * self.price


# ==================== EXPENSES ====================

class Expense(Base):
    """Expense record"""
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True)
    expense_number = Column(String(50), nullable=False)
    expense_date = Column(Date, nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sub_total = Column(Numeric(15, 2), default=Decimal("0.00"))
    vat_amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    vendor_id = Column(Integer, ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True)
    paid_from_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True)
    expense_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="expenses")
    business = relationship("Business", back_populates="expenses")
    vendor = relationship("Vendor")
    paid_from_account = relationship("Account", foreign_keys=[paid_from_account_id])
    expense_account = relationship("Account", foreign_keys=[expense_account_id])
    
    __table_args__ = (
        UniqueConstraint('expense_number', 'business_id', name='uq_expense_number'),
    )


# ==================== HR MODELS ====================

class Employee(Base):
    """Employee"""
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date, nullable=True)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="employees")
    business = relationship("Business", back_populates="employees")
    payroll_config = relationship("PayrollConfig", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    payslips = relationship("Payslip", back_populates="employee", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_employees_business_id', 'business_id'),
    )


class PayrollConfig(Base):
    """Employee payroll configuration"""
    __tablename__ = 'payroll_configs'
    
    id = Column(Integer, primary_key=True)
    gross_salary = Column(Numeric(15, 2), default=Decimal("0.00"))
    pay_frequency = Column(Enum(PayFrequency), default=PayFrequency.MONTHLY)
    paye_rate = Column(Numeric(5, 2), default=Decimal("0.00"))
    pension_employee_rate = Column(Numeric(5, 2), default=Decimal("0.00"))
    pension_employer_rate = Column(Numeric(5, 2), default=Decimal("0.00"))
    other_deductions = Column(Numeric(15, 2), default=Decimal("0.00"))
    other_allowances = Column(Numeric(15, 2), default=Decimal("0.00"))
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="payroll_config")


class Payslip(Base):
    """Employee payslip"""
    __tablename__ = 'payslips'
    
    id = Column(Integer, primary_key=True)
    payslip_number = Column(String(50), nullable=False)
    pay_period_start = Column(Date, nullable=False)
    pay_period_end = Column(Date, nullable=False)
    gross_salary = Column(Numeric(15, 2), default=Decimal("0.00"))
    paye_deduction = Column(Numeric(15, 2), default=Decimal("0.00"))
    pension_deduction = Column(Numeric(15, 2), default=Decimal("0.00"))
    other_deductions = Column(Numeric(15, 2), default=Decimal("0.00"))
    total_deductions = Column(Numeric(15, 2), default=Decimal("0.00"))
    net_salary = Column(Numeric(15, 2), default=Decimal("0.00"))
    is_paid = Column(Boolean, default=False)
    paid_date = Column(Date, nullable=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="payslips")
    business = relationship("Business")
    
    __table_args__ = (
        UniqueConstraint('payslip_number', 'business_id', name='uq_payslip_number'),
    )


# ==================== BANKING MODELS ====================

class BankAccount(Base):
    """Bank Account"""
    __tablename__ = 'bank_accounts'
    
    id = Column(Integer, primary_key=True)
    account_name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(50), nullable=True)
    currency = Column(String(10), default="USD")
    opening_balance = Column(Numeric(15, 2), default=Decimal("0.00"))
    current_balance = Column(Numeric(15, 2), default=Decimal("0.00"))
    last_reconciliation_date = Column(Date, nullable=True)
    last_reconciliation_balance = Column(Numeric(15, 2), nullable=True)
    chart_of_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chart_of_account = relationship("Account", back_populates="bank_accounts")
    branch = relationship("Branch", back_populates="bank_accounts")
    business = relationship("Business", back_populates="bank_accounts")
    fund_transfers_from = relationship("FundTransfer", foreign_keys="FundTransfer.from_account_id", back_populates="from_account")
    fund_transfers_to = relationship("FundTransfer", foreign_keys="FundTransfer.to_account_id", back_populates="to_account")
    
    __table_args__ = (
        Index('ix_bank_accounts_business_id', 'business_id'),
    )


class FundTransfer(Base):
    """Fund transfer between bank accounts"""
    __tablename__ = 'fund_transfers'
    
    id = Column(Integer, primary_key=True)
    transfer_number = Column(String(50), nullable=False)
    transfer_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)
    from_account_id = Column(Integer, ForeignKey('bank_accounts.id', ondelete='CASCADE'), nullable=False)
    to_account_id = Column(Integer, ForeignKey('bank_accounts.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_account = relationship("BankAccount", foreign_keys=[from_account_id], back_populates="fund_transfers_from")
    to_account = relationship("BankAccount", foreign_keys=[to_account_id], back_populates="fund_transfers_to")
    branch = relationship("Branch")
    business = relationship("Business")
    
    __table_args__ = (
        UniqueConstraint('transfer_number', 'business_id', name='uq_fund_transfer_number'),
        CheckConstraint('from_account_id != to_account_id', name='ck_different_accounts'),
    )


# ==================== BUDGETING ====================

class Budget(Base):
    """Budget"""
    __tablename__ = 'budgets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="budgets")
    items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('name', 'fiscal_year', 'business_id', name='uq_budget_name_year'),
    )


class BudgetItem(Base):
    """Budget line item"""
    __tablename__ = 'budget_items'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Numeric(15, 2), default=Decimal("0.00"))
    month = Column(Integer, nullable=True)  # 1-12 for monthly, null for annual
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    budget_id = Column(Integer, ForeignKey('budgets.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="budget_items")
    budget = relationship("Budget", back_populates="items")


# ==================== FIXED ASSETS ====================

class FixedAsset(Base):
    """Fixed Asset"""
    __tablename__ = 'fixed_assets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    asset_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    purchase_date = Column(Date, nullable=False)
    purchase_cost = Column(Numeric(15, 2), default=Decimal("0.00"))
    salvage_value = Column(Numeric(15, 2), default=Decimal("0.00"))
    useful_life_years = Column(Integer, default=5)
    depreciation_method = Column(String(50), default="straight_line")
    accumulated_depreciation = Column(Numeric(15, 2), default=Decimal("0.00"))
    book_value = Column(Numeric(15, 2), default=Decimal("0.00"))
    is_active = Column(Boolean, default=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account")
    business = relationship("Business", back_populates="fixed_assets")
    
    __table_args__ = (
        Index('ix_fixed_assets_business_id', 'business_id'),
    )


# ==================== EXPORT ALL MODELS ====================

__all__ = [
    # Enums
    'AccountType', 'InvoiceStatus', 'PayFrequency', 'PlanType',
    # Association Tables
    'RolePermission', 'UserBranchRole',
    # Core Models
    'Business', 'User', 'Branch', 'Permission', 'Role',
    # Accounting
    'Account', 'JournalVoucher', 'LedgerEntry',
    # CRM
    'Customer', 'Vendor',
    # Inventory
    'Category', 'Product', 'StockAdjustment',
    # Sales
    'SalesInvoice', 'SalesInvoiceItem', 'Payment', 'CreditNote', 'CreditNoteItem',
    # Purchases
    'PurchaseBill', 'PurchaseBillItem', 'DebitNote', 'DebitNoteItem',
    # Expenses
    'Expense',
    # HR
    'Employee', 'PayrollConfig', 'Payslip',
    # Banking
    'BankAccount', 'FundTransfer',
    # Budgeting
    'Budget', 'BudgetItem',
    # Fixed Assets
    'FixedAsset',
]
