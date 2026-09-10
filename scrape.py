"""FinTern main entry.

    python scrape.py                 full run: fetch, filter, dedupe, render, notify
    python scrape.py --no-notify     same, but skip Discord (use for the first seed run)
    python scrape.py --dry-run       fetch and filter only, write nothing
    python scrape.py --only ramp     limit to one company slug while debugging
    python scrape.py -v              debug logging (shows every filtered-out title)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import filters
import notify
import render
from sources import SOURCES, Posting, SourceError

log = logging.getLogger("fintern")

ROOT = Path(__file__).resolve().parent
COMPANIES_PATH = ROOT / "companies.json"
SEEN_PATH = ROOT / "seen.json"
README_PATH = ROOT / "README.md"

VALID_CATEGORIES = {"fintech", "tech", "media", "bank", "pe", "consulting", "wealth", "other"}
REQUIRED_COMPANY_KEYS = {"name", "slug", "source", "board_token", "category"}


def load_companies(path: Path) -> list[dict[str, Any]]:
    """Load and validate companies.json. Config errors fail loud."""
    if not path.exists():
        raise SystemExit(f"config error: {path} not found")
    companies = json.loads(path.read_text())
    if not isinstance(companies, list) or not companies:
        raise SystemExit("config error: companies.json must be a non-empty list")
    slugs: set[str] = set()
    for entry in companies:
        missing = REQUIRED_COMPANY_KEYS - set(entry)
        if missing:
            raise SystemExit(f"config error: {entry.get('name')} missing {sorted(missing)}")
        if entry["source"] not in SOURCES:
            raise SystemExit(f"config error: {entry['name']} has unknown source {entry['source']}")
        if entry["category"] not in VALID_CATEGORIES:
            raise SystemExit(f"config error: {entry['name']} has bad category {entry['category']}")
        if entry["slug"] in slugs:
            raise SystemExit(f"config error: duplicate slug {entry['slug']}")
        slugs.add(entry["slug"])
    return companies


def load_seen(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit("config error: seen.json must be a JSON object")
    return data


def save_seen(seen: dict[str, dict[str, Any]], path: Path) -> None:
    ordered = dict(sorted(seen.items()))
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")


def fetch_company(company: dict[str, Any]) -> list[Posting] | None:
    """Fetch one company's board. Returns None when the fetch failed or was skipped."""
    source = SOURCES[company["source"]]
    if not getattr(source, "implemented", True):
        log.info("skip %s: %s not supported yet", company["name"], source.name)
        return None
    try:
        postings = source.fetch(company)
    except SourceError as exc:
        log.error("fetch failed for %s: %s", company["name"], exc)
        return None
    except Exception:
        log.exception("unexpected error fetching %s", company["name"])
        return None
    log.info("%s: %d postings on board", company["name"], len(postings))
    return postings


def fetch_all(companies: list[dict[str, Any]]) -> tuple[list[Posting], set[str]]:
    """Fetch every company. Returns (postings, names of companies reached)."""
    postings: list[Posting] = []
    reached: set[str] = set()
    for company in companies:
        result = fetch_company(company)
        if result is None:
            continue
        reached.add(company["name"])
        postings.extend(result)
    return postings, reached


def merge(
    seen: dict[str, dict[str, Any]],
    current: list[Posting],
    fetched_companies: set[str],
    today: str,
) -> list[Posting]:
    """Update seen in place. Returns the postings that are new this run.

    Postings that vanished from a board we successfully fetched are marked
    inactive, never deleted. Companies whose fetch failed are left alone so a
    flaky endpoint does not flip everything to inactive.
    """
    new: list[Posting] = []
    current_ids = {p.id for p in current}
    for posting in current:
        existing = seen.get(posting.id)
        if existing is None:
            posting.first_seen = today
            seen[posting.id] = posting.to_dict()
            new.append(posting)
            continue
        existing.update(title=posting.title, location=posting.location, url=posting.url)
        existing["posted_at"] = posting.posted_at or existing.get("posted_at")
        existing["active"] = True
    for pid, entry in seen.items():
        if pid in current_ids or entry.get("company") not in fetched_companies:
            continue
        if entry.get("active", True):
            log.info("inactive: %s at %s", entry.get("title"), entry.get("company"))
            entry["active"] = False
    return new


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape finance internship postings.")
    parser.add_argument("--no-notify", action="store_true", help="skip Discord alerts")
    parser.add_argument("--dry-run", action="store_true", help="fetch and filter, write nothing")
    parser.add_argument("--only", metavar="SLUG", help="run a single company slug")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    companies = load_companies(COMPANIES_PATH)
    if args.only:
        companies = [c for c in companies if c["slug"] == args.only]
        if not companies:
            raise SystemExit(f"config error: no company with slug {args.only}")
    if not args.no_notify and not args.dry_run:
        notify.require_webhook()

    seen = load_seen(SEEN_PATH)
    raw, reached = fetch_all(companies)
    relaxed = {c["name"] for c in companies if c["category"] in filters.RELAXED_CATEGORIES}
    matched = filters.apply(raw, relaxed)
    today = date.today().isoformat()
    new = merge(seen, matched, reached, today)
    log.info("%d matched, %d new, %d total seen", len(matched), len(new), len(seen))
    for posting in new:
        log.info("NEW: %s | %s | %s", posting.company, posting.title, posting.location)

    if args.dry_run:
        log.info("dry run, nothing written")
        return 0
    save_seen(seen, SEEN_PATH)
    render.write_readme(seen, README_PATH, datetime.now(timezone.utc))
    if new and not args.no_notify:
        notify.send(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
