import json
from datetime import datetime, timezone as dt_timezone
import logging
import jwt
import requests
from django.utils import timezone
from django.contrib.auth import get_user_model
from decouple import config
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from user_management.models import TokenModule
from user_management.utility import get_auth0_userinfo

UserModel = get_user_model()

logger = logging.getLogger('application')

# -------------------- Helpers --------------------

def check_expiration(decoded_token):
    """Check if JWT token is expired"""
    try:
        exp = decoded_token.get(    "exp")
        if not exp:
            return True
        exp_datetime = datetime.fromtimestamp(exp, dt_timezone.utc)
        return exp_datetime < datetime.now(dt_timezone.utc)
    except Exception as e:
        print(e)
        return True


def get_token_from_request(request):
    """Extract Bearer token from request header"""
    header = (
            request.headers.get("Authorization") or
            request.META.get("HTTP_AUTHORIZATION")
    )
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1]


# -------------------- Azure --------------------

def validate_azure_token(token):
    try:
        # Fetch Azure JWKS for signature verification
        azure_ad = json.loads(config("AZURE_AD_DATA").replace("'", "\""))
        tenant_id = azure_ad.get("tenant_id")
        jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

        jwks = requests.get(jwks_url, timeout=10).json()
        unverified_header = jwt.get_unverified_header(token)

        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == unverified_header.get("kid"):
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break
        if not public_key:
            return None

        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=config("AZURE_CLIENT_ID"),  # must match client_id
            issuer=f"https://sts.windows.net/{tenant_id}/"
        )

        if check_expiration(decoded_token):
            return None

        email = decoded_token.get("upn") or decoded_token.get("unique_name")
        if email:
            UserModel.objects.filter(email=email).update(last_login=timezone.now())
        return email

    except Exception as e:
        print(f"Azure token validation error: {e}")
        return None


# -------------------- Google --------------------

def validate_google_token(token):
    try:
        # Get Google's public keys
        keys_response = requests.get('https://www.googleapis.com/oauth2/v3/certs', timeout=10)
        if keys_response.status_code != 200:
            return None

        jwks = keys_response.json()
        unverified_header = jwt.get_unverified_header(token)
        key_id = unverified_header.get("kid")

        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == key_id:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break
        if not public_key:
            return None

        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=config("GOOGLE_OAUTH_CLIENT_ID"),
            issuer=["accounts.google.com", "https://accounts.google.com"]
        )

        if check_expiration(decoded_token):
            return None

        email = decoded_token.get("email")
        if email:
            UserModel.objects.filter(email=email).update(last_login=timezone.now())
        return email

    except Exception as e:
        print(f"Google token validation error: {e}")
        return None


# def validate_auth0_token(token):
#     """
#     Validate an Auth0-issued ACCESS TOKEN using JWKS public keys
#     """
#     try:
#         auth0_domain = config("AUTH0_DOMAIN").strip()
#         api_audience = config("AUTH0_API_AUDIENCE").strip()
#
#         if not auth0_domain or not api_audience:
#             logging.error("AUTH0_DOMAIN or AUTH0_API_AUDIENCE not configured")
#             return None
#
#         issuer = f"https://{auth0_domain}/"
#
#         # Fetch JWKS
#         jwks_url = f"{issuer}.well-known/jwks.json"
#         jwks = requests.get(jwks_url, timeout=10).json()
#
#         # Read token header
#         unverified_header = jwt.get_unverified_header(token)
#         kid = unverified_header.get("kid")
#
#         if not kid:
#             logging.error("Missing kid in token header")
#             return None
#
#         # Find matching public key
#         public_key = None
#         for key in jwks["keys"]:
#             if key["kid"] == kid:
#                 public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
#                     json.dumps(key)
#                 )
#                 break
#
#         if not public_key:
#             logging.error("Public key not found for given kid")
#             return None
#
#         # Decode & verify token
#         decoded_token = jwt.decode(
#             token,
#             public_key,
#             algorithms=["RS256"],
#             audience=api_audience,   # MUST match API audience
#             issuer=issuer,
#             leeway=60                # clock skew tolerance
#         )
#
#         # Access tokens identify users by `sub`
#         user_sub = decoded_token.get("sub")
#
#         if not user_sub:
#             logging.error("Token missing sub claim")
#             return None
#
#         logging.info(f"Valid Auth0 access token for sub: {user_sub}")
#
#         # OPTIONAL: Update last_login using sub mapping
#         try:
#             user = UserModel.objects.filter(auth0_id=user_sub).first()
#             if user:
#                 user.last_login = timezone.now()
#                 user.save()
#             else:
#                 logging.warning(f"User not found for sub: {user_sub}")
#         except Exception as e:
#             logging.warning(f"Error updating last_login: {e}")
#
#         return user_sub
#
#     except jwt.ExpiredSignatureError:
#         logging.error("Auth0 token expired")
#     except jwt.InvalidAudienceError as e:
#         logging.error(f"Invalid audience: {e}")
#     except jwt.InvalidIssuerError as e:
#         logging.error(f"Invalid issuer: {e}")
#     except jwt.InvalidTokenError as e:
#         logging.error(f"Invalid token: {e}")
#     except Exception as e:
#         logging.error(f"Auth0 token validation error: {e}")
#
#     return None





# -------------------- Auth Backend --------------------
# This actually authenticate users (backend)

def validate_auth0_token(token):
    """
    Validate an Auth0-issued ACCESS TOKEN using JWKS public keys
    Returns: (user_sub, error_message) tuple
    """
    try:
        auth0_domain = config("AUTH0_DOMAIN").strip()
        api_audience = config("AUTH0_API_AUDIENCE").strip()

        if not auth0_domain or not api_audience:
            error_msg = "AUTH0_DOMAIN or AUTH0_API_AUDIENCE not configured"
            logging.error(error_msg)
            return None, error_msg

        issuer = f"https://{auth0_domain}/"

        # Fetch JWKS
        jwks_url = f"{issuer}.well-known/jwks.json"
        jwks = requests.get(jwks_url, timeout=10).json()

        # Read token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            error_msg = "Missing kid in token header"
            logging.error(error_msg)
            return None, error_msg

        # Find matching public key
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
                    json.dumps(key)
                )
                break

        if not public_key:
            error_msg = f"Public key not found for kid: {kid}"
            logging.error(error_msg)
            return None, error_msg

        # Decode & verify token
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=api_audience,
            issuer=issuer,
            leeway=60
        )
        # print("decoded_token",decoded_token)

        # Access tokens identify users by `sub`
        # user_sub = decoded_token.get("sub")
        # email based token identification
        user_sub = decoded_token.get('email')


        if not user_sub:
            error_msg = "Token missing sub claim"
            logging.error(error_msg)
            return None, error_msg

        logging.info(f"Valid Auth0 access token for sub: {user_sub}")

        # Update last_login
        try:
            # user = UserModel.objects.filter(auth0_id=user_sub).first()
            user = UserModel.objects.filter(email=user_sub).first()
            if user:
                user.last_login = timezone.now()
                user.save()
        except Exception as e:
            logging.warning(f"Error updating last_login: {e}")

        return user_sub, None

    except jwt.ExpiredSignatureError as e:
        error_msg = f"Auth0 token expired: {str(e)}"
        logging.error(error_msg)
        return None, error_msg
    except jwt.InvalidAudienceError as e:
        error_msg = f"Invalid audience - expected: {api_audience}, error: {str(e)}"
        logging.error(error_msg)
        return None, error_msg
    except jwt.InvalidIssuerError as e:
        error_msg = f"Invalid issuer - expected: {issuer}, error: {str(e)}"
        logging.error(error_msg)
        return None, error_msg
    except jwt.InvalidTokenError as e:
        error_msg = f"Invalid token: {str(e)}"
        logging.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Auth0 token validation error: {str(e)}"
        logging.error(error_msg)
        return None, error_msg

class MultiProviderJWTAuthenticationBackend(BaseAuthentication):
    def authenticate(self, request):
        # 1️⃣ API Key Auth
        x_api_key = request.headers.get("X-API-KEY")
        if x_api_key:
            try:
                token_object = TokenModule.objects.get(primary_token=x_api_key)
            except TokenModule.DoesNotExist:
                raise AuthenticationFailed("Invalid API key")

            if token_object.expiry_time < timezone.now():
                raise AuthenticationFailed("API key expired")

            return token_object.user_id, x_api_key

        # 2️⃣ JWT Auth
        token = get_token_from_request(request)
        if not token:
            return None

        user_email = None
        provider = None

        # Try Google first
        user_email = validate_google_token(token)
        if user_email:
            provider = "google"

        # Fallback to Azure
        if not user_email:
            user_email = validate_azure_token(token)
            if user_email:
                provider = "azure"

        if not user_email:
            user_email = validate_auth0_token(token)
            if user_email:
                provider = "auth0"

        if not user_email:
            return None

        try:
            user = UserModel.objects.get(email__iexact=user_email, status=True)
        except UserModel.DoesNotExist:
            return None
        except Exception as e:
            print(e)
            return None

        return user, {"token": token, "provider": provider}


# class Auth0JWTAuthenticationBackend(BaseAuthentication):
#     """
#     Dedicated authentication backend for Auth0 JWT tokens
#     """
#     def authenticate(self, request):
#         token = get_token_from_request(request)
#         if not token:
#             return None
#
#         auth0_id = validate_auth0_token(token)
#         if not auth0_id:
#             return None
#
#         try:
#             user = UserModel.objects.get(auth0_id__iexact=auth0_id, status=True)
#             if not user:
#                 return None
#         except UserModel.DoesNotExist:
#             # Better error message
#             print(f"Auth0: User not found or inactive: {auth0_id}")
#             raise AuthenticationFailed(f"User with email {auth0_id} not found or inactive")
#         except Exception as e:
#             print(f"Auth0 auth error: {e}")
#             raise AuthenticationFailed("Authentication failed")
#
#         return user, {"token": token, "provider": "auth0"}
#
#     def authenticate_header(self, request):
#         return 'Bearer realm="api"'

# -------------------- OpenAPI Integration --------------------
# This documents how that authentication works
# class Auth0JWTAuthenticationBackend(BaseAuthentication):
#     """
#     Dedicated authentication backend for Auth0 JWT tokens
#     """
#
#     def authenticate(self, request):
#         token = get_token_from_request(request)
#         if not token:
#             return None
#
#         auth0_id = validate_auth0_token(token)
#         if not auth0_id:
#             return None
#
#         try:
#             user = UserModel.objects.get(auth0_id__iexact=auth0_id, status=True)
#             return user, {"token": token, "provider": "auth0"}
#
#         except UserModel.DoesNotExist:
#             # User not found in database - fetch from Auth0 and create
#             logging.info(f"User not found in DB with auth0_id: {auth0_id}. Fetching from Auth0...")
#
#             # Get user info from Auth0
#             user_info = get_auth0_userinfo(token)
#
#             if not user_info:
#                 logging.error(f"Failed to fetch user info from Auth0 for: {auth0_id}")
#                 raise AuthenticationFailed("Unable to retrieve user information from Auth0")
#
#             # Create new user from Auth0 data
#             try:
#                 user = self._create_user_from_auth0(user_info)
#                 logging.info(f"Successfully created new user: {user.email}")
#                 return user, {"token": token, "provider": "auth0"}
#
#             except Exception as e:
#                 logging.error(f"Failed to create user from Auth0 data: {e}")
#                 raise AuthenticationFailed(f"Failed to create user account: {str(e)}")
#
#         except Exception as e:
#             logging.error(f"Auth0 authentication error: {e}")
#             raise AuthenticationFailed("Authentication failed")
#
#     def _create_user_from_auth0(self, user_info):
#         """
#         Create a new user in the database from Auth0 user info
#         """
#         # Extract user data from Auth0 response
#         email = user_info.get('email')
#         auth0_id = user_info.get('sub')
#
#         if not email or not auth0_id:
#             raise ValueError("Email and auth0_id are required to create user")
#
#         # Parse name fields
#         first_name = user_info.get('given_name', '')
#         last_name = user_info.get('family_name', '')
#
#         # If given_name/family_name not available, try to parse from 'name'
#         if not first_name and not last_name:
#             full_name = user_info.get('name', '')
#             name_parts = full_name.split(' ', 1)
#             first_name = name_parts[0] if len(name_parts) > 0 else ''
#             last_name = name_parts[1] if len(name_parts) > 1 else ''
#
#         # Truncate names to fit max_length=15
#         first_name = first_name[:15] if first_name else 'User'
#         last_name = last_name[:15] if last_name else ''
#
#         # Create the user
#         user = UserModel.objects.create(
#             email=email,
#             auth0_id=auth0_id,
#             first_name=first_name,
#             last_name=last_name,
#             status=True,
#             # Optional: Set email_verified based on Auth0 data
#             # is_verified=user_info.get('email_verified', False),
#         )
#
#         logging.info(f"Created new user: {user.email} (auth0_id: {auth0_id})")
#         return user
#
#     def authenticate_header(self, request):
#         return 'Bearer realm="api"'

class Auth0JWTAuthenticationBackend(BaseAuthentication):
    """
    Dedicated authentication backend for Auth0 JWT tokens
    """

    def authenticate(self, request):
        token = get_token_from_request(request)
        if not token:
            return None

        # auth0_id, error_message = validate_auth0_token(token)
        email_id, error_message = validate_auth0_token(token)
        if not email_id:
            # Raise detailed error instead of returning None
            raise AuthenticationFailed(
                f"Auth0 token validation failed: {error_message or 'Unknown error'}"
            )

        try:
            user = UserModel.objects.get(email__iexact=email_id, status=True)
            print('user',user)
            return user, {"token": token, "provider": "auth0"}

        except UserModel.DoesNotExist:
            logging.info(f"User not found in DB with auth0_id: {email_id}. Fetching from Auth0...")

            user_info = get_auth0_userinfo(token)

            if not user_info:
                logging.error(f"Failed to fetch user info from Auth0 for: {email_id}")
                raise AuthenticationFailed(
                    f"Unable to retrieve user information from Auth0 for sub: {email_id}"
                )

            try:
                user = self._create_user_from_auth0(user_info)
                logging.info(f"Successfully created new user: {user.email}")
                return user, {"token": token, "provider": "auth0"}

            except Exception as e:
                error_msg = f"Failed to create user from Auth0 data: {str(e)}"
                logging.error(error_msg)
                raise AuthenticationFailed(error_msg)

        except Exception as e:
            error_msg = f"Auth0 authentication error: {str(e)}"
            logging.error(error_msg)
            raise AuthenticationFailed(error_msg)

    def _create_user_from_auth0(self, user_info):
        """
        Create a new user in the database from Auth0 user info
        """
        # Extract user data from Auth0 response
        email = user_info.get('email')
        auth0_id = user_info.get('sub')

        if not email or not auth0_id:
            raise ValueError("Email and auth0_id are required to create user")

        # Parse name fields
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')

        # If given_name/family_name not available, try to parse from 'name'
        if not first_name and not last_name:
            full_name = user_info.get('name', '')
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0] if len(name_parts) > 0 else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Truncate names to fit max_length=15
        first_name = first_name[:15] if first_name else 'User'
        last_name = last_name[:15] if last_name else ''

        # Create the user
        user = UserModel.objects.create(
            email=email,
            auth0_id=auth0_id,
            first_name=first_name,
            last_name=last_name,
            status=True,
            # Optional: Set email_verified based on Auth0 data
            # is_verified=user_info.get('email_verified', False),
        )

        logging.info(f"Created new user: {user.email} (auth0_id: {auth0_id})")
        return user

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

class MultiProviderJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "vendor_booking_tool.custom_authentication.MultiProviderJWTAuthenticationBackend"
    name = "MultiProviderJWTAuth"

    def get_security_definition(self, *args, **kwargs):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Supports API Key, Google, Azure AD, and Auth0 JWT Authentication",
        }

    def get_security_requirement(self, *args, **kwargs):
        return {self.name: []}

class Auth0JWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "vendor_booking_tool.custom_authentication.Auth0JWTAuthenticationBackend"
    name = "Auth0JWTAuth"

    def get_security_definition(self, *args, **kwargs):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Auth0 JWT Authentication",
        }