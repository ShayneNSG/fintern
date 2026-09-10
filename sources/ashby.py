"""Ashby public job board API.

Endpoint: https://api.ashbyhq.com/posting-api/job-board/{board_name}
Response: {"jobs": [{"id", "title", "location", "secondaryLocations",
          "employmentType", "isListed", "isRemote", "publishedAt",
          "jobUrl", "applyUrl", "department", "team", ...}]}
"""

from __future__ import annotations

import logging
from typing import Any

from sources.base import Posting, Source, SourceError, get_json, make_id

log = logging.getLogger(__name__)

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_token}"


class AshbySource(Source):
    name = "ashby"

    def fetch(self, company: dict[str, Any]) -> list[Posting]:
        token = company.get("board_token")
        if not token:
            raise SourceError(f"{company.get('name')}: missing board_token")
        data = get_json(BASE_URL.format(board_token=token))
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if jobs is None:
            raise SourceError(f"{company['name']}: unexpected Ashby response shape")
        return [self._to_posting(company, job) for job in jobs if job.get("isListed", True)]

    def _to_posting(self, company: dict[str, Any], job: dict[str, Any]) -> Posting:
        location = job.get("location") or ""
        extra = [loc.get("location", "") for loc in job.get("secondaryLocations") or []]
        extra = [loc for loc in extra if loc and loc != location]
        if extra:
            location = "; ".join([location, *extra]) if location else "; ".join(extra)
        if job.get("isRemote") and "remote" not in location.lower():
            location = f"{location} (Remote)".strip()
        return Posting(
            id=make_id(self.name, company["slug"], job["id"]),
            company=company["name"],
            title=job.get("title", "").strip(),
            location=location.strip(),
            url=job.get("jobUrl") or job.get("applyUrl") or "",
            source=self.name,
            posted_at=job.get("publishedAt") or None,
        )
