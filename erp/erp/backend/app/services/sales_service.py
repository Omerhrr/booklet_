"""
Sales Service - Invoices, Credit Notes, Payments
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from datetime import date
from app.models import SalesInvoice, SalesInvoiceItem, CreditNote, CreditNoteItem, LedgerEntry, Account, Product
from app.schemas import SalesInvoiceCreate, SalesInvoiceUpdate


class SalesService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, invoice_id: int, business_id: int, branch_id: int = None) -> Optional[SalesInvoice]:
        query = self.db.query(SalesInvoice).options(
            joinedload(SalesInvoice.items).joinedload(SalesInvoiceItem.product),
            joinedload(SalesInvoice.customer)
        ).filter(
            SalesInvoice.id == invoice_id,
            SalesInvoice.business_id == business_id
        )
        if branch_id:
            query = query.filter(SalesInvoice.branch_id == branch_id)
        return query.first()
    
    def get_by_branch(self, branch_id: int, business_id: int, status: str = None) -> List[SalesInvoice]:
        query = self.db.query(SalesInvoice).options(
            joinedload(SalesInvoice.customer)
        ).filter(
            SalesInvoice.branch_id == branch_id,
            SalesInvoice.business_id == business_id
        )
        if status:
            query = query.filter(SalesInvoice.status == status)
        return query.order_by(SalesInvoice.created_at.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        """Generate next invoice number"""
        last_invoice = self.db.query(SalesInvoice).filter(
            SalesInvoice.business_id == business_id
        ).order_by(SalesInvoice.id.desc()).first()
        
        if last_invoice:
            try:
                num = int(last_invoice.invoice_number.replace("INV-", ""))
                return f"INV-{num + 1:05d}"
            except ValueError:
                pass
        
        return "INV-00001"
    
    def calculate_totals(self, items: List[dict], vat_rate: Decimal = Decimal("0")) -> dict:
        """Calculate invoice totals"""
        sub_total = sum(item["quantity"] * item["price"] for item in items)
        vat_amount = sub_total * (vat_rate / 100) if vat_rate else Decimal("0")
        total = sub_total + vat_amount
        return {
            "sub_total": sub_total,
            "vat_amount": vat_amount,
            "total_amount": total
        }
    
    def create(self, invoice_data: SalesInvoiceCreate, business_id: int, branch_id: int, vat_rate: Decimal = Decimal("0")) -> SalesInvoice:
        # Calculate totals
        items_data = [{"quantity": item.quantity, "price": item.price} for item in invoice_data.items]
        totals = self.calculate_totals(items_data, vat_rate)
        
        # Create invoice
        invoice = SalesInvoice(
            invoice_number=self.get_next_number(business_id),
            customer_id=invoice_data.customer_id,
            invoice_date=invoice_data.invoice_date,
            due_date=invoice_data.due_date,
            notes=invoice_data.notes,
            sub_total=totals["sub_total"],
            vat_amount=totals["vat_amount"],
            total_amount=totals["total_amount"],
            paid_amount=Decimal("0"),
            status="Unpaid",
            branch_id=branch_id,
            business_id=business_id
        )
        self.db.add(invoice)
        self.db.flush()
        
        # Create items
        for item_data in invoice_data.items:
            item = SalesInvoiceItem(
                sales_invoice_id=invoice.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price=item_data.price,
                returned_quantity=Decimal("0")
            )
            self.db.add(item)
            
            # Update product stock
            product = self.db.query(Product).get(item_data.product_id)
            if product:
                product.stock_quantity -= item_data.quantity
        
        # Create ledger entries
        self._create_ledger_entries(invoice)
        
        self.db.flush()
        return invoice
    
    def _create_ledger_entries(self, invoice: SalesInvoice):
        """Create double-entry ledger entries for invoice"""
        # Get accounts
        receivable_account = self.db.query(Account).filter(
            Account.business_id == invoice.business_id,
            Account.name == "Accounts Receivable"
        ).first()
        
        sales_account = self.db.query(Account).filter(
            Account.business_id == invoice.business_id,
            Account.name == "Sales Revenue"
        ).first()
        
        if not receivable_account or not sales_account:
            return
        
        # Debit Accounts Receivable
        debit_entry = LedgerEntry(
            transaction_date=invoice.invoice_date,
            description=f"Invoice {invoice.invoice_number}",
            debit=invoice.total_amount,
            credit=Decimal("0"),
            account_id=receivable_account.id,
            customer_id=invoice.customer_id,
            sales_invoice_id=invoice.id,
            branch_id=invoice.branch_id
        )
        self.db.add(debit_entry)
        
        # Credit Sales Revenue
        credit_entry = LedgerEntry(
            transaction_date=invoice.invoice_date,
            description=f"Invoice {invoice.invoice_number}",
            debit=Decimal("0"),
            credit=invoice.sub_total,
            account_id=sales_account.id,
            customer_id=invoice.customer_id,
            sales_invoice_id=invoice.id,
            branch_id=invoice.branch_id
        )
        self.db.add(credit_entry)
        
        # Credit VAT Payable if applicable
        if invoice.vat_amount > 0:
            vat_account = self.db.query(Account).filter(
                Account.business_id == invoice.business_id,
                Account.name == "VAT Payable"
            ).first()
            
            if vat_account:
                vat_entry = LedgerEntry(
                    transaction_date=invoice.invoice_date,
                    description=f"VAT for Invoice {invoice.invoice_number}",
                    debit=Decimal("0"),
                    credit=invoice.vat_amount,
                    account_id=vat_account.id,
                    customer_id=invoice.customer_id,
                    sales_invoice_id=invoice.id,
                    branch_id=invoice.branch_id
                )
                self.db.add(vat_entry)
    
    def record_payment(self, invoice_id: int, payment_data: dict, business_id: int) -> SalesInvoice:
        invoice = self.get_by_id(invoice_id, business_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        amount = payment_data["amount"]
        payment_account_id = payment_data["payment_account_id"]
        payment_date = payment_data["payment_date"]
        
        # Update invoice
        invoice.paid_amount += amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "Paid"
        elif invoice.paid_amount > 0:
            invoice.status = "Partial"
        
        # Get accounts
        cash_account = self.db.query(Account).get(payment_account_id)
        receivable_account = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.name == "Accounts Receivable"
        ).first()
        
        if cash_account and receivable_account:
            # Debit Cash/Bank
            debit_entry = LedgerEntry(
                transaction_date=payment_date,
                description=f"Payment for Invoice {invoice.invoice_number}",
                debit=amount,
                credit=Decimal("0"),
                account_id=cash_account.id,
                customer_id=invoice.customer_id,
                sales_invoice_id=invoice.id,
                branch_id=invoice.branch_id
            )
            self.db.add(debit_entry)
            
            # Credit Accounts Receivable
            credit_entry = LedgerEntry(
                transaction_date=payment_date,
                description=f"Payment for Invoice {invoice.invoice_number}",
                debit=Decimal("0"),
                credit=amount,
                account_id=receivable_account.id,
                customer_id=invoice.customer_id,
                sales_invoice_id=invoice.id,
                branch_id=invoice.branch_id
            )
            self.db.add(credit_entry)
        
        self.db.flush()
        return invoice
    
    def write_off(self, invoice_id: int, business_id: int, write_off_date: date) -> SalesInvoice:
        """Write off an unpaid invoice as bad debt"""
        invoice = self.get_by_id(invoice_id, business_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        remaining = invoice.total_amount - invoice.paid_amount
        if remaining <= 0:
            raise ValueError("Invoice already paid in full")
        
        invoice.status = "Written Off"
        
        # Get accounts
        receivable_account = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.name == "Accounts Receivable"
        ).first()
        
        bad_debt_account = self.db.query(Account).filter(
            Account.business_id == business_id,
            Account.name == "Operating Expenses"
        ).first()
        
        if receivable_account and bad_debt_account:
            # Debit Bad Debt Expense
            debit_entry = LedgerEntry(
                transaction_date=write_off_date,
                description=f"Bad debt write-off for Invoice {invoice.invoice_number}",
                debit=remaining,
                credit=Decimal("0"),
                account_id=bad_debt_account.id,
                customer_id=invoice.customer_id,
                sales_invoice_id=invoice.id,
                branch_id=invoice.branch_id
            )
            self.db.add(debit_entry)
            
            # Credit Accounts Receivable
            credit_entry = LedgerEntry(
                transaction_date=write_off_date,
                description=f"Bad debt write-off for Invoice {invoice.invoice_number}",
                debit=Decimal("0"),
                credit=remaining,
                account_id=receivable_account.id,
                customer_id=invoice.customer_id,
                sales_invoice_id=invoice.id,
                branch_id=invoice.branch_id
            )
            self.db.add(credit_entry)
        
        self.db.flush()
        return invoice


class CreditNoteService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, credit_note_id: int, business_id: int, branch_id: int = None) -> Optional[CreditNote]:
        query = self.db.query(CreditNote).options(
            joinedload(CreditNote.items).joinedload(CreditNoteItem.product),
            joinedload(CreditNote.customer)
        ).filter(
            CreditNote.id == credit_note_id,
            CreditNote.business_id == business_id
        )
        if branch_id:
            query = query.filter(CreditNote.branch_id == branch_id)
        return query.first()
    
    def get_by_branch(self, branch_id: int, business_id: int) -> List[CreditNote]:
        return self.db.query(CreditNote).options(
            joinedload(CreditNote.customer)
        ).filter(
            CreditNote.business_id == business_id,
            CreditNote.branch_id == branch_id
        ).order_by(CreditNote.created_at.desc()).all()
    
    def get_next_number(self, business_id: int) -> str:
        last_cn = self.db.query(CreditNote).filter(
            CreditNote.business_id == business_id
        ).order_by(CreditNote.id.desc()).first()
        
        if last_cn:
            try:
                num = int(last_cn.credit_note_number.replace("CN-", ""))
                return f"CN-{num + 1:05d}"
            except ValueError:
                pass
        
        return "CN-00001"
    
    def create_for_invoice(self, original_invoice: SalesInvoice, items_to_return: List[dict], credit_note_date: date) -> CreditNote:
        """Create credit note for invoice return"""
        total_amount = sum(item["quantity"] * item["price"] for item in items_to_return)
        
        credit_note = CreditNote(
            credit_note_number=self.get_next_number(original_invoice.business_id),
            credit_note_date=credit_note_date,
            total_amount=total_amount,
            reason="Invoice Return",
            customer_id=original_invoice.customer_id,
            business_id=original_invoice.business_id,
            branch_id=original_invoice.branch_id
        )
        self.db.add(credit_note)
        self.db.flush()
        
        for item_data in items_to_return:
            cn_item = CreditNoteItem(
                credit_note_id=credit_note.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                price=item_data["price"]
            )
            self.db.add(cn_item)
            
            # Update product stock
            product = self.db.query(Product).get(item_data["product_id"])
            if product:
                product.stock_quantity += item_data["quantity"]
            
            # Update returned quantity on original item
            orig_item = self.db.query(SalesInvoiceItem).get(item_data["original_item_id"])
            if orig_item:
                orig_item.returned_quantity += item_data["quantity"]
        
        self.db.flush()
        return credit_note
