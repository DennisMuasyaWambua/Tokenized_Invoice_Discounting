"""
Invoice verification utilities.
Handles KRA eTIMS verification and invoice validation.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from django.conf import settings
from .kra_api_client import KRAAPIClient

logger = logging.getLogger('discounting.verification')


class InvoiceVerificationService:
    """
    Service for verifying invoices with KRA eTIMS system.
    """

    def __init__(self):
        self.kra_client = KRAAPIClient()
        self.verification_enabled = getattr(settings, 'KRA_VERIFICATION_ENABLED', True)

    def verify_invoice_with_kra(
        self,
        invoice_number: str,
        invoice_date: Optional[str] = None,
        amount: Optional[float] = None,
        supplier_pin: Optional[str] = None
    ) -> Dict:
        """
        Verify invoice with KRA eTIMS API.

        Args:
            invoice_number: Invoice/SCU ID from eTIMS
            invoice_date: Invoice date (YYYY-MM-DD format)
            amount: Invoice amount
            supplier_pin: Supplier KRA PIN

        Returns:
            Dict containing:
                - verified: Boolean indicating if invoice is valid
                - kra_response: Full KRA API response data
                - error: Error message if verification failed
                - verification_date: Timestamp of verification
        """
        result = {
            'verified': False,
            'kra_response': None,
            'error': None,
            'verification_date': datetime.now()
        }

        # Check if verification is enabled
        if not self.verification_enabled:
            logger.info("KRA verification is disabled")
            result['error'] = 'KRA verification is disabled'
            result['verified'] = None  # Unknown status
            return result

        # Validate inputs
        if not invoice_number:
            result['error'] = 'Invoice number is required for verification'
            logger.warning("Attempted verification without invoice number")
            return result

        try:
            # Call KRA API
            logger.info(f"Initiating KRA verification for invoice: {invoice_number}")
            kra_result = self.kra_client.verify_invoice(
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                amount=amount,
                supplier_pin=supplier_pin
            )

            # Process KRA response
            if kra_result.get('success'):
                result['verified'] = kra_result.get('verified', False)
                result['kra_response'] = kra_result.get('data', {})

                if result['verified']:
                    logger.info(f"Invoice {invoice_number} verified successfully with KRA")
                else:
                    result['error'] = kra_result.get('error', 'Invoice not verified by KRA')
                    logger.warning(f"Invoice {invoice_number} not verified: {result['error']}")
            else:
                result['error'] = kra_result.get('error', 'KRA API request failed')
                logger.error(f"KRA verification failed for {invoice_number}: {result['error']}")

            # Store full KRA response for debugging
            result['kra_response'] = {
                'api_data': kra_result.get('data', {}),
                'kra_status': kra_result.get('kra_response', {}),
                'timestamp': result['verification_date'].isoformat()
            }

        except Exception as e:
            result['error'] = f'Verification error: {str(e)}'
            logger.error(f"Unexpected error during KRA verification: {str(e)}", exc_info=True)

        return result

    def validate_invoice_data(self, invoice_data: Dict) -> Dict:
        """
        Validate invoice data before submission.

        Args:
            invoice_data: Dict containing invoice fields

        Returns:
            Dict with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check required fields
        required_fields = ['invoice_number', 'invoice_amount']
        for field in required_fields:
            if not invoice_data.get(field):
                validation_result['valid'] = False
                validation_result['errors'].append(f'{field} is required')

        # Validate amount
        amount = invoice_data.get('invoice_amount')
        if amount:
            try:
                amount_value = float(amount)
                if amount_value <= 0:
                    validation_result['valid'] = False
                    validation_result['errors'].append('Invoice amount must be greater than zero')
            except (ValueError, TypeError):
                validation_result['valid'] = False
                validation_result['errors'].append('Invalid invoice amount format')

        # Validate KRA PINs if provided
        supplier_pin = invoice_data.get('supplier_kra_pin')
        if supplier_pin and not self._is_valid_kra_pin(supplier_pin):
            validation_result['warnings'].append('Supplier KRA PIN format appears invalid')

        buyer_pin = invoice_data.get('buyer_kra_pin')
        if buyer_pin and not self._is_valid_kra_pin(buyer_pin):
            validation_result['warnings'].append('Buyer KRA PIN format appears invalid')

        return validation_result

    def _is_valid_kra_pin(self, pin: str) -> bool:
        """
        Validate KRA PIN format.

        Args:
            pin: KRA PIN string

        Returns:
            True if PIN format is valid
        """
        if not pin or len(pin) != 11:
            return False
        return pin.isalnum()

    def get_verification_summary(self, invoice) -> Dict:
        """
        Get a summary of the invoice verification status.

        Args:
            invoice: Invoice model instance

        Returns:
            Dict with verification summary
        """
        return {
            'invoice_number': invoice.invoice_number,
            'kra_verified': invoice.kra_verified,
            'verification_date': invoice.kra_verification_date.isoformat() if invoice.kra_verification_date else None,
            'supplier_pin': invoice.supplier_kra_pin,
            'buyer_pin': invoice.buyer_kra_pin,
            'verification_error': invoice.kra_verification_error,
            'has_verification_response': bool(invoice.kra_verification_response)
        }


def verify_invoice_after_ocr(ocr_extracted_data: Dict) -> Dict:
    """
    Convenience function to verify invoice immediately after OCR extraction.

    Args:
        ocr_extracted_data: Data extracted from OCR

    Returns:
        Dict with verification results
    """
    verifier = InvoiceVerificationService()

    invoice_number = ocr_extracted_data.get('invoice_number')
    invoice_date = ocr_extracted_data.get('invoice_date')
    amount = ocr_extracted_data.get('invoice_amount')
    supplier_pin = ocr_extracted_data.get('supplier_kra_pin')

    # Convert amount to float if it's a Decimal
    if amount:
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = None

    return verifier.verify_invoice_with_kra(
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        supplier_pin=supplier_pin
    )
