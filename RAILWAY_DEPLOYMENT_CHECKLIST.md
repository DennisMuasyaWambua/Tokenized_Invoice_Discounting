# Railway Production Deployment Checklist

This checklist ensures all production fixes are properly deployed to Railway.

## Critical Environment Variables

These MUST be set in Railway's environment variables settings:

### 1. Debug and Security
```bash
DEBUG=False                    # CRITICAL: Must be False in production
SECRET_KEY=<generate-secure-key-here>  # Use Django secret key generator
ENV=production
```

### 2. Database
```bash
DATABASE_URL=<railway-postgres-url>    # Automatically provided by Railway
```

### 3. KRA eTIMS API (Optional but recommended)
```bash
KRA_API_BASE_URL=https://sbx.kra.go.ke
KRA_CONSUMER_KEY=<your-key>
KRA_CONSUMER_SECRET=<your-secret>
KRA_API_TIMEOUT=30
KRA_VERIFICATION_ENABLED=True
```

## Pre-Deployment Checklist

### Step 1: Verify Code Changes
Ensure the following files have been updated:

- [ ] `discounting/serializers.py` - InvoiceUploadSerializer fixed for kra_verified handling
- [ ] `discounting/views.py` - UserViewSet has enhanced security filtering
- [ ] `discounting/migrations/0005_ensure_kra_verified_not_null.py` - New migration created

### Step 2: Local Testing
Before deploying to production, test locally:

```bash
# Run migrations
python manage.py migrate

# Test invoice creation with minimal payload
curl -X POST http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_number": "TEST-20260421-001",
    "invoice_amount": "50000.00",
    "invoice_date": "2026-04-21",
    "due_date": "2026-05-21"
  }'

# Verify users endpoint only returns own profile
curl -X GET http://localhost:8000/api/users/ \
  -H "Authorization: Bearer <non-staff-token>"
```

### Step 3: Railway Environment Configuration

1. Go to Railway dashboard → Your project → Variables
2. Add/update the following variables:

```env
DEBUG=False
ENV=production
SECRET_KEY=<generate-new-secret-key>
```

3. Verify DATABASE_URL is set (automatically added by Railway when Postgres is connected)

### Step 4: Deploy to Railway

```bash
# Push your changes to the git branch connected to Railway
git add .
git commit -m "Fix critical production issues:
- Invoice creation kra_verified null constraint
- Remove legacy field requirements
- Fix users endpoint data exposure
- Add database-level NOT NULL constraint for kra_verified"
git push origin <your-branch>
```

### Step 5: Run Migrations on Railway

Railway should auto-run migrations, but verify:

1. Check Railway logs to confirm migrations ran
2. If not, manually trigger via Railway CLI or dashboard:

```bash
# Using Railway CLI
railway run python manage.py migrate
```

Or via Railway dashboard:
- Go to Settings → Deploy
- Add start command: `python manage.py migrate && gunicorn InvoiceDiscounting.wsgi`

### Step 6: Verify Migrations Ran

Check that all migrations are applied:

```bash
# Via Railway CLI
railway run python manage.py showmigrations discounting
```

Expected output should show:
```
[X] 0001_initial
[X] 0002_kycdocument
[X] 0003_invoice_buyer_kra_pin_invoice_kra_verification_date_and_more
[X] 0004_fix_kra_verified_default
[X] 0005_ensure_kra_verified_not_null
```

### Step 7: Check Database User is_staff Status

The users endpoint exposure might be due to the test user being marked as staff. Verify:

```sql
-- Via Railway PostgreSQL console
SELECT id, email, is_staff, is_superuser
FROM discounting_user
WHERE email = 'muasyathegreat4@gmail.com';
```

If `is_staff=true` for this user, update it:

```sql
UPDATE discounting_user
SET is_staff = FALSE, is_superuser = FALSE
WHERE email = 'muasyathegreat4@gmail.com';
```

## Post-Deployment Testing

### Test 1: Invoice Creation - Minimal Payload

```bash
# Should return 201 Created
curl -X POST https://tokenizedinvoicediscounting-production.up.railway.app/api/invoices/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_number": "TEST-20260421-002",
    "invoice_amount": "50000.00",
    "invoice_date": "2026-04-21",
    "due_date": "2026-05-21"
  }'
```

Expected: 201 Created with full invoice object

### Test 2: Invoice Creation - Legacy Fields Still Work

```bash
# Should also work for backward compatibility
curl -X POST https://tokenizedinvoicediscounting-production.up.railway.app/api/invoices/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "patientName": "Test Patient",
    "insurerName": "Test Insurer",
    "amount": "50000.00",
    "invoice_date": "2026-04-21",
    "due_date": "2026-05-21"
  }'
```

Expected: 201 Created

### Test 3: Users Endpoint - No Data Exposure

```bash
# With supplier/regular user token
curl -X GET https://tokenizedinvoicediscounting-production.up.railway.app/api/users/ \
  -H "Authorization: Bearer <supplier-token>"
```

Expected: Only 1 user returned (the authenticated user's own profile)

```json
{
  "count": 1,
  "results": [
    {
      "id": 5,
      "email": "muasyathegreat4@gmail.com",
      ...
    }
  ]
}
```

### Test 4: No Debug HTML in Errors

```bash
# Intentionally trigger an error
curl -X POST https://tokenizedinvoicediscounting-production.up.railway.app/api/invoices/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{invalid json'
```

Expected: JSON error response, NOT Django debug HTML

```json
{
  "detail": "JSON parse error..."
}
```

## Rollback Plan

If something goes wrong after deployment:

1. **Revert Git Commit:**
   ```bash
   git revert HEAD
   git push origin <branch>
   ```

2. **Rollback Migrations (if needed):**
   ```bash
   railway run python manage.py migrate discounting 0004_fix_kra_verified_default
   ```

3. **Check Railway Logs:**
   ```bash
   railway logs
   ```

## Success Criteria

All of the following must be true:

- [ ] POST /api/invoices/ accepts minimal payload (just invoice_number, amount, dates)
- [ ] POST /api/invoices/ does NOT return IntegrityError for kra_verified
- [ ] GET /api/users/ returns only 1 user for non-staff accounts
- [ ] API errors return JSON, not HTML debug pages
- [ ] DEBUG=False is confirmed in Railway environment variables
- [ ] All 5 migrations are applied in production database

## Troubleshooting

### Issue: Migration 0005 fails with "column already has NOT NULL constraint"

This is actually GOOD - it means the constraint is already there. The migration will skip the NOT NULL step.

### Issue: Still getting kra_verified null error

1. Check migration 0005 ran successfully
2. Verify the serializer changes are deployed
3. Check Railway logs for the actual code version deployed
4. Manually run the SQL fixes:
   ```sql
   UPDATE discounting_invoice SET kra_verified = FALSE WHERE kra_verified IS NULL;
   ALTER TABLE discounting_invoice ALTER COLUMN kra_verified SET DEFAULT FALSE;
   ALTER TABLE discounting_invoice ALTER COLUMN kra_verified SET NOT NULL;
   ```

### Issue: Users endpoint still exposing all users

1. Verify views.py changes are deployed
2. Check if user is marked as staff:
   ```sql
   SELECT email, is_staff FROM discounting_user WHERE email = 'muasyathegreat4@gmail.com';
   ```
3. Update if needed:
   ```sql
   UPDATE discounting_user SET is_staff = FALSE WHERE email = 'muasyathegreat4@gmail.com';
   ```

## Additional Notes

- Railway automatically redeploys when you push to the connected git branch
- Railway runs `python manage.py migrate` automatically if configured
- Check Railway logs for detailed error messages
- Database backups are recommended before major migrations

## Contact

If issues persist after following this checklist:
1. Check Railway logs: `railway logs`
2. Check database state directly via Railway PostgreSQL console
3. Verify environment variables are set correctly
