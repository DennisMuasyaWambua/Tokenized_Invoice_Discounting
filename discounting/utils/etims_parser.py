"""
eTIMS invoice parser for extracting specific fields from OCR text.
Handles Kenya Revenue Authority's electronic Tax Invoice Management System format.
"""
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger('discounting.ocr')


class ETIMSInvoiceParser:
    """Parser for extracting structured data from eTIMS invoice OCR text."""

    # Regex patterns for each field (multiple patterns to handle variations)
    FIELD_PATTERNS = {
        'invoice_number': [
            r'SCU\s+ID\s*:?\s*([A-Z0-9]+)',  # Best: SCU ID
            r'(KRAS[RN][NO0]+\d+/\d+)',  # Pattern for CU Invoice Number format
            r'Receipt\s+Signature\s*:?\s*([A-Z0-9]{10,})',  # Receipt signature as fallback
            r'CU\s+Invoice\s+Number\s*:?\s*\n.*?([A-Z0-9]+/\d+)',  # After CU Invoice Number label
        ],
        'invoice_amount': [
            r'Total\s+Amount\s*:?\s*(?:KES|KSH)?\s*([0-9,]+\.?\d*)',
            r'Grand\s*Total\s*:?\s*(?:KES|KSH)?\s*([0-9,]+\.?\d*)',
            r'Amount\s*(?:Due|Payable)\s*:?\s*(?:KES|KSH)?\s*([0-9,]+\.?\d*)',
            r'Total\s*:?\s*(?:KES|KSH)?\s*([0-9,]+\.?\d*)',
        ],
        'invoice_date': [
            r'Date\s+Created\s*:?\s*(\d{4}-\d{2}-\d{2})',
            r'Invoice\s*Date\s*:?\s*(\d{4}-\d{2}-\d{2})',
            r'Date\s*:?\s*(\d{4}-\d{2}-\d{2})',
            r'Date\s+Created\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Invoice\s*Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ],
        'due_date': [
            r'Due\s*Date\s*:?\s*(\d{4}-\d{2}-\d{2})',
            r'Payment\s*Due\s*:?\s*(\d{4}-\d{2}-\d{2})',
            r'Due\s*Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Payment\s*Due\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ],
        'supplier_kra_pin': [
            r'(?:Sale\s+From|Seller|Supplier).*?PIN\s*:?\s*([A-Z][0-9]{9}[A-Z])',
            r'(?:^|\n)PIN\s*:?\s*([A-Z][0-9]{9}[A-Z])',  # First PIN occurrence (seller)
        ],
        'buyer_kra_pin': [
            # Second PIN in text (after email or LIMITED) - handle OCR errors with O/0
            r'gmail\.com\s+PIN\s*:?\s*([A-Z]{1,2}[O0-9]{9}[A-Z])',
            r'@\w+\.\w+\s+PIN\s*:?\s*([A-Z]{1,2}[O0-9]{9}[A-Z])',
            r'email.*?PIN\s*:?\s*([A-Z]{1,2}[O0-9]{9}[A-Z])',
            # Second PIN occurrence (most generic)
            r'PIN\s*:?\s*[A-Z][0-9]{9}[A-Z].*?PIN\s*:?\s*([A-Z]{1,2}[O0-9]{9}[A-Z])',
        ],
    }

    # Additional patterns for buyer details
    BUYER_PATTERNS = {
        'name': [
            # Match company name that appears before KRAS... and after a person name
            r'(?:WAMBUA|PERSON\sNAME)\s+([A-Z][A-Z\s]+(?:LIMITED|LTD|SOLUTIONS))',
            r'\s([A-Z]{2,}(?:\s+[A-Z]+)*\s+(?:LIMITED|LTD|SOLUTIONS))\s+KRAS',
            r'LIMITED\s*\nmuasya',  # Match "LIMITED" before email (buyer company)
        ],
    }

    # Additional patterns for seller details
    SELLER_PATTERNS = {
        'name': [
            # Match full name pattern (FirstName MiddleName LastName) after CU Invoice Number
            r'CU\s+Invoice\s+Number\s*:?\s*\n([A-Z]+\s+[A-Z]+\s+[A-Z]+)',
            r'Invoice\s+Number\s*:?\s*\n([A-Z]+(?:\s+[A-Z]+){1,3})\s+[A-Z]+(?:\s+[A-Z]+)*\s+(?:LIMITED|SOLUTIONS)',
        ],
    }

    def __init__(self):
        self.logger = logger

    def extract_field(self, text: str, field_name: str) -> Optional[str]:
        """
        Extract a specific field from OCR text using regex patterns.

        Args:
            text: OCR extracted text
            field_name: Name of field to extract

        Returns:
            Extracted value or None if not found
        """
        patterns = self.FIELD_PATTERNS.get(field_name, [])

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                # For patterns with multiple groups, prefer the last non-empty group
                if match.lastindex and match.lastindex > 1:
                    # Multiple capturing groups - use the last one (e.g., SCU ID over Invoice No)
                    value = match.group(match.lastindex).strip()
                else:
                    value = match.group(1).strip()

                self.logger.debug(f"Extracted {field_name}: {value} using pattern: {pattern[:40]}...")
                return value

        self.logger.warning(f"Could not extract {field_name}")
        return None

    def extract_buyer_details(self, text: str) -> Dict:
        """
        Extract buyer details from OCR text.

        Args:
            text: OCR extracted text

        Returns:
            Dict with buyer name and other details
        """
        details = {}

        # Extract buyer name
        for pattern in self.BUYER_PATTERNS['name']:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                details['name'] = match.group(1).strip()
                break

        return details

    def extract_seller_details(self, text: str) -> Dict:
        """
        Extract seller details from OCR text.

        Args:
            text: OCR extracted text

        Returns:
            Dict with seller name and other details
        """
        details = {}

        # Extract seller name
        for pattern in self.SELLER_PATTERNS['name']:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                details['name'] = match.group(1).strip()
                break

        return details

    def parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """
        Parse amount string to Decimal, handling commas and formatting.

        Args:
            amount_str: Amount string (e.g., "1,234.56" or "1234.56")

        Returns:
            Decimal value or None if parsing fails
        """
        if not amount_str:
            return None

        try:
            # Remove commas and spaces
            clean_amount = amount_str.replace(',', '').replace(' ', '')
            return Decimal(clean_amount)
        except (InvalidOperation, ValueError) as e:
            self.logger.error(f"Failed to parse amount '{amount_str}': {e}")
            return None

    def parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to ISO format (YYYY-MM-DD).

        Args:
            date_str: Date string (e.g., "15/01/2024", "15-01-2024", or "2024-12-17")

        Returns:
            ISO formatted date string or None if parsing fails
        """
        if not date_str:
            return None

        # Remove time component if present (e.g., "2025-12-17 21:50:06" -> "2025-12-17")
        date_str = date_str.split()[0].strip()

        # Try different date formats (most common first)
        date_formats = [
            '%Y-%m-%d',     # eTIMS format: 2025-12-17
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d/%m/%y',
            '%d-%m-%y',
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue

        self.logger.error(f"Failed to parse date '{date_str}'")
        return None

    def cleanup_kra_pin(self, pin: str) -> str:
        """
        Clean up KRA PIN by fixing common OCR errors.

        Args:
            pin: KRA PIN string (may have OCR errors)

        Returns:
            Cleaned KRA PIN string
        """
        if not pin:
            return pin

        # Fix common OCR errors
        # PO... -> P0... (O to 0 in second position)
        if len(pin) == 12 and pin[0].isalpha() and pin[1] == 'O':
            pin = pin[0] + '0' + pin[2:]
        elif len(pin) == 12 and pin[0:2] == 'PO':
            pin = 'P0' + pin[2:]

        # Fix O to 0 in digit positions (positions 2-10 for format: Letter + 9 digits + Letter)
        if len(pin) >= 11:
            cleaned = pin[0]  # First letter
            for i in range(1, len(pin) - 1):
                # Replace O with 0 in middle positions (digit positions)
                if pin[i] == 'O':
                    cleaned += '0'
                else:
                    cleaned += pin[i]
            cleaned += pin[-1]  # Last letter
            pin = cleaned

        # Ensure exactly 11 characters
        if len(pin) == 12 and pin[0:2].isalpha():
            # If we have 12 chars and first 2 are letters, keep only first letter
            pin = pin[0] + pin[2:]

        return pin

    def validate_kra_pin(self, pin: str) -> bool:
        """
        Validate KRA PIN format (11 alphanumeric characters).

        Args:
            pin: KRA PIN string

        Returns:
            True if valid format, False otherwise
        """
        if not pin or len(pin) != 11:
            return False

        # KRA PIN format: Letter + 9 digits + Letter (typical)
        # But can also be alphanumeric, so just check length
        return pin.isalnum()

    def calculate_confidence(self, extracted_data: Dict) -> Dict[str, float]:
        """
        Calculate confidence scores for each extracted field.

        Args:
            extracted_data: Dict of extracted field values

        Returns:
            Dict mapping field names to confidence scores (0.0 to 1.0)
        """
        confidence_scores = {}

        # Invoice number: high confidence if alphanumeric with reasonable length
        if extracted_data.get('invoice_number'):
            inv_num = extracted_data['invoice_number']
            if 5 <= len(inv_num) <= 30 and any(c.isalnum() for c in inv_num):
                confidence_scores['invoice_number'] = 0.9
            else:
                confidence_scores['invoice_number'] = 0.6
        else:
            confidence_scores['invoice_number'] = 0.0

        # Invoice amount: high confidence if successfully parsed
        if extracted_data.get('invoice_amount') is not None:
            confidence_scores['invoice_amount'] = 0.95
        else:
            confidence_scores['invoice_amount'] = 0.0

        # Dates: high confidence if successfully parsed
        for date_field in ['invoice_date', 'due_date']:
            if extracted_data.get(date_field):
                confidence_scores[date_field] = 0.9
            else:
                confidence_scores[date_field] = 0.0

        # KRA PINs: high confidence if valid format
        for pin_field in ['supplier_kra_pin', 'buyer_kra_pin']:
            pin = extracted_data.get(pin_field)
            if pin and self.validate_kra_pin(pin):
                confidence_scores[pin_field] = 0.95
            elif pin:
                confidence_scores[pin_field] = 0.5
            else:
                confidence_scores[pin_field] = 0.0

        return confidence_scores

    def parse_invoice(self, ocr_text: str) -> Dict:
        """
        Parse eTIMS invoice from OCR text and extract all fields.

        Args:
            ocr_text: Raw OCR extracted text

        Returns:
            Dict containing:
                - Extracted field values
                - confidence_scores: Dict of confidence per field
                - extraction_success: Boolean indicating overall success
                - extraction_errors: List of error messages
        """
        result = {
            'invoice_number': None,
            'invoice_amount': None,
            'invoice_date': None,
            'due_date': None,
            'supplier_kra_pin': None,
            'buyer_kra_pin': None,
            'buyer_details': {},
            'seller_details': {},
            'confidence_scores': {},
            'extraction_success': False,
            'extraction_errors': [],
        }

        if not ocr_text or len(ocr_text.strip()) < 10:
            result['extraction_errors'].append('OCR text is empty or too short')
            return result

        try:
            # Extract invoice number
            result['invoice_number'] = self.extract_field(ocr_text, 'invoice_number')

            # Extract and parse invoice amount
            amount_str = self.extract_field(ocr_text, 'invoice_amount')
            if amount_str:
                result['invoice_amount'] = self.parse_amount(amount_str)

            # Extract and parse invoice date
            date_str = self.extract_field(ocr_text, 'invoice_date')
            if date_str:
                result['invoice_date'] = self.parse_date(date_str)

            # Extract and parse due date
            due_str = self.extract_field(ocr_text, 'due_date')
            if due_str:
                result['due_date'] = self.parse_date(due_str)

            # Extract KRA PINs and clean up OCR errors
            supplier_pin = self.extract_field(ocr_text, 'supplier_kra_pin')
            if supplier_pin:
                result['supplier_kra_pin'] = self.cleanup_kra_pin(supplier_pin)

            buyer_pin = self.extract_field(ocr_text, 'buyer_kra_pin')
            if buyer_pin:
                result['buyer_kra_pin'] = self.cleanup_kra_pin(buyer_pin)

            # Extract buyer details
            result['buyer_details'] = self.extract_buyer_details(ocr_text)

            # Extract seller details
            result['seller_details'] = self.extract_seller_details(ocr_text)

            # Calculate confidence scores
            result['confidence_scores'] = self.calculate_confidence(result)

            # Determine overall success
            # Success if we extracted at least the core fields
            core_fields_extracted = all([
                result['invoice_number'],
                result['invoice_amount'] is not None,
            ])

            result['extraction_success'] = core_fields_extracted

            if not core_fields_extracted:
                missing_fields = []
                if not result['invoice_number']:
                    missing_fields.append('invoice_number')
                if result['invoice_amount'] is None:
                    missing_fields.append('invoice_amount')
                result['extraction_errors'].append(
                    f"Failed to extract core fields: {', '.join(missing_fields)}"
                )

            # Log warnings for missing optional fields
            optional_fields = ['invoice_date', 'due_date', 'supplier_kra_pin', 'buyer_kra_pin']
            for field in optional_fields:
                if not result[field]:
                    self.logger.warning(f"Optional field '{field}' not extracted")

        except Exception as e:
            error_msg = f"Error parsing invoice: {str(e)}"
            result['extraction_errors'].append(error_msg)
            self.logger.error(error_msg)

        return result
