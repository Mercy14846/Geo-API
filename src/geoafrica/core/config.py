"""
GeoAfrica Configuration Manager
=================================
Merczcord Technologies Ltd.

Handles API keys, cache directory, and user settings.
Keys can be set via:
  1. Environment variables (highest priority)
  2. ~/.geoafrica/config.toml
  3. Explicit kwargs to GeoAfricaConfig()
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

# -------------------------------------------------------------------
# Default paths
# -------------------------------------------------------------------
_HOME = Path.home()
_CONFIG_DIR = _HOME / ".geoafrica"
_CACHE_DIR = _CONFIG_DIR / "cache"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"

# -------------------------------------------------------------------
# Environment variable names for each provider
# -------------------------------------------------------------------
ENV_KEYS = {
    "NASA_FIRMS": "GEOAFRICA_FIRMS_KEY",
    "OPENTOPODATA": "GEOAFRICA_OPENTOPO_KEY",
    "COPERNICUS_CDS": "GEOAFRICA_CDS_KEY",
    "HEALTHSITES": "GEOAFRICA_HEALTHSITES_KEY",
    "STADIA_MAPS": "GEOAFRICA_STADIA_KEY",
}


class GeoAfricaConfig:
    """
    Central configuration object for the GeoAfrica SDK.

    Parameters
    ----------
    cache_dir : str or Path, optional
        Directory to cache downloaded data. Defaults to ~/.geoafrica/cache/
    cache_ttl : int, optional
        Cache time-to-live in seconds. Defaults to 86400 (24 hours).
    timeout : int, optional
        Default HTTP request timeout in seconds. Defaults to 30.
    verbose : bool, optional
        If True, log download progress to stdout. Defaults to False.
    **api_keys
        Provider API keys. These override environment variables.
        e.g., GeoAfricaConfig(nasa_firms_key="abc123")
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        cache_ttl: int = 86400,
        timeout: int = 30,
        verbose: bool = False,
        **api_keys: str,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else _CACHE_DIR
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.verbose = verbose
        self._api_keys: dict[str, str] = {}

        # Load from file first, then override with env/kwargs
        self._load_file_config()
        self._load_env_vars()
        self._api_keys.update({k.upper(): v for k, v in api_keys.items()})

        # Ensure dirs exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_api_key(self, provider: str) -> str | None:
        """Return the API key for *provider*, or None if not set."""
        env_var = ENV_KEYS.get(provider.upper())
        if env_var:
            val = os.environ.get(env_var) or self._api_keys.get(env_var)
            return val
        return self._api_keys.get(provider.upper())

    def require_api_key(self, provider: str) -> str:
        """Return the API key or raise APIKeyMissingError."""
        from geoafrica.core.exceptions import APIKeyMissingError
        key = self.get_api_key(provider)
        if not key:
            env_var = ENV_KEYS.get(provider.upper(), f"GEOAFRICA_{provider.upper()}_KEY")
            raise APIKeyMissingError(provider, env_var)
        return key

    def set_api_key(self, provider: str, key: str, persist: bool = True) -> None:
        """
        Set an API key for *provider* and optionally persist to config file.

        Parameters
        ----------
        provider : str
            Provider name, e.g. 'NASA_FIRMS'
        key : str
            The API key string.
        persist : bool
            If True, save to ~/.geoafrica/config.toml
        """
        env_var = ENV_KEYS.get(provider.upper(), f"GEOAFRICA_{provider.upper()}_KEY")
        self._api_keys[env_var] = key
        if persist:
            self._save_key_to_file(env_var, key)

    def info(self) -> dict:
        """Return current configuration as a dict (keys redacted)."""
        configured = {
            p: "✓ set" if self.get_api_key(p) else "✗ not set"
            for p in ENV_KEYS
        }
        return {
            "cache_dir": str(self.cache_dir),
            "cache_ttl_seconds": self.cache_ttl,
            "timeout_seconds": self.timeout,
            "verbose": self.verbose,
            "api_keys": configured,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_env_vars(self) -> None:
        for env_var in ENV_KEYS.values():
            val = os.environ.get(env_var)
            if val:
                self._api_keys[env_var] = val

    def _load_file_config(self) -> None:
        if not _CONFIG_FILE.exists():
            return
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                try:
                    import tomllib  # type: ignore[no-redef]
                except ImportError:
                    try:
                        import tomli as tomllib  # type: ignore[no-redef]
                    except ImportError:
                        return
            with open(_CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            keys = data.get("api_keys", {})
            self._api_keys.update(keys)
            settings = data.get("settings", {})
            if "cache_ttl" in settings:
                self.cache_ttl = int(settings["cache_ttl"])
            if "timeout" in settings:
                self.timeout = int(settings["timeout"])
        except Exception as exc:
            warnings.warn(f"Could not read {_CONFIG_FILE}: {exc}", stacklevel=2)

    def _save_key_to_file(self, env_var: str, key: str) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if _CONFIG_FILE.exists():
            try:
                if sys.version_info >= (3, 11):
                    import tomllib
                else:
                    try:
                        import tomllib  # type: ignore[no-redef]
                    except ImportError:
                        try:
                            import tomli as tomllib  # type: ignore[no-redef]
                        except ImportError:
                            tomllib = None  # type: ignore[assignment]
                if tomllib:
                    with open(_CONFIG_FILE, "rb") as f:
                        existing = tomllib.load(f)
            except Exception:
                pass
        if "api_keys" not in existing:
            existing["api_keys"] = {}
        existing["api_keys"][env_var] = key
        # Write back as TOML manually (avoids tomli-w dependency)
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("# GeoAfrica SDK Configuration\n")
            f.write("# Generated by Merczcord Technologies Ltd.\n\n")
            f.write("[api_keys]\n")
            for k, v in existing.get("api_keys", {}).items():
                f.write(f'{k} = "{v}"\n')
            if "settings" in existing:
                f.write("\n[settings]\n")
                for k, v in existing["settings"].items():
                    f.write(f"{k} = {json.dumps(v)}\n")


# -------------------------------------------------------------------
# Module-level singleton (lazy init)
# -------------------------------------------------------------------
_default_config: GeoAfricaConfig | None = None


def get_config() -> GeoAfricaConfig:
    """Return the global default GeoAfricaConfig singleton."""
    global _default_config
    if _default_config is None:
        _default_config = GeoAfricaConfig()
    return _default_config


def configure(**kwargs) -> GeoAfricaConfig:
    """
    Update the global config and return it.

    Example
    -------
    >>> import geoafrica
    >>> geoafrica.configure(nasa_firms_key="abc123", verbose=True)
    """
    global _default_config
    _default_config = GeoAfricaConfig(**kwargs)
    return _default_config
