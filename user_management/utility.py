from django.contrib.auth import get_user_model
from django.db.models import Value, Q
from django.db.models.functions import Concat
import requests
import logging
from decouple import config
import re
import secrets
import string

# from shipment_management.utility import parse_year_month, parse_day_month, parse_search_date

User = get_user_model()

logger = logging.getLogger('application')


def return_user_info():
    queryset = User.objects.values('id', 'first_name', 'last_name')
    user_dict = {user['id']: f"{user['first_name']} {user['last_name']}".strip() for user in queryset}
    return user_dict


def return_user_id_by_name(name):
    if name:
        # Annotate full name by concatenating first_name and last_name
        users = User.objects.annotate(
            full_name=Concat('first_name', Value(' '), 'last_name')
        ).filter(full_name__icontains=name).values_list("id", flat=True)

        if users:  # If the QuerySet is not empty
            return list(users)
        else:
            return []  # Explicitly return an empty list if the QuerySet is empty
    return []  # Return an empty list if no name is provided


def build_user_global_search_q(search_value: str) -> Q:
    """
    Global search for User list view.
    Supports:
    - first_name
    - last_name
    - role_name
    - status (active/inactive/true/false/1/0)
    - created_on (YYYY or DD/MM or DD-MM)
    """
    q = Q()

    if not search_value:
        return q

    value = search_value.strip()
    lower = value.lower()

    # ---------------- TEXT SEARCH ----------------
    q |= Q(first_name__icontains=value)
    q |= Q(last_name__icontains=value)
    q |= Q(role_user__role__role_name__icontains=value)

    # ---------------- STATUS SEARCH ----------------
    if lower in ("active", "true", "1"):
        q |= Q(status=True)
    elif lower in ("inactive", "false", "0"):
        q |= Q(status=False)

        # -------- INTEGER SEARCH --------
        if search_value.isdigit():
            int_value = int(search_value)
            # Year search
            if len(search_value) == 4:
                q |= Q(created_on__year=int_value)

            if search_value.isdigit() and len(search_value) == 2:
                int_value = int(search_value)

                # Month: 01–12
                if 1 <= int_value <= 12:
                    q |= Q(created_on__month=int_value)

                # Day: 01–31
                if 1 <= int_value <= 31:
                    q |= Q(created_on__day=int_value)

        # ---------------- YEAR-MONTH ----------------
        ym = parse_year_month(search_value)
        if ym:
            if ym:
                year, month = ym
                q |= Q(created_on__year=year, created_on__month=month)

        # ---------------- DAY-MONTH (DD/MM) ----------------
        dm = parse_day_month(search_value)
        if dm:
            month, day = dm
            q |= Q(created_on__month=month, created_on__day=day)

        # ---------------- FULL DATE ----------------
        try:
            parsed_date = parse_search_date(search_value)
            q |= Q(created_on__date=parsed_date)
        except ValueError:
            pass

    return q


def create_user_in_auth0(email, password=None, first_name=None, last_name=None):
    """
    Create a user in Auth0 using Management API v2 (no Auth0 SDK required)
    """
    AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
    AUTH0_M2M_CLIENT_ID = config('CLIENT_ID', default='').strip()
    AUTH0_M2M_CLIENT_SECRET = config('CLIENT_SECRET', default='').strip()

    logging.info(f"Clean DOMAIN: '{repr(AUTH0_DOMAIN)}'")
    logging.info(f"Creating Auth0 user for {email}")

    if not password:
        password = generate_auth0_password(
            first_name=first_name,
            last_name=last_name,
            email=email
        )

    # Validate configuration
    if not all([AUTH0_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET]) or ' ' in AUTH0_DOMAIN:
        raise ValueError("Invalid Auth0 configuration")

    # Step 1: Get Management API access token
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_M2M_CLIENT_ID,
        "client_secret": AUTH0_M2M_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/"
    }

    try:
        token_resp = requests.post(token_url, json=token_payload, timeout=10)
        logging.info(f"Token request status: {token_resp.status_code}")
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        logging.info(" Management API token acquired")
    except requests.RequestException as e:
        logging.error(f"Failed to get Auth0 token: {str(e)}")
        raise

    # Prepare headers for API calls
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 2: Check if user already exists
    users_by_email_url = f"https://{AUTH0_DOMAIN}/api/v2/users-by-email"
    params = {"email": email}

    try:
        exist_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
        logging.info(f"User existence check status: {exist_resp.status_code}")

        if exist_resp.status_code == 200:
            existing_users = exist_resp.json()
            if existing_users:
                user_id = existing_users[0]["user_id"]
                logging.info(f" User already exists in Auth0: {user_id}")
                return user_id
    except requests.RequestException as e:
        logging.warning(f"Error checking user existence: {str(e)}")

    # Step 3: Create new user
    create_user_url = f"https://{AUTH0_DOMAIN}/api/v2/users"
    user_payload = {
        "connection": "Username-Password-Authentication",
        "email": email,
        "password": password,
        "email_verified": False,
        "verify_email": True,
        "given_name": first_name or "",
        "family_name": last_name or "",
        "name": f"{first_name or ''} {last_name or ''}".strip() or email.split('@')[0],
        "user_metadata": {
            "source": "django-registration"
        }
    }
    try:
        create_resp = requests.post(create_user_url, headers=headers, json=user_payload, timeout=10)
        logging.info(f"User creation status: {create_resp.status_code}")

        if create_resp.status_code == 201:
            auth0_user = create_resp.json()
            user_id = auth0_user.get("user_id")
            logging.info(f" Auth0 user created successfully: {user_id}")
            return user_id
        elif create_resp.status_code == 409:
            logging.warning(f"User {email} already exists (409 conflict)")
            exist_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
            if exist_resp.status_code == 200 and exist_resp.json():
                return exist_resp.json()[0]["user_id"]
            raise ValueError(f"User exists but couldn't retrieve: {email}")
        else:
            error_msg = create_resp.json() if create_resp.text else "Unknown error"
            logging.error(f"Auth0 user creation failed: {error_msg}")
            create_resp.raise_for_status()

    except requests.RequestException as e:
        logging.exception(f" Auth0 create failed for {email}: {str(e)}")
        raise


# def create_user_in_auth0(email, password, first_name=None, last_name=None):
#     """
#     Create a user in Auth0 using Database Connection Signup (SPA-compatible)
#     """
#     AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
#     AUTH0_CLIENT_ID = config('CLIENT_ID', default='').strip()
#
#     logging.info(f"Creating Auth0 user (DB signup) for {email}")
#
#     # Validate configuration
#     if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID]) or ' ' in AUTH0_DOMAIN:
#         raise ValueError("Invalid Auth0 configuration")
#
#     signup_url = f"https://{AUTH0_DOMAIN}/dbconnections/signup"
#
#     payload = {
#         "client_id": AUTH0_CLIENT_ID,
#         "email": email,
#         "password": password,
#         "connection": "Username-Password-Authentication",
#         "given_name": first_name or "",
#         "family_name": last_name or "",
#         "name": f"{first_name or ''} {last_name or ''}".strip() or email.split("@")[0],
#     }
#
#     try:
#         resp = requests.post(signup_url, json=payload, timeout=10)
#         logging.info(f"Signup status: {resp.status_code}")
#
#         if resp.status_code == 200:
#             auth0_user = resp.json()
#             return f"auth0|{auth0_user.get('_id')}"  # Auth0 user_id
#
#         elif resp.status_code == 400 and "user already exists" in resp.text.lower():
#             logging.warning(f"User already exists in Auth0: {email}")
#             return None
#
#         else:
#             logging.error(f"Auth0 signup failed: {resp.text}")
#             resp.raise_for_status()
#
#     except requests.RequestException as e:
#         logging.exception(f"Auth0 signup failed for {email}: {str(e)}")
#         raise


# def update_user_in_auth0(lookup_email, auth0_updates):
#     """
#     Update a user's fields in Auth0 using M2M credentials.
#
#     Args:
#         lookup_email: The current email to find the user in Auth0.
#         auth0_updates: Dict of Auth0 fields to update. Supported keys:
#                        - email, email_verified, verify_email
#                        - given_name (first_name)
#                        - family_name (last_name)
#     """
#
#     AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
#     AUTH0_CLIENT_ID = config('CLIENT_ID', default='').strip()
#     AUTH0_CLIENT_SECRET = config('CLIENT_SECRET', default='').strip()
#
#     # Normalize lookup email to lowercase (Auth0 stores emails in lowercase)
#     lookup_email = lookup_email.strip().lower()
#
#     logging.info(f"Updating Auth0 user (lookup: {lookup_email}) with fields: {list(auth0_updates.keys())}")
#
#     if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]) or ' ' in AUTH0_DOMAIN:
#         raise ValueError("Invalid Auth0 configuration")
#
#     # Step 1: Get Management API token
#     token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
#     token_payload = {
#         "grant_type": "client_credentials",
#         "client_id": AUTH0_CLIENT_ID,
#         "client_secret": AUTH0_CLIENT_SECRET,
#         "audience": f"https://{AUTH0_DOMAIN}/api/v2/"
#     }
#
#     try:
#         logging.info(f"Requesting Management API token from {token_url}")
#         token_resp = requests.post(token_url, json=token_payload, timeout=10)
#
#         if token_resp.status_code != 200:
#             logging.error(f"Token request failed: {token_resp.status_code} - {token_resp.text}")
#
#         token_resp.raise_for_status()
#         access_token = token_resp.json()["access_token"]
#         logging.info("Successfully obtained Management API token")
#     except requests.RequestException:
#         logging.exception("Failed to obtain Auth0 Management API token")
#         raise
#
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }
#
#     # Step 2: Find user by email
#     users_by_email_url = f"https://{AUTH0_DOMAIN}/api/v2/users-by-email"
#     params = {"email": lookup_email}
#
#     try:
#         logging.info(f"Searching for Auth0 user with email: {lookup_email}")
#         search_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
#         search_resp.raise_for_status()
#         users = search_resp.json()
#
#         if not users:
#             raise ValueError(f"No Auth0 user found with email {lookup_email}")
#
#         auth0_user = users[0]
#         auth0_user_id = users[0]["user_id"]
#         logging.info(f"Found Auth0 user: {auth0_user_id}")
#
#     except requests.RequestException:
#         logging.exception("Failed to lookup Auth0 user by email")
#         raise
#
#     # Step 3: Update user with provided fields
#     update_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{auth0_user_id}"
#
#     # Normalize email in the payload if present
#     if 'email' in auth0_updates:
#         auth0_updates['email'] = auth0_updates['email'].strip().lower()
#     if 'given_name' in auth0_updates or 'family_name' in auth0_updates:
#         given_name = auth0_updates.get('given_name', auth0_user.get('given_name', ''))
#         family_name = auth0_updates.get('family_name', auth0_user.get('family_name', ''))
#         auth0_updates['name'] = f"{given_name} {family_name}".strip()
#
#     try:
#         logging.info(f"Updating Auth0 user {auth0_user_id} with payload: {auth0_updates}")
#         resp = requests.patch(update_url, headers=headers, json=auth0_updates, timeout=10)
#         logging.info(f"Auth0 update status: {resp.status_code}")
#
#         if resp.status_code == 200:
#             logging.info(f"Auth0 user {auth0_user_id} updated successfully")
#             return auth0_user_id
#
#         try:
#             error_body = resp.json()
#         except ValueError:
#             error_body = resp.text
#
#         logging.error(
#             "Auth0 user update failed",
#             extra={
#                 "auth0_user_id": auth0_user_id,
#                 "updates": auth0_updates,
#                 "status": resp.status_code,
#                 "response": error_body
#             }
#         )
#         resp.raise_for_status()
#
#     except requests.RequestException:
#         logging.exception("Auth0 user update request failed")
#         raise


def update_user_in_auth0(lookup_email, auth0_updates):
    """
    Update a user's fields in Auth0 using M2M credentials.
    Only updates users with UPA (Username-Password-Authentication) connection.
    Social/enterprise connections (Google, Microsoft, etc.) are skipped.

    Args:
        lookup_email: The current email to find the user in Auth0.
        auth0_updates: Dict of Auth0 fields to update. Supported keys:
                       - email, email_verified, verify_email
                       - given_name (first_name)
                       - family_name (last_name)
    """

    AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
    AUTH0_CLIENT_ID = config('CLIENT_ID', default='').strip()
    AUTH0_CLIENT_SECRET = config('CLIENT_SECRET', default='').strip()

    lookup_email = lookup_email.strip().lower()

    logging.info(f"Updating Auth0 user (lookup: {lookup_email}) with fields: {list(auth0_updates.keys())}")

    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]) or ' ' in AUTH0_DOMAIN:
        raise ValueError("Invalid Auth0 configuration")

    # Step 1: Get Management API token
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/"
    }

    try:
        logging.info(f"Requesting Management API token from {token_url}")
        token_resp = requests.post(token_url, json=token_payload, timeout=10)

        if token_resp.status_code != 200:
            logging.error(f"Token request failed: {token_resp.status_code} - {token_resp.text}")

        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        logging.info("Successfully obtained Management API token")
    except requests.RequestException:
        logging.exception("Failed to obtain Auth0 Management API token")
        raise

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 2: Find user by email — filter for UPA connection only
    users_by_email_url = f"https://{AUTH0_DOMAIN}/api/v2/users-by-email"
    params = {"email": lookup_email}

    try:
        logging.info(f"Searching for Auth0 user with email: {lookup_email}")
        search_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
        search_resp.raise_for_status()
        users = search_resp.json()

        if not users:
            raise ValueError(f"No Auth0 user found with email {lookup_email}")

        # Filter for UPA user only — social connections (Google, Microsoft, etc.)
        # cannot be updated via Management API for fields like email/password
        auth0_user = next(
            (
                u for u in users
                if any(
                identity.get("connection") == "Username-Password-Authentication"
                for identity in u.get("identities", [])
            )
            ),
            None
        )

        if not auth0_user:
            found_connections = [
                identity.get("connection")
                for u in users
                for identity in u.get("identities", [])
            ]
            logging.warning(
                f"No UPA user found for email {lookup_email}. "
                f"Found connections: {found_connections}. "
                f"Skipping Auth0 update — social/enterprise accounts cannot be updated via Management API."
            )
            return None

        auth0_user_id = auth0_user["user_id"]
        logging.info(f"Found UPA Auth0 user: {auth0_user_id}")

    except requests.RequestException:
        logging.exception("Failed to lookup Auth0 user by email")
        raise

    # Step 3: Update UPA user with provided fields
    update_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{auth0_user_id}"

    if 'email' in auth0_updates:
        auth0_updates['email'] = auth0_updates['email'].strip().lower()
    if 'given_name' in auth0_updates or 'family_name' in auth0_updates:
        given_name = auth0_updates.get('given_name', auth0_user.get('given_name', ''))
        family_name = auth0_updates.get('family_name', auth0_user.get('family_name', ''))
        auth0_updates['name'] = f"{given_name} {family_name}".strip()

    try:
        logging.info(f"Updating Auth0 UPA user {auth0_user_id} with payload: {auth0_updates}")
        resp = requests.patch(update_url, headers=headers, json=auth0_updates, timeout=10)
        logging.info(f"Auth0 update status: {resp.status_code}")

        if resp.status_code == 200:
            logging.info(f"Auth0 UPA user {auth0_user_id} updated successfully")
            return auth0_user_id

        try:
            error_body = resp.json()
        except ValueError:
            error_body = resp.text

        logging.error(
            "Auth0 user update failed",
            extra={
                "auth0_user_id": auth0_user_id,
                "updates": auth0_updates,
                "status": resp.status_code,
                "response": error_body
            }
        )
        resp.raise_for_status()

    except requests.RequestException:
        logging.exception("Auth0 UPA user update request failed")
        raise


def get_auth0_userinfo(access_token):
    """
    Fetch user profile from Auth0 /userinfo endpoint

    Args:
        access_token: User's access token from frontend authentication

    Returns:
        dict: User profile data or None if request fails
    """
    try:
        auth0_domain = config("AUTH0_DOMAIN", default='').strip()

        if not auth0_domain:
            logging.error("AUTH0_DOMAIN not configured")
            return None

        url = f"https://{auth0_domain}/userinfo"

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )

        if response.status_code != 200:
            logging.error(
                f"Auth0 /userinfo failed: {response.status_code} - {response.text}"
            )
            return None

        user_data = response.json()
        logging.info(f"Successfully fetched user info for: {user_data.get('email', 'unknown')}")
        return user_data

    except requests.RequestException as e:
        logging.error(f"Auth0 /userinfo request error: {e}")
        return None
    except Exception as e:
        logging.error(f"Auth0 /userinfo unexpected error: {e}")
        return None


# def check_user_exists_auth0(email):
#     '''
#
#     :param email:
#     :return: auth0_id
#
#     this function is used to check if the user present in the Auth0 DB but not registered in the user's DataBase.
#     '''
#     AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
#     AUTH0_CLIENT_ID = config('CLIENT_ID', default='').strip()
#     AUTH0_CLIENT_SECRET = config('CLIENT_SECRET', default='').strip()
#
#     # Normalize email to lowercase (Auth0 stores emails in lowercase) and check if it exists
#     email = email.strip().lower()
#
#     if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]) or ' ' in AUTH0_DOMAIN:
#         raise ValueError("Invalid Auth0 configuration")
#
#         # Step 1: Get Management API token
#     token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
#     token_payload = {
#         "grant_type": "client_credentials",
#         "client_id": AUTH0_CLIENT_ID,
#         "client_secret": AUTH0_CLIENT_SECRET,
#         "audience": f"https://{AUTH0_DOMAIN}/api/v2/"
#     }
#
#     try:
#         logging.info(f"Requesting Management API token from {token_url}")
#         token_resp = requests.post(token_url, json=token_payload, timeout=10)
#
#         if token_resp.status_code != 200:
#             logging.error(f"Token request failed: {token_resp.status_code} - {token_resp.text}")
#
#         token_resp.raise_for_status()
#         access_token = token_resp.json()["access_token"]
#         logging.info("Successfully obtained Management API token")
#     except requests.RequestException:
#         logging.exception("Failed to obtain Auth0 Management API token")
#         raise
#
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }
#     users_by_email_url = f"https://{AUTH0_DOMAIN}/api/v2/users-by-email"
#     params = {"email": email}
#
#     try:
#         logging.info(f"Searching for Auth0 user with email: {email}")
#         search_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
#         search_resp.raise_for_status()
#         users = search_resp.json()
#
#         if not users:
#             logging.exception(f"No Auth0 user found with email {email}")
#             return []
#
#         # auth0_user_id = users[0]["user_id"]
#         return [
#             logging.info(f"Found Auth0 user: {auth0_user_id}")
#
#             {
#                 "user_id": u["user_id"],
#                 "connection": u.get("identities", [{}])[0].get("connection"),
#             }
#         for u in users
#         ]
#     except:
#         logging.exception("Failed to lookup Auth0 user by email")
#         raise
#
#     return auth0_user_id


def check_user_exists_auth0(email):
    AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
    AUTH0_CLIENT_ID = config('CLIENT_ID', default='').strip()
    AUTH0_CLIENT_SECRET = config('CLIENT_SECRET', default='').strip()

    email = email.strip().lower()

    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]) or ' ' in AUTH0_DOMAIN:
        raise ValueError("Invalid Auth0 configuration")

    # Step 1: Get token
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/"
    }

    try:
        token_resp = requests.post(token_url, json=token_payload, timeout=10)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
    except requests.RequestException:
        logging.exception("Failed to obtain Auth0 token")
        raise

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 2: Search user across ALL connections
    users_by_email_url = f"https://{AUTH0_DOMAIN}/api/v2/users-by-email"
    params = {"email": email}

    try:
        search_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
        search_resp.raise_for_status()
        users = search_resp.json()

        if not users:
            return []

        result = []
        for u in users:
            connection = None
            identities = u.get("identities", [])
            if identities:
                connection = identities[0].get("connection")

            result.append({
                "user_id": u.get("user_id"),
                "email": u.get("email"),
                "connection": connection
            })

        # ✅ Prefer DB connection if exists
        result.sort(key=lambda x: x["connection"] != "Username-Password-Authentication")

        return result

    except Exception:
        logging.exception("Failed to lookup Auth0 user by email")
        raise


# # existing code for checking auth0
# def check_user_exists_auth0(email):
#     AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='').strip()
#     AUTH0_CLIENT_ID = config('CLIENT_ID', default='').strip()
#     AUTH0_CLIENT_SECRET = config('CLIENT_SECRET', default='').strip()
#
#     email = email.strip().lower()
#
#     if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]) or ' ' in AUTH0_DOMAIN:
#         raise ValueError("Invalid Auth0 configuration")
#
#     # Step 1: Get token
#     token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
#     token_payload = {
#         "grant_type": "client_credentials",
#         "client_id": AUTH0_CLIENT_ID,
#         "client_secret": AUTH0_CLIENT_SECRET,
#         "audience": f"https://{AUTH0_DOMAIN}/api/v2/"
#     }
#
#     try:
#         token_resp = requests.post(token_url, json=token_payload, timeout=10)
#         token_resp.raise_for_status()
#         access_token = token_resp.json()["access_token"]
#     except requests.RequestException:
#         logging.exception("Failed to obtain Auth0 token")
#         raise
#
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }
#
#     # Step 2: Search user
#     users_by_email_url = f"https://{AUTH0_DOMAIN}/api/v2/users-by-email"
#     params = {"email": email}
#
#     try:
#         search_resp = requests.get(users_by_email_url, headers=headers, params=params, timeout=10)
#         search_resp.raise_for_status()
#         users = search_resp.json()
#
#         # No user → return empty list
#         if not users:
#             logging.info(f"No Auth0 user found with email {email}")
#             return []
#
#         result = []
#
#         for u in users:
#             user_data = {
#                 "user_id": u["user_id"],
#                 "connection": u.get("identities", [{}])[0].get("connection"),
#             }
#             logging.info(f"Found Auth0 user: {user_data}")
#             result.append(user_data)
#
#         return result
#
#     except Exception:
#         logging.exception("Failed to lookup Auth0 user by email")
#         raise


def generate_auth0_password(first_name=None, last_name=None, email=None):
    """
    Generate an Auth0-compliant password of EXACTLY 14 characters.

    Guarantees:
    - 14 characters total
    - ≥1 uppercase
    - ≥1 lowercase
    - ≥1 digit
    - ≥1 special character
    """

    PASSWORD_LENGTH = 14

    # Normalize inputs
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    email_part = (email.split("@")[0] if email else "user")

    # Clean base (optional entropy source)
    base = f"{first}{last}{email_part}"
    base = re.sub(r"[^a-zA-Z]", "", base)

    # Character pools
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*()-_=+[]{}"

    # Mandatory Auth0-required characters
    password_chars = [
        secrets.choice(upper),  # Uppercase
        secrets.choice(lower),  # Lowercase
        secrets.choice(digits),  # Digit
        secrets.choice(special),  # Special character
    ]

    # Fill remaining characters (14 - 4 = 10)
    all_chars = upper + lower + digits + special
    while len(password_chars) < PASSWORD_LENGTH:
        password_chars.append(secrets.choice(all_chars))

    # Shuffle to avoid predictable positions
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)
