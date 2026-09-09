"""Regenerate the README table below the TABLE_START marker from seen.json."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MARKER = "<!-- TABLE_START -->"
HEADER = "| Company | Role | Location | Posted | Apply |\n|---|---|---|---|---|\n"

DEFAULT_TOP = """# FinTern: Finance Internships at Tech, Fintech, and Media Companies

A curated, auto-updated list of finance internship postings (FP&A, strategic
finance, corp dev, treasury, bizops, and similar) at companies finance students
actually want to work for. Not a firehose. The company list is hand-picked.

Refreshes every 6 hours from company career pages. Newest postings on top.

"""


def escape_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def row(entry: dict[str, Any]) -> str:
    posted = entry.get("posted_at") or entry.get("first_seen") or ""
    link = f"[Apply]({entry['url']})" if entry.get("url") else ""
    return "| {} | {} | {} | {} | {} |\n".format(
        escape_cell(entry.get("company", "")),
        escape_cell(entry.get("title", "")),
        escape_cell(entry.get("location", "")) or "Not listed",
        posted,
        link,
    )


def active_sorted(seen: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    active = [e for e in seen.values() if e.get("active", True)]
    return sorted(
        active,
        key=lambda e: (e.get("first_seen") or "", e.get("posted_at") or "", e.get("company", "")),
        reverse=True,
    )


def build_table(seen: dict[str, dict[str, Any]], now: datetime) -> str:
    entries = active_sorted(seen)
    body = "".join(row(e) for e in entries)
    if not entries:
        body = "| No active postings right now. Check back soon. | | | | |\n"
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    footer = f"\nLast updated: {stamp}. {len(entries)} active posting{'s' if len(entries) != 1 else ''}.\n"
    return HEADER + body + footer


def write_readme(seen: dict[str, dict[str, Any]], path: Path, now: datetime) -> None:
    """Keep everything above MARKER, replace everything below it."""
    top = DEFAULT_TOP
    if path.exists():
        existing = path.read_text()
        if MARKER in existing:
            top = existing.split(MARKER, 1)[0]
        else:
            log.warning("README has no %s marker, keeping existing text as header", MARKER)
            top = existing.rstrip("\n") + "\n\n"
    content = top + MARKER + "\n\n" + build_table(seen, now)
    path.write_text(content)
    log.info("README written: %d active postings", len(active_sorted(seen)))
