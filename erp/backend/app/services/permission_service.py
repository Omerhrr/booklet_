"""
Permission Service - Business Logic for RBAC
"""
from typing import List, Set
from sqlalchemy.orm import Session
from app.models import Permission, Role, RolePermission, User


class PermissionService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_permissions(self) -> List[Permission]:
        return self.db.query(Permission).all()
    
    def get_permissions_by_category(self) -> dict:
        permissions = self.get_all_permissions()
        categorized = {}
        for perm in permissions:
            if perm.category not in categorized:
                categorized[perm.category] = []
            categorized[perm.category].append(perm)
        return categorized
    
    def get_user_permissions(self, user: User) -> Set[str]:
        """Get all permissions for a user through their roles"""
        permissions = set()
        
        for user_role in user.roles:
            role = user_role.role
            for role_perm in role.permissions:
                permissions.add(role_perm.permission.name)
        
        return permissions
    
    def user_has_permission(self, user: User, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        user_permissions = self.get_user_permissions(user)
        return permission_name in user_permissions
    
    def user_has_any_permission(self, user: User, permission_names: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = self.get_user_permissions(user)
        return bool(set(permission_names) & user_permissions)


class RoleService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, role_id: int) -> Role:
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_roles_by_business(self, business_id: int) -> List[Role]:
        return self.db.query(Role).filter(Role.business_id == business_id).all()
    
    def create(self, name: str, description: str, business_id: int, permission_ids: List[int] = None) -> Role:
        role = Role(
            name=name,
            description=description,
            business_id=business_id
        )
        self.db.add(role)
        self.db.flush()
        
        if permission_ids:
            for perm_id in permission_ids:
                role_perm = RolePermission(role_id=role.id, permission_id=perm_id)
                self.db.add(role_perm)
        
        self.db.flush()
        return role
    
    def create_default_roles_for_business(self, business_id: int) -> Role:
        """Create default Admin role with all permissions"""
        admin_role = Role(
            name="Admin",
            description="Full administrative access",
            is_system=True,
            business_id=business_id
        )
        self.db.add(admin_role)
        self.db.flush()
        
        # Assign all permissions
        permissions = self.db.query(Permission).all()
        for perm in permissions:
            role_perm = RolePermission(role_id=admin_role.id, permission_id=perm.id)
            self.db.add(role_perm)
        
        self.db.flush()
        return admin_role
    
    def update_permissions(self, role_id: int, permission_ids: List[int]) -> Role:
        role = self.get_by_id(role_id)
        if not role:
            return None
        
        # Remove existing permissions
        self.db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        
        # Add new permissions
        for perm_id in permission_ids:
            role_perm = RolePermission(role_id=role.id, permission_id=perm_id)
            self.db.add(role_perm)
        
        self.db.flush()
        return role
    
    def delete(self, role_id: int) -> bool:
        role = self.get_by_id(role_id)
        if not role or role.is_system:
            return False
        
        self.db.delete(role)
        return True


def seed_permissions(db: Session):
    """Seed default permissions into the database"""
    all_permissions = [
        # Users
        {"name": "users:view", "category": "Users", "description": "View users list"},
        {"name": "users:create", "category": "Users", "description": "Create new users"},
        {"name": "users:edit", "category": "Users", "description": "Edit existing users"},
        {"name": "users:delete", "category": "Users", "description": "Delete users"},
        {"name": "users:assign-roles", "category": "Users", "description": "Assign roles to users"},
        # Roles
        {"name": "roles:view", "category": "Roles", "description": "View roles"},
        {"name": "roles:create", "category": "Roles", "description": "Create new roles"},
        {"name": "roles:edit", "category": "Roles", "description": "Edit existing roles"},
        {"name": "roles:delete", "category": "Roles", "description": "Delete roles"},
        # Branches
        {"name": "branches:view", "category": "Branches", "description": "View branches"},
        {"name": "branches:create", "category": "Branches", "description": "Create new branches"},
        {"name": "branches:edit", "category": "Branches", "description": "Edit existing branches"},
        {"name": "branches:delete", "category": "Branches", "description": "Delete branches"},
        # Banking
        {"name": "bank:view", "category": "Banking", "description": "View bank accounts"},
        {"name": "bank:create", "category": "Banking", "description": "Create bank accounts"},
        {"name": "bank:reconcile", "category": "Banking", "description": "Perform bank reconciliation"},
        # Reports
        {"name": "report:view", "category": "Reports", "description": "View reports"},
        {"name": "report:export", "category": "Reports", "description": "Export reports"},
        # AI Analyst
        {"name": "jarvis:ask", "category": "AI Analyst", "description": "Use AI assistant"},
        # Customers
        {"name": "customers:view", "category": "Customers", "description": "View customers"},
        {"name": "customers:create", "category": "Customers", "description": "Create customers"},
        {"name": "customers:edit", "category": "Customers", "description": "Edit customers"},
        {"name": "customers:delete", "category": "Customers", "description": "Delete customers"},
        # Vendors
        {"name": "vendors:view", "category": "Vendors", "description": "View vendors"},
        {"name": "vendors:create", "category": "Vendors", "description": "Create vendors"},
        {"name": "vendors:edit", "category": "Vendors", "description": "Edit vendors"},
        {"name": "vendors:delete", "category": "Vendors", "description": "Delete vendors"},
        # Inventory
        {"name": "inventory:view", "category": "Inventory", "description": "View inventory"},
        {"name": "inventory:create", "category": "Inventory", "description": "Create products"},
        {"name": "inventory:edit", "category": "Inventory", "description": "Edit products"},
        {"name": "inventory:delete", "category": "Inventory", "description": "Delete products"},
        {"name": "inventory:adjust_stock", "category": "Inventory", "description": "Adjust stock levels"},
        # Purchases
        {"name": "purchases:view", "category": "Purchases", "description": "View purchases"},
        {"name": "purchases:create", "category": "Purchases", "description": "Create purchase bills"},
        {"name": "purchases:edit", "category": "Purchases", "description": "Edit purchase bills"},
        {"name": "purchases:delete", "category": "Purchases", "description": "Delete purchase bills"},
        {"name": "purchases:create_debit_note", "category": "Purchases", "description": "Create debit notes"},
        # Sales
        {"name": "sales:view", "category": "Sales", "description": "View sales"},
        {"name": "sales:create", "category": "Sales", "description": "Create sales invoices"},
        {"name": "sales:edit", "category": "Sales", "description": "Edit sales invoices"},
        {"name": "sales:delete", "category": "Sales", "description": "Delete sales invoices"},
        {"name": "sales:create_credit_note", "category": "Sales", "description": "Create credit notes"},
        # Expenses
        {"name": "expenses:view", "category": "Expenses", "description": "View expenses"},
        {"name": "expenses:create", "category": "Expenses", "description": "Create expenses"},
        {"name": "expenses:edit", "category": "Expenses", "description": "Edit expenses"},
        {"name": "expenses:delete", "category": "Expenses", "description": "Delete expenses"},
        # Accounting
        {"name": "accounting:view", "category": "Accounting", "description": "View accounting"},
        {"name": "accounting:create", "category": "Accounting", "description": "Create journal entries"},
        {"name": "accounting:edit", "category": "Accounting", "description": "Edit journal entries"},
        {"name": "accounting:delete", "category": "Accounting", "description": "Delete journal entries"},
        # HR
        {"name": "hr:view", "category": "HR", "description": "View HR"},
        {"name": "hr:create", "category": "HR", "description": "Create employees"},
        {"name": "hr:edit", "category": "HR", "description": "Edit employees"},
        {"name": "hr:delete", "category": "HR", "description": "Delete employees"},
        {"name": "hr:run_payroll", "category": "HR", "description": "Run payroll"},
        # Budgeting
        {"name": "budgeting:view", "category": "Budgeting", "description": "View budgets"},
        {"name": "budgeting:create", "category": "Budgeting", "description": "Create budgets"},
        {"name": "budgeting:edit", "category": "Budgeting", "description": "Edit budgets"},
        {"name": "budgeting:delete", "category": "Budgeting", "description": "Delete budgets"},
    ]
    
    existing = {p.name for p in db.query(Permission.name).all()}
    
    for perm_data in all_permissions:
        if perm_data["name"] not in existing:
            perm = Permission(**perm_data)
            db.add(perm)
    
    db.commit()
