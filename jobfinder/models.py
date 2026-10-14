"""Common posting format for supported public employer boards."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class RawJob(BaseModel):
    """Raw job posting as fetched from email, ATS, or API."""
    source: str               # "linkedin_alert", "greenhouse", "lever", "ashby", "jooble", etc.
    source_job_id: str        # Original ID from source
    title: str
    company: str
    location: str
    url: str                  # Original URL
    apply_url: Optional[str] = None
    apply_type: str = "direct"  # "direct", "easy_apply", "ats", "external"
    salary: Optional[str] = None
    snippet: Optional[str] = None
    raw_jd: Optional[str] = None
    posted_date: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
