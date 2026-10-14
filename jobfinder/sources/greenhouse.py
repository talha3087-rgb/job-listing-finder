"""Greenhouse public job board API client."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from jobfinder.sources.httputil import retrying_transport
from jobfinder.models import RawJob
from jobfinder.sources.base import SourceFetchError


class GreenhouseSource:
    name = "greenhouse"

    async def fetch_board_jobs(self, board_slug: str, company_name: str) -> List[RawJob]:
        """Fetch active jobs from Greenhouse public JSON endpoint."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
        jobs: List[RawJob] = []
        async with httpx.AsyncClient(transport=retrying_transport(), timeout=15.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise SourceFetchError(f"Greenhouse {board_slug}: HTTP {resp.status_code}")
                data = resp.json()
            except SourceFetchError:
                raise
            except Exception as exc:
                raise SourceFetchError(f"Greenhouse {board_slug}: {type(exc).__name__}: {exc}") from exc

            job_list = data.get("jobs", [])
            for item in job_list:
                job_id = str(item.get("id"))
                title = item.get("title", "").strip()
                apply_url = item.get("absolute_url", f"https://boards.greenhouse.io/{board_slug}/jobs/{job_id}")
                location_data = item.get("location", {})
                loc_name = location_data.get("name", "Remote / Unspecified") if isinstance(location_data, dict) else str(location_data)
                raw_content = item.get("content", "")

                jobs.append(RawJob(
                    source="greenhouse",
                    source_job_id=f"gh_{board_slug}_{job_id}",
                    title=title,
                    company=company_name,
                    location=loc_name,
                    url=apply_url,
                    apply_url=apply_url,
                    apply_type="ats",
                    raw_jd=raw_content
                ))
        return jobs
