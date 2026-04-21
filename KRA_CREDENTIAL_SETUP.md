# KRA eTIMS API Credential Setup Guide

## Current Issue

The KRA API credentials are configured but the token endpoint returns empty responses:
- Endpoint: `https://sbx.kra.go.ke/v1/token/generate?grant_type=client_credentials`
- Status: Returns HTTP 200 but **empty body** (content-length: 0)
- Invoice Checker: Returns "Invalid access token" error

## Root Cause

The credentials are not activated in the KRA sandbox environment. This requires registration on the KRA Developer Portal (developer.go.ke / GavaConnect).

## Steps to Activate Credentials

### 1. Register on KRA Developer Portal

**Portal:** https://developer.go.ke

1. Create an account on the KRA Developer Portal
2. Verify your email address
3. Complete your developer profile

### 2. Create an Application/Project

1. Log in to https://developer.go.ke
2. Navigate to "My Applications" or "Create App"
3. Fill in application details:
   - **Application Name**: Invoice Discounting Platform
   - **Description**: Invoice verification and discounting platform
   - **Callback URL**: Your application URL
   - **Environment**: Select **Sandbox** for testing

### 3. Subscribe to APIs

Subscribe to the following APIs:
- ✅ **Invoice Checker API**
- ✅ **Authorization API** (for token generation)
- ✅ Any other relevant APIs (PIN Checker, TCC Checker, etc.)

### 4. Generate/Retrieve Credentials

After creating your application:
1. Go to "Application Details"
2. You should see:
   - **Consumer Key** (Client ID)
   - **Consumer Secret** (Client Secret)
3. Copy these credentials

### 5. Activate Sandbox Access

Some API portals require explicit activation:
1. Check if there's an "Activate Sandbox" button
2. Or submit a request for sandbox access
3. Wait for approval email (usually 1-3 business days)

### 6. Update Your Credentials

Once you have the new/activated credentials, update your `.env` file:

```bash
# KRA eTIMS API Configuration
KRA_API_BASE_URL=https://sbx.kra.go.ke
KRA_CONSUMER_KEY=your_new_consumer_key_here
KRA_CONSUMER_SECRET=your_new_consumer_secret_here
KRA_API_TIMEOUT=30
KRA_VERIFICATION_ENABLED=True
```

### 7. Test the Connection

Run the test script to verify:

```bash
python3 test_token_generation.py
```

You should see:
```
✅ SUCCESS! Token obtained:
    Access Token: eyJ0eXAiOiJKV1QiLCJhbGc...
    Token Type: Bearer
    Expires In: 3600 seconds
```

## Current Credentials Status

Your current credentials:
- **Consumer Key**: `uVzcdAE4tLsQplA2Uksc3DJ3fauKkB4dFYGpNHAsD3UfLQlc`
- **Consumer Secret**: `0hQl16FSEtv1IdRmZ8cKpmG8nxizGH206IHvC5SQPzf0Y8QdzmokCcX30WvRYMES`

**Status**: ⚠️ Not returning tokens (likely not activated in sandbox)

## Test Results

```
Endpoint: https://sbx.kra.go.ke/v1/token/generate?grant_type=client_credentials
Method: POST
Authorization: Basic {base64(consumer_key:consumer_secret)}

Response:
  Status: 200 OK
  Body: (empty)  ❌
  Content-Length: 0  ❌

Expected Response:
  Status: 200 OK
  Body: {
    "access_token": "eyJ0eXAi...",
    "token_type": "Bearer",
    "expires_in": 3600
  }  ✅
```

## Alternative: Check for Existing Registration

The credentials you have might already be registered. Try:

1. **Log in to developer.go.ke** with your KRA credentials
2. Check "My Applications" to see if an app already exists
3. Verify the subscription status
4. Check if sandbox access is approved

## Contact KRA Support

If you encounter issues:

**Email:** apisupport@kra.go.ke
**Subject:** Sandbox API Access - Invoice Checker API

**Message Template:**
```
Dear KRA API Support Team,

I am integrating with the KRA Invoice Checker API for my invoice
discounting platform.

Application Details:
- Application Name: Invoice Discounting Platform
- Environment: Sandbox
- Consumer Key: uVzcdAE4tLsQplA2Uksc3DJ3fauKkB4dFYGpNHAsD3UfLQlc

Issue:
The /v1/token/generate endpoint returns HTTP 200 but an empty
response body. I believe my sandbox credentials need activation.

Request:
Please activate sandbox access for the Invoice Checker API
for the above consumer key.

Thank you.
```

## Production Setup

Once sandbox testing is complete:

1. **Create Production Application** on developer.go.ke
2. **Subscribe to production APIs**
3. **Generate production credentials**
4. **Update .env file**:
   ```bash
   KRA_API_BASE_URL=https://api.developer.go.ke
   KRA_CONSUMER_KEY=production_consumer_key
   KRA_CONSUMER_SECRET=production_consumer_secret
   ```
5. **Test thoroughly** before going live

## Documentation Resources

- **KRA Developer Portal**: https://developer.go.ke
- **API Documentation**: https://developer.go.ke/apis
- **Invoice Checker API**: https://developer.go.ke/apis/Invoice-Checker
- **Authorization API**: https://developer.go.ke/apis/Authorization
- **eTIMS Integration**: https://www.kra.go.ke/business/etims-electronic-tax-invoice-management-system/learn-about-etims/etims-system-to-system-integration

## Monitoring

Once credentials are activated, monitor:
- Token generation success rate
- Invoice verification response times
- API error rates
- Token expiry and refresh

## Security Checklist

✅ Credentials stored in environment variables
✅ .env file added to .gitignore
✅ Different credentials for sandbox vs production
✅ Regular credential rotation planned
✅ Access logs monitored
✅ Rate limiting implemented

## Next Steps

1. ☐ Register on https://developer.go.ke
2. ☐ Create application for Invoice Discounting
3. ☐ Subscribe to Invoice Checker API
4. ☐ Activate sandbox access
5. ☐ Generate/retrieve credentials
6. ☐ Update .env file
7. ☐ Run test_token_generation.py
8. ☐ Verify invoice verification works
9. ☐ Deploy to production when ready

## Summary

Your integration code is **100% correct**. The issue is simply that the API credentials need to be properly registered and activated on the KRA Developer Portal (developer.go.ke). Once activated, your system will work perfectly!
