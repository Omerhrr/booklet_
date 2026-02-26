"""
Business Service - Business Logic for Business Operations
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Business, Branch, Role, Account, AccountType, Permission
from app.schemas import BusinessCreate, BusinessUpdate, BranchCreate


class BusinessService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, business_id: int) -> Optional[Business]:
        return self.db.query(Business).filter(Business.id == business_id).first()
    
    def get_by_name(self, name: str) -> Optional[Business]:
        return self.db.query(Business).filter(Business.name == name).first()
    
    def create(self, business_data: dict) -> Business:
        """Create a new business"""
        name = business_data.get("business_name") or business_data.get("name")
        business = Business(name=name)
        self.db.add(business)
        self.db.flush()
        return business
    
    def update(self, business_id: int, business_data: BusinessUpdate) -> Optional[Business]:
        business = self.get_by_id(business_id)
        if not business:
            return None
        
        update_data = business_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(business, key, value)
        
        self.db.flush()
        return business
    
    def create_default_chart_of_accounts(self, business_id: int) -> List[Account]:
        """Create default chart of accounts for a new business"""
        default_accounts = [
            # Assets
            Account(name="Cash", code="1000", type=AccountType.ASSET, is_system_account=True, business_id=business_id),
            Account(name="Bank", code="1100", type=AccountType.ASSET, is_system_account=True, business_id=business_id),
            Account(name="Accounts Receivable", code="1200", type=AccountType.ASSET, is_system_account=True, business_id=business_id),
            Account(name="Inventory", code="1300", type=AccountType.ASSET, is_system_account=True, business_id=business_id),
            Account(name="Fixed Assets", code="1400", type=AccountType.ASSET, is_system_account=True, business_id=business_id),
            # Liabilities
            Account(name="Accounts Payable", code="2000", type=AccountType.LIABILITY, is_system_account=True, business_id=business_id),
            Account(name="VAT Payable", code="2100", type=AccountType.LIABILITY, is_system_account=True, business_id=business_id),
            Account(name="Payroll Liabilities", code="2200", type=AccountType.LIABILITY, is_system_account=True, business_id=business_id),
            # Equity
            Account(name="Owner's Equity", code="3000", type=AccountType.EQUITY, is_system_account=True, business_id=business_id),
            Account(name="Retained Earnings", code="3100", type=AccountType.EQUITY, is_system_account=True, business_id=business_id),
            # Revenue
            Account(name="Sales Revenue", code="4000", type=AccountType.REVENUE, is_system_account=True, business_id=business_id),
            Account(name="Other Income", code="4100", type=AccountType.REVENUE, is_system_account=True, business_id=business_id),
            Account(name="Sales Returns", code="4200", type=AccountType.REVENUE, is_system_account=True, business_id=business_id),
            # Expenses
            Account(name="Cost of Goods Sold", code="5000", type=AccountType.EXPENSE, is_system_account=True, business_id=business_id),
            Account(name="Operating Expenses", code="5100", type=AccountType.EXPENSE, is_system_account=True, business_id=business_id),
            Account(name="Salaries Expense", code="5200", type=AccountType.EXPENSE, is_system_account=True, business_id=business_id),
            Account(name="Utilities Expense", code="5300", type=AccountType.EXPENSE, is_system_account=True, business_id=business_id),
            Account(name="Depreciation Expense", code="5400", type=AccountType.EXPENSE, is_system_account=True, business_id=business_id),
        ]
        
        for account in default_accounts:
            self.db.add(account)
        
        self.db.flush()
        return default_accounts


class BranchService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, branch_id: int) -> Optional[Branch]:
        return self.db.query(Branch).filter(Branch.id == branch_id).first()
    
    def get_branches_by_business(self, business_id: int) -> List[Branch]:
        return self.db.query(Branch).filter(
            Branch.business_id == business_id,
            Branch.is_active == True
        ).all()
    
    def create(self, branch_data: dict, business_id: int, is_default: bool = False) -> Branch:
        name = branch_data.get("name")
        currency = branch_data.get("currency", "USD")
        
        # If this branch is set as default, remove default from other branches
        if is_default:
            self.db.query(Branch).filter(
                Branch.business_id == business_id
            ).update({"is_default": False})
        
        branch = Branch(
            name=name,
            currency=currency,
            business_id=business_id,
            is_default=is_default,
            is_active=True  # Explicitly set to True
        )
        self.db.add(branch)
        self.db.flush()
        return branch
    
    def set_default(self, branch_id: int, business_id: int) -> Optional[Branch]:
        # Remove default from other branches
        self.db.query(Branch).filter(
            Branch.business_id == business_id
        ).update({"is_default": False})
        
        # Set new default
        branch = self.get_by_id(branch_id)
        if branch:
            branch.is_default = True
            self.db.flush()
        return branch
