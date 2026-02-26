"""
Banking API Routes - Bank Accounts, Fund Transfers, Reconciliation
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    BankAccountCreate, BankAccountResponse,
    FundTransferCreate, FundTransferResponse
)
from app.services.banking_service import BankAccountService, FundTransferService

router = APIRouter(prefix="/banking", tags=["Banking"])


# ==================== BANK ACCOUNTS ====================

@router.get("/accounts", response_model=List[BankAccountResponse])
async def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all bank accounts"""
    account_service = BankAccountService(db)
    return account_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id
    )


@router.post("/accounts", response_model=BankAccountResponse, dependencies=[Depends(PermissionChecker(["bank:create"]))])
async def create_bank_account(
    account_data: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new bank account"""
    account_service = BankAccountService(db)
    account = account_service.create(
        account_data,
        current_user.selected_branch.id,
        current_user.business_id
    )
    db.commit()
    return account


@router.get("/accounts/{account_id}", response_model=BankAccountResponse)
async def get_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get bank account by ID"""
    account_service = BankAccountService(db)
    account = account_service.get_by_id(account_id, current_user.business_id)
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return account


@router.post("/accounts/{account_id}/deposit", dependencies=[Depends(PermissionChecker(["bank:create"]))])
async def deposit_to_account(
    account_id: int,
    amount: float,
    description: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Deposit to bank account"""
    account_service = BankAccountService(db)
    try:
        account = account_service.deposit(
            account_id,
            current_user.business_id,
            Decimal(str(amount)),
            description
        )
        db.commit()
        return {"message": "Deposit successful", "balance": account.current_balance}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/{account_id}/withdraw", dependencies=[Depends(PermissionChecker(["bank:create"]))])
async def withdraw_from_account(
    account_id: int,
    amount: float,
    description: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Withdraw from bank account"""
    account_service = BankAccountService(db)
    try:
        account = account_service.withdraw(
            account_id,
            current_user.business_id,
            Decimal(str(amount)),
            description
        )
        db.commit()
        return {"message": "Withdrawal successful", "balance": account.current_balance}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/{account_id}/reconcile", dependencies=[Depends(PermissionChecker(["bank:reconcile"]))])
async def reconcile_account(
    account_id: int,
    statement_balance: float,
    reconciliation_date: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Reconcile bank account"""
    account_service = BankAccountService(db)
    try:
        result = account_service.reconcile(
            account_id,
            current_user.business_id,
            Decimal(str(statement_balance)),
            reconciliation_date
        )
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/accounts/{account_id}", dependencies=[Depends(PermissionChecker(["bank:create"]))])
async def delete_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete bank account"""
    account_service = BankAccountService(db)
    if not account_service.delete(account_id, current_user.business_id):
        raise HTTPException(status_code=400, detail="Cannot delete account with transfers")
    db.commit()
    return {"message": "Bank account deleted"}


# ==================== FUND TRANSFERS ====================

@router.get("/transfers", response_model=List[FundTransferResponse])
async def list_transfers(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all fund transfers"""
    transfer_service = FundTransferService(db)
    return transfer_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id
    )


@router.post("/transfers", response_model=FundTransferResponse, dependencies=[Depends(PermissionChecker(["bank:create"]))])
async def create_transfer(
    transfer_data: FundTransferCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a fund transfer"""
    transfer_service = FundTransferService(db)
    try:
        transfer = transfer_service.create(
            transfer_data,
            current_user.selected_branch.id,
            current_user.business_id
        )
        db.commit()
        return transfer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transfers/{transfer_id}", response_model=FundTransferResponse)
async def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get fund transfer by ID"""
    transfer_service = FundTransferService(db)
    transfer = transfer_service.get_by_id(transfer_id, current_user.business_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


@router.get("/accounts/{account_id}/transfer-history")
async def get_transfer_history(
    account_id: int,
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get transfer history for an account"""
    transfer_service = FundTransferService(db)
    return transfer_service.get_transfer_history(
        account_id,
        current_user.business_id,
        start_date,
        end_date
    )
