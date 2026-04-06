"""
Tests for geoafrica.core.config and geoafrica.core.exceptions
"""
import os
import pytest


class TestGeoAfricaConfig:
    def test_default_cache_dir(self):
        from geoafrica.core.config import GeoAfricaConfig
        from pathlib import Path
        cfg = GeoAfricaConfig()
        assert cfg.cache_dir.exists()
        assert "geoafrica" in str(cfg.cache_dir)

    def test_custom_cache_dir(self, tmp_path):
        from geoafrica.core.config import GeoAfricaConfig
        cfg = GeoAfricaConfig(cache_dir=str(tmp_path / "test_cache"))
        assert cfg.cache_dir == tmp_path / "test_cache"
        assert cfg.cache_dir.exists()

    def test_default_timeout(self):
        from geoafrica.core.config import GeoAfricaConfig
        cfg = GeoAfricaConfig()
        assert cfg.timeout == 30

    def test_set_and_get_api_key(self, tmp_path):
        from geoafrica.core.config import GeoAfricaConfig
        cfg = GeoAfricaConfig(cache_dir=str(tmp_path))
        cfg.set_api_key("NASA_FIRMS", "test_key_abc", persist=False)
        result = cfg.get_api_key("NASA_FIRMS")
        assert result == "test_key_abc"

    def test_env_var_override(self, monkeypatch):
        from geoafrica.core.config import GeoAfricaConfig
        monkeypatch.setenv("GEOAFRICA_FIRMS_KEY", "env_key_999")
        cfg = GeoAfricaConfig()
        assert cfg.get_api_key("NASA_FIRMS") == "env_key_999"

    def test_require_api_key_raises_when_missing(self):
        from geoafrica.core.config import GeoAfricaConfig
        from geoafrica.core.exceptions import APIKeyMissingError
        key = os.environ.pop("GEOAFRICA_FIRMS_KEY", None)
        try:
            cfg = GeoAfricaConfig()
            with pytest.raises(APIKeyMissingError) as exc_info:
                cfg.require_api_key("NASA_FIRMS")
            assert "NASA_FIRMS" in str(exc_info.value)
        finally:
            if key:
                os.environ["GEOAFRICA_FIRMS_KEY"] = key

    def test_info_returns_dict(self):
        from geoafrica.core.config import GeoAfricaConfig
        cfg = GeoAfricaConfig()
        info = cfg.info()
        assert "cache_dir" in info
        assert "api_keys" in info
        assert "timeout_seconds" in info

    def test_configure_singleton(self):
        from geoafrica.core.config import configure, get_config
        cfg = configure(timeout=45, verbose=True)
        assert cfg.timeout == 45
        assert cfg.verbose is True
        assert get_config() is cfg


class TestExceptions:
    def test_data_not_found(self):
        from geoafrica.core.exceptions import DataNotFoundError
        exc = DataNotFoundError("Not found", query="test_query")
        assert exc.query == "test_query"
        assert "Not found" in str(exc)

    def test_api_key_missing(self):
        from geoafrica.core.exceptions import APIKeyMissingError
        exc = APIKeyMissingError("NASA_FIRMS", "GEOAFRICA_FIRMS_KEY")
        assert exc.provider == "NASA_FIRMS"
        assert "GEOAFRICA_FIRMS_KEY" in str(exc)

    def test_rate_limit_error(self):
        from geoafrica.core.exceptions import RateLimitError
        exc = RateLimitError("overpass-api.de", retry_after=120)
        assert exc.retry_after == 120
        assert "120" in str(exc)

    def test_invalid_bbox(self):
        from geoafrica.core.exceptions import InvalidBoundingBoxError
        exc = InvalidBoundingBoxError([1, 2])
        assert "[1, 2]" in str(exc)

    def test_unsupported_format(self):
        from geoafrica.core.exceptions import UnsupportedFormatError
        exc = UnsupportedFormatError("xyz", ["geojson", "shp"])
        assert "xyz" in str(exc)
        assert "geojson" in str(exc)

    def test_exception_hierarchy(self):
        from geoafrica.core.exceptions import (
            GeoAfricaError, DataNotFoundError, APIKeyMissingError, RateLimitError
        )
        assert issubclass(DataNotFoundError, GeoAfricaError)
        assert issubclass(APIKeyMissingError, GeoAfricaError)
        assert issubclass(RateLimitError, GeoAfricaError)
