from typing import Any


class AppError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    detail: str = "An unexpected error occurred"

    def __init__(
        self,
        detail: str | None = None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.error_code = error_code or self.__class__.error_code
        self.extra = extra or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "detail": self.detail,
            **self.extra,
        }
