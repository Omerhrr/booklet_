"""
Settings API Routes - Business, Users, Roles, Branches
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user, PermissionChecker, get_password_hash
from app.models import Permission
from app.schemas import (
    BusinessUpdate, BusinessResponse, BranchCreate, BranchUpdate, BranchResponse,
    RoleCreate, RoleUpdate, RoleResponse, PermissionResponse,
    UserCreate, UserUpdate, UserResponse, AssignRoleRequest, ChangePasswordRequest
)
from app.services.business_service import BusinessService, BranchService
from app.services.user_service import UserService
from app.services.permission_service import RoleService, PermissionService

router = APIRouter(prefix="/settings", tags=["Settings"])


# ==================== BUSINESS ====================

@router.get("/business", response_model=BusinessResponse)
async def get_business_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current business settings"""
    business_service = BusinessService(db)
    business = business_service.get_by_id(current_user.business_id)
    return business


@router.put("/business", response_model=BusinessResponse)
async def update_business_settings(
    business_data: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update business settings"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only admins can update business settings")
    
    business_service = BusinessService(db)
    business = business_service.update(current_user.business_id, business_data)
    db.commit()
    return business


# ==================== BRANCHES ====================

@router.get("/branches", response_model=List[BranchResponse])
async def list_branches(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """List branches accessible to the current user"""
    # Return only branches the user has access to
    if current_user.is_superuser:
        # Superusers see all branches in their business
        branch_service = BranchService(db)
        return branch_service.get_branches_by_business(current_user.business_id)
    else:
        # Regular users see only branches they're assigned to
        return list(current_user._accessible_branches)


@router.get("/branches/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single branch"""
    branch_service = BranchService(db)
    branch = branch_service.get_by_id(branch_id)
    if not branch or branch.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.post("/branches", response_model=BranchResponse, dependencies=[Depends(PermissionChecker(["branches:create"]))])
async def create_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new branch"""
    branch_service = BranchService(db)
    branch = branch_service.create(
        branch_data.model_dump(), 
        current_user.business_id,
        is_default=branch_data.is_default
    )
    db.commit()
    return branch


@router.put("/branches/{branch_id}", response_model=BranchResponse, dependencies=[Depends(PermissionChecker(["branches:edit"]))])
async def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update branch"""
    branch_service = BranchService(db)
    branch = branch_service.get_by_id(branch_id)
    if not branch or branch.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    update_data = branch_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(branch, key, value)
    
    db.commit()
    return branch


@router.post("/branches/{branch_id}/set-default", dependencies=[Depends(PermissionChecker(["branches:edit"]))])
async def set_default_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Set branch as default"""
    branch_service = BranchService(db)
    branch = branch_service.set_default(branch_id, current_user.business_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    db.commit()
    return {"message": "Default branch updated"}


# ==================== ROLES ====================

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all roles"""
    role_service = RoleService(db)
    return role_service.get_roles_by_business(current_user.business_id)


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single role"""
    role_service = RoleService(db)
    role = role_service.get_by_id(role_id)
    if not role or role.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("/roles", response_model=RoleResponse, dependencies=[Depends(PermissionChecker(["roles:create"]))])
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new role"""
    role_service = RoleService(db)
    role = role_service.create(
        role_data.name,
        role_data.description,
        current_user.business_id,
        role_data.permission_ids
    )
    db.commit()
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse, dependencies=[Depends(PermissionChecker(["roles:edit"]))])
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update role"""
    role_service = RoleService(db)
    role = role_service.get_by_id(role_id)
    if not role or role.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role_data.name:
        role.name = role_data.name
    if role_data.description is not None:
        role.description = role_data.description
    if role_data.permission_ids is not None:
        role_service.update_permissions(role_id, role_data.permission_ids)
    
    db.commit()
    return role


@router.delete("/roles/{role_id}", dependencies=[Depends(PermissionChecker(["roles:delete"]))])
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete role"""
    role_service = RoleService(db)
    if not role_service.delete(role_id):
        raise HTTPException(status_code=400, detail="Cannot delete system role")
    db.commit()
    return {"message": "Role deleted"}


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all available permissions"""
    permission_service = PermissionService(db)
    return permission_service.get_all_permissions()


@router.get("/permissions/by-category")
async def list_permissions_by_category(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List permissions grouped by category"""
    permission_service = PermissionService(db)
    return permission_service.get_permissions_by_category()


@router.post("/permissions/seed")
async def seed_missing_permissions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Seed any missing permissions to the database and update admin roles"""
    from app.services.permission_service import seed_permissions
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only admins can seed permissions")
    
    # Seed missing permissions
    seed_permissions(db)
    
    # Update admin role with all permissions
    role_service = RoleService(db)
    all_permissions = db.query(Permission).all()
    all_permission_ids = [p.id for p in all_permissions]
    
    # Find and update the Admin role
    roles = role_service.get_roles_by_business(current_user.business_id)
    for role in roles:
        if role.is_system and role.name == "Admin":
            role_service.update_permissions(role.id, all_permission_ids)
            break
    
    db.commit()
    return {"message": "Permissions seeded and Admin role updated successfully"}


# ==================== USERS ====================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all users in business"""
    user_service = UserService(db)
    return user_service.get_users_by_business(current_user.business_id)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single user"""
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    if not user or user.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/details")
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get user details with roles and permissions"""
    user_service = UserService(db)
    user = user_service.get_user_with_roles_and_permissions(user_id)
    
    if not user or user['business_id'] != current_user.business_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/users", response_model=UserResponse, dependencies=[Depends(PermissionChecker(["users:create"]))])
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new user"""
    user_service = UserService(db)
    
    if user_service.get_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if user_service.get_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = user_service.create(user_data, current_user.business_id, user_data.is_superuser)
    db.commit()
    return user


@router.put("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(PermissionChecker(["users:edit"]))])
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update user"""
    user_service = UserService(db)
    user = user_service.update(user_id, user_data)
    if not user or user.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    return user


@router.delete("/users/{user_id}", dependencies=[Depends(PermissionChecker(["users:delete"]))])
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete user"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user_service = UserService(db)
    if not user_service.delete(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    return {"message": "User deleted"}


@router.post("/users/assign-role", dependencies=[Depends(PermissionChecker(["users:assign-roles"]))])
async def assign_role(
    assignment: AssignRoleRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Assign role to user for a branch"""
    user_service = UserService(db)
    assignment = user_service.assign_role(
        assignment.user_id,
        assignment.branch_id,
        assignment.role_id
    )
    db.commit()
    return {"message": "Role assigned successfully"}


@router.post("/users/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Change current user's password"""
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    user_service = UserService(db)
    
    # Verify current password
    if not user_service.verify_password(current_user, password_data.current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    user_service.change_password(current_user.id, password_data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/set-branch/{branch_id}")
async def set_active_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Set user's active branch"""
    # Verify user has access to this branch
    accessible_ids = [b.id for b in getattr(current_user, '_accessible_branches', [])]
    if branch_id not in accessible_ids and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="You don't have access to this branch")
    
    return {"message": "Branch set successfully", "branch_id": branch_id}
