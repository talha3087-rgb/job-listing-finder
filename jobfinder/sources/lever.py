"""Lever public postings API client."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from jobfinder.sources.httputil import retrying_transport
from jobfinder.models import RawJob
from jobfinder.sources.base import SourceFetchError


class LeverSource:
    name = "lever"

    async def fetch_board_jobs(self, board_slug: str, company_name: str) -> List[RawJob]:
        """Fetch active jobs from Lever public JSON endpoint."""
        url = f"https://api.lever.co/v0/postings/{board_slug}?mode=json"
        jobs: List[RawJob] = []
        async with httpx.AsyncClient(transport=retrying_transport(), timeout=15.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise SourceFetchError(f"Lever {board_slug}: HTTP {resp.status_code}")
                data = resp.json()
            except SourceFetchError:
                raise
            except Exception as exc:
                raise SourceFetchError(f"Lever {board_slug}: {type(exc).__name__}: {exc}") from exc

            for item in data:
                job_id = str(item.get("id"))
                title = item.get("text", "").strip()
                apply_url = item.get("hostedUrl", f"https://jobs.lever.co/{board_slug}/{job_id}")
                categories = item.get("categories", {})
                loc_name = categories.get("location", "Remote / Unspecified") if isinstance(categories, dict) else "Unspecified"
                raw_desc = item.get("descriptionPlain") or item.get("description", "")

                jobs.append(RawJob(
                    source="lever",
                    source_job_id=f"lev_{board_slug}_{job_id}",
                    title=title,
                    company=company_name,
                    location=loc_name,
                    url=apply_url,
                    apply_url=apply_url,
                    apply_type="ats",
                    raw_jd=raw_desc
                ))
        return jobs
