"""Create a superuser, or promote an existing user to superuser.

Credentials come from (highest priority first):
  1. --email / --password arguments
  2. SUPERUSER_EMAIL / SUPERUSER_PASSWORD environment variables
  3. FIRST_SUPERUSER_EMAIL / FIRST_SUPERUSER_PASSWORD (app settings, so the
     values in .env apply)
  4. An interactive prompt (the password prompt does not echo)

Without a terminal, the script exits with an error when a value is missing.
When APP_ENV is production, the script refuses the default password
("changeme").

The command is idempotent. If the user already exists, the script promotes the
user to superuser, activates and restores the account, and marks the email as verified. It
resets the password only when you pass --reset-password.

Usage:
    uv run python scripts/create_superuser.py --email admin@example.com
    make create-superuser EMAIL=admin@example.com
"""

import argparse
import asyncio
import getpass
import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.api.users.model import UserRole
from app.api.users.schemas import UserCreate
from app.api.users.service import UserService
from app.config.database import async_session_factory, engine
from app.config.settings import settings
from app.core.security import get_password_hash

MIN_PASSWORD_LENGTH = 8
DEFAULT_PASSWORD = "changeme"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a superuser or promote an existing user."
    )
    parser.add_argument("--email", help="Superuser email address")
    parser.add_argument(
        "--password",
        help="Superuser password (prefer the SUPERUSER_PASSWORD env var or the prompt)",
    )
    parser.add_argument("--first-name", default="Super", help="First name")
    parser.add_argument("--last-name", default="Admin", help="Last name")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Set the given password on an existing user",
    )
    return parser.parse_args()


def _require_tty(what: str) -> None:
    if not sys.stdin.isatty():
        sys.exit(f"Missing {what} and no terminal is available to prompt for it.")


def _resolve_email(arg: str | None) -> str:
    email = arg or os.environ.get("SUPERUSER_EMAIL") or settings.FIRST_SUPERUSER_EMAIL
    if not email:
        _require_tty("email (--email or SUPERUSER_EMAIL)")
        email = input("Email: ").strip()
    try:
        return str(TypeAdapter(EmailStr).validate_python(email))
    except ValidationError as exc:
        sys.exit(f"Invalid email address: {email!r} ({exc.errors()[0]['msg']})")


def _check_password(password: str | None) -> str:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if "\x00" in password:
        sys.exit("Password must not contain NUL characters.")
    if settings.APP_ENV == "production" and password == DEFAULT_PASSWORD:
        sys.exit(
            f"Refusing the default password {DEFAULT_PASSWORD!r} when "
            "APP_ENV=production. Set SUPERUSER_PASSWORD to a strong value."
        )
    return password


def _resolve_password(arg: str | None, *, required: bool) -> str | None:
    password = (
        arg or os.environ.get("SUPERUSER_PASSWORD") or settings.FIRST_SUPERUSER_PASSWORD
    )
    if password or not required:
        return password
    _require_tty("password (--password or SUPERUSER_PASSWORD)")
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords do not match.")
    return password


async def _run(args: argparse.Namespace) -> None:
    from app.models import register_all_models

    register_all_models()
    email = _resolve_email(args.email)

    try:
        async with async_session_factory() as db:
            service = UserService(db)
            user = await service.get_by_email(email)

            if user is None:
                password = _check_password(
                    _resolve_password(args.password, required=True)
                )
                user = await service.create(
                    UserCreate(
                        email=email,
                        password=password,
                        first_name=args.first_name,
                        last_name=args.last_name,
                    )
                )
                action = "Created"
            else:
                action = "Promoted"
                if args.reset_password:
                    password = _check_password(
                        _resolve_password(args.password, required=True)
                    )
                    user.hashed_password = get_password_hash(password)
                    action = "Promoted and reset password for"
                elif user.role == UserRole.superuser and user.is_active:
                    action = "Already a superuser:"

            user.role = UserRole.superuser
            user.is_active = True
            user.is_email_verified = True
            user.deleted_at = None
            db.add(user)
            await db.commit()
            print(f"✓ {action} {email}")
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    main()
