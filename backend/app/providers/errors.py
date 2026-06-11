"""Unified provider errors."""

from app.services.minimax_errors import MiniMaxAPIError


class ProviderError(RuntimeError):
    """Base provider error with retry hint."""

    def __init__(self, message: str, *, retryable: bool = True, provider_id: str = ""):
        self.retryable = retryable
        self.provider_id = provider_id
        super().__init__(message)

    @property
    def user_message(self) -> str:
        return str(self)


def is_non_retryable(exc: Exception) -> bool:
    if isinstance(exc, ProviderError):
        return not exc.retryable
    if isinstance(exc, MiniMaxAPIError):
        return not exc.retryable
    return False


def user_facing_message(exc: Exception) -> str:
    if isinstance(exc, ProviderError):
        return exc.user_message
    if isinstance(exc, MiniMaxAPIError):
        return exc.user_message
    return str(exc)
