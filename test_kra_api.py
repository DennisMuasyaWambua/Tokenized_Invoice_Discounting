"""
Test script for KRA eTIMS API integration.
Run this to verify that the KRA API client is working correctly.
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvoiceDiscounting.settings')
django.setup()

from discounting.utils.kra_api_client import KRAAPIClient
from discounting.utils.invoice_verification import InvoiceVerificationService


def test_kra_api_connectivity():
    """Test basic connectivity to KRA API."""
    print("\n" + "="*60)
    print("Testing KRA eTIMS API Connectivity")
    print("="*60)

    client = KRAAPIClient()

    print(f"\nAPI Configuration:")
    print(f"  Base URL: {client.base_url}")
    print(f"  Consumer Key: {client.consumer_key[:20]}..." if client.consumer_key else "  Consumer Key: Not set")
    print(f"  Consumer Secret: {'*' * 20}..." if client.consumer_secret else "  Consumer Secret: Not set")

    # Test health check
    print("\n1. Testing API health check...")
    health_result = client.health_check()

    print(f"   API Accessible: {health_result['api_accessible']}")
    print(f"   Credentials Valid: {health_result['credentials_valid']}")
    if health_result.get('error'):
        print(f"   Error: {health_result['error']}")

    return health_result


def test_invoice_verification():
    """Test invoice verification with sample data."""
    print("\n" + "="*60)
    print("Testing Invoice Verification")
    print("="*60)

    client = KRAAPIClient()

    # Test with sample invoice number
    test_invoice_number = "KRASRN000314580"  # Sample from your OCR tests
    test_amount = 60000.00
    test_date = "2025-12-17"
    test_supplier_pin = "A014019184W"

    print(f"\nVerifying sample invoice:")
    print(f"  Invoice Number: {test_invoice_number}")
    print(f"  Amount: KES {test_amount}")
    print(f"  Date: {test_date}")
    print(f"  Supplier PIN: {test_supplier_pin}")

    result = client.verify_invoice(
        invoice_number=test_invoice_number,
        invoice_date=test_date,
        amount=test_amount,
        supplier_pin=test_supplier_pin
    )

    print(f"\nVerification Result:")
    print(f"  Success: {result['success']}")
    print(f"  Verified: {result['verified']}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    if result.get('kra_response'):
        print(f"  KRA Response Status: {result['kra_response'].get('status_code')}")

    return result


def test_verification_service():
    """Test the invoice verification service."""
    print("\n" + "="*60)
    print("Testing Invoice Verification Service")
    print("="*60)

    service = InvoiceVerificationService()

    print(f"\nService Configuration:")
    print(f"  Verification Enabled: {service.verification_enabled}")

    # Test validation
    print("\n1. Testing invoice data validation...")
    sample_data = {
        'invoice_number': 'KRASRN000314580',
        'invoice_amount': 60000.00,
        'supplier_kra_pin': 'A014019184W',
        'buyer_kra_pin': 'P0052006107N'
    }

    validation_result = service.validate_invoice_data(sample_data)
    print(f"   Valid: {validation_result['valid']}")
    if validation_result['errors']:
        print(f"   Errors: {validation_result['errors']}")
    if validation_result['warnings']:
        print(f"   Warnings: {validation_result['warnings']}")

    # Test verification
    print("\n2. Testing invoice verification...")
    verification_result = service.verify_invoice_with_kra(
        invoice_number=sample_data['invoice_number'],
        amount=sample_data['invoice_amount'],
        supplier_pin=sample_data['supplier_kra_pin']
    )

    print(f"   Verified: {verification_result['verified']}")
    if verification_result.get('error'):
        print(f"   Error: {verification_result['error']}")

    return verification_result


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("KRA eTIMS API INTEGRATION TEST SUITE")
    print("="*60)

    try:
        # Test 1: API Connectivity
        connectivity_result = test_kra_api_connectivity()

        # Test 2: Invoice Verification (only if credentials are valid)
        if connectivity_result.get('credentials_valid'):
            test_invoice_verification()
        else:
            print("\n⚠️  Skipping invoice verification test - credentials not valid")

        # Test 3: Verification Service
        test_verification_service()

        print("\n" + "="*60)
        print("TEST SUITE COMPLETED")
        print("="*60)

        print("\n📋 Summary:")
        print("  ✓ API client initialized successfully")
        print("  ✓ Verification service initialized successfully")

        if connectivity_result.get('api_accessible'):
            print("  ✓ KRA API is accessible")
        else:
            print("  ✗ KRA API is not accessible")

        if connectivity_result.get('credentials_valid'):
            print("  ✓ API credentials are valid")
        else:
            print("  ✗ API credentials are invalid or authentication failed")

        print("\n💡 Next Steps:")
        if not connectivity_result.get('credentials_valid'):
            print("  1. Verify your KRA API credentials in .env file")
            print("  2. Check if the sandbox API is accessible")
            print("  3. Review the API documentation for authentication requirements")
        else:
            print("  1. Test with real invoice data")
            print("  2. Monitor verification responses in production")
            print("  3. Set up error alerting for failed verifications")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
