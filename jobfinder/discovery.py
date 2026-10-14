"""Configurable discovery without candidate-specific assumptions."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import yaml
from pydantic import BaseModel, Field

from jobfinder.sources.ashby import AshbySource
from jobfinder.sources.greenhouse import GreenhouseSource
from jobfinder.sources.lever import LeverSource


class Board(BaseModel):
    company: str = Field(min_length=1)
    ats: Literal["greenhouse", "lever", "ashby"]
    slug: str = Field(pattern=r"^[A-Za-z0-9_-]+$")


class SearchConfig(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    boards: list[Board] = Field(min_length=1, max_length=100)
    concurrency: int = Field(default=3, ge=1, le=5)


def load_config(path: Path) -> SearchConfig:
    return SearchConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def matches(value: str, terms: list[str]) -> bool:
    """Case-insensitive substring matching, OR within each filter group."""
    clean = [term.strip().casefold() for term in terms if term.strip()]
    return not clean or any(term in value.casefold() for term in clean)


def canonical_url(url: str) -> str:
    # Preserve query parameters: some boards use them to identify the opening.
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


async def discover(config: SearchConfig) -> dict:
    adapters = {"greenhouse": GreenhouseSource(), "lever": LeverSource(), "ashby": AshbySource()}
    semaphore = asyncio.Semaphore(config.concurrency)

    async def fetch(board: Board):
        async with semaphore:
            started = time.monotonic()
            health = {"company": board.company, "source": board.ats, "board": board.slug}
            try:
                jobs = await adapters[board.ats].fetch_board_jobs(board.slug, board.company)
                health.update(status="success" if jobs else "empty", fetched=len(jobs))
                return jobs, health
            except Exception as exc:
                health.update(status="error", fetched=0, error=str(exc))
                return [], health
            finally:
                health["elapsed_seconds"] = round(time.monotonic() - started, 3)

    results = await asyncio.gather(*(fetch(board) for board in config.boards))
    postings = []
    seen = set()
    health = []
    for jobs, source_health in results:
        kept = 0
        for job in jobs:
            if not matches(job.title, config.keywords) or not matches(job.location, config.locations):
                continue
            kept += 1
            key = canonical_url(job.apply_url or job.url)
            if key in seen:
                continue
            seen.add(key)
            postings.append(job.model_dump())
        source_health["matched"] = kept
        health.append(source_health)
    postings.sort(key=lambda job: (job["company"].casefold(), job["title"].casefold()))
    return {
        "searched_at_utc": datetime.now(timezone.utc).isoformat(),
        "keywords": config.keywords,
        "locations": config.locations,
        "complete": all(item["status"] != "error" for item in health),
        "jobs": postings,
        "sources": health,
    }
