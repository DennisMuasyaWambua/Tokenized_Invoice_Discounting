# API Documentation - Invoice Discounting Platform

## 📚 API Documentation URLs

Your API is now fully documented with interactive Swagger UI and ReDoc interfaces:

### Swagger UI (Interactive)
```
http://localhost:8000/api/docs/
```
- Interactive API explorer
- Try out endpoints directly from browser
- See request/response examples
- Test authentication

### ReDoc (Clean Documentation)
```
http://localhost:8000/api/redoc/
```
- Clean, three-panel documentation
- Easy navigation
- Mobile-friendly
- Print-friendly

### OpenAPI Schema (Raw)
```
http://localhost:8000/api/schema/
```
- Download raw OpenAPI 3.0 schema
- Use for code generation
- Import into Postman/Insomnia

## 🎯 New OCR Endpoints Documented

### 1. Invoice OCR Extraction
**Endpoint:** `POST /api/invoices/extract/`

**Purpose:** Extract invoice data from uploaded PDF/image files using OCR

**Request:**
- Content-Type: multipart/form-data
- Body: `invoice_document` (file) - PDF, JPG, or PNG file (max 10MB)

**Response Example:**
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
    "invoice_date": 0.90,
    "supplier_kra_pin": 0.95,
    "buyer_kra_pin": 0.50
  },
  "extraction_success": true,
  "extraction_errors": []
}
```

### 2. Invoice Creation with Auto-OCR
**Endpoint:** `POST /api/invoices/`

**Enhanced:** Now supports automatic OCR extraction when `invoice_document` is uploaded

**Two Modes:**

#### Manual Mode (Traditional):
```json
{
  "invoice_number": "INV-2024-001234",
  "amount": "60000.00",
  "due_date": "2024-02-14",
  "patientName": "BEVTECH SOLUTIONS",
  "insurerName": "DENNIS MUASYA WAMBUA"
}
```

#### Auto-OCR Mode (New):
```
Content-Type: multipart/form-data

invoice_document: <file upload>
invoice_number: "" (optional - OCR will extract)
amount: "" (optional - OCR will extract)
```

**Behavior:**
- If `invoice_document` is provided, OCR runs automatically
- OCR-extracted data fills in any missing fields
- User-provided data always takes priority
- Invoice is created immediately

## 🚀 Testing the API Documentation

### Start the Server
```bash
cd /home/dennis/Desktop/projects/InvoiceDiscounting
python3 manage.py runserver
```

### Access Documentation
1. Open browser to http://localhost:8000/api/docs/
2. Click "Authorize" button
3. Login via `/api/auth/login/` to get JWT token
4. Paste token in Authorization dialog
5. Try out the OCR endpoints!

## 📋 API Structure

### Tags/Categories

1. **Invoice OCR**
   - `/api/invoices/extract/` - Extract invoice data using OCR

2. **Invoices**
   - `GET /api/invoices/` - List invoices
   - `POST /api/invoices/` - Create invoice (with auto-OCR)
   - `GET /api/invoices/{id}/` - Get invoice details
   - `PUT/PATCH /api/invoices/{id}/` - Update invoice
   - `DELETE /api/invoices/{id}/` - Delete invoice

3. **Authentication**
   - `POST /api/auth/login/` - Login and get JWT tokens
   - `POST /api/auth/register/` - Register new user
   - `POST /api/auth/logout/` - Logout
   - `POST /api/auth/token/refresh/` - Refresh access token

4. **KYC**
   - `GET /api/kyc-documents/` - List user's KYC documents
   - `POST /api/kyc-documents/` - Upload KYC document
   - `GET /api/kyc-documents/status/` - Get KYC verification status

5. **Dashboard**
   - `GET /api/dashboard/stats/` - Get dashboard statistics
   - `GET /api/dashboard/recent-invoices/` - Recent invoices
   - `GET /api/dashboard/funding-history/` - Funding history

6. **Contracts**
   - CRUD operations for buyer-supplier contracts

7. **Payments**
   - Track payments and M-Pesa transactions

## 🔐 Authentication

Most endpoints require JWT authentication:

1. **Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

2. **Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {...},
  "role": {...}
}
```

3. **Use Token:**
```bash
curl -X POST http://localhost:8000/api/invoices/extract/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -F "invoice_document=@/path/to/invoice.pdf"
```

## 📊 OCR Workflow Examples

### Workflow 1: Two-Step (Preview + Confirm)
```bash
# Step 1: Extract data
curl -X POST http://localhost:8000/api/invoices/extract/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "invoice_document=@invoice.pdf"

# Review extracted data in frontend

# Step 2: Create invoice with confirmed data
curl -X POST http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_number": "KRASRN000314580",
    "amount": "60000.00",
    "due_date": "2025-12-17",
    "patientName": "BEVTECH SOLUTIONS",
    "insurerName": "DENNIS MUASYA WAMBUA"
  }'
```

### Workflow 2: One-Step (Direct Upload)
```bash
# Upload file - OCR + create in one step
curl -X POST http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "invoice_document=@invoice.pdf"

# OCR extracts data automatically
# Invoice created immediately
```

## 🎨 Swagger UI Features

- **Try it out:** Test endpoints directly from browser
- **Request body editor:** JSON syntax highlighting
- **Response examples:** See what to expect
- **Schema explorer:** Browse all models
- **Authentication:** Persist JWT token across requests
- **Filter:** Search endpoints
- **Deep linking:** Share specific operation URLs

## 📱 Using with Mobile/Frontend

### Import into Postman
1. Go to http://localhost:8000/api/schema/
2. Copy the URL
3. In Postman: Import → Link → Paste URL
4. All endpoints imported automatically!

### Generate SDK
Use OpenAPI Generator to create client SDKs:
```bash
# Download schema
curl http://localhost:8000/api/schema/ > schema.yml

# Generate JavaScript client
openapi-generator-cli generate \
  -i schema.yml \
  -g javascript \
  -o ./client-sdk
```

## 🔍 Schema Validation

The OpenAPI schema passes validation with minimal warnings:
- ✅ 7 warnings (2 unique) - minor typing hints
- ✅ All core endpoints documented
- ✅ OCR endpoints fully documented
- ✅ Request/response examples included
- ✅ Authentication documented

## 📝 Notes

- Schema is auto-generated from code
- Documentation stays in sync with code
- Examples are based on actual test data
- All OCR features fully documented
- Interactive testing available in Swagger UI

---

**Generated:** 2026-01-14
**API Version:** 1.0.0
**Framework:** Django REST Framework + drf-spectacular
