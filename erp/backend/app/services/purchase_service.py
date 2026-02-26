"""
Purchases Service - Bills, Debit Notes
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from datetime import date
from app.models import PurchaseBill, PurchaseBillItem, DebitNote, DebitNoteItem, LedgerEntry, Account, Product
from app.schemas import PurchaseBillCreate


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, bill_id: int, business_id: int) -> Optional[PurchaseBill]:
        return self.db.query(PurchaseBill).options(
            joinedload(PurchaseBill.items).joinedload(PurchaseBillItem.product),
            joinedload(PurchaseBill.vendor)
        ).filter(
            PurchaseBill.id == bill_id,
            PurchaseBill.business_id == business_id
        ).first()
    
    def get_by_branch(self, branch_id: int, business_id: int, status: str = None) -> List[PurchaseBill]:
        query = self.db.query(PurchaseBill).options(
            joinedload(PurchaseBill.vendor)
        ).filter(
            PurchaseBill.branch_id == branch_id,
            PurchaseBill.business_id == business_id
        )
        if status:
            query = query.filter(PurchaseBill.status == status)
        return query.order_by(PurchaseBill.created_at.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        last_bill = self.db.query(PurchaseBill).filter(
            PurchaseBill.business_id == business_id
        ).order_by(PurchaseBill.id.desc()).first()
        
        if last_bill:
            try:
                num = int(last_bill.bill_number.replace("PO-", ""))
                return f"PO-{num + 1:05d}"
            except ValueError:
                pass
        
        return "PO-00001"
    
    def create(self, bill_data: PurchaseBillCreate, business_id: int, branch_id: int, vat_rate: Decimal = Decimal("0")) -> PurchaseBill:
        # Calculate totals
        sub_total = sum(item.quantity * item.price for item in bill_data.items)
        vat_amount = sub_total * (vat_rate / 100) if vat_rate else Decimal("0")
        total_amount = sub_total + vat_amount
        
        # Create bill
        bill = PurchaseBill(
            bill_number=bill_data.bill_number or self.get_next_number(business_id),
            vendor_id=bill_data.vendor_id,
            bill_date=bill_data.bill_date,
            due_date=bill_data.due_date,
            notes=bill_data.notes,
            sub_total=sub_total,
            vat_amount=vat_amount,
            total_amount=total_amount,
            paid_amount=Decimal("0"),
            status="Unpaid",
            branch_id=branch_id,
            business_id=business_id
        )
        self.db.add(bill)
        self.db.flush()
        
        # Create items
        for item_data in bill_data.items:
            item = PurchaseBillItem(
                purchase_bill_id=bill.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price=item_data.price,
                returned_quantity=Decimal("0")
            )
            self.db.add(item)
            
            # Update product stock
            product = self.db.query(Product).get(item_data.product_id)
            if product:
                product.stock_quantity += item_data.quantity
        
        # Create ledger entries
        self._create_ledger_entries(bill)
        
        self.db.flush()
        return bill
    
    def _create_ledger_entries(self, bill: PurchaseBill):
        """Create double-entry ledger entries for purchase bill"""
        # Get accounts
        payable_account = self.db.query(Account).filter(
            Account.business_id == bill.business_id,
            Account.name == "Accounts Payable"
        ).first()
        
        inventory_account = self.db.query(Account).filter(
            Account.business_id == bill.business_id,
            Account.name == "Inventory"
        ).first()
        
        if not payable_account or not inventory_account:
            return
        
        # Debit Inventory
        debit_entry = LedgerEntry(
            transaction_date=bill.bill_date,
            description=f"Purchase Bill {bill.bill_number}",
            debit=bill.sub_total,
            credit=Decimal("0"),
            account_id=inventory_account.id,
            vendor_id=bill.vendor_id,
            purchase_bill_id=bill.id,
            branch_id=bill.branch_id
        )
        self.db.add(debit_entry)
        
        # Credit Accounts Payable
        credit_entry = LedgerEntry(
            transaction_date=bill.bill_date,
            description=f"Purchase Bill {bill.bill_number}",
            debit=Decimal("0"),
            credit=bill.total_amount,
            account_id=payable_account.id,
            vendor_id=bill.vendor_id,
            purchase_bill_id=bill.id,
            branch_id=bill.branch_id
        )
        self.db.add(credit_entry)
        
        # Debit VAT Receivable if applicable
        if bill.vat_amount > 0:
            vat_account = self.db.query(Account).filter(
                Account.business_id == bill.business_id,
                Account.name == "VAT Payable"
            ).first()
            
            if vat_account:
                vat_entry = LedgerEntry(
                    transaction_date=bill.bill_date,
                    description=f"VAT for Purchase Bill {bill.bill_number}",
                    debit=bill.vat_amount,
                    credit=Decimal("0"),
                    account_id=vat_account.id,
                    vendor_id=bill.vendor_id,
                    purchase_bill_id=bill.id,
                    branch_id=bill.branch_id
                )
                self.db.add(vat_entry)
    
    def record_payment(self, bill_id: int, payment_data: dict, business_id: int) -> PurchaseBill:
        bill = self.get_by_id(bill_id, business_id)
        if not bill:
            raise ValueError("Bill not found")
        
        amount = payment_data["amount"]
        payment_account_id = payment_data["payment_account_id"]
        payment_date = payment_data["payment_date"]
        
        # Update bill
        bill.paid_amount += amount
        if bill.paid_amount >= bill.total_amount:
            bill.status = "Paid"
        elif bill.paid_amount > 0:
            bill.status = "Partial"
        
        # Get accounts
        cash_account = self.db.query(Account).get(payment_account_id)
        payable_account = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.name == "Accounts Payable"
        ).first()
        
        if cash_account and payable_account:
            # Debit Accounts Payable
            debit_entry = LedgerEntry(
                transaction_date=payment_date,
                description=f"Payment for Bill {bill.bill_number}",
                debit=amount,
                credit=Decimal("0"),
                account_id=payable_account.id,
                vendor_id=bill.vendor_id,
                purchase_bill_id=bill.id,
                branch_id=bill.branch_id
            )
            self.db.add(debit_entry)
            
            # Credit Cash/Bank
            credit_entry = LedgerEntry(
                transaction_date=payment_date,
                description=f"Payment for Bill {bill.bill_number}",
                debit=Decimal("0"),
                credit=amount,
                account_id=cash_account.id,
                vendor_id=bill.vendor_id,
                purchase_bill_id=bill.id,
                branch_id=bill.branch_id
            )
            self.db.add(credit_entry)
        
        self.db.flush()
        return bill


class DebitNoteService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, debit_note_id: int, business_id: int) -> Optional[DebitNote]:
        return self.db.query(DebitNote).options(
            joinedload(DebitNote.items).joinedload(DebitNoteItem.product),
            joinedload(DebitNote.purchase_bill).joinedload(PurchaseBill.vendor)
        ).filter(
            DebitNote.id == debit_note_id,
            DebitNote.business_id == business_id
        ).first()
    
    def get_by_business(self, business_id: int) -> List[DebitNote]:
        return self.db.query(DebitNote).options(
            joinedload(DebitNote.purchase_bill).joinedload(PurchaseBill.vendor)
        ).filter(
            DebitNote.business_id == business_id
        ).order_by(DebitNote.created_at.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        last_dn = self.db.query(DebitNote).filter(
            DebitNote.business_id == business_id
        ).order_by(DebitNote.id.desc()).first()
        
        if last_dn:
            try:
                num = int(last_dn.debit_note_number.replace("DN-", ""))
                return f"DN-{num + 1:05d}"
            except ValueError:
                pass
        
        return "DN-00001"
    
    def create_for_bill(self, original_bill: PurchaseBill, items_to_return: List[dict], debit_note_date: date) -> DebitNote:
        total_amount = sum(item["quantity"] * item["price"] for item in items_to_return)
        
        debit_note = DebitNote(
            debit_note_number=self.get_next_number(original_bill.business_id),
            debit_note_date=debit_note_date,
            total_amount=total_amount,
            reason="Purchase Return",
            purchase_bill_id=original_bill.id,
            branch_id=original_bill.branch_id,
            business_id=original_bill.business_id
        )
        self.db.add(debit_note)
        self.db.flush()
        
        for item_data in items_to_return:
            dn_item = DebitNoteItem(
                debit_note_id=debit_note.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                price=item_data["price"]
            )
            self.db.add(dn_item)
            
            # Update product stock
            product = self.db.query(Product).get(item_data["product_id"])
            if product:
                product.stock_quantity -= item_data["quantity"]
            
            # Update returned quantity on original item
            orig_item = self.db.query(PurchaseBillItem).get(item_data["original_item_id"])
            if orig_item:
                orig_item.returned_quantity += item_data["quantity"]
        
        self.db.flush()
        return debit_note
