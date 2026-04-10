"""
GeoAfrica HTTP Session Manager
================================
Merczcord Technologies Ltd.

Provides a shared, cached, rate-limited requests session for all
dataset modules to use.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import requests
import requests_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from geoafrica.core.config import get_config

# -------------------------------------------------------------------
# Per-provider rate limits (requests per second)
# -------------------------------------------------------------------
RATE_LIMITS: dict[str, float] = {
    "overpass-api.de": 0.5,   # 1 req / 2 sec
    "api.humdata.org": 2.0,
    "worldpop.org": 2.0,
    "firms.modaps.eosdis.nasa.gov": 1.0,
    "portal.opentopography.org": 1.0,
    "healthsites.io": 1.0,
}

_last_request_time: dict[str, float] = {}
_lock = threading.Lock()


def _rate_limit(host: str) -> None:
    """Block if necessary to comply with per-host rate limits."""
    limit = RATE_LIMITS.get(host)
    if limit is None:
        return
    min_interval = 1.0 / limit
    with _lock:
        last = _last_request_time.get(host, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        _last_request_time[host] = time.monotonic()


# -------------------------------------------------------------------
# Session factory
# -------------------------------------------------------------------

def _build_session(use_cache: bool = True) -> requests.Session:
    """Build a requests.Session with retry logic and optional caching."""
    cfg = get_config()

    if use_cache:
        session = requests_cache.CachedSession(
            cache_name=str(cfg.cache_dir / "http_cache"),
            backend="sqlite",
            expire_after=cfg.cache_ttl,
            allowable_methods=["GET"],
            stale_if_error=True,
        )
    else:
        session = requests.Session()  # type: ignore[assignment]

    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": "GeoAfrica-SDK/0.2.0 (Merczcord Technologies Ltd.; https://github.com/Mercy14846/Geo-API)",
        "Accept": "application/json, application/geo+json, */*",
    })
    return session


# -------------------------------------------------------------------
# Singleton session
# -------------------------------------------------------------------
_session: requests.Session | None = None


def get_session(use_cache: bool = True) -> requests.Session:
    """Return the global HTTP session (lazy init)."""
    global _session
    if _session is None:
        _session = _build_session(use_cache=use_cache)
    return _session


def reset_session() -> None:
    """Force creation of a fresh session (clears in-memory state)."""
    global _session
    _session = None


class GeoAfricaSession:
    """
    Context-manager wrapper around the shared session.
    Adds rate limiting and unified error handling.

    Usage
    -----
    with GeoAfricaSession() as s:
        resp = s.get("https://overpass-api.de/api/interpreter", params=...)
    """

    def __init__(self, use_cache: bool = True) -> None:
        self._session = get_session(use_cache=use_cache)
        self._cfg = get_config()

    def __enter__(self) -> GeoAfricaSession:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        from urllib.parse import urlparse

        from geoafrica.core.exceptions import RateLimitError

        host = urlparse(url).hostname or ""
        _rate_limit(host)

        kwargs.setdefault("timeout", self._cfg.timeout)
        resp = self._session.get(url, **kwargs)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise RateLimitError(host, retry_after)

        resp.raise_for_status()
        return resp

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        from urllib.parse import urlparse

        from geoafrica.core.exceptions import RateLimitError

        host = urlparse(url).hostname or ""
        _rate_limit(host)

        kwargs.setdefault("timeout", self._cfg.timeout)
        resp = self._session.post(url, **kwargs)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise RateLimitError(host, retry_after)

        resp.raise_for_status()
        return resp

    def download(self, url: str, dest_path: str, show_progress: bool = True) -> str:
        """
        Stream-download *url* to *dest_path*, with optional progress bar.

        Returns
        -------
        str
            Absolute path to the downloaded file.
        """
        from pathlib import Path

        from tqdm import tqdm

        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with self._session.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(dest, "wb") as f:
                with tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc=dest.name,
                    disable=not (show_progress and self._cfg.verbose),
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        bar.update(len(chunk))
        return str(dest.resolve())
