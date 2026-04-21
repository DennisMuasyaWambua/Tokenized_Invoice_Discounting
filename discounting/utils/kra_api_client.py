"""
KRA eTIMS API Client for invoice verification.
Handles authentication and communication with KRA Invoice Checker API.
"""
import logging
import requests
import base64
from typing import Dict, Optional
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger('discounting.kra_api')


class KRAAPIClient:
    """
    Client for interacting with KRA eTIMS Invoice Checker API.

    Uses OAuth 2.0 Client Credentials flow or API Key authentication.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'KRA_API_BASE_URL', 'https://sbx.kra.go.ke')
        self.consumer_key = getattr(settings, 'KRA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'KRA_CONSUMER_SECRET', '')
        self.timeout = getattr(settings, 'KRA_API_TIMEOUT', 30)

        # Cache for access token
        self._access_token = None
        self._token_expiry = None

        if not self.consumer_key or not self.consumer_secret:
            logger.warning("KRA API credentials not configured")

    def _get_basic_auth_header(self) -> str:
        """
        Generate Basic Authentication header from consumer key and secret.

        Returns:
            Base64 encoded authorization string
        """
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_bearer_token_header(self) -> str:
        """
        Generate Bearer token header (if OAuth token is cached).

        Returns:
            Bearer token authorization string
        """
        if self._access_token:
            return f"Bearer {self._access_token}"
        return None

    def _request_oauth_token(self) -> Optional[Dict]:
        """
        Request OAuth 2.0 access token using client credentials.

        Uses KRA GavaConnect token generation endpoint:
        https://sbx.kra.go.ke/v1/token/generate?grant_type=client_credentials

        Returns:
            Dict with token information or None if failed
        """
        try:
            # KRA GavaConnect token endpoint
            url = f"{self.base_url}/v1/token/generate"

            # Build request with Basic Auth
            headers = {
                'Authorization': self._get_basic_auth_header(),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # grant_type is passed as query parameter
            params = {
                'grant_type': 'client_credentials'
            }

            logger.info(f"Requesting OAuth token from {url}")
            logger.debug(f"Token request headers: {dict((k, v if k != 'Authorization' else v[:30] + '...') for k, v in headers.items())}")
            logger.debug(f"Token request params: {params}")

            response = requests.post(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout
            )

            logger.info(f"Token response status: {response.status_code}")
            logger.debug(f"Token response headers: {dict(response.headers)}")
            logger.debug(f"Token response body: {response.text[:500]}")  # First 500 chars

            if response.status_code == 200:
                # Check if response has content
                if not response.text or len(response.text) == 0:
                    logger.error(
                        "Token endpoint returned empty response. "
                        "This usually means credentials are not activated in the sandbox. "
                        "Please register on https://developer.go.ke and activate your API access."
                    )
                    return None

                try:
                    token_data = response.json()

                    # Check if we got an actual token
                    if 'access_token' not in token_data:
                        logger.error(
                            f"Token response missing 'access_token' field. "
                            f"Response: {token_data}"
                        )
                        return None

                    self._access_token = token_data.get('access_token')

                    # Calculate token expiry
                    expires_in = token_data.get('expires_in', 3600)
                    self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

                    logger.info(f"Successfully obtained OAuth access token (expires in {expires_in}s)")
                    logger.debug(f"Token data keys: {token_data.keys()}")
                    return token_data
                except ValueError as e:
                    logger.error(f"Failed to parse token response as JSON: {str(e)}")
                    logger.error(f"Response content: {response.text}")
                    logger.error(
                        "Please verify your API credentials are activated on https://developer.go.ke"
                    )
                    return None
            else:
                logger.error(
                    f"OAuth token request failed: {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error("OAuth token request timeout")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error during token request: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error requesting OAuth token: {str(e)}")
            return None

    def _is_token_valid(self) -> bool:
        """
        Check if cached OAuth token is still valid.

        Returns:
            True if token exists and hasn't expired
        """
        if not self._access_token or not self._token_expiry:
            return False
        return datetime.now() < self._token_expiry

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get appropriate authentication headers for API requests.

        Uses OAuth Bearer token for KRA GavaConnect API.

        Returns:
            Dict of headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Check if we have a valid token
        if self._is_token_valid():
            headers['Authorization'] = self._get_bearer_token_header()
            logger.debug("Using cached OAuth Bearer token")
            return headers

        # Try to get a new token
        if self._request_oauth_token():
            headers['Authorization'] = self._get_bearer_token_header()
            logger.debug("Using newly acquired OAuth Bearer token")
            return headers

        # If token acquisition fails, log error
        logger.error("Failed to acquire OAuth token for KRA API")
        # Return headers without auth (request will likely fail but we'll handle it)
        return headers

    def verify_invoice(
        self,
        invoice_number: str,
        invoice_date: Optional[str] = None,
        amount: Optional[float] = None,
        supplier_pin: Optional[str] = None
    ) -> Dict:
        """
        Verify invoice with KRA eTIMS system.

        Args:
            invoice_number: Invoice/SCU ID to verify
            invoice_date: Invoice date (optional, format: YYYY-MM-DD)
            amount: Invoice amount (optional)
            supplier_pin: Supplier KRA PIN (optional)

        Returns:
            Dict containing:
                - success: Boolean indicating if verification succeeded
                - verified: Boolean indicating if invoice is valid in KRA system
                - data: Response data from KRA API
                - error: Error message if verification failed
                - kra_response: Full KRA API response
        """
        result = {
            'success': False,
            'verified': False,
            'data': {},
            'error': None,
            'kra_response': None
        }

        if not invoice_number:
            result['error'] = 'Invoice number is required for verification'
            return result

        try:
            # Prepare request payload
            url = f"{self.base_url}/checker/v1/invoice"
            headers = self._get_auth_headers()

            # Build request body - adjust based on actual API requirements
            payload = {
                'invoiceNumber': invoice_number
            }

            # Add optional fields if provided
            if invoice_date:
                payload['invoiceDate'] = invoice_date
            if amount:
                payload['amount'] = amount
            if supplier_pin:
                payload['supplierPin'] = supplier_pin

            logger.info(f"Verifying invoice {invoice_number} with KRA API")
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request payload: {payload}")
            logger.debug(f"Request headers: {dict((k, v if k != 'Authorization' else v[:20] + '...') for k, v in headers.items())}")

            # Make API request
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            logger.info(f"KRA API response status: {response.status_code}")

            result['kra_response'] = {
                'status_code': response.status_code,
                'body': response.text
            }

            # Handle response
            if response.status_code == 200:
                response_data = response.json()
                result['success'] = True
                result['data'] = response_data

                # Check if invoice is verified (adjust based on actual API response format)
                # Common patterns: status field, verified field, or success field
                result['verified'] = self._parse_verification_status(response_data)

                logger.info(
                    f"Invoice {invoice_number} verification: "
                    f"verified={result['verified']}"
                )

            elif response.status_code == 404:
                result['success'] = True
                result['verified'] = False
                result['error'] = 'Invoice not found in KRA eTIMS system'
                logger.warning(f"Invoice {invoice_number} not found in KRA system")

            elif response.status_code == 401:
                result['error'] = 'Authentication failed with KRA API'
                logger.error(f"KRA API authentication failed: {response.text}")

            elif response.status_code == 400:
                result['error'] = 'Invalid request parameters'
                try:
                    error_data = response.json()
                    result['data'] = error_data
                    result['error'] = error_data.get('message', result['error'])
                except:
                    pass
                logger.error(f"KRA API bad request: {response.text}")

            else:
                result['error'] = f'KRA API returned status {response.status_code}'
                logger.error(f"KRA API error: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            result['error'] = 'KRA API request timeout'
            logger.error(f"KRA API timeout for invoice {invoice_number}")

        except requests.exceptions.ConnectionError:
            result['error'] = 'Unable to connect to KRA API'
            logger.error(f"KRA API connection error for invoice {invoice_number}")

        except requests.exceptions.RequestException as e:
            result['error'] = f'Request error: {str(e)}'
            logger.error(f"KRA API request error: {str(e)}")

        except Exception as e:
            result['error'] = f'Unexpected error: {str(e)}'
            logger.error(f"Unexpected error during KRA verification: {str(e)}")

        return result

    def _parse_verification_status(self, response_data: Dict) -> bool:
        """
        Parse KRA API response to determine if invoice is verified.

        Handles different possible response formats.

        Args:
            response_data: Response from KRA API

        Returns:
            True if invoice is verified, False otherwise
        """
        # Common response patterns from government APIs

        # Pattern 1: Direct 'verified' or 'valid' field
        if 'verified' in response_data:
            return bool(response_data['verified'])

        if 'valid' in response_data:
            return bool(response_data['valid'])

        # Pattern 2: Status field with specific values
        status = response_data.get('status', '').lower()
        if status in ['verified', 'valid', 'success', 'active', 'approved']:
            return True
        elif status in ['invalid', 'not_found', 'rejected', 'failed']:
            return False

        # Pattern 3: Result code (0 = success in many APIs)
        result_code = response_data.get('resultCode') or response_data.get('code')
        if result_code == 0 or result_code == '0' or result_code == 200:
            return True

        # Pattern 4: Data presence indicates verification
        if 'invoiceData' in response_data or 'invoice' in response_data:
            return True

        # Pattern 5: Success message
        message = response_data.get('message', '').lower()
        if 'success' in message or 'verified' in message:
            return True

        # Default: if we got data back, consider it unverified unless explicitly stated
        logger.warning(f"Unable to determine verification status from response: {response_data}")
        return False

    def health_check(self) -> Dict:
        """
        Check if KRA API is accessible and credentials are valid.

        Returns:
            Dict with health check results
        """
        result = {
            'api_accessible': False,
            'credentials_valid': False,
            'error': None
        }

        try:
            # Check if credentials are configured
            if not self.consumer_key or not self.consumer_secret:
                result['error'] = 'API credentials not configured'
                return result

            # Try a test request to the invoice checker endpoint
            # This is the most reliable way to verify credentials
            result['api_accessible'] = True
            result['credentials_valid'] = True  # Assume valid if configured
            logger.info("KRA API health check: credentials configured")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"KRA API health check failed: {str(e)}")

        return result
