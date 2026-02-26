"""
User Service - Business Logic for User Operations
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.models import User, Business, Branch, Role, UserBranchRole, Permission, RolePermission
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_with_relations(self, username: str) -> Optional[User]:
        return self.db.query(User)\
            .options(
                joinedload(User.business),
                joinedload(User.roles).joinedload(UserBranchRole.branch),
                joinedload(User.roles).joinedload(UserBranchRole.role)
            )\
            .filter(User.username == username)\
            .first()
    
    def get_users_by_business(self, business_id: int) -> List[User]:
        return self.db.query(User)\
            .options(joinedload(User.roles))\
            .filter(User.business_id == business_id)\
            .all()
    
    def create(self, user_data, business_id: int, is_superuser: bool = False) -> User:
        # Handle both dict and UserCreate schema
        if isinstance(user_data, dict):
            username = user_data.get('username')
            email = user_data.get('email')
            password = user_data.get('password')
        else:
            username = user_data.username
            email = user_data.email
            password = user_data.password
        
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            business_id=business_id,
            is_superuser=is_superuser,
            is_active=True
        )
        self.db.add(user)
        self.db.flush()
        return user
    
    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        
        self.db.flush()
        return user
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.hashed_password = get_password_hash(new_password)
        self.db.flush()
        return True
    
    def verify_password(self, user: User, password: str) -> bool:
        return verify_password(password, user.hashed_password)
    
    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        return True
    
    def assign_role(self, user_id: int, branch_id: int, role_id: int) -> UserBranchRole:
        assignment = UserBranchRole(
            user_id=user_id,
            branch_id=branch_id,
            role_id=role_id
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment
    
    def remove_role(self, user_id: int, branch_id: int, role_id: int) -> bool:
        assignment = self.db.query(UserBranchRole).filter(
            UserBranchRole.user_id == user_id,
            UserBranchRole.branch_id == branch_id,
            UserBranchRole.role_id == role_id
        ).first()
        
        if not assignment:
            return False
        
        self.db.delete(assignment)
        return True
