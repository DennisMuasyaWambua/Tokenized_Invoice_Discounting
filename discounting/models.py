from django.contrib.auth.models import AbstractUser
from django.db import models
from discounting.choices import ROLES, INVOICE_STATUS, PAYMENT_STATUS, CONTRACT_STATUS


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=100, choices=ROLES, default='buyer')
    description = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    username = models.CharField(max_length=15, blank=True)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15)
    created_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)

    # KYC fields for financiers
    company_name = models.CharField(max_length=255, blank=True, null=True)
    kra_pin = models.CharField(max_length=20, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class Contract(models.Model):
    """Agreement between a buyer (hospital) and supplier"""
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contracts_as_buyer',
        limit_choices_to={'role__short_name': 'buyer'}
    )
    supplier = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contracts_as_supplier',
        limit_choices_to={'role__short_name': 'supplier'}
    )
    contract_reference = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date_from = models.DateField()
    date_to = models.DateField()
    status = models.CharField(max_length=20, choices=CONTRACT_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.contract_reference} - {self.supplier} to {self.buyer}"


class Invoice(models.Model):
    """Invoice submitted by supplier for discounting"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='invoices')
    supplier = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoices_as_supplier'
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoices_as_buyer'
    )
    financier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices_as_financier',
        limit_choices_to={'role__short_name': 'financier'}
    )

    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_amount = models.DecimalField(max_digits=15, decimal_places=2)
    invoice_date = models.DateField()
    due_date = models.DateField()

    # Discounting terms
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # e.g., 3.50%
    advance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=85.00)  # e.g., 85%
    advance_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    retention_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    # Document storage (for the actual invoice file)
    invoice_document = models.FileField(upload_to='invoices/', null=True, blank=True)

    def __str__(self):
        return f"{self.invoice_number} - KES {self.invoice_amount}"

    def calculate_advance(self):
        """Calculate advance and retention amounts"""
        self.advance_amount = (self.invoice_amount * self.advance_rate) / 100
        self.retention_amount = self.invoice_amount - self.advance_amount
        return self.advance_amount


class Payment(models.Model):
    """Tracks all payments in the system"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')

    # Who pays whom
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    payee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_received')

    # Payment details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_type = models.CharField(max_length=30, choices=[
        ('advance', 'Advance to Supplier'),  # Financier → Supplier
        ('settlement', 'Buyer Settlement'),  # Buyer → Financier
        ('retention_release', 'Retention Release'),  # Financier → Supplier (after buyer pays)
        ('fee', 'Platform Fee'),
    ])

    # M-Pesa integration
    mpesa_transaction_id = models.CharField(max_length=50, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)

    # Blockchain/DeFi tracking (for your tokenization feature)
    blockchain_tx_hash = models.CharField(max_length=100, blank=True, null=True)
    wallet_address = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.payment_type} - KES {self.amount} ({self.status})"


class KYCDocument(models.Model):
    """KYC documents for user verification"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=30, choices=[
        ('national_id', 'National ID'),
        ('business_certificate', 'Business Certificate'),
        ('kra_certificate', 'KRA Certificate'),
    ])
    document_file = models.FileField(upload_to='kyc_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'document_type']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_document_type_display()}"