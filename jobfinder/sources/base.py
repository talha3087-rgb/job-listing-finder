"""JobSource base protocol."""
from __future__ import annotations

from typing import List, Optional, Protocol
from jobfinder.models import RawJob


class SourceFetchError(RuntimeError):
    """A source could not be queried or returned an unusable response."""


class JobSource(Protocol):
    """Protocol for job sources."""
    name: str

    async def search(
        self,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[RawJob]:
        """Search or fetch postings from source."""
        ...
