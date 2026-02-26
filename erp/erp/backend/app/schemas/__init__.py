"""
Pydantic Schemas for API Validation
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ==================== ENUMS ====================

class AccountTypeEnum(str, Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class PayFrequencyEnum(str, Enum):
    MONTHLY = "Monthly"
    WEEKLY = "Weekly"
    BI_WEEKLY = "Bi-Weekly"


# ==================== AUTH SCHEMAS ====================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    business_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class SignupRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


# ==================== USER SCHEMAS ====================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    is_active: bool
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserWithRoles(UserResponse):
    accessible_branches: List["BranchResponse"] = []
    selected_branch: Optional["BranchResponse"] = None


# ==================== BUSINESS SCHEMAS ====================

class BusinessBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    is_vat_registered: Optional[bool] = None
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)


class BusinessResponse(BusinessBase):
    id: int
    plan: str
    is_vat_registered: bool
    vat_rate: Decimal
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== BRANCH SCHEMAS ====================

class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    currency: str = Field(default="USD", max_length=10)


class BranchCreate(BranchBase):
    is_default: bool = False


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    currency: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: int
    is_default: bool
    is_active: bool
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== ROLE & PERMISSION SCHEMAS ====================

class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(RoleBase):
    id: int
    is_system: bool
    business_id: int
    permission_ids: List[int] = []
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AssignRoleRequest(BaseModel):
    user_id: int
    branch_id: int
    role_id: int


# ==================== ACCOUNT SCHEMAS ====================

class AccountBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=20)
    type: AccountTypeEnum
    description: Optional[str] = None


class AccountCreate(AccountBase):
    parent_id: Optional[int] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    id: int
    is_system_account: bool
    is_active: bool
    parent_id: Optional[int]
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AccountWithBalance(AccountResponse):
    balance: Decimal = Decimal("0.00")


# ==================== CUSTOMER SCHEMAS ====================

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    credit_limit: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)


class CustomerCreate(CustomerBase):
    branch_id: Optional[int] = None  # Optional - backend uses user's selected branch


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CustomerWithBalance(CustomerResponse):
    total_outstanding: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")


# ==================== VENDOR SCHEMAS ====================

class VendorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)


class VendorCreate(VendorBase):
    branch_id: Optional[int] = None  # Optional - backend uses user's selected branch


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: int
    is_active: bool
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VendorWithBalance(VendorResponse):
    total_outstanding: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")


# ==================== CATEGORY SCHEMAS ====================

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== PRODUCT SCHEMAS ====================

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=20)
    purchase_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    sales_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    reorder_level: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)


class ProductCreate(ProductBase):
    category_id: int
    opening_stock: Decimal = Field(default=Decimal("0.00"), ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=20)
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    sales_price: Optional[Decimal] = Field(None, ge=0)
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    opening_stock: Decimal
    stock_quantity: Decimal
    is_active: bool
    category_id: Optional[int]
    branch_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StockAdjustmentCreate(BaseModel):
    quantity_change: Decimal = Field(..., description="Positive for increase, negative for decrease")
    reason: str = Field(..., min_length=2, max_length=500)


class StockAdjustmentResponse(BaseModel):
    id: int
    product_id: int
    quantity_change: Decimal
    reason: str
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== SALES INVOICE SCHEMAS ====================

class SalesInvoiceItemBase(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., ge=0)


class SalesInvoiceItemCreate(SalesInvoiceItemBase):
    pass


class SalesInvoiceItemResponse(SalesInvoiceItemBase):
    id: int
    sales_invoice_id: int
    returned_quantity: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class SalesInvoiceBase(BaseModel):
    customer_id: int
    invoice_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None


class SalesInvoiceCreate(SalesInvoiceBase):
    items: List[SalesInvoiceItemCreate] = Field(..., min_length=1)


class SalesInvoiceUpdate(BaseModel):
    customer_id: Optional[int] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class SalesInvoiceResponse(SalesInvoiceBase):
    id: int
    invoice_number: str
    sub_total: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    status: str
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SalesInvoiceWithItems(SalesInvoiceResponse):
    items: List[SalesInvoiceItemResponse] = []


class RecordPaymentRequest(BaseModel):
    invoice_id: int
    payment_date: date
    amount: Decimal = Field(..., gt=0)
    payment_account_id: int
    reference: Optional[str] = None


# ==================== PURCHASE BILL SCHEMAS ====================

class PurchaseBillItemBase(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., ge=0)


class PurchaseBillItemCreate(PurchaseBillItemBase):
    pass


class PurchaseBillItemResponse(PurchaseBillItemBase):
    id: int
    purchase_bill_id: int
    returned_quantity: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class PurchaseBillBase(BaseModel):
    vendor_id: int
    bill_date: date
    due_date: Optional[date] = None
    bill_number: Optional[str] = None
    notes: Optional[str] = None


class PurchaseBillCreate(PurchaseBillBase):
    items: List[PurchaseBillItemCreate] = Field(..., min_length=1)


class PurchaseBillResponse(PurchaseBillBase):
    id: int
    bill_number: str
    sub_total: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    status: str
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PurchaseBillWithItems(PurchaseBillResponse):
    items: List[PurchaseBillItemResponse] = []


# ==================== EXPENSE SCHEMAS ====================

class ExpenseBase(BaseModel):
    expense_date: date
    category: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    sub_total: Decimal = Field(..., ge=0)
    vat_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    paid_from_account_id: int
    expense_account_id: int
    vendor_id: Optional[int] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseResponse(ExpenseBase):
    id: int
    expense_number: str
    amount: Decimal
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== EMPLOYEE SCHEMAS ====================

class PayrollConfigBase(BaseModel):
    gross_salary: Decimal = Field(..., ge=0)
    pay_frequency: PayFrequencyEnum
    paye_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    pension_employee_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    pension_employer_rate: Optional[Decimal] = Field(None, ge=0, le=100)


class PayrollConfigCreate(PayrollConfigBase):
    pass


class PayrollConfigResponse(PayrollConfigBase):
    id: int
    employee_id: int
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    hire_date: date
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)


class EmployeeCreate(EmployeeBase):
    branch_id: Optional[int] = None  # Optional - backend uses user's selected branch
    payroll_config: Optional[PayrollConfigCreate] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    id: int
    is_active: bool
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeWithPayroll(EmployeeResponse):
    payroll_config: Optional[PayrollConfigResponse] = None


# ==================== PAYSLIP SCHEMAS ====================

class PayslipBase(BaseModel):
    employee_id: int
    pay_period_start: date
    pay_period_end: date
    basic_salary: Decimal
    gross_salary: Decimal
    total_deductions: Decimal
    net_salary: Decimal


class PayslipCreate(BaseModel):
    employee_id: int
    pay_period_start: date
    pay_period_end: date
    additional_deductions: Decimal = Decimal("0.00")
    additional_allowances: Decimal = Decimal("0.00")


class Payslip(PayslipBase):
    id: int
    payslip_number: str
    paye: Decimal
    pension_employee: Decimal
    pension_employer: Decimal
    other_deductions: Decimal
    allowances: Decimal
    status: str
    paid_date: Optional[date]
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== BANK ACCOUNT SCHEMAS ====================

class BankAccountBase(BaseModel):
    account_name: str = Field(..., min_length=2, max_length=255)
    bank_name: Optional[str] = Field(None, max_length=255)
    account_number: Optional[str] = Field(None, max_length=50)
    currency: str = Field(default="USD", max_length=10)


class BankAccountCreate(BankAccountBase):
    chart_of_account_id: int


class BankAccountResponse(BankAccountBase):
    id: int
    chart_of_account_id: int
    branch_id: int
    business_id: int
    last_reconciliation_date: Optional[date]
    last_reconciliation_balance: Optional[Decimal]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FundTransferCreate(BaseModel):
    transfer_date: date
    amount: Decimal = Field(..., gt=0)
    from_account_id: int
    to_account_id: int
    description: Optional[str] = None
    reference: Optional[str] = None


class FundTransferResponse(BaseModel):
    id: int
    transfer_date: date
    amount: Decimal
    from_account_id: int
    to_account_id: int
    description: Optional[str]
    reference: Optional[str]
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== BUDGET SCHEMAS ====================

class BudgetItemBase(BaseModel):
    account_id: int
    amount: Decimal = Field(..., ge=0)
    month: Optional[int] = Field(None, ge=1, le=12)


class BudgetItemCreate(BudgetItemBase):
    pass


class BudgetItem(BudgetItemBase):
    id: int
    budget_id: int
    
    model_config = ConfigDict(from_attributes=True)


class BudgetBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    fiscal_year: int = Field(..., ge=2000, le=2100)
    description: Optional[str] = None


class BudgetCreate(BudgetBase):
    items: List[BudgetItemCreate] = []


class BudgetResponse(BudgetBase):
    id: int
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== FIXED ASSET SCHEMAS ====================

class FixedAssetBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    asset_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    purchase_date: date
    purchase_cost: Decimal = Field(..., ge=0)
    salvage_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    useful_life_years: int = Field(default=5, ge=1)
    depreciation_method: str = Field(default="straight_line")


class FixedAssetCreate(FixedAssetBase):
    account_id: Optional[int] = None


class FixedAssetResponse(FixedAssetBase):
    id: int
    accumulated_depreciation: Decimal
    book_value: Decimal
    is_active: bool
    account_id: Optional[int]
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== JOURNAL VOUCHER SCHEMAS ====================

class JournalLineCreate(BaseModel):
    account_id: int
    debit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0)
    description: Optional[str] = None


class JournalVoucherCreate(BaseModel):
    transaction_date: date
    description: Optional[str] = None
    reference: Optional[str] = None
    lines: List[JournalLineCreate] = Field(..., min_length=2)


class JournalVoucherResponse(BaseModel):
    id: int
    voucher_number: str
    transaction_date: date
    description: Optional[str]
    reference: Optional[str]
    branch_id: int
    business_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== DASHBOARD SCHEMAS ====================

class DashboardStats(BaseModel):
    total_sales: Decimal
    total_purchases: Decimal
    total_expenses: Decimal
    total_receivables: Decimal
    total_payables: Decimal
    cash_balance: Decimal
    total_customers: int
    total_vendors: int
    total_products: int
    low_stock_products: int


class ChartData(BaseModel):
    labels: List[str]
    values: List[Decimal]


class DashboardResponse(BaseModel):
    stats: DashboardStats
    sales_chart: ChartData
    expense_chart: ChartData
    receivables_aging: dict
    payables_aging: dict


# ==================== PAGINATION ====================

class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
