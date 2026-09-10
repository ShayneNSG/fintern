"""Greenhouse job board API.

Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
Response: {"jobs": [{"id", "title", "location": {"name"}, "absolute_url",
           "updated_at", "first_published", ...}]}
"""

from __future__ import annotations

import logging
from typing import Any

from sources.base import Posting, Source, SourceError, get_json, make_id

log = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"


class GreenhouseSource(Source):
    name = "greenhouse"

    def fetch(self, company: dict[str, Any]) -> list[Posting]:
        token = company.get("board_token")
        if not token:
            raise SourceError(f"{company.get('name')}: missing board_token")
        data = get_json(BASE_URL.format(board_token=token))
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if jobs is None:
            raise SourceError(f"{company['name']}: unexpected Greenhouse response shape")
        return [self._to_posting(company, job) for job in jobs]

    def _to_posting(self, company: dict[str, Any], job: dict[str, Any]) -> Posting:
        location = (job.get("location") or {}).get("name") or ""
        posted = job.get("first_published") or job.get("updated_at")
        return Posting(
            id=make_id(self.name, company["slug"], job["id"]),
            company=company["name"],
            title=job.get("title", "").strip(),
            location=location.strip(),
            url=job.get("absolute_url", ""),
            source=self.name,
            posted_at=posted or None,
        )
