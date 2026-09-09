"""Registry of ATS sources keyed by the `source` field in companies.json."""

from __future__ import annotations

from sources.ashby import AshbySource
from sources.base import Posting, Source, SourceError, make_id
from sources.greenhouse import GreenhouseSource
from sources.lever import LeverSource
from sources.workday import WorkdaySource

SOURCES: dict[str, Source] = {
    "greenhouse": GreenhouseSource(),
    "lever": LeverSource(),
    "ashby": AshbySource(),
    "workday": WorkdaySource(),
}

__all__ = ["SOURCES", "Posting", "Source", "SourceError", "make_id"]
