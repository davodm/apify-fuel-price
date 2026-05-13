"""Custom errors for clearer logs and upstream attribution."""


class FuelPriceError(Exception):
    """Base class for recoverable Actor domain errors."""


class UnsupportedCountryError(FuelPriceError):
    """Raised when ``country`` is not implemented."""


class ParseError(FuelPriceError):
    """Raised when HTML/JSON from a source could not be interpreted."""


class UpstreamHttpError(FuelPriceError):
    """Raised when an HTTP request fails or returns an unexpected status."""
