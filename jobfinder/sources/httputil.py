"""Shared HTTP defaults for public career-board clients."""
from __future__ import annotations

DEFAULT_HEADERS = {
    "User-Agent": "jobhunt/0.1 (personal job-search client)",
    "Accept": "application/json",
}


def retrying_transport(retries: int = 3):
    """Transport that retries failed connects (incl. transient Windows DNS errno 11002).

    httpcore applies exponential backoff between attempts; HTTP-level errors are not retried.
    """
    import httpx

    return httpx.AsyncHTTPTransport(retries=retries)
