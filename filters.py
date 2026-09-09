"""Title keyword filters. Edit the lists below to tune what gets through.

Matching is case insensitive and anchored at the start of a word, so
"intern" matches "Internship" but "tax" does not match "Syntax" and
"venture" does not match "Adventure".
"""

from __future__ import annotations

import logging
import re
from datetime import date

from sources.base import Posting

log = logging.getLogger(__name__)

_THIS_YEAR = date.today().year

INTERN_KEYWORDS: list[str] = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "summer analyst",
    f"summer {_THIS_YEAR}",
    f"summer {_THIS_YEAR + 1}",
]

FINANCE_KEYWORDS: list[str] = [
    "finance",
    "fp&a",
    "fpa",
    "financial analyst",
    "financial planning",
    "corporate finance",
    "strategic finance",
    "strategy & finance",
    "corp dev",
    "corporate development",
    "treasury",
    "investment banking",
    "equity research",
    "wealth management",
    "asset management",
    "private equity",
    "venture",
    "bizops",
    "business operations",
    "revenue operations",
    "accounting",
]

EXCLUDE_KEYWORDS: list[str] = [
    "software",
    "engineer",
    "engineering",
    "data science",
    "machine learning",
    "tax",
    "audit",
    "assurance",
    "payroll",
    "accounts payable",
    "accounts receivable",
    "bookkeep",
]


def _compile(keywords: list[str]) -> re.Pattern[str]:
    parts = [re.escape(k) for k in keywords]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + ")", re.IGNORECASE)


_INTERN_RE = _compile(INTERN_KEYWORDS)
_FINANCE_RE = _compile(FINANCE_KEYWORDS)
_EXCLUDE_RE = _compile(EXCLUDE_KEYWORDS)


# Words that start with "intern" but are not internships.
_INTERN_FALSE_POSITIVES = {"internal", "internally", "international", "internationally"}
_WORD_RE = re.compile(r"[a-z0-9&-]+", re.IGNORECASE)


def is_internship(title: str) -> bool:
    for match in _INTERN_RE.finditer(title):
        word = _WORD_RE.match(title, match.start())
        if word and word.group(0).lower() in _INTERN_FALSE_POSITIVES:
            continue
        return True
    return False


def is_finance(title: str) -> bool:
    return bool(_FINANCE_RE.search(title))


def is_excluded(title: str) -> bool:
    return bool(_EXCLUDE_RE.search(title))


def passes(title: str) -> bool:
    """True when the title is an internship, is finance, and hits no exclude word."""
    if not is_internship(title):
        log.debug("filtered (not internship): %s", title)
        return False
    if not is_finance(title):
        log.debug("filtered (not finance): %s", title)
        return False
    if is_excluded(title):
        log.debug("filtered (excluded keyword): %s", title)
        return False
    return True


def apply(postings: list[Posting]) -> list[Posting]:
    kept = [p for p in postings if passes(p.title)]
    log.info("filter: %d of %d postings passed", len(kept), len(postings))
    return kept
