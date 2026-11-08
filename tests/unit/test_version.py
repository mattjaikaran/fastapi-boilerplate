import tomllib
from pathlib import Path

from app.config.settings import Settings, _project_version


def _pyproject_version() -> str:
    root = Path(__file__).resolve().parents[2]
    with (root / "pyproject.toml").open("rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def test_project_version_matches_pyproject() -> None:
    assert _project_version() == _pyproject_version()


def test_app_version_defaults_to_project_version(monkeypatch) -> None:
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("JWT_SECRET_KEY", "y" * 32)
    assert _pyproject_version() == Settings(_env_file=None).APP_VERSION


def test_app_version_env_override(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("JWT_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    assert Settings(_env_file=None).APP_VERSION == "9.9.9"
