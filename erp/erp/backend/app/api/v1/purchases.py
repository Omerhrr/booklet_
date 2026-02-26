"""
Purchases API Routes - Bills and Debit Notes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    PurchaseBillCreate, PurchaseBillResponse, PurchaseBillWithItems
)
from app.services.purchase_service import PurchaseService, DebitNoteService

router = APIRouter(prefix="/purchases", tags=["Purchases"])


@router.get("/bills", response_model=List[PurchaseBillResponse])
async def list_bills(
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all purchase bills"""
    purchase_service = PurchaseService(db)
    return purchase_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id,
        status
    )


@router.post("/bills", response_model=PurchaseBillWithItems, dependencies=[Depends(PermissionChecker(["purchases:create"]))])
async def create_bill(
    bill_data: PurchaseBillCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new purchase bill"""
    purchase_service = PurchaseService(db)
    vat_rate = current_user.business.vat_rate if current_user.business.is_vat_registered else 0
    
    bill = purchase_service.create(
        bill_data,
        current_user.business_id,
        current_user.selected_branch.id,
        vat_rate
    )
    db.commit()
    return bill


@router.get("/bills/{bill_id}", response_model=PurchaseBillWithItems)
async def get_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get purchase bill by ID"""
    purchase_service = PurchaseService(db)
    bill = purchase_service.get_by_id(
        bill_id, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.post("/bills/{bill_id}/payment", dependencies=[Depends(PermissionChecker(["purchases:edit"]))])
async def record_bill_payment(
    bill_id: int,
    amount: float,
    payment_account_id: int,
    payment_date: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Record payment for purchase bill"""
    purchase_service = PurchaseService(db)
    try:
        bill = purchase_service.record_payment(
            bill_id,
            {
                "amount": amount,
                "payment_account_id": payment_account_id,
                "payment_date": payment_date
            },
            current_user.business_id
        )
        db.commit()
        return {"message": "Payment recorded", "bill": PurchaseBillResponse.model_validate(bill)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/next-number")
async def get_next_bill_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get next bill number"""
    purchase_service = PurchaseService(db)
    return {"next_number": purchase_service.get_next_number(current_user.business_id)}


# Debit Notes
@router.get("/debit-notes")
async def list_debit_notes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all debit notes"""
    dn_service = DebitNoteService(db)
    return dn_service.get_by_branch(current_user.selected_branch.id, current_user.business_id)


@router.get("/debit-notes/{debit_note_id}")
async def get_debit_note(
    debit_note_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get debit note by ID"""
    dn_service = DebitNoteService(db)
    dn = dn_service.get_by_id(
        debit_note_id, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    if not dn:
        raise HTTPException(status_code=404, detail="Debit note not found")
    return dn


@router.post("/debit-notes", dependencies=[Depends(PermissionChecker(["purchases:create_debit_note"]))])
async def create_debit_note(
    bill_id: int,
    items_to_return: List[dict],
    debit_note_date: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create debit note for purchase return"""
    purchase_service = PurchaseService(db)
    dn_service = DebitNoteService(db)
    
    bill = purchase_service.get_by_id(
        bill_id, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    dn = dn_service.create_for_bill(bill, items_to_return, debit_note_date)
    db.commit()
    return dn
