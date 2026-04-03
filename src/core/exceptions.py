class ApplicationError(Exception):
    """Base application error."""


class UnauthorizedError(ApplicationError):
    """Raised when API key is invalid."""


class PaymentNotFoundError(ApplicationError):
    """Raised when payment is not found."""
