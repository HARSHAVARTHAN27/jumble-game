"""Transport recovery must not duplicate game writes or hide auth outages."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from supabase import ClientOptions, create_client

from app.database_http import DatabaseHttpClient, create_database_http_client
from app.main import global_exception_handler
from app.utils import validators


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_transient_read_recovers_once(method):
    calls = []

    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadError("connection interrupted", request=request)
        return httpx.Response(200, json=[])

    with DatabaseHttpClient(transport=httpx.MockTransport(handle)) as client:
        assert client.request(method, "https://database.test/table").status_code == 200
    assert len(calls) == 2


@pytest.mark.parametrize("method,expected", [("GET", 2), ("POST", 1), ("PATCH", 1), ("DELETE", 1)])
def test_retry_is_bounded_and_writes_are_not_replayed(method, expected):
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadError("private connection details", request=request)

    with DatabaseHttpClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(httpx.ReadError):
            client.request(method, "https://database.test/table")
    assert len(calls) == expected


def test_supabase_custom_transport_keeps_auth_and_schema_headers():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    with DatabaseHttpClient(transport=httpx.MockTransport(handle)) as client:
        database = create_client("https://database.test", "test-secret", options=ClientOptions(
            httpx_client=client, persist_session=False, auto_refresh_token=False))
        assert database.from_("employees").select("name").execute().data == []
    assert requests[0].headers["apikey"] == "test-secret"
    assert requests[0].headers["authorization"] == "Bearer test-secret"
    assert requests[0].headers["accept-profile"] == "public"


def test_http2_is_disabled_and_timeout_bounded():
    with create_database_http_client() as client:
        assert client._transport._pool._http2 is False
        assert client.timeout.read == 5
        assert client.timeout.pool == 3


def test_transport_error_returns_safe_temporary_response():
    response = asyncio.run(global_exception_handler(None, httpx.ReadError("private connection details")))
    assert response.status_code == 503
    assert response.headers["retry-after"] == "2"
    assert json.loads(response.body)["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert b"private connection details" not in response.body


def test_host_connection_failure_is_not_invalid_credentials(monkeypatch):
    def fail(token):
        raise httpx.ReadError("connection interrupted")

    monkeypatch.setattr(validators, "supabase", SimpleNamespace(auth=SimpleNamespace(get_user=fail)))
    with pytest.raises(httpx.ReadError):
        validators.require_host(HTTPAuthorizationCredentials(scheme="Bearer", credentials="test"))
