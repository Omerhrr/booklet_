"""
Banking Service - Bank Accounts, Fund Transfers, Reconciliation
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from decimal import Decimal
from datetime import date
from app.models import BankAccount, FundTransfer, LedgerEntry, Account
from app.schemas import BankAccountCreate, FundTransferCreate


class BankAccountService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, account_id: int, business_id: int) -> Optional[BankAccount]:
        return self.db.query(BankAccount).options(
            joinedload(BankAccount.chart_of_account)
        ).filter(
            BankAccount.id == account_id,
            BankAccount.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int) -> List[BankAccount]:
        return self.db.query(BankAccount).options(
            joinedload(BankAccount.chart_of_account)
        ).filter(
            BankAccount.branch_id == branch_id,
            BankAccount.business_id == business_id
        ).order_by(BankAccount.account_name).all()
    
    def get_all_by_business(self, business_id: int) -> List[BankAccount]:
        return self.db.query(BankAccount).options(
            joinedload(BankAccount.chart_of_account)
        ).filter(
            BankAccount.business_id == business_id
        ).order_by(BankAccount.account_name).all()
    
    def create(self, account_data: BankAccountCreate, branch_id: int, business_id: int) -> BankAccount:
        account = BankAccount(
            account_name=account_data.account_name,
            bank_name=account_data.bank_name,
            account_number=account_data.account_number,
            currency=account_data.currency,
            opening_balance=Decimal("0"),
            current_balance=Decimal("0"),
            chart_of_account_id=account_data.chart_of_account_id,
            branch_id=branch_id,
            business_id=business_id
        )
        self.db.add(account)
        self.db.flush()
        return account
    
    def update_balance(self, account_id: int, amount: Decimal, is_debit: bool = True) -> Optional[BankAccount]:
        """Update account balance"""
        account = self.db.query(BankAccount).get(account_id)
        if not account:
            return None
        
        if is_debit:
            account.current_balance += amount
        else:
            account.current_balance -= amount
        
        self.db.flush()
        return account
    
    def deposit(self, account_id: int, business_id: int, amount: Decimal, 
               description: str = None) -> BankAccount:
        """Make a deposit to bank account"""
        account = self.get_by_id(account_id, business_id)
        if not account:
            raise ValueError("Account not found")
        
        account.current_balance += amount
        
        # Create ledger entry
        if account.chart_of_account_id:
            entry = LedgerEntry(
                transaction_date=date.today(),
                description=description or "Bank Deposit",
                debit=amount,
                credit=Decimal("0"),
                account_id=account.chart_of_account_id,
                branch_id=account.branch_id
            )
            self.db.add(entry)
        
        self.db.flush()
        return account
    
    def withdraw(self, account_id: int, business_id: int, amount: Decimal,
                description: str = None) -> BankAccount:
        """Make a withdrawal from bank account"""
        account = self.get_by_id(account_id, business_id)
        if not account:
            raise ValueError("Account not found")
        
        if account.current_balance < amount:
            raise ValueError("Insufficient funds")
        
        account.current_balance -= amount
        
        # Create ledger entry
        if account.chart_of_account_id:
            entry = LedgerEntry(
                transaction_date=date.today(),
                description=description or "Bank Withdrawal",
                debit=Decimal("0"),
                credit=amount,
                account_id=account.chart_of_account_id,
                branch_id=account.branch_id
            )
            self.db.add(entry)
        
        self.db.flush()
        return account
    
    def reconcile(self, account_id: int, business_id: int, statement_balance: Decimal,
                 reconciliation_date: date = None) -> Dict:
        """Perform bank reconciliation"""
        account = self.get_by_id(account_id, business_id)
        if not account:
            raise ValueError("Account not found")
        
        difference = statement_balance - account.current_balance
        
        account.last_reconciliation_date = reconciliation_date or date.today()
        account.last_reconciliation_balance = statement_balance
        
        self.db.flush()
        
        return {
            "account": account,
            "book_balance": account.current_balance,
            "statement_balance": statement_balance,
            "difference": difference,
            "reconciliation_date": account.last_reconciliation_date
        }
    
    def delete(self, account_id: int, business_id: int) -> bool:
        account = self.get_by_id(account_id, business_id)
        if not account:
            return False
        
        # Check for transfers
        has_transfers = self.db.query(FundTransfer).filter(
            (FundTransfer.from_account_id == account_id) | 
            (FundTransfer.to_account_id == account_id)
        ).first()
        
        if has_transfers:
            return False
        
        self.db.delete(account)
        return True


class FundTransferService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, transfer_id: int, business_id: int) -> Optional[FundTransfer]:
        return self.db.query(FundTransfer).options(
            joinedload(FundTransfer.from_account),
            joinedload(FundTransfer.to_account)
        ).filter(
            FundTransfer.id == transfer_id,
            FundTransfer.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int) -> List[FundTransfer]:
        return self.db.query(FundTransfer).options(
            joinedload(FundTransfer.from_account),
            joinedload(FundTransfer.to_account)
        ).filter(
            FundTransfer.branch_id == branch_id,
            FundTransfer.business_id == business_id
        ).order_by(FundTransfer.transfer_date.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        last_transfer = self.db.query(FundTransfer).filter(
            FundTransfer.business_id == business_id
        ).order_by(FundTransfer.id.desc()).first()
        
        if last_transfer:
            try:
                num = int(last_transfer.transfer_number.replace("FT-", ""))
                return f"FT-{num + 1:05d}"
            except ValueError:
                pass
        
        return "FT-00001"
    
    def create(self, transfer_data: FundTransferCreate, branch_id: int, business_id: int) -> FundTransfer:
        """Create a fund transfer between accounts"""
        from_account = self.db.query(BankAccount).get(transfer_data.from_account_id)
        to_account = self.db.query(BankAccount).get(transfer_data.to_account_id)
        
        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")
        
        if from_account.current_balance < transfer_data.amount:
            raise ValueError("Insufficient funds in source account")
        
        # Create transfer record
        transfer = FundTransfer(
            transfer_number=self.get_next_number(business_id),
            transfer_date=transfer_data.transfer_date,
            amount=transfer_data.amount,
            description=transfer_data.description,
            reference=transfer_data.reference,
            from_account_id=transfer_data.from_account_id,
            to_account_id=transfer_data.to_account_id,
            branch_id=branch_id,
            business_id=business_id
        )
        self.db.add(transfer)
        
        # Update balances
        from_account.current_balance -= transfer_data.amount
        to_account.current_balance += transfer_data.amount
        
        # Create ledger entries
        if from_account.chart_of_account_id:
            from_entry = LedgerEntry(
                transaction_date=transfer_data.transfer_date,
                description=f"Transfer to {to_account.account_name}",
                debit=Decimal("0"),
                credit=transfer_data.amount,
                account_id=from_account.chart_of_account_id,
                branch_id=branch_id
            )
            self.db.add(from_entry)
        
        if to_account.chart_of_account_id:
            to_entry = LedgerEntry(
                transaction_date=transfer_data.transfer_date,
                description=f"Transfer from {from_account.account_name}",
                debit=transfer_data.amount,
                credit=Decimal("0"),
                account_id=to_account.chart_of_account_id,
                branch_id=branch_id
            )
            self.db.add(to_entry)
        
        self.db.flush()
        return transfer
    
    def get_transfer_history(self, account_id: int, business_id: int, 
                            start_date: date = None, end_date: date = None) -> List[FundTransfer]:
        """Get transfer history for an account"""
        query = self.db.query(FundTransfer).filter(
            FundTransfer.business_id == business_id,
            (FundTransfer.from_account_id == account_id) | 
            (FundTransfer.to_account_id == account_id)
        )
        
        if start_date:
            query = query.filter(FundTransfer.transfer_date >= start_date)
        if end_date:
            query = query.filter(FundTransfer.transfer_date <= end_date)
        
        return query.order_by(FundTransfer.transfer_date.desc()).all()
