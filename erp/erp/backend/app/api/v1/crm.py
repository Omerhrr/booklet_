"""
CRM API Routes - Customers and Vendors
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    VendorCreate, VendorUpdate, VendorResponse, MessageResponse
)
from app.services.crm_service import CustomerService, VendorService

router = APIRouter(prefix="/crm", tags=["CRM"])


# ==================== CUSTOMERS ====================

@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all customers for current branch"""
    customer_service = CustomerService(db)
    return customer_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id,
        include_inactive
    )


@router.post("/customers", response_model=CustomerResponse, dependencies=[Depends(PermissionChecker(["customers:create"]))])
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new customer"""
    customer_service = CustomerService(db)
    customer = customer_service.create(
        customer_data, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    db.commit()
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get customer by ID"""
    customer_service = CustomerService(db)
    customer = customer_service.get_by_id(
        customer_id, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse, dependencies=[Depends(PermissionChecker(["customers:edit"]))])
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update customer"""
    customer_service = CustomerService(db)
    customer = customer_service.update(
        customer_id, 
        current_user.business_id, 
        customer_data,
        current_user.selected_branch.id
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.commit()
    return customer


@router.delete("/customers/{customer_id}", dependencies=[Depends(PermissionChecker(["customers:delete"]))])
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete customer"""
    customer_service = CustomerService(db)
    if not customer_service.delete(
        customer_id, 
        current_user.business_id,
        current_user.selected_branch.id
    ):
        raise HTTPException(status_code=404, detail="Customer not found")
    db.commit()
    return {"message": "Customer deleted successfully"}


@router.get("/customers/{customer_id}/balance")
async def get_customer_balance(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get customer outstanding balance"""
    customer_service = CustomerService(db)
    balance = customer_service.get_balance(customer_id)
    return {"customer_id": customer_id, "outstanding_balance": balance}


# ==================== VENDORS ====================

@router.get("/vendors", response_model=List[VendorResponse])
async def list_vendors(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all vendors for current branch"""
    vendor_service = VendorService(db)
    return vendor_service.get_by_branch(
        current_user.selected_branch.id,
        current_user.business_id,
        include_inactive
    )


@router.post("/vendors", response_model=VendorResponse, dependencies=[Depends(PermissionChecker(["vendors:create"]))])
async def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new vendor"""
    vendor_service = VendorService(db)
    vendor = vendor_service.create(
        vendor_data, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    db.commit()
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get vendor by ID"""
    vendor_service = VendorService(db)
    vendor = vendor_service.get_by_id(
        vendor_id, 
        current_user.business_id,
        current_user.selected_branch.id
    )
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/vendors/{vendor_id}", response_model=VendorResponse, dependencies=[Depends(PermissionChecker(["vendors:edit"]))])
async def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update vendor"""
    vendor_service = VendorService(db)
    vendor = vendor_service.update(
        vendor_id, 
        current_user.business_id, 
        vendor_data,
        current_user.selected_branch.id
    )
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.commit()
    return vendor


@router.delete("/vendors/{vendor_id}", dependencies=[Depends(PermissionChecker(["vendors:delete"]))])
async def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete vendor"""
    vendor_service = VendorService(db)
    if not vendor_service.delete(
        vendor_id, 
        current_user.business_id,
        current_user.selected_branch.id
    ):
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.commit()
    return {"message": "Vendor deleted successfully"}


@router.get("/vendors/{vendor_id}/balance")
async def get_vendor_balance(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get vendor outstanding balance"""
    vendor_service = VendorService(db)
    balance = vendor_service.get_balance(vendor_id)
    return {"vendor_id": vendor_id, "outstanding_balance": balance}
