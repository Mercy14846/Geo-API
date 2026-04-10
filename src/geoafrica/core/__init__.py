"""
GeoAfrica Core Package
"""

from geoafrica.core.config import GeoAfricaConfig, configure, get_config
from geoafrica.core.exceptions import (
    APIKeyMissingError,
    DataNotFoundError,
    GeoAfricaError,
    InvalidBoundingBoxError,
    RateLimitError,
    UnsupportedFormatError,
)
from geoafrica.core.session import GeoAfricaSession, get_session

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
