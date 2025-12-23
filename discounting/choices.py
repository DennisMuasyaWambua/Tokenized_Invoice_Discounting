# discounting/choices.py

ROLES = (
    ('financier', 'Financier'),
    ('supplier', 'Supplier'),
    ('buyer', 'Buyer'),
)

INVOICE_STATUS = (
    ('pending', 'Pending Approval'),
    ('approved', 'Approved'),
    ('funded', 'Funded'),           # Advance paid to supplier
    ('settled', 'Settled'),         # Buyer paid financier
    ('completed', 'Completed'),     # Retention released
    ('rejected', 'Rejected'),
    ('defaulted', 'Defaulted'),
)

PAYMENT_STATUS = (
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
)

CONTRACT_STATUS = (
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('terminated', 'Terminated'),
)