"""Custom exceptions."""


class CallAssistError(Exception):
    """Base error."""


class RateLimitExceeded(CallAssistError):
    """User exceeded their request quota."""


class TierAccessError(CallAssistError):
    """Feature not available on the user's subscription tier."""


class IntegrationError(CallAssistError):
    """An external API call failed."""


class NotFoundError(CallAssistError):
    """Requested record does not exist."""
