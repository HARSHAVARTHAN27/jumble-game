"""Host credential provisioning against a mocked Supabase Auth boundary; no cloud writes."""
import json

import httpx
import pytest
from app.config import settings
from scripts.create_host import ProvisionError, provision_host

BASE = "https://auth.test"
ADMIN = "service-role-test-key"
PUBLIC = "public-test-key"
EMAIL = "host@example.test"
PASSWORD = "correct-horse-42"
USER_ID = "d39b6c7a-cf92-4a41-a158-ce9839547ad0"


def transport(existing=None, role="host", create_status=201, sign_in_status=200, sign_in_role="host"):
    """Record requests and replay the Auth Admin password flow."""
    seen = []

    def handler(request):
        seen.append(request)
        path, query = request.url.path, request.url.query
        if request.method == "GET" and path == "/auth/v1/admin/users":
            users = [] if existing is None else [existing]
            return httpx.Response(200, json={"users": users})
        if request.method == "POST" and path == "/auth/v1/admin/users":
            if create_status != 201:
                return httpx.Response(create_status, json={"code": create_status, "msg": "email_exists"})
            body = json_body(request)
            assert body["email_confirm"] is True
            return httpx.Response(201, json={"id": USER_ID, "email": body["email"], "app_metadata": body["app_metadata"]})
        if request.method == "PATCH" and path.startswith("/auth/v1/admin/users/"):
            body = json_body(request)
            assert body["app_metadata"]["role"] == role
            return httpx.Response(200, json={"id": USER_ID, "email": EMAIL, "app_metadata": body["app_metadata"]})
        if request.method == "POST" and path == "/auth/v1/token":
            assert request.url.params.get("grant_type") == "password"
            assert json_body(request)["email"] == EMAIL
            if sign_in_status != 200:
                return httpx.Response(sign_in_status, json={"error": "invalid_grant", "error_description": "Invalid login credentials"})
            return httpx.Response(200, json={"access_token": "token", "user": {"app_metadata": {"role": sign_in_role}}})
        return httpx.Response(404, json={"msg": "unexpected request"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return client, seen


def json_body(request):
    return json.loads(request.content)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", BASE)
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", ADMIN)
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", PUBLIC)


def test_new_host_is_created_with_role_and_verified():
    client, seen = transport()
    result = provision_host(EMAIL, PASSWORD, base_url=BASE, public_key=PUBLIC, client=client)
    assert result == {"action": "created", "email": EMAIL, "id": USER_ID, "role": "host", "verified": True}
    admin_headers = [r.headers for r in seen if r.url.path.startswith("/auth/v1/admin/users") and r.method == "POST"]
    assert admin_headers[0]["apikey"] == ADMIN
    assert any(r.url.path == "/auth/v1/token" for r in seen)


def test_existing_account_requires_rotate():
    client, seen = transport(existing={"id": USER_ID, "email": EMAIL, "app_metadata": {"role": "host"}})
    with pytest.raises(ProvisionError, match="--rotate"):
        provision_host(EMAIL, PASSWORD, base_url=BASE, public_key=PUBLIC, client=client)
    assert not any(r.method in ("POST", "PATCH") and "admin/users" in r.url.path for r in seen)


def test_rotate_resets_password_and_preserves_metadata():
    existing = {"id": USER_ID, "email": EMAIL, "app_metadata": {"team": "production"}}
    client, seen = transport(existing=existing)
    result = provision_host(EMAIL, PASSWORD, rotate=True, base_url=BASE, public_key=PUBLIC, client=client)
    patched = json_body(next(r for r in seen if r.method == "PATCH"))
    assert patched["password"] == PASSWORD
    assert patched["app_metadata"] == {"team": "production", "role": "host"}
    assert result["action"] == "updated"
    assert result["verified"] is True


@pytest.mark.parametrize("email,password", [("not-an-email", PASSWORD), (EMAIL, "short"), (EMAIL, EMAIL)])
def test_invalid_credentials_are_rejected_before_any_request(email, password):
    client, seen = transport()
    with pytest.raises(ProvisionError):
        provision_host(email, password, base_url=BASE, public_key=PUBLIC, client=client)
    assert seen == []


def test_successful_sign_in_without_host_role_is_a_failure():
    client, seen = transport(sign_in_role="player")
    with pytest.raises(ProvisionError, match="app_metadata.role"):
        provision_host(EMAIL, PASSWORD, base_url=BASE, public_key=PUBLIC, client=client)


def test_failed_sign_in_reports_credentials_problem():
    client, seen = transport(sign_in_status=400)
    with pytest.raises(ProvisionError, match="Sign-in verification failed"):
        provision_host(EMAIL, PASSWORD, base_url=BASE, public_key=PUBLIC, client=client)


def test_missing_supabase_configuration_is_reported(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
    with pytest.raises(ProvisionError, match="backend/.env"):
        provision_host(EMAIL, PASSWORD, base_url=BASE, public_key=PUBLIC, client=transport()[0])


def test_verification_can_be_skipped():
    client, seen = transport()
    result = provision_host(EMAIL, PASSWORD, verify=False, base_url=BASE, public_key=PUBLIC, client=client)
    assert result["verified"] is None
    assert not any(r.url.path == "/auth/v1/token" for r in seen)
