"""
Advanced token generation testing with different approaches.
"""
import requests
import base64
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Get credentials
CONSUMER_KEY = os.getenv('KRA_CONSUMER_KEY', '')
CONSUMER_SECRET = os.getenv('KRA_CONSUMER_SECRET', '')
BASE_URL = os.getenv('KRA_API_BASE_URL', 'https://sbx.kra.go.ke')

print("="*80)
print("ADVANCED KRA TOKEN TESTING")
print("="*80)

# Encode credentials
credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

# Test 4: Check if token is in response headers
print("\n" + "="*80)
print("TEST 4: Check response headers for token")
print("="*80)

token_url = f"{BASE_URL}/v1/token/generate?grant_type=client_credentials"

headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Accept': '*/*'
}

try:
    response = requests.post(token_url, headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"\nResponse Headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
        if 'token' in k.lower() or 'auth' in k.lower():
            print(f"    ⭐ FOUND TOKEN-RELATED HEADER!")

    print(f"\nResponse Body: '{response.text}'")
    print(f"Response Body Length: {len(response.text)}")

except Exception as e:
    print(f"ERROR: {e}")

# Test 5: Try with additional headers from Apigee/API Gateway
print("\n" + "="*80)
print("TEST 5: POST with API Gateway headers")
print("="*80)

headers5 = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-API-Key': CONSUMER_KEY,
    'apikey': CONSUMER_KEY
}

payload5 = {
    'grant_type': 'client_credentials',
    'client_id': CONSUMER_KEY,
    'client_secret': CONSUMER_SECRET
}

try:
    response5 = requests.post(
        f"{BASE_URL}/v1/token/generate",
        headers=headers5,
        json=payload5,
        timeout=30
    )
    print(f"Status: {response5.status_code}")
    print(f"Response: '{response5.text}'")

    if response5.text:
        try:
            data = response5.json()
            print(f"\n✅ JSON Response:")
            print(json.dumps(data, indent=2))
        except:
            pass

except Exception as e:
    print(f"ERROR: {e}")

# Test 6: Check if credentials work with invoice checker directly
print("\n" + "="*80)
print("TEST 6: Test invoice checker endpoint directly (will fail without token)")
print("="*80)

invoice_url = f"{BASE_URL}/checker/v1/invoice"

headers6 = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

payload6 = {
    'invoiceNumber': 'KRASRN000314580'
}

try:
    response6 = requests.post(invoice_url, headers=headers6, json=payload6, timeout=30)
    print(f"Status: {response6.status_code}")
    print(f"Response: '{response6.text[:500]}'")

except Exception as e:
    print(f"ERROR: {e}")

# Test 7: Try OAuth endpoint variations
print("\n" + "="*80)
print("TEST 7: Try alternative OAuth endpoints")
print("="*80)

alternative_endpoints = [
    f"{BASE_URL}/oauth/token",
    f"{BASE_URL}/oauth2/token",
    f"{BASE_URL}/v1/oauth/token",
    f"{BASE_URL}/api/v1/token",
]

for endpoint in alternative_endpoints:
    print(f"\nTrying: {endpoint}")
    try:
        response = requests.post(
            endpoint,
            headers={'Authorization': f'Basic {encoded_credentials}'},
            data={'grant_type': 'client_credentials'},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        if response.status_code != 404:
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*80)
print("RECOMMENDATIONS:")
print("="*80)
print("""
Based on the test results:

1. The /v1/token/generate endpoint returns HTTP 200 but empty body
   - This suggests the endpoint exists but may require different parameters
   - OR the credentials are not properly activated in the sandbox

2. Possible next steps:
   a) Contact KRA support at apisupport@kra.go.ke
   b) Verify credentials are activated for sandbox environment
   c) Check developer.go.ke portal for any activation steps
   d) Review if there are additional registration requirements

3. The endpoint format suggests it should work, but the empty response
   indicates either:
   - Credentials not yet activated
   - Missing required parameter or header
   - Sandbox environment issue
""")

print("\n" + "="*80)
print("TEST COMPLETED")
print("="*80)
