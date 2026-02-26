"""
Security Module - Authentication & Authorization
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """
    Dependency to get the current authenticated user from JWT token.
    Supports both Authorization header and cookies.
    """
    from app.services.user_service import UserService
    
    token = None
    
    # Try Authorization header first
    if credentials:
        token = credentials.credentials
    
    # Fall back to cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_service = UserService(db)
    user = user_service.get_user_with_relations(username=username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enhanced dependency that attaches branch information to the user.
    """
    from app.services.branch_service import BranchService
    
    branch_service = BranchService(db)
    
    # Get accessible branches
    if current_user.is_superuser:
        accessible_branches = branch_service.get_branches_by_business(current_user.business_id)
    else:
        accessible_branches = [assignment.branch for assignment in current_user.roles]
    
    if not accessible_branches:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any branch"
        )
    
    # Attach to user object
    current_user.accessible_branches = accessible_branches
    
    # Get selected branch from cookie or default
    selected_branch_id = request.cookies.get("selected_branch_id")
    selected_branch = None
    
    if selected_branch_id:
        try:
            selected_branch_id = int(selected_branch_id)
            selected_branch = next(
                (b for b in accessible_branches if b.id == selected_branch_id), 
                None
            )
        except (ValueError, TypeError):
            pass
    
    if not selected_branch:
        # Default to first branch or default branch for superusers
        selected_branch = next(
            (b for b in accessible_branches if b.is_default),
            accessible_branches[0]
        )
    
    current_user.selected_branch = selected_branch
    
    return current_user


class PermissionChecker:
    """Dependency for checking user permissions"""
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = set(required_permissions)
    
    def __call__(self, user = Depends(get_current_active_user), db: Session = Depends(get_db)):
        # Superusers have all permissions
        if user.is_superuser:
            return
        
        from app.services.permission_service import PermissionService
        permission_service = PermissionService(db)
        user_permissions = permission_service.get_user_permissions(user)
        
        if not self.required_permissions.issubset(user_permissions):
            missing = self.required_permissions - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing)}"
            )
