import pytest

from app.core.security.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security.password import get_password_hash, verify_password
from app.core.exceptions.auth import InvalidTokenError


@pytest.mark.unit
def test_password_hash_and_verify():
    password = "supersecret123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)


@pytest.mark.unit
def test_wrong_password_fails():
    hashed = get_password_hash("correct")
    assert not verify_password("wrong", hashed)


@pytest.mark.unit
def test_access_token_roundtrip():
    token = create_access_token("user-123", extra={"role": "user"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["role"] == "user"


@pytest.mark.unit
def test_refresh_token_roundtrip():
    token = create_refresh_token("user-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


@pytest.mark.unit
def test_invalid_token_raises():
    with pytest.raises(InvalidTokenError):
        decode_token("not.a.valid.token")
