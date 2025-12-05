# payments/mpesa.py
import requests
import base64
import json
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class MpesaAPI:
    def __init__(self, consumer_key=None, consumer_secret=None, shortcode=None, passkey=None, environment='sandbox'):
        """Initialize M-Pesa API

        Args:
            consumer_key: M-Pesa Consumer Key
            consumer_secret: M-Pesa Consumer Secret
            shortcode: Business Shortcode
            passkey: Lipa Na M-Pesa Online Passkey
            environment: 'sandbox' or 'production'
        """
        self.consumer_key = consumer_key or getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = consumer_secret or getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode = shortcode or getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey = passkey or getattr(settings, 'MPESA_PASSKEY', '')

        if environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'

        self.access_token = None
        self.token_expiry = None

        # Validate credentials
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("M-Pesa credentials are required")

    def get_access_token(self, force_refresh=False):
        """Get OAuth access token"""
        if self.access_token and not force_refresh:
            # Check if token is still valid (expires in 3600 seconds)
            if self.token_expiry and datetime.now() < self.token_expiry:
                return self.access_token

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            logger.info(f"Token request status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 3599)

                # Convert expires_in to int if it's a string
                if isinstance(expires_in, str):
                    try:
                        expires_in = int(expires_in)
                    except ValueError:
                        expires_in = 3599  # Default value

                # Set expiry time using datetime instead of timestamp
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

                logger.info("Access token obtained successfully")
                return self.access_token
            else:
                error_msg = f"Failed to get access token: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error getting access token: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error getting access token: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def make_request(self, endpoint, method='POST', data=None, headers=None):
        """Make authenticated request to M-Pesa API"""
        if headers is None:
            headers = {}

        # Get access token
        try:
            token = self.get_access_token()
            headers['Authorization'] = f'Bearer {token}'
            headers['Content-Type'] = 'application/json'
        except Exception as e:
            logger.error(f"Failed to get access token: {str(e)}")
            return {
                'success': False,
                'error_message': f"Authentication failed: {str(e)}",
                'status_code': 401
            }

        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.info(f"{method} {endpoint} - Status: {response.status_code}")

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {'raw_response': response.text}

            # Add status code to response
            response_data['status_code'] = response.status_code

            return response_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {str(e)}")
            return {
                'success': False,
                'error_message': f"Network error: {str(e)}",
                'status_code': 0
            }
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'status_code': 0
            }

    def generate_password(self):
        """Generate Lipa Na M-Pesa Online password"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        return password, timestamp

    def stk_push(self, phone_number, amount, account_reference, transaction_desc, callback_url):
        """Initiate STK Push request

        Args:
            phone_number: Customer phone number (format: 2547XXXXXXXX)
            amount: Amount to charge
            account_reference: Account reference
            transaction_desc: Transaction description
            callback_url: Callback URL for payment confirmation

        Returns:
            dict: Response with success status and details
        """
        try:
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number.startswith('+254'):
                phone_number = phone_number[1:]

            # Generate password and timestamp
            password, timestamp = self.generate_password()

            # Prepare request payload
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": str(int(Decimal(amount))),  # Convert to integer string
                "PartyA": phone_number,
                "PartyB": self.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }

            logger.info(f"STK Push payload: {json.dumps(payload, indent=2)}")

            # Make request
            response = self.make_request('/mpesa/stkpush/v1/processrequest', data=payload)

            # Parse response
            if response.get('ResponseCode') == '0':
                logger.info(f"STK Push successful: {response.get('CustomerMessage')}")
                return {
                    'success': True,
                    'merchant_request_id': response.get('MerchantRequestID'),
                    'checkout_request_id': response.get('CheckoutRequestID'),
                    'response_code': response.get('ResponseCode'),
                    'customer_message': response.get('CustomerMessage'),
                    'response_description': response.get('ResponseDescription'),
                    'raw_response': response
                }
            else:
                error_msg = response.get('errorMessage') or response.get('ResponseDescription') or 'STK Push failed'
                logger.error(f"STK Push failed: {error_msg}")
                return {
                    'success': False,
                    'error_message': error_msg,
                    'response_code': response.get('ResponseCode'),
                    'response_description': response.get('ResponseDescription'),
                    'raw_response': response
                }

        except Exception as e:
            error_msg = f"STK Push exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error_message': error_msg,
                'raw_response': None
            }

    def query_status(self, checkout_request_id):
        """Query STK Push transaction status

        Args:
            checkout_request_id: Checkout Request ID from STK Push

        Returns:
            dict: Transaction status
        """
        try:
            # Generate password and timestamp
            password, timestamp = self.generate_password()

            # Prepare query payload
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }

            logger.info(f"Query status for checkout: {checkout_request_id}")

            # Make request
            response = self.make_request('/mpesa/stkpushquery/v1/query', data=payload)

            # Parse response
            result_code = response.get('ResultCode')
            result_desc = response.get('ResultDesc')

            if result_code is not None:
                logger.info(f"Query result: Code={result_code}, Desc={result_desc}")

                if result_code == '0':
                    # Transaction successful
                    return {
                        'success': True,
                        'result_code': result_code,
                        'result_description': result_desc,
                        'mpesa_receipt_number': response.get('MpesaReceiptNumber'),
                        'transaction_date': response.get('TransactionDate'),
                        'phone_number': response.get('PhoneNumber'),
                        'amount': response.get('Amount'),
                        'raw_response': response
                    }
                else:
                    # Transaction failed or pending
                    return {
                        'success': False,
                        'result_code': result_code,
                        'result_description': result_desc,
                        'error_message': result_desc,
                        'raw_response': response
                    }
            else:
                error_msg = response.get('errorMessage') or 'Invalid response from query'
                logger.error(f"Query failed: {error_msg}")
                return {
                    'success': False,
                    'error_message': error_msg,
                    'raw_response': response
                }

        except Exception as e:
            error_msg = f"Query status exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error_message': error_msg
            }


# Utility function to get MpesaAPI instance
def get_mpesa_api():
    """Get configured MpesaAPI instance"""
    try:
        # Create MpesaAPI instance
        mpesa_api = MpesaAPI(
            consumer_key=getattr(settings, 'MPESA_CONSUMER_KEY', ''),
            consumer_secret=getattr(settings, 'MPESA_CONSUMER_SECRET', ''),
            shortcode=getattr(settings, 'MPESA_SHORTCODE', '174379'),
            passkey=getattr(settings, 'MPESA_PASSKEY', ''),
            environment=getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        )

        # Test the connection by getting access token
        token = mpesa_api.get_access_token()
        if token:
            logger.info("MpesaAPI initialized successfully")
            return mpesa_api
        else:
            raise Exception("Failed to get access token")

    except Exception as e:
        logger.error(f"Failed to initialize MpesaAPI: {str(e)}")
        raise