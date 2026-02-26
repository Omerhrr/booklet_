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
        
        # Debug: Make sure user has roles loaded
        if not user.roles:
            return permissions
        
        for user_role in user.roles:
            role = user_role.role
            if not role:
                continue
            
            # Get permissions through role.permission_links
            if hasattr(role, 'permission_links') and role.permission_links:
                for role_perm in role.permission_links:
                    if role_perm.permission:
                        permissions.add(role_perm.permission.name)
            # Fallback: try role.permissions property
            elif hasattr(role, 'permissions') and role.permissions:
                for perm in role.permissions:
                    permissions.add(perm.name)
        
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
        # Settings
        {"name": "settings:edit", "category": "Settings", "description": "Edit business settings"},
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
        # Banking (template uses banking:view, transfers:view, reconciliation:view)
        {"name": "banking:view", "category": "Banking", "description": "View bank accounts"},
        {"name": "banking:create", "category": "Banking", "description": "Create bank accounts"},
        {"name": "banking:edit", "category": "Banking", "description": "Edit bank accounts"},
        {"name": "banking:delete", "category": "Banking", "description": "Delete bank accounts"},
        {"name": "transfers:view", "category": "Banking", "description": "View fund transfers"},
        {"name": "transfers:create", "category": "Banking", "description": "Create fund transfers"},
        {"name": "reconciliation:view", "category": "Banking", "description": "View bank reconciliation"},
        {"name": "reconciliation:create", "category": "Banking", "description": "Perform bank reconciliation"},
        # Reports (template uses reports:view)
        {"name": "reports:view", "category": "Reports", "description": "View reports"},
        {"name": "reports:export", "category": "Reports", "description": "Export reports"},
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
        # Inventory (template uses products:view, categories:view, stock:view)
        {"name": "products:view", "category": "Inventory", "description": "View products"},
        {"name": "products:create", "category": "Inventory", "description": "Create products"},
        {"name": "products:edit", "category": "Inventory", "description": "Edit products"},
        {"name": "products:delete", "category": "Inventory", "description": "Delete products"},
        {"name": "categories:view", "category": "Inventory", "description": "View categories"},
        {"name": "categories:create", "category": "Inventory", "description": "Create categories"},
        {"name": "categories:edit", "category": "Inventory", "description": "Edit categories"},
        {"name": "categories:delete", "category": "Inventory", "description": "Delete categories"},
        {"name": "stock:view", "category": "Inventory", "description": "View stock adjustments"},
        {"name": "stock:create", "category": "Inventory", "description": "Create stock adjustments"},
        # Purchases (template uses bills:view, bills:create, debit_notes:view)
        {"name": "bills:view", "category": "Purchases", "description": "View purchase bills"},
        {"name": "bills:create", "category": "Purchases", "description": "Create purchase bills"},
        {"name": "bills:edit", "category": "Purchases", "description": "Edit purchase bills"},
        {"name": "bills:delete", "category": "Purchases", "description": "Delete purchase bills"},
        {"name": "debit_notes:view", "category": "Purchases", "description": "View debit notes"},
        {"name": "debit_notes:create", "category": "Purchases", "description": "Create debit notes"},
        # Sales (template uses invoices:view, invoices:create, credit_notes:view)
        {"name": "invoices:view", "category": "Sales", "description": "View sales invoices"},
        {"name": "invoices:create", "category": "Sales", "description": "Create sales invoices"},
        {"name": "invoices:edit", "category": "Sales", "description": "Edit sales invoices"},
        {"name": "invoices:delete", "category": "Sales", "description": "Delete sales invoices"},
        {"name": "credit_notes:view", "category": "Sales", "description": "View credit notes"},
        {"name": "credit_notes:create", "category": "Sales", "description": "Create credit notes"},
        # Expenses
        {"name": "expenses:view", "category": "Expenses", "description": "View expenses"},
        {"name": "expenses:create", "category": "Expenses", "description": "Create expenses"},
        {"name": "expenses:edit", "category": "Expenses", "description": "Edit expenses"},
        {"name": "expenses:delete", "category": "Expenses", "description": "Delete expenses"},
        # Accounting (template uses accounts:view, journal:view)
        {"name": "accounts:view", "category": "Accounting", "description": "View chart of accounts"},
        {"name": "accounts:create", "category": "Accounting", "description": "Create accounts"},
        {"name": "accounts:edit", "category": "Accounting", "description": "Edit accounts"},
        {"name": "accounts:delete", "category": "Accounting", "description": "Delete accounts"},
        {"name": "journal:view", "category": "Accounting", "description": "View journal entries"},
        {"name": "journal:create", "category": "Accounting", "description": "Create journal entries"},
        {"name": "journal:edit", "category": "Accounting", "description": "Edit journal entries"},
        {"name": "journal:delete", "category": "Accounting", "description": "Delete journal entries"},
        # HR (template uses employees:view, payroll:view)
        {"name": "employees:view", "category": "HR", "description": "View employees"},
        {"name": "employees:create", "category": "HR", "description": "Create employees"},
        {"name": "employees:edit", "category": "HR", "description": "Edit employees"},
        {"name": "employees:delete", "category": "HR", "description": "Delete employees"},
        {"name": "payroll:view", "category": "HR", "description": "View payroll"},
        {"name": "payroll:create", "category": "HR", "description": "Run payroll"},
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
