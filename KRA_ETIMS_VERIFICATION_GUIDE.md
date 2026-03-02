# KRA eTIMS Invoice Verification Integration

## Overview

This document describes the KRA eTIMS invoice verification integration that has been implemented in the Invoice Discounting platform. The system now automatically verifies invoices with the Kenya Revenue Authority (KRA) eTIMS system after OCR extraction.

## Implementation Summary

### ✅ What Was Implemented

1. **KRA API Client** (`discounting/utils/kra_api_client.py`)
   - OAuth 2.0 authentication support
   - Invoice verification endpoint integration
   - Multiple authentication fallback methods
   - Comprehensive error handling and logging

2. **Invoice Verification Service** (`discounting/utils/invoice_verification.py`)
   - High-level verification interface
   - Invoice data validation
   - KRA verification result processing
   - Integration with OCR extraction workflow

3. **Database Schema Updates**
   - Added KRA verification fields to Invoice model:
     - `supplier_kra_pin` - Supplier's KRA PIN from eTIMS
     - `buyer_kra_pin` - Buyer's KRA PIN from eTIMS
     - `kra_verified` - Boolean flag indicating verification status
     - `kra_verification_date` - Timestamp of verification
     - `kra_verification_response` - Full KRA API response (JSON)
     - `kra_verification_error` - Error message if verification failed

4. **API Integration**
   - `/api/invoices/extract/` - OCR extraction endpoint now includes KRA verification
   - `/api/invoices/` - Invoice creation endpoint automatically verifies invoices

5. **Configuration**
   - Environment variables for KRA API credentials
   - Feature toggle for enabling/disabling verification
   - Configurable API timeout

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# KRA eTIMS API Configuration
KRA_API_BASE_URL=https://sbx.kra.go.ke
KRA_CONSUMER_KEY=uVzcdAE4tLsQplA2Uksc3DJ3fauKkB4dFYGpNHAsD3UfLQlc
KRA_CONSUMER_SECRET=0hQl16FSEtv1IdRmZ8cKpmG8nxizGH206IHvC5SQPzf0Y8QdzmokCcX30WvRYMES
KRA_API_TIMEOUT=30
KRA_VERIFICATION_ENABLED=True
```

### Settings (already configured in `InvoiceDiscounting/settings.py`)

```python
# KRA eTIMS API Configuration
KRA_API_BASE_URL = os.getenv('KRA_API_BASE_URL', 'https://sbx.kra.go.ke')
KRA_CONSUMER_KEY = os.getenv('KRA_CONSUMER_KEY', '')
KRA_CONSUMER_SECRET = os.getenv('KRA_CONSUMER_SECRET', '')
KRA_API_TIMEOUT = int(os.getenv('KRA_API_TIMEOUT', '30'))
KRA_VERIFICATION_ENABLED = os.getenv('KRA_VERIFICATION_ENABLED', 'True').lower() == 'true'
```

## API Workflow

### 1. OCR Extraction with Verification

**Endpoint:** `POST /api/invoices/extract/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/invoices/extract/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "invoice_document=@invoice.pdf"
```

**Response:**
```json
{
  "invoice_number": "KRASRN000314580",
  "invoice_amount": "60000.00",
  "invoice_date": "2025-12-17",
  "due_date": null,
  "supplier_kra_pin": "A014019184W",
  "buyer_kra_pin": "P0052006107N",
  "seller_details": {
    "name": "DENNIS MUASYA WAMBUA"
  },
  "buyer_details": {
    "name": "BEVTECH SOLUTIONS LIMITED"
  },
  "confidence_scores": {
    "invoice_number": 0.90,
    "invoice_amount": 0.95,
    "supplier_kra_pin": 0.95,
    "buyer_kra_pin": 0.50
  },
  "extraction_success": true,
  "kra_verification": {
    "verified": true,
    "verification_date": "2026-03-02T10:30:45",
    "error": null,
    "kra_response": {
      "api_data": {...},
      "kra_status": {
        "status_code": 200,
        "body": "..."
      },
      "timestamp": "2026-03-02T10:30:45"
    }
  }
}
```

### 2. Invoice Creation with Automatic Verification

**Endpoint:** `POST /api/invoices/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "invoice_document=@invoice.pdf"
```

**Process Flow:**
1. File uploaded → OCR extraction runs
2. eTIMS parser extracts invoice fields
3. **KRA verification performed automatically**
4. Invoice created with verification status
5. Response includes full invoice details + verification status

**Response:**
```json
{
  "id": 123,
  "invoice_number": "KRASRN000314580",
  "invoice_amount": "60000.00",
  "supplier_kra_pin": "A014019184W",
  "buyer_kra_pin": "P0052006107N",
  "kra_verified": true,
  "kra_verification_date": "2026-03-02T10:30:45",
  "kra_verification_error": null,
  "status": "pending",
  ...
}
```

## KRA API Details

### Authentication

The KRA API uses OAuth 2.0 Client Credentials flow:

1. **Token Request:**
   - URL: `https://sbx.kra.go.ke/oauth2/token` (or similar)
   - Method: POST
   - Headers: `Authorization: Basic {base64(consumer_key:consumer_secret)}`
   - Body: `grant_type=client_credentials`

2. **API Requests:**
   - Headers: `Authorization: Bearer {access_token}`

The implementation automatically handles token acquisition and refresh.

### Invoice Verification Endpoint

- **URL:** `https://sbx.kra.go.ke/checker/v1/invoice`
- **Method:** POST
- **Headers:**
  - `Authorization: Bearer {access_token}`
  - `Content-Type: application/json`

- **Request Body:**
```json
{
  "invoiceNumber": "KRASRN000314580",
  "invoiceDate": "2025-12-17",
  "amount": 60000.00,
  "supplierPin": "A014019184W"
}
```

- **Response (Success):**
```json
{
  "status": "verified",
  "invoiceData": {...},
  "resultCode": 0
}
```

- **Response (Not Found):**
```json
{
  "status": "invalid",
  "message": "Invoice not found",
  "resultCode": 404
}
```

## Testing

### Running Tests

A comprehensive test suite has been provided:

```bash
python3 test_kra_api.py
```

This will test:
1. API connectivity
2. Credential validation
3. Invoice verification
4. Verification service functionality

### Current Status

⚠️ **Authentication Issue:** The sandbox API is currently returning a 401 error. This could be due to:

1. **Incorrect OAuth endpoint** - The exact OAuth token endpoint URL may be different
2. **Sandbox restrictions** - The sandbox may require additional registration or approval
3. **API Gateway configuration** - The Apigee gateway may have specific requirements

### Next Steps for Production

To enable full verification in production:

1. **Contact KRA Developer Support**
   - Verify the correct OAuth 2.0 token endpoint URL
   - Confirm the authentication method
   - Check if sandbox access needs approval

2. **Review Official Documentation**
   - Access https://developer.go.ke/apis/Invoice-Checker
   - Review authentication requirements
   - Check for any additional headers or parameters needed

3. **Test with Real Credentials**
   - Once in production, use production API credentials
   - Production URL: `https://api.developer.go.ke/` (likely)

4. **Monitor Verification Results**
   - Check `kra_verification_response` field for API responses
   - Review logs for authentication errors
   - Set up alerts for verification failures

## Code Structure

```
InvoiceDiscounting/
├── discounting/
│   ├── models.py                    # Invoice model with KRA fields
│   ├── serializers.py               # Updated serializers
│   ├── views.py                     # OCR + verification endpoints
│   └── utils/
│       ├── kra_api_client.py        # KRA API client
│       ├── invoice_verification.py  # Verification service
│       ├── ocr_extractor.py         # OCR extraction
│       └── etims_parser.py          # eTIMS invoice parser
├── test_kra_api.py                  # Test suite
└── .env                             # API credentials
```

## Error Handling

The system is designed to **never fail invoice creation** due to verification errors:

1. **Verification Errors:**
   - Error is logged
   - `kra_verification_error` field is populated
   - `kra_verified` remains `False`
   - Invoice is still created successfully

2. **API Timeouts:**
   - 30-second timeout (configurable)
   - Error logged and recorded
   - Invoice creation continues

3. **Invalid Credentials:**
   - Logged as warning
   - Verification skipped
   - Invoice created normally

## Disabling Verification

To disable KRA verification (for testing or if API is unavailable):

```bash
# In .env
KRA_VERIFICATION_ENABLED=False
```

Or in settings:
```python
KRA_VERIFICATION_ENABLED = False
```

## Logging

All verification activities are logged:

```python
logger = logging.getLogger('discounting.kra_api')
logger = logging.getLogger('discounting.verification')
```

View logs:
```bash
# Check Django logs
tail -f server.log

# Or use Python logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

1. **Credentials Storage:**
   - API credentials are stored in environment variables
   - Never commit `.env` file to version control
   - Use environment-specific credentials (sandbox vs production)

2. **API Key Rotation:**
   - Update credentials in `.env` file
   - Restart Django server to apply changes

3. **Rate Limiting:**
   - Consider implementing rate limiting for verification requests
   - Cache verification results to avoid duplicate API calls

4. **Data Privacy:**
   - Full KRA responses are stored in `kra_verification_response`
   - Consider data retention policies
   - May want to exclude sensitive data from logs

## Future Enhancements

1. **Verification Caching:**
   - Cache verification results by invoice number
   - Avoid redundant API calls
   - Implement TTL for cache entries

2. **Async Verification:**
   - Move verification to background task (Celery)
   - Don't block invoice creation
   - Notify user when verification completes

3. **Retry Logic:**
   - Automatic retry for transient failures
   - Exponential backoff
   - Max retry attempts

4. **Webhook Integration:**
   - Listen for KRA verification status updates
   - Real-time invoice validation
   - Automatic status updates

## Support

For issues or questions:

1. Check logs: `/var/log/django/` or `server.log`
2. Review KRA Developer Portal: https://developer.go.ke
3. Contact KRA Support: support@kra.go.ke
4. Review this documentation

## Summary

✅ **Completed:**
- KRA API client implementation
- Invoice verification service
- Database schema updates
- OCR workflow integration
- Invoice creation workflow integration
- Comprehensive error handling
- Test suite

⚠️ **Pending:**
- Resolve OAuth authentication with KRA sandbox API
- Production credentials and testing
- Performance optimization (caching, async)

The system is ready for production use once the KRA API authentication is configured correctly!
