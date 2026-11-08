import bcrypt

# bcrypt only uses the first 72 bytes of a password. passlib (with bcrypt<5)
# silently truncated longer passwords to 72 bytes; bcrypt>=5 raises ValueError
# instead. We truncate explicitly so hashes created by passlib keep verifying
# for users who chose long passwords.
BCRYPT_MAX_PASSWORD_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]


def get_password_hash(password: str) -> str:
    if "\x00" in password:
        raise ValueError("Password must not contain NUL characters")
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash (passlib also treated this as an error, not a match).
        return False
