"""Bounded HTTP/1.1 connections for the server's Supabase API calls."""
import httpx


class DatabaseHttpClient(httpx.Client):
    def send(self, request, **kwargs):
        try:
            return super().send(request, **kwargs)
        except (httpx.ReadError, httpx.ReadTimeout, httpx.RemoteProtocolError):
            # A read can be repeated safely. Never replay a write/RPC after an
            # ambiguous failure: it may already have committed on the server.
            if request.method not in ("GET", "HEAD"):
                raise
            return super().send(request, **kwargs)


def create_database_http_client():
    return DatabaseHttpClient(
        http1=True,
        http2=False,
        transport=httpx.HTTPTransport(http1=True, http2=False, retries=1,
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=10,
                                keepalive_expiry=5)),
        timeout=httpx.Timeout(5, connect=3, pool=3),
        follow_redirects=True,
    )
