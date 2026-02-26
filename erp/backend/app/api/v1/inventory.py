"""
Inventory API Routes - Products and Categories
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user, PermissionChecker
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, StockAdjustmentCreate,
    CategoryCreate, CategoryUpdate, CategoryResponse
)
from app.services.inventory_service import ProductService, CategoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ==================== CATEGORIES ====================

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all categories for current branch"""
    category_service = CategoryService(db)
    return category_service.get_by_branch(current_user.selected_branch.id)


@router.post("/categories", response_model=CategoryResponse, dependencies=[Depends(PermissionChecker(["inventory:create"]))])
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new category"""
    category_service = CategoryService(db)
    category = category_service.create(
        category_data,
        current_user.selected_branch.id,
        current_user.business_id
    )
    db.commit()
    return category


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get category by ID"""
    category_service = CategoryService(db)
    category = category_service.get_by_id(category_id, current_user.selected_branch.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse, dependencies=[Depends(PermissionChecker(["inventory:edit"]))])
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update category"""
    category_service = CategoryService(db)
    category = category_service.update(category_id, current_user.selected_branch.id, category_data)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.commit()
    return category


@router.delete("/categories/{category_id}", dependencies=[Depends(PermissionChecker(["inventory:delete"]))])
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete category"""
    category_service = CategoryService(db)
    if not category_service.delete(category_id, current_user.selected_branch.id):
        raise HTTPException(status_code=400, detail="Cannot delete category with products")
    db.commit()
    return {"message": "Category deleted successfully"}


# ==================== PRODUCTS ====================

@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List all products for current branch"""
    product_service = ProductService(db)
    return product_service.get_by_branch(current_user.selected_branch.id, include_inactive)


@router.get("/products/low-stock", response_model=List[ProductResponse])
async def list_low_stock_products(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List products below reorder level"""
    product_service = ProductService(db)
    return product_service.get_low_stock(current_user.selected_branch.id)


@router.post("/products", response_model=ProductResponse, dependencies=[Depends(PermissionChecker(["inventory:create"]))])
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new product"""
    product_service = ProductService(db)
    product = product_service.create(
        product_data,
        current_user.selected_branch.id,
        current_user.business_id
    )
    db.commit()
    return product


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get product by ID"""
    product_service = ProductService(db)
    product = product_service.get_by_id(product_id, current_user.selected_branch.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}", response_model=ProductResponse, dependencies=[Depends(PermissionChecker(["inventory:edit"]))])
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update product"""
    product_service = ProductService(db)
    product = product_service.update(product_id, current_user.selected_branch.id, product_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
    return product


@router.delete("/products/{product_id}", dependencies=[Depends(PermissionChecker(["inventory:delete"]))])
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete product"""
    product_service = ProductService(db)
    if not product_service.delete(product_id, current_user.selected_branch.id):
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
    return {"message": "Product deleted successfully"}


@router.post("/products/{product_id}/adjust-stock", response_model=ProductResponse, dependencies=[Depends(PermissionChecker(["inventory:adjust_stock"]))])
async def adjust_product_stock(
    product_id: int,
    adjustment_data: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Adjust product stock"""
    product_service = ProductService(db)
    try:
        product = product_service.adjust_stock(product_id, adjustment_data, current_user.id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        db.commit()
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
