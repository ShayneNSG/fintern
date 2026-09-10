"""Workday careers sites via the unofficial cxs JSON endpoint.

Every Workday tenant serves the same JSON that its own careers page uses:

    POST https://{host}/wday/cxs/{tenant}/{site}/jobs
    body {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "intern"}
    reply {"total": N, "jobPostings": [{"title", "externalPath",
           "locationsText", "postedOn", "bulletFields": [req_id]}]}

board_token is the careers URL minus the scheme, for example
"blackstone.wd1.myworkdayjobs.com/Blackstone_Campus_Careers" or, for the
older myworkdaysite.com style, "wd1.myworkdaysite.com/recruiting/wf/WellsFargoJobs".

Big banks have thousands of postings, so instead of paging the whole board we
run a few targeted searches and let filters.py do the real work. Unofficial
endpoint: if Workday changes it, this module is the only thing that breaks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sources.base import Posting, Source, SourceError, make_id, post_json

log = logging.getLogger(__name__)

SEARCH_TERMS = ["intern", "summer analyst"]
PAGE_SIZE = 20
MAX_PAGES_PER_SEARCH = 15


class WorkdaySource(Source):
    name = "workday"
    implemented = True

    def fetch(self, company: dict[str, Any]) -> list[Posting]:
        board = parse_board_token(company)
        endpoint = f"https://{board.host}/wday/cxs/{board.tenant}/{board.site}/jobs"
        seen: dict[str, Posting] = {}
        for term in SEARCH_TERMS:
            for job in self._search(endpoint, term):
                posting = self._to_posting(company, board, job)
                seen.setdefault(posting.id, posting)
        return list(seen.values())

    def _search(self, endpoint: str, term: str) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for page in range(MAX_PAGES_PER_SEARCH):
            body = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": page * PAGE_SIZE, "searchText": term}
            data = post_json(endpoint, body)
            if not isinstance(data, dict) or "jobPostings" not in data:
                raise SourceError(f"unexpected Workday response shape from {endpoint}")
            batch = data.get("jobPostings") or []
            jobs.extend(batch)
            total = data.get("total") or 0
            if len(batch) < PAGE_SIZE or (page + 1) * PAGE_SIZE >= total:
                break
        return jobs

    def _to_posting(self, company: dict[str, Any], board: Board, job: dict[str, Any]) -> Posting:
        path = job.get("externalPath") or ""
        job_id = _job_id(job, path)
        return Posting(
            id=make_id(self.name, company["slug"], job_id),
            company=company["name"],
            title=(job.get("title") or "").strip(),
            location=(job.get("locationsText") or "").strip(),
            url=f"https://{board.host}{board.base_path}{path}",
            source=self.name,
            posted_at=parse_posted_on(job.get("postedOn")),
        )


@dataclass(frozen=True)
class Board:
    host: str
    tenant: str
    site: str
    base_path: str


def parse_board_token(company: dict[str, Any]) -> Board:
    """Accept both Workday URL styles.

    {tenant}.wd5.myworkdayjobs.com/{site}                  tenant is the first host label
    wd1.myworkdaysite.com/recruiting/{tenant}/{site}      tenant is in the path
    """
    token = (company.get("board_token") or "").strip().strip("/")
    name = company.get("name")
    if "/" not in token:
        raise SourceError(f"{name}: workday board_token must be host/site, got {token!r}")
    host, path = token.split("/", 1)
    parts = [p for p in path.split("/") if p]
    if host.endswith("myworkdayjobs.com") and len(parts) == 1:
        return Board(host, host.split(".")[0], parts[0], f"/{parts[0]}")
    if host.endswith("myworkdaysite.com") and len(parts) == 3 and parts[0] == "recruiting":
        return Board(host, parts[1], parts[2], f"/recruiting/{parts[1]}/{parts[2]}")
    raise SourceError(f"{name}: unrecognized workday board_token {token!r}")


def _job_id(job: dict[str, Any], path: str) -> str:
    bullets = job.get("bulletFields") or []
    if bullets and isinstance(bullets[0], str) and bullets[0].strip():
        return bullets[0].strip()
    return path.rsplit("/", 1)[-1] or path


_DAYS_AGO = re.compile(r"(\d+)\+?\s+days?\s+ago", re.IGNORECASE)


def parse_posted_on(text: str | None, today: date | None = None) -> str | None:
    """Workday gives relative text like "Posted 3 Days Ago". Convert to a date."""
    if not text:
        return None
    today = today or date.today()
    lowered = text.lower()
    if "today" in lowered:
        return today.isoformat()
    if "yesterday" in lowered:
        return (today - timedelta(days=1)).isoformat()
    match = _DAYS_AGO.search(lowered)
    if match and "+" not in lowered:
        return (today - timedelta(days=int(match.group(1)))).isoformat()
    return None
