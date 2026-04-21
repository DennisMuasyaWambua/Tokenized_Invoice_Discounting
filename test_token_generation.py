"""
Simple test script to debug KRA token generation.
"""
import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials from environment
CONSUMER_KEY = os.getenv('KRA_CONSUMER_KEY', '')
CONSUMER_SECRET = os.getenv('KRA_CONSUMER_SECRET', '')
BASE_URL = os.getenv('KRA_API_BASE_URL', 'https://sbx.kra.go.ke')

print("="*80)
print("KRA TOKEN GENERATION TEST")
print("="*80)

print(f"\nConfiguration:")
print(f"  Base URL: {BASE_URL}")
print(f"  Consumer Key: {CONSUMER_KEY[:30]}...")
print(f"  Consumer Secret: {'*' * 30}...")

# Prepare credentials
credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

print(f"\n  Encoded Credentials: {encoded_credentials[:40]}...")

# Token endpoint
token_url = f"{BASE_URL}/v1/token/generate"

print(f"\nToken Endpoint: {token_url}")

# Test 1: POST with query parameter
print("\n" + "="*80)
print("TEST 1: POST with grant_type as query parameter")
print("="*80)

headers1 = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

params1 = {
    'grant_type': 'client_credentials'
}

print(f"\nRequest:")
print(f"  Method: POST")
print(f"  URL: {token_url}")
print(f"  Headers:")
for k, v in headers1.items():
    if k == 'Authorization':
        print(f"    {k}: {v[:40]}...")
    else:
        print(f"    {k}: {v}")
print(f"  Params: {params1}")

try:
    response1 = requests.post(token_url, headers=headers1, params=params1, timeout=30)
    print(f"\nResponse:")
    print(f"  Status Code: {response1.status_code}")
    print(f"  Headers:")
    for k, v in response1.headers.items():
        print(f"    {k}: {v}")
    print(f"  Body:")
    print(f"    {response1.text[:1000]}")

    if response1.status_code == 200:
        try:
            token_data = response1.json()
            print(f"\n✅ SUCCESS! Token obtained:")
            print(f"    Access Token: {token_data.get('access_token', 'N/A')[:50]}...")
            print(f"    Token Type: {token_data.get('token_type', 'N/A')}")
            print(f"    Expires In: {token_data.get('expires_in', 'N/A')} seconds")
        except ValueError as e:
            print(f"\n❌ Response is not valid JSON: {e}")
    else:
        print(f"\n❌ Token request failed with status {response1.status_code}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: POST with grant_type in body
print("\n" + "="*80)
print("TEST 2: POST with grant_type in request body")
print("="*80)

headers2 = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json'
}

data2 = {
    'grant_type': 'client_credentials'
}

print(f"\nRequest:")
print(f"  Method: POST")
print(f"  URL: {token_url}")
print(f"  Headers:")
for k, v in headers2.items():
    if k == 'Authorization':
        print(f"    {k}: {v[:40]}...")
    else:
        print(f"    {k}: {v}")
print(f"  Body: {data2}")

try:
    response2 = requests.post(token_url, headers=headers2, data=data2, timeout=30)
    print(f"\nResponse:")
    print(f"  Status Code: {response2.status_code}")
    print(f"  Headers:")
    for k, v in response2.headers.items():
        print(f"    {k}: {v}")
    print(f"  Body:")
    print(f"    {response2.text[:1000]}")

    if response2.status_code == 200:
        try:
            token_data = response2.json()
            print(f"\n✅ SUCCESS! Token obtained:")
            print(f"    Access Token: {token_data.get('access_token', 'N/A')[:50]}...")
            print(f"    Token Type: {token_data.get('token_type', 'N/A')}")
            print(f"    Expires In: {token_data.get('expires_in', 'N/A')} seconds")
        except ValueError as e:
            print(f"\n❌ Response is not valid JSON: {e}")
    else:
        print(f"\n❌ Token request failed with status {response2.status_code}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: GET request
print("\n" + "="*80)
print("TEST 3: GET request with grant_type as query parameter")
print("="*80)

headers3 = {
    'Authorization': f'Basic {encoded_credentials}',
    'Accept': 'application/json'
}

params3 = {
    'grant_type': 'client_credentials'
}

print(f"\nRequest:")
print(f"  Method: GET")
print(f"  URL: {token_url}")
print(f"  Headers:")
for k, v in headers3.items():
    if k == 'Authorization':
        print(f"    {k}: {v[:40]}...")
    else:
        print(f"    {k}: {v}")
print(f"  Params: {params3}")

try:
    response3 = requests.get(token_url, headers=headers3, params=params3, timeout=30)
    print(f"\nResponse:")
    print(f"  Status Code: {response3.status_code}")
    print(f"  Headers:")
    for k, v in response3.headers.items():
        print(f"    {k}: {v}")
    print(f"  Body:")
    print(f"    {response3.text[:1000]}")

    if response3.status_code == 200:
        try:
            token_data = response3.json()
            print(f"\n✅ SUCCESS! Token obtained:")
            print(f"    Access Token: {token_data.get('access_token', 'N/A')[:50]}...")
            print(f"    Token Type: {token_data.get('token_type', 'N/A')}")
            print(f"    Expires In: {token_data.get('expires_in', 'N/A')} seconds")
        except ValueError as e:
            print(f"\n❌ Response is not valid JSON: {e}")
    else:
        print(f"\n❌ Token request failed with status {response3.status_code}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST COMPLETED")
print("="*80)
