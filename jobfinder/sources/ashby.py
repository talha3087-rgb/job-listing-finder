"""Ashby public job board API client."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from jobfinder.sources.httputil import retrying_transport
from jobfinder.models import RawJob
from jobfinder.sources.base import SourceFetchError


class AshbySource:
    name = "ashby"

    async def fetch_board_jobs(self, board_slug: str, company_name: str) -> List[RawJob]:
        """Fetch active jobs from Ashby public posting API."""
        url = f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
        jobs: List[RawJob] = []
        async with httpx.AsyncClient(transport=retrying_transport(), timeout=15.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise SourceFetchError(f"Ashby {board_slug}: HTTP {resp.status_code}")
                data = resp.json()
            except SourceFetchError:
                raise
            except Exception as exc:
                raise SourceFetchError(f"Ashby {board_slug}: {type(exc).__name__}: {exc}") from exc

            job_list = data.get("jobs", [])
            for item in job_list:
                job_id = str(item.get("id"))
                title = item.get("title", "").strip()
                apply_url = item.get("jobUrl", f"https://jobs.ashbyhq.com/{board_slug}/{job_id}")
                loc_name = item.get("location", "Remote / Unspecified")
                raw_desc = item.get("descriptionPlain") or item.get("descriptionHtml", "")

                jobs.append(RawJob(
                    source="ashby",
                    source_job_id=f"ash_{board_slug}_{job_id}",
                    title=title,
                    company=company_name,
                    location=loc_name,
                    url=apply_url,
                    apply_url=apply_url,
                    apply_type="ats",
                    raw_jd=raw_desc
                ))
        return jobs
