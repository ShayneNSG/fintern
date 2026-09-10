"""Shared data model and the Source interface every ATS module implements."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "FinTern/0.1 (finance internship tracker; "
    "https://github.com/shaynegalura/fintern)"
)
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3
TIMEOUT_SECONDS = 20


@dataclass
class Posting:
    id: str
    company: str
    title: str
    location: str
    url: str
    source: str
    first_seen: str | None = None
    posted_at: str | None = None
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Posting":
        known = {k: data.get(k) for k in cls.__dataclass_fields__}
        if known.get("active") is None:
            known["active"] = True
        return cls(**known)


def make_id(source: str, company_slug: str, ats_job_id: str | int) -> str:
    return f"{source}:{company_slug}:{ats_job_id}"


class Source(ABC):
    """One ATS. Subclasses turn a companies.json entry into Postings."""

    name: str = "base"

    @abstractmethod
    def fetch(self, company: dict[str, Any]) -> list[Posting]:
        """Return every posting on the company's board, unfiltered."""


class SourceError(Exception):
    """Raised when a company's board cannot be fetched. Caller logs and moves on."""


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET a JSON endpoint politely: UA header, delay, backoff on 429 and 5xx."""
    return request_json("GET", url, params=params)


def post_json(url: str, body: dict[str, Any]) -> Any:
    """POST a JSON body and parse the JSON reply, same politeness as get_json."""
    return request_json("POST", url, body=body)


def request_json(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            resp = requests.request(
                method, url, params=params, json=body, headers=headers, timeout=TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            last_error = exc
            log.warning("request failed (%s/%s) %s: %s", attempt, MAX_RETRIES, url, exc)
            _backoff(attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            last_error = SourceError(f"HTTP {resp.status_code} from {url}")
            log.warning("retryable HTTP %s (%s/%s) %s", resp.status_code, attempt, MAX_RETRIES, url)
            _backoff(attempt)
            continue
        if resp.status_code >= 400:
            raise SourceError(f"HTTP {resp.status_code} from {url}")
        try:
            return resp.json()
        except ValueError as exc:
            raise SourceError(f"non-JSON response from {url}") from exc
    raise SourceError(f"gave up on {url}: {last_error}")


def _backoff(attempt: int) -> None:
    if attempt < MAX_RETRIES:
        time.sleep(2 ** attempt)
