"""Deployment defaults must permit authenticated Render/Vercel requests."""
import pytest
from app.config import player_cookie_samesite


def test_production_cookie_defaults_to_none(monkeypatch):
    monkeypatch.delenv('PLAYER_COOKIE_SAMESITE', raising=False)
    assert player_cookie_samesite('production') == 'none'
    assert player_cookie_samesite('development') == 'lax'


def test_same_site_override_is_preserved(monkeypatch):
    monkeypatch.setenv('PLAYER_COOKIE_SAMESITE', 'lax')
    assert player_cookie_samesite('production') == 'lax'


def test_none_requires_secure_environment(monkeypatch):
    monkeypatch.setenv('PLAYER_COOKIE_SAMESITE', 'none')
    with pytest.raises(ValueError, match='secure cookies'):
        player_cookie_samesite('development')


def test_invalid_cookie_policy_is_rejected(monkeypatch):
    monkeypatch.setenv('PLAYER_COOKIE_SAMESITE', 'invalid')
    with pytest.raises(ValueError, match='lax, strict or none'):
        player_cookie_samesite('production')
