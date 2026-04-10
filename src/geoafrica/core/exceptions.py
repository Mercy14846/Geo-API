"""
GeoAfrica Custom Exceptions
============================
Merczcord Technologies Ltd.
"""


class GeoAfricaError(Exception):
    """Base exception for all GeoAfrica errors."""

    pass


class DataNotFoundError(GeoAfricaError):
    """Raised when a requested dataset or region cannot be found."""

    def __init__(self, message: str, query: str = "") -> None:
        self.query = query
        super().__init__(message)


class APIKeyMissingError(GeoAfricaError):
    """Raised when a required API key is not configured."""

    def __init__(self, provider: str, env_var: str) -> None:
        self.provider = provider
        self.env_var = env_var
        super().__init__(
            f"API key for '{provider}' is missing. "
            f"Set it via: export {env_var}=<your_key>  "
            f"or: geoafrica config set {env_var} <your_key>"
        )


class RateLimitError(GeoAfricaError):
    """Raised when a data provider rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int = 60) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for '{provider}'. "
            f"Please wait {retry_after} seconds before retrying."
        )


class InvalidBoundingBoxError(GeoAfricaError):
    """Raised when a bounding box is malformed."""

    def __init__(self, bbox: object) -> None:
        super().__init__(
            f"Invalid bounding box: {bbox}. Expected [min_lon, min_lat, max_lon, max_lat]."
        )


class UnsupportedFormatError(GeoAfricaError):
    """Raised when an unsupported file format is requested."""

    def __init__(self, fmt: str, supported: list) -> None:
        self.fmt = fmt
        super().__init__(f"Unsupported format '{fmt}'. Supported formats: {', '.join(supported)}")


class CacheError(GeoAfricaError):
    """Raised when there is an error reading or writing the cache."""

    pass
