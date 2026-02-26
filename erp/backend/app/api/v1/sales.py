"""
Sales API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    SalesInvoiceCreate, SalesInvoiceResponse, SalesInvoiceWithItems,
    RecordPaymentRequest
)
from app.services.sales_service import SalesService, CreditNoteService

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/invoices", response_model=List[SalesInvoiceResponse])
async def list_invoices(
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all sales invoices"""
    sales_service = SalesService(db)
    return sales_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id,
        status
    )


@router.post("/invoices", response_model=SalesInvoiceWithItems, dependencies=[Depends(PermissionChecker(["sales:create"]))])
async def create_invoice(
    invoice_data: SalesInvoiceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new sales invoice"""
    sales_service = SalesService(db)
    vat_rate = current_user.business.vat_rate if current_user.business.is_vat_registered else 0
    
    invoice = sales_service.create(
        invoice_data,
        current_user.business_id,
        current_user.selected_branch.id,
        vat_rate
    )
    db.commit()
    return invoice


@router.get("/invoices/{invoice_id}", response_model=SalesInvoiceWithItems)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get sales invoice by ID"""
    sales_service = SalesService(db)
    invoice = sales_service.get_by_id(invoice_id, current_user.business_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/payment", dependencies=[Depends(PermissionChecker(["sales:edit"]))])
async def record_payment(
    invoice_id: int,
    payment_data: RecordPaymentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Record payment for invoice"""
    sales_service = SalesService(db)
    try:
        invoice = sales_service.record_payment(
            invoice_id,
            {
                "amount": payment_data.amount,
                "payment_account_id": payment_data.payment_account_id,
                "payment_date": payment_data.payment_date
            },
            current_user.business_id
        )
        db.commit()
        return {"message": "Payment recorded", "invoice": SalesInvoiceResponse.model_validate(invoice)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoices/{invoice_id}/write-off", dependencies=[Depends(PermissionChecker(["sales:delete"]))])
async def write_off_invoice(
    invoice_id: int,
    write_off_date: date,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Write off unpaid invoice as bad debt"""
    sales_service = SalesService(db)
    try:
        invoice = sales_service.write_off(invoice_id, current_user.business_id, write_off_date)
        db.commit()
        return {"message": "Invoice written off", "invoice": SalesInvoiceResponse.model_validate(invoice)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/next-number")
async def get_next_invoice_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get next invoice number"""
    sales_service = SalesService(db)
    return {"next_number": sales_service.get_next_number(current_user.business_id)}


# Credit Notes
@router.get("/credit-notes")
async def list_credit_notes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all credit notes"""
    cn_service = CreditNoteService(db)
    return cn_service.get_by_business(current_user.business_id)


@router.get("/credit-notes/{credit_note_id}")
async def get_credit_note(
    credit_note_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get credit note by ID"""
    cn_service = CreditNoteService(db)
    cn = cn_service.get_by_id(credit_note_id, current_user.business_id)
    if not cn:
        raise HTTPException(status_code=404, detail="Credit note not found")
    return cn
