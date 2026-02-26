"""
Accounting Service - Chart of Accounts, Journal Vouchers, Ledger
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from decimal import Decimal
from datetime import date
from app.models import (
    Account, AccountType, JournalVoucher, LedgerEntry, 
    Budget, BudgetItem, FixedAsset, Business
)
from app.schemas import (
    AccountCreate, AccountUpdate, JournalVoucherCreate,
    BudgetCreate
)


class AccountService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, account_id: int, business_id: int) -> Optional[Account]:
        return self.db.query(Account).filter(
            Account.id == account_id,
            Account.business_id == business_id
        ).first()
    
    def get_by_code(self, code: str, business_id: int) -> Optional[Account]:
        return self.db.query(Account).filter(
            Account.code == code,
            Account.business_id == business_id
        ).first()
    
    def get_by_business(self, business_id: int, include_inactive: bool = False) -> List[Account]:
        query = self.db.query(Account).filter(Account.business_id == business_id)
        if not include_inactive:
            query = query.filter(Account.is_active == True)
        return query.order_by(Account.code).all()
    
    def get_by_type(self, business_id: int, account_type: AccountType) -> List[Account]:
        return self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.type == account_type,
            Account.is_active == True
        ).order_by(Account.code).all()
    
    def create(self, account_data: AccountCreate, business_id: int) -> Account:
        account = Account(
            name=account_data.name,
            code=account_data.code,
            type=account_data.type,
            description=account_data.description,
            parent_id=account_data.parent_id,
            business_id=business_id
        )
        self.db.add(account)
        self.db.flush()
        return account
    
    def update(self, account_id: int, business_id: int, account_data: AccountUpdate) -> Optional[Account]:
        account = self.get_by_id(account_id, business_id)
        if not account:
            return None
        
        update_data = account_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(account, key, value)
        
        self.db.flush()
        return account
    
    def get_balance(self, account_id: int) -> Decimal:
        """Calculate account balance from ledger entries"""
        result = self.db.query(
            func.sum(LedgerEntry.debit - LedgerEntry.credit)
        ).filter(LedgerEntry.account_id == account_id).scalar()
        
        return result or Decimal("0")
    
    def get_with_balance(self, account_id: int, business_id: int) -> Optional[Dict]:
        account = self.get_by_id(account_id, business_id)
        if not account:
            return None
        
        balance = self.get_balance(account_id)
        
        # For liability, equity, revenue accounts, credit balance is positive
        if account.type in [AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE]:
            balance = -balance
        
        return {
            "account": account,
            "balance": balance
        }
    
    def delete(self, account_id: int, business_id: int) -> bool:
        account = self.get_by_id(account_id, business_id)
        if not account or account.is_system_account:
            return False
        
        # Check for ledger entries
        has_entries = self.db.query(LedgerEntry).filter(
            LedgerEntry.account_id == account_id
        ).first()
        
        if has_entries:
            account.is_active = False
        else:
            self.db.delete(account)
        
        return True


class JournalVoucherService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, voucher_id: int, business_id: int) -> Optional[JournalVoucher]:
        return self.db.query(JournalVoucher).options(
            joinedload(JournalVoucher.ledger_entries).joinedload(LedgerEntry.account)
        ).filter(
            JournalVoucher.id == voucher_id,
            JournalVoucher.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int) -> List[JournalVoucher]:
        return self.db.query(JournalVoucher).filter(
            JournalVoucher.branch_id == branch_id,
            JournalVoucher.business_id == business_id
        ).order_by(JournalVoucher.created_at.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        last_voucher = self.db.query(JournalVoucher).filter(
            JournalVoucher.business_id == business_id
        ).order_by(JournalVoucher.id.desc()).first()
        
        if last_voucher:
            try:
                num = int(last_voucher.voucher_number.replace("JV-", ""))
                return f"JV-{num + 1:05d}"
            except ValueError:
                pass
        
        return "JV-00001"
    
    def create(self, voucher_data: JournalVoucherCreate, business_id: int, branch_id: int, user_id: int) -> JournalVoucher:
        # Validate that debits equal credits
        total_debit = sum(line.debit for line in voucher_data.lines)
        total_credit = sum(line.credit for line in voucher_data.lines)
        
        if total_debit != total_credit:
            raise ValueError("Debits must equal credits")
        
        voucher = JournalVoucher(
            voucher_number=self.get_next_number(business_id),
            transaction_date=voucher_data.transaction_date,
            description=voucher_data.description,
            reference=voucher_data.reference,
            branch_id=branch_id,
            business_id=business_id,
            created_by=user_id
        )
        self.db.add(voucher)
        self.db.flush()
        
        # Create ledger entries
        for line in voucher_data.lines:
            entry = LedgerEntry(
                transaction_date=voucher_data.transaction_date,
                description=line.description,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                journal_voucher_id=voucher.id,
                branch_id=branch_id
            )
            self.db.add(entry)
        
        self.db.flush()
        return voucher
    
    def post(self, voucher_id: int, business_id: int) -> Optional[JournalVoucher]:
        """Post a journal voucher (make it permanent)"""
        voucher = self.get_by_id(voucher_id, business_id)
        if not voucher or voucher.is_posted:
            return None
        
        voucher.is_posted = True
        self.db.flush()
        return voucher


class BudgetService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, budget_id: int, business_id: int) -> Optional[Budget]:
        return self.db.query(Budget).options(
            joinedload(Budget.items).joinedload(BudgetItem.account)
        ).filter(
            Budget.id == budget_id,
            Budget.business_id == business_id
        ).first()
    
    def get_by_business(self, business_id: int) -> List[Budget]:
        return self.db.query(Budget).filter(
            Budget.business_id == business_id
        ).order_by(Budget.fiscal_year.desc()).all()
    
    def create(self, budget_data: BudgetCreate, business_id: int) -> Budget:
        budget = Budget(
            name=budget_data.name,
            fiscal_year=budget_data.fiscal_year,
            description=budget_data.description,
            business_id=business_id
        )
        self.db.add(budget)
        self.db.flush()
        return budget
    
    def add_item(self, budget_id: int, account_id: int, amount: Decimal, month: int = None) -> BudgetItem:
        item = BudgetItem(
            budget_id=budget_id,
            account_id=account_id,
            amount=amount,
            month=month
        )
        self.db.add(item)
        self.db.flush()
        return item
    
    def get_budget_vs_actual(self, budget_id: int, business_id: int) -> Dict:
        """Compare budget vs actual figures"""
        budget = self.get_by_id(budget_id, business_id)
        if not budget:
            return None
        
        result = []
        for item in budget.items:
            # Calculate actual from ledger
            actual = self.db.query(
                func.sum(LedgerEntry.debit - LedgerEntry.credit)
            ).filter(
                LedgerEntry.account_id == item.account_id,
                func.extract('year', LedgerEntry.transaction_date) == budget.fiscal_year
            ).scalar() or Decimal("0")
            
            result.append({
                "account": item.account,
                "budgeted": item.amount,
                "actual": actual,
                "variance": item.amount - actual
            })
        
        return {
            "budget": budget,
            "items": result
        }


class FixedAssetService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, asset_id: int, business_id: int) -> Optional[FixedAsset]:
        return self.db.query(FixedAsset).filter(
            FixedAsset.id == asset_id,
            FixedAsset.business_id == business_id
        ).first()
    
    def get_by_business(self, business_id: int, include_inactive: bool = False) -> List[FixedAsset]:
        query = self.db.query(FixedAsset).filter(
            FixedAsset.business_id == business_id
        )
        if not include_inactive:
            query = query.filter(FixedAsset.is_active == True)
        return query.order_by(FixedAsset.created_at.desc()).all()
    
    def create(self, asset_data: dict, business_id: int) -> FixedAsset:
        asset = FixedAsset(
            name=asset_data["name"],
            asset_code=asset_data.get("asset_code"),
            description=asset_data.get("description"),
            purchase_date=asset_data["purchase_date"],
            purchase_cost=asset_data["purchase_cost"],
            salvage_value=asset_data.get("salvage_value", Decimal("0")),
            useful_life_years=asset_data.get("useful_life_years", 5),
            depreciation_method=asset_data.get("depreciation_method", "straight_line"),
            accumulated_depreciation=Decimal("0"),
            book_value=asset_data["purchase_cost"],
            account_id=asset_data.get("account_id"),
            business_id=business_id
        )
        self.db.add(asset)
        self.db.flush()
        return asset
    
    def calculate_depreciation(self, asset_id: int, business_id: int) -> Decimal:
        """Calculate annual depreciation"""
        asset = self.get_by_id(asset_id, business_id)
        if not asset:
            return Decimal("0")
        
        if asset.depreciation_method == "straight_line":
            depreciable_amount = asset.purchase_cost - asset.salvage_value
            annual_depreciation = depreciable_amount / asset.useful_life_years
            return annual_depreciation
        
        return Decimal("0")
    
    def record_depreciation(self, asset_id: int, business_id: int, amount: Decimal) -> FixedAsset:
        """Record depreciation for an asset"""
        asset = self.get_by_id(asset_id, business_id)
        if not asset:
            return None
        
        asset.accumulated_depreciation += amount
        asset.book_value = asset.purchase_cost - asset.accumulated_depreciation
        
        self.db.flush()
        return asset


class ReportService:
    """Financial reports service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_trial_balance(self, business_id: int, as_of_date: date = None) -> List[Dict]:
        """Generate trial balance report"""
        accounts = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.is_active == True
        ).all()
        
        result = []
        for account in accounts:
            query = self.db.query(
                func.sum(LedgerEntry.debit).label("total_debit"),
                func.sum(LedgerEntry.credit).label("total_credit")
            ).filter(LedgerEntry.account_id == account.id)
            
            if as_of_date:
                query = query.filter(LedgerEntry.transaction_date <= as_of_date)
            
            totals = query.first()
            
            debit = totals.total_debit or Decimal("0")
            credit = totals.total_credit or Decimal("0")
            balance = debit - credit
            
            if balance != 0:
                result.append({
                    "account": account,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance
                })
        
        return result
    
    def get_balance_sheet(self, business_id: int, as_of_date: date = None) -> Dict:
        """Generate balance sheet"""
        assets = []
        liabilities = []
        equity = []
        
        accounts = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.is_active == True
        ).all()
        
        for account in accounts:
            query = self.db.query(
                func.sum(LedgerEntry.debit - LedgerEntry.credit).label("balance")
            ).filter(LedgerEntry.account_id == account.id)
            
            if as_of_date:
                query = query.filter(LedgerEntry.transaction_date <= as_of_date)
            
            balance = query.scalar() or Decimal("0")
            
            if balance == 0:
                continue
            
            item = {"account": account, "balance": abs(balance)}
            
            if account.type == AccountType.ASSET:
                assets.append(item)
            elif account.type == AccountType.LIABILITY:
                item["balance"] = abs(balance)  # Liability has credit balance
                liabilities.append(item)
            elif account.type == AccountType.EQUITY:
                item["balance"] = abs(balance)  # Equity has credit balance
                equity.append(item)
        
        total_assets = sum(item["balance"] for item in assets)
        total_liabilities = sum(item["balance"] for item in liabilities)
        total_equity = sum(item["balance"] for item in equity)
        
        return {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "as_of_date": as_of_date or date.today()
        }
    
    def get_income_statement(self, business_id: int, start_date: date, end_date: date) -> Dict:
        """Generate income statement (Profit & Loss)"""
        revenue = []
        expenses = []
        
        accounts = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.is_active == True,
            Account.type.in_([AccountType.REVENUE, AccountType.EXPENSE])
        ).all()
        
        for account in accounts:
            query = self.db.query(
                func.sum(LedgerEntry.credit - LedgerEntry.debit).label("balance")
            ).filter(
                LedgerEntry.account_id == account.id,
                LedgerEntry.transaction_date >= start_date,
                LedgerEntry.transaction_date <= end_date
            )
            
            balance = query.scalar() or Decimal("0")
            
            if balance == 0:
                continue
            
            item = {"account": account, "balance": abs(balance)}
            
            if account.type == AccountType.REVENUE:
                revenue.append(item)
            elif account.type == AccountType.EXPENSE:
                expenses.append(item)
        
        total_revenue = sum(item["balance"] for item in revenue)
        total_expenses = sum(item["balance"] for item in expenses)
        net_income = total_revenue - total_expenses
        
        return {
            "revenue": revenue,
            "expenses": expenses,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_income": net_income,
            "start_date": start_date,
            "end_date": end_date
        }
    
    def get_general_ledger(self, business_id: int, account_id: int = None, 
                          start_date: date = None, end_date: date = None) -> List[Dict]:
        """Generate general ledger report"""
        query = self.db.query(LedgerEntry).options(
            joinedload(LedgerEntry.account)
        ).join(Account).filter(
            Account.business_id == business_id
        )
        
        if account_id:
            query = query.filter(LedgerEntry.account_id == account_id)
        if start_date:
            query = query.filter(LedgerEntry.transaction_date >= start_date)
        if end_date:
            query = query.filter(LedgerEntry.transaction_date <= end_date)
        
        entries = query.order_by(LedgerEntry.transaction_date, LedgerEntry.id).all()
        
        result = []
        running_balance = Decimal("0")
        
        for entry in entries:
            running_balance += entry.debit - entry.credit
            result.append({
                "entry": entry,
                "balance": running_balance
            })
        
        return result
