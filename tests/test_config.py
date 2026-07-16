"""Validacao de credenciais fortes fora de development (hardening de startup)."""

import pytest

from app.config import Settings

_STRONG = "x" * 32


def test_production_weak_secret_raises():
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret="dev-secret-change-me", admin_password_hash="x")


def test_production_short_secret_raises():
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret="curto", admin_password_hash="x")


def test_production_missing_admin_hash_raises():
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret=_STRONG, admin_password_hash="")


def test_production_strong_ok():
    Settings(app_env="production", jwt_secret=_STRONG, admin_password_hash="x")  # nao levanta


def test_development_defaults_ok():
    Settings(app_env="development")  # defaults fracos sao aceitos em dev
