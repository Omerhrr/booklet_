"""
Authentication API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, get_current_user
from app.core.config import settings
from app.schemas import LoginRequest, SignupRequest, Token, UserResponse, MessageResponse
from app.services.user_service import UserService
from app.services.business_service import BusinessService, BranchService
from app.services.permission_service import RoleService, seed_permissions, PermissionService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=dict)
async def signup(
    signup_data: SignupRequest,
    db: Session = Depends(get_db)
):
    """Register a new business and admin user"""
    user_service = UserService(db)
    business_service = BusinessService(db)
    branch_service = BranchService(db)
    role_service = RoleService(db)
    
    # Check if username exists
    if user_service.get_by_username(signup_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if user_service.get_by_email(signup_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create business
        business = business_service.create(signup_data.model_dump(include={"business_name"}))
        
        # Seed permissions if needed
        seed_permissions(db)
        
        # Create default admin role
        admin_role = role_service.create_default_roles_for_business(business.id)
        
        # Create user
        user_data = {
            "username": signup_data.username,
            "email": signup_data.email,
            "password": signup_data.password
        }
        user = user_service.create(user_data, business.id, is_superuser=True)
        
        # Create default branch
        branch = branch_service.create(
            {"name": "Main Branch", "currency": "USD"},
            business.id,
            is_default=True
        )
        
        # Assign role to user
        user_service.assign_role(user.id, branch.id, admin_role.id)
        
        # Create default chart of accounts
        business_service.create_default_chart_of_accounts(business.id)
        
        db.commit()
        
        # Create token
        access_token = create_access_token(
            data={"sub": user.username, "business_id": business.id}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "business_id": business.id
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    user_service = UserService(db)
    
    user = user_service.get_by_username(login_data.username)
    
    if not user or not user_service.verify_password(user, login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "business_id": user.business_id},
        expires_delta=access_token_expires
    )
    
    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=int(access_token_expires.total_seconds()),
        samesite="lax"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Logout and clear token"""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get current user info"""
    return current_user


@router.get("/permissions")
async def get_user_permissions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current user's permissions"""
    if current_user.is_superuser:
        # Superusers have all permissions
        permission_service = PermissionService(db)
        all_perms = permission_service.get_all_permissions()
        return {"permissions": [p.name for p in all_perms], "is_superuser": True, "user_id": current_user.id}
    
    permission_service = PermissionService(db)
    user_permissions = permission_service.get_user_permissions(current_user)
    
    # Debug info
    debug_info = {
        "user_id": current_user.id,
        "username": current_user.username,
        "is_superuser": current_user.is_superuser,
        "roles_count": len(current_user.roles) if current_user.roles else 0,
        "roles": []
    }
    
    if current_user.roles:
        for ur in current_user.roles:
            role_info = {
                "role_id": ur.role_id,
                "role_name": ur.role.name if ur.role else None,
                "branch_id": ur.branch_id
            }
            if ur.role and hasattr(ur.role, 'permission_links'):
                role_info["permissions_count"] = len(ur.role.permission_links) if ur.role.permission_links else 0
            debug_info["roles"].append(role_info)
    
    return {
        "permissions": list(user_permissions), 
        "is_superuser": False,
        "debug": debug_info
    }
