import pytest

from app.core.exceptions.auth import InvalidTokenError
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security.password import get_password_hash, verify_password


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


# Hashes generated with passlib 1.7.4 + bcrypt 4.x before the switch to bcrypt.
PASSLIB_HASH = "$2b$12$YnOs.X1SV9lyfjcYXadz7uoQdv2yKMWzYUMnPYBh.VDkBLWQezri2"
PASSLIB_PASSWORD = "correct horse battery staple"
# passlib silently truncated this 80-byte password to 72 bytes.
PASSLIB_LONG_HASH = "$2b$12$c/72VCLijB5cj9sIEaCQcOHsMnVZwQBlysojuezh3g.9POTzy2DyC"
PASSLIB_LONG_PASSWORD = "a" * 80


@pytest.mark.unit
def test_legacy_passlib_hash_verifies():
    assert verify_password(PASSLIB_PASSWORD, PASSLIB_HASH)
    assert not verify_password("wrong", PASSLIB_HASH)


@pytest.mark.unit
def test_legacy_passlib_long_password_hash_verifies():
    assert verify_password(PASSLIB_LONG_PASSWORD, PASSLIB_LONG_HASH)
    assert verify_password("a" * 72, PASSLIB_LONG_HASH)


@pytest.mark.unit
def test_long_password_does_not_raise():
    hashed = get_password_hash("é" * 100)
    assert verify_password("é" * 100, hashed)


@pytest.mark.unit
def test_malformed_hash_returns_false():
    assert not verify_password("x", "not-a-bcrypt-hash")


@pytest.mark.unit
def test_expired_token_rejected():
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.config.settings import settings

    token = jwt.encode(
        {"sub": "u", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        decode_token(token)


@pytest.mark.unit
def test_decode_token_tolerates_small_clock_skew():
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.config.settings import settings

    future = datetime.now(UTC) + timedelta(seconds=5)
    token = jwt.encode(
        {"sub": "u", "iat": future, "exp": future + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_token(token)["sub"] == "u"


@pytest.mark.unit
def test_password_with_nul_is_rejected():
    from pydantic import ValidationError

    from app.api.auth.schemas import (
        ChangePasswordRequest,
        RegisterRequest,
        ResetPasswordRequest,
    )
    from app.api.users.schemas import UserCreate

    bad = "valid-pass\x00word"
    with pytest.raises(ValueError, match="NUL"):
        get_password_hash(bad)
    for model, kwargs in (
        (RegisterRequest, {"email": "a@example.com", "password": bad}),
        (UserCreate, {"email": "a@example.com", "password": bad}),
        (ResetPasswordRequest, {"token": "t", "new_password": bad}),
        (ChangePasswordRequest, {"current_password": "x", "new_password": bad}),
    ):
        with pytest.raises(ValidationError):
            model(**kwargs)
