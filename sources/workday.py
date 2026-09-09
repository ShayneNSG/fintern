"""Workday stub. No public API and every tenant differs. Planned for v2.

Companies with "source": "workday" stay in companies.json so the list is
ready when support lands. scrape.py skips them with a log line.
"""

from __future__ import annotations

from typing import Any

from sources.base import Posting, Source


class WorkdaySource(Source):
    name = "workday"
    implemented = False

    def fetch(self, company: dict[str, Any]) -> list[Posting]:
        raise NotImplementedError("Workday support is planned for v2")
