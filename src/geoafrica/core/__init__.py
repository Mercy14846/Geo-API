"""
GeoAfrica Core Package
"""
from geoafrica.core.config import GeoAfricaConfig, get_config, configure
from geoafrica.core.session import GeoAfricaSession, get_session
from geoafrica.core.exceptions import (
    GeoAfricaError,
    DataNotFoundError,
    APIKeyMissingError,
    RateLimitError,
    InvalidBoundingBoxError,
    UnsupportedFormatError,
)

__all__ = [
    "GeoAfricaConfig",
    "get_config",
    "configure",
    "GeoAfricaSession",
    "get_session",
    "GeoAfricaError",
    "DataNotFoundError",
    "APIKeyMissingError",
    "RateLimitError",
    "InvalidBoundingBoxError",
    "UnsupportedFormatError",
]
