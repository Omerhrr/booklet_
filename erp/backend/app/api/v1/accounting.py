"""
Accounting API Routes - Chart of Accounts, Journal Vouchers, Reports
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    AccountCreate, AccountUpdate, AccountResponse,
    JournalVoucherCreate, JournalVoucherResponse,
    BudgetCreate, BudgetItem
)
from app.services.accounting_service import (
    AccountService, JournalVoucherService, BudgetService,
    FixedAssetService, ReportService
)

router = APIRouter(prefix="/accounting", tags=["Accounting"])


# ==================== CHART OF ACCOUNTS ====================

@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all accounts"""
    account_service = AccountService(db)
    return account_service.get_by_business(current_user.business_id, include_inactive)


@router.post("/accounts", response_model=AccountResponse, dependencies=[Depends(PermissionChecker(["accounting:create"]))])
async def create_account(
    account_data: AccountCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new account"""
    account_service = AccountService(db)
    account = account_service.create(account_data, current_user.business_id)
    db.commit()
    return account


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get account by ID"""
    account_service = AccountService(db)
    account = account_service.get_by_id(account_id, current_user.business_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/accounts/{account_id}", response_model=AccountResponse, dependencies=[Depends(PermissionChecker(["accounting:edit"]))])
async def update_account(
    account_id: int,
    account_data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update account"""
    account_service = AccountService(db)
    account = account_service.update(account_id, current_user.business_id, account_data)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.commit()
    return account


@router.delete("/accounts/{account_id}", dependencies=[Depends(PermissionChecker(["accounting:delete"]))])
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete account"""
    account_service = AccountService(db)
    if not account_service.delete(account_id, current_user.business_id):
        raise HTTPException(status_code=400, detail="Cannot delete system account or account with entries")
    db.commit()
    return {"message": "Account deleted"}


@router.get("/accounts/{account_id}/balance")
async def get_account_balance(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get account balance"""
    account_service = AccountService(db)
    result = account_service.get_with_balance(account_id, current_user.business_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


# ==================== JOURNAL VOUCHERS ====================

@router.get("/journal-vouchers", response_model=List[JournalVoucherResponse])
async def list_journal_vouchers(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all journal vouchers"""
    jv_service = JournalVoucherService(db)
    return jv_service.get_by_branch(current_user.selected_branch.id, current_user.business_id)


@router.post("/journal-vouchers", response_model=JournalVoucherResponse, dependencies=[Depends(PermissionChecker(["accounting:create"]))])
async def create_journal_voucher(
    voucher_data: JournalVoucherCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new journal voucher"""
    jv_service = JournalVoucherService(db)
    try:
        voucher = jv_service.create(
            voucher_data,
            current_user.business_id,
            current_user.selected_branch.id,
            current_user.id
        )
        db.commit()
        return voucher
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/journal-vouchers/{voucher_id}", response_model=JournalVoucherResponse)
async def get_journal_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get journal voucher by ID"""
    jv_service = JournalVoucherService(db)
    voucher = jv_service.get_by_id(voucher_id, current_user.business_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Journal voucher not found")
    return voucher


@router.post("/journal-vouchers/{voucher_id}/post", dependencies=[Depends(PermissionChecker(["accounting:edit"]))])
async def post_journal_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Post journal voucher"""
    jv_service = JournalVoucherService(db)
    voucher = jv_service.post(voucher_id, current_user.business_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Journal voucher not found")
    db.commit()
    return {"message": "Journal voucher posted"}


# ==================== BUDGETS ====================

@router.get("/budgets")
async def list_budgets(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all budgets"""
    budget_service = BudgetService(db)
    return budget_service.get_by_business(current_user.business_id)


@router.post("/budgets", dependencies=[Depends(PermissionChecker(["budgeting:create"]))])
async def create_budget(
    budget_data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new budget"""
    budget_service = BudgetService(db)
    budget = budget_service.create(budget_data, current_user.business_id)
    db.commit()
    return budget


@router.get("/budgets/{budget_id}")
async def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get budget by ID"""
    budget_service = BudgetService(db)
    budget = budget_service.get_by_id(budget_id, current_user.business_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.get("/budgets/{budget_id}/vs-actual")
async def get_budget_vs_actual(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get budget vs actual comparison"""
    budget_service = BudgetService(db)
    result = budget_service.get_budget_vs_actual(budget_id, current_user.business_id)
    if not result:
        raise HTTPException(status_code=404, detail="Budget not found")
    return result


# ==================== FIXED ASSETS ====================

@router.get("/fixed-assets")
async def list_fixed_assets(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all fixed assets"""
    asset_service = FixedAssetService(db)
    return asset_service.get_by_business(current_user.business_id, include_inactive)


@router.post("/fixed-assets", dependencies=[Depends(PermissionChecker(["accounting:create"]))])
async def create_fixed_asset(
    asset_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new fixed asset"""
    asset_service = FixedAssetService(db)
    asset = asset_service.create(asset_data, current_user.business_id)
    db.commit()
    return asset


@router.get("/fixed-assets/{asset_id}")
async def get_fixed_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get fixed asset by ID"""
    asset_service = FixedAssetService(db)
    asset = asset_service.get_by_id(asset_id, current_user.business_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    return asset


@router.post("/fixed-assets/{asset_id}/depreciate", dependencies=[Depends(PermissionChecker(["accounting:edit"]))])
async def record_depreciation(
    asset_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Record depreciation for asset"""
    from decimal import Decimal
    asset_service = FixedAssetService(db)
    asset = asset_service.record_depreciation(asset_id, current_user.business_id, Decimal(str(amount)))
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    db.commit()
    return {"message": "Depreciation recorded", "book_value": asset.book_value}


# ==================== REPORTS ====================

@router.get("/reports/trial-balance")
async def get_trial_balance(
    as_of_date: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get trial balance report"""
    report_service = ReportService(db)
    return report_service.get_trial_balance(current_user.business_id, as_of_date)


@router.get("/reports/balance-sheet")
async def get_balance_sheet(
    as_of_date: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get balance sheet report"""
    report_service = ReportService(db)
    return report_service.get_balance_sheet(current_user.business_id, as_of_date)


@router.get("/reports/income-statement")
async def get_income_statement(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get income statement (P&L) report"""
    report_service = ReportService(db)
    return report_service.get_income_statement(current_user.business_id, start_date, end_date)


@router.get("/reports/general-ledger")
async def get_general_ledger(
    account_id: int = None,
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get general ledger report"""
    report_service = ReportService(db)
    return report_service.get_general_ledger(
        current_user.business_id, account_id, start_date, end_date
    )
