"""Provision a Supabase Auth account that can sign in at /control with app_metadata.role = "host"."""
import argparse
import getpass
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings

HOST_ROLE = "host"
MIN_PASSWORD_LENGTH = 8


class ProvisionError(Exception):
    """A credential problem the operator can fix; never contains the password."""


def _headers(admin_key):
    return {
        "apikey": admin_key,
        "Authorization": f"Bearer {admin_key}",
        "Content-Type": "application/json",
    }


def _body(response):
    try:
        value = response.json()
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _reason(response, fallback):
    payload = _body(response)
    return payload.get("msg") or payload.get("error_description") or payload.get("message") or payload.get("error") or fallback


def _public_key(override=None):
    return override if override is not None else settings.SUPABASE_ANON_KEY


def validate_credentials(email, password):
    email = (email or "").strip()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ProvisionError("Enter a valid host email address.")
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ProvisionError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password.lower() == email.lower():
        raise ProvisionError("Password must not match the email address.")
    return email


def find_user(client, base_url, admin_key, email):
    response = client.get(
        f"{base_url}/auth/v1/admin/users",
        params={"filter": email},
        headers=_headers(admin_key),
    )
    if response.status_code != 200:
        raise ProvisionError(f"Supabase Auth user lookup failed ({response.status_code}): {_reason(response, 'service key rejected')}")
    users = _body(response).get("users") or []
    for user in users:
        if (user.get("email") or "").lower() == email.lower():
            return user
    return None


def create_user(client, base_url, admin_key, email, password):
    response = client.post(
        f"{base_url}/auth/v1/admin/users",
        headers=_headers(admin_key),
        json={"email": email, "password": password, "email_confirm": True, "app_metadata": {"role": HOST_ROLE}},
    )
    if response.status_code in (200, 201):
        return _body(response)
    if response.status_code == 422:
        raise ProvisionError(f"{email} already exists. Re-run with --rotate to reset its password and re-apply the host role.")
    raise ProvisionError(f"Host account creation failed ({response.status_code}): {_reason(response, 'unexpected error')}")


def update_user(client, base_url, admin_key, user, password):
    metadata = dict(user.get("app_metadata") or {})
    metadata["role"] = HOST_ROLE
    response = client.patch(
        f"{base_url}/auth/v1/admin/users/{user['id']}",
        headers=_headers(admin_key),
        json={"password": password, "app_metadata": metadata},
    )
    if response.status_code != 200:
        raise ProvisionError(f"Host account update failed ({response.status_code}): {_reason(response, 'unexpected error')}")
    return _body(response)


def verify_sign_in(client, base_url, email, password, public_key=None):
    """Replay the exact password grant the /control sign-in form uses."""
    public_key = _public_key(public_key)
    if not public_key:
        return None
    response = client.post(
        f"{base_url}/auth/v1/token?grant_type=password",
        headers={"apikey": public_key, "Authorization": f"Bearer {public_key}", "Content-Type": "application/json"},
        json={"email": email, "password": password},
    )
    if response.status_code != 200:
        raise ProvisionError(f"Sign-in verification failed ({response.status_code}): {_reason(response, 'check the account credentials')}")
    role = (_body(response).get("user") or {}).get("app_metadata", {}).get("role")
    if role != HOST_ROLE:
        raise ProvisionError("Sign-in succeeded but app_metadata.role is not 'host'; the account would be rejected at /control.")
    return True


def provision_host(email, password, *, rotate=False, verify=True, base_url=None, public_key=None, client=None):
    base_url = (base_url or settings.SUPABASE_URL).rstrip("/")
    admin_key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not base_url or not admin_key:
        raise ProvisionError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_SECRET_KEY must be set in backend/.env.")
    email = validate_credentials(email, password)
    owned = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        existing = find_user(client, base_url, admin_key, email)
        if existing:
            if not rotate:
                raise ProvisionError(f"{email} already exists. Re-run with --rotate to reset its password and re-apply the host role.")
            user = update_user(client, base_url, admin_key, existing, password)
            action = "updated"
        else:
            user = create_user(client, base_url, admin_key, email, password)
            action = "created"
        if (user.get("app_metadata") or {}).get("role") != HOST_ROLE:
            raise ProvisionError("Account was stored without app_metadata.role = 'host'; it would be rejected at /control.")
        verified = verify_sign_in(client, base_url, email, password, public_key) if verify else None
        return {"action": action, "email": email, "id": user.get("id"), "role": HOST_ROLE, "verified": verified}
    finally:
        if owned:
            client.close()


def _read_password(args):
    if args.password:
        return args.password
    if not sys.stdin.isatty():
        raise ProvisionError("No password supplied. Pass --password or run the command in an interactive terminal.")
    first = getpass.getpass("Host password: ")
    if not first:
        raise ProvisionError("Password must not be empty.")
    if first != getpass.getpass("Confirm password: "):
        raise ProvisionError("Passwords do not match.")
    return first


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Host sign-in email address")
    parser.add_argument("--password", help="Host password (at least 8 characters); prompted securely when omitted")
    parser.add_argument("--rotate", action="store_true", help="Reset the password of an existing account and re-apply the host role")
    parser.add_argument("--no-verify", action="store_true", help="Skip the password sign-in verification")
    args = parser.parse_args()
    try:
        result = provision_host(args.email, _read_password(args), rotate=args.rotate, verify=not args.no_verify)
    except ProvisionError as exc:
        parser.exit(1, f"Host provisioning failed: {exc}\n")
    except httpx.HTTPError:
        parser.exit(1, "Host provisioning failed: Supabase Auth is unreachable; check the network and backend/.env.\n")
    print("Host account ready")
    print(f"Email: {result['email']}")
    print(f"User ID: {result['id']}")
    print(f"Action: {result['action']}")
    print(f"app_metadata.role: {result['role']}")
    if result["verified"] is None:
        print("Sign-in check: skipped (no public key configured)")
    else:
        print("Sign-in check: passed")
    print(f"Sign in at {settings.FRONTEND_URL}/control")
    return 0


if __name__ == "__main__":
    sys.exit(main())
