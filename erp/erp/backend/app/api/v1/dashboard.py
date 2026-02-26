"""
Dashboard API Routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_branch_id(current_user):
    """Get the current user's branch ID safely"""
    branch = getattr(current_user, '_selected_branch', None)
    if branch:
        return branch.id
    # Fallback to first accessible branch
    branches = getattr(current_user, '_accessible_branches', [])
    if branches:
        return branches[0].id
    return None


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get main dashboard statistics"""
    dashboard_service = DashboardService(db)
    branch_id = get_branch_id(current_user)
    return dashboard_service.get_stats(
        current_user.business_id,
        branch_id
    )


@router.get("/full")
async def get_full_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get complete dashboard data"""
    dashboard_service = DashboardService(db)
    branch_id = get_branch_id(current_user)
    return dashboard_service.get_full_dashboard(
        current_user.business_id,
        branch_id
    )


@router.get("/sales-chart")
async def get_sales_chart(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get sales chart data"""
    dashboard_service = DashboardService(db)
    branch_id = get_branch_id(current_user)
    return dashboard_service.get_sales_chart(
        current_user.business_id,
        branch_id,
        days
    )


@router.get("/expense-chart")
async def get_expense_chart(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get expense chart data"""
    dashboard_service = DashboardService(db)
    branch_id = get_branch_id(current_user)
    return dashboard_service.get_expense_chart(
        current_user.business_id,
        branch_id,
        days
    )


@router.get("/aging")
async def get_aging_reports(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get receivables and payables aging"""
    dashboard_service = DashboardService(db)
    branch_id = get_branch_id(current_user)
    return {
        "receivables": dashboard_service.get_receivables_aging(
            current_user.business_id,
            branch_id
        ),
        "payables": dashboard_service.get_payables_aging(
            current_user.business_id,
            branch_id
        )
    }
