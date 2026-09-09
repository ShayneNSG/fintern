"""Lever postings API.

Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
Response: a JSON array of {"id", "text", "categories": {"location", "team",
          "commitment", "department"}, "hostedUrl", "applyUrl",
          "createdAt" (ms epoch), "workplaceType", ...}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sources.base import Posting, Source, SourceError, get_json, make_id

log = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings/{board_token}"


class LeverSource(Source):
    name = "lever"

    def fetch(self, company: dict[str, Any]) -> list[Posting]:
        token = company.get("board_token")
        if not token:
            raise SourceError(f"{company.get('name')}: missing board_token")
        data = get_json(BASE_URL.format(board_token=token), params={"mode": "json"})
        if not isinstance(data, list):
            raise SourceError(f"{company['name']}: unexpected Lever response shape")
        return [self._to_posting(company, job) for job in data]

    def _to_posting(self, company: dict[str, Any], job: dict[str, Any]) -> Posting:
        cats = job.get("categories") or {}
        location = cats.get("location") or ", ".join(cats.get("allLocations") or []) or ""
        if job.get("workplaceType") == "remote" and "remote" not in location.lower():
            location = f"{location} (Remote)".strip()
        return Posting(
            id=make_id(self.name, company["slug"], job["id"]),
            company=company["name"],
            title=job.get("text", "").strip(),
            location=location.strip(),
            url=job.get("hostedUrl") or job.get("applyUrl") or "",
            source=self.name,
            posted_at=_ms_to_date(job.get("createdAt")),
        )


def _ms_to_date(value: Any) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None
