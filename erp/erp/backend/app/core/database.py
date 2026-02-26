"""
Database Configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

from app.core.config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Ensures the session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    # Import all models to register them with Base
    from app.models import (
        Business, User, Branch, Permission, Role, UserBranchRole, RolePermission,
        Account, JournalVoucher, LedgerEntry, Budget, BudgetItem, FixedAsset,
        Customer, Vendor, Category, Product, StockAdjustment,
        SalesInvoice, SalesInvoiceItem, Payment, CreditNote, CreditNoteItem,
        PurchaseBill, PurchaseBillItem, DebitNote, DebitNoteItem,
        Employee, PayrollConfig, Payslip, BankAccount, FundTransfer, Expense
    )
    Base.metadata.create_all(bind=engine)
