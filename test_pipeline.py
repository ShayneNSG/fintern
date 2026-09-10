"""Offline end-to-end test using canned ATS responses. Run: python -m pytest -q

Fixture shapes mirror the real Greenhouse, Lever, and Ashby responses.
No network needed, so this also works inside CI.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

import notify
import render
import scrape
from sources import Posting, SOURCES, base

GREENHOUSE = {
    "jobs": [
        {
            "id": 111,
            "title": "Finance Intern, Summer 2027",
            "location": {"name": "New York, NY"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/111",
            "updated_at": "2026-09-01T10:00:00-04:00",
            "first_published": "2026-08-30T09:00:00-04:00",
        },
        {
            "id": 222,
            "title": "Software Engineer Intern",
            "location": {"name": "Remote"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/222",
            "updated_at": "2026-09-01T10:00:00-04:00",
            "first_published": None,
        },
    ]
}

LEVER = [
    {
        "id": "abc-123",
        "text": "Strategic Finance Intern",
        "categories": {"location": "San Francisco", "commitment": "Intern", "team": "Finance"},
        "hostedUrl": "https://jobs.lever.co/beta/abc-123",
        "applyUrl": "https://jobs.lever.co/beta/abc-123/apply",
        "createdAt": 1788336000000,
        "workplaceType": "hybrid",
    }
]

ASHBY = {
    "jobs": [
        {
            "id": "uuid-1",
            "title": "FP&A Intern (Summer 2027)",
            "location": "New York, NY (HQ)",
            "secondaryLocations": [{"location": "San Francisco, CA"}],
            "employmentType": "Intern",
            "isListed": True,
            "isRemote": False,
            "publishedAt": "2026-09-02T17:12:35.753+00:00",
            "jobUrl": "https://jobs.ashbyhq.com/gamma/uuid-1",
            "applyUrl": "https://jobs.ashbyhq.com/gamma/uuid-1/application",
        },
        {
            "id": "uuid-2",
            "title": "Treasury Intern",
            "location": "Remote",
            "isListed": False,
            "jobUrl": "https://jobs.ashbyhq.com/gamma/uuid-2",
        },
    ]
}

WORKDAY_PAGE = {
    "total": 4,
    "jobPostings": [
        {
            "title": "2027 Summer Analyst Program",
            "externalPath": "/job/New-York/XMLNAME-2027-Summer-Analyst-Program_40001",
            "locationsText": "New York",
            "postedOn": "Posted 3 Days Ago",
            "bulletFields": ["40001"],
        },
        {
            "title": "2027 Data Science Summer Analyst",
            "externalPath": "/job/New-York/XMLNAME-2027-Data-Science-Summer-Analyst_40002",
            "locationsText": "New York",
            "postedOn": "Posted Today",
            "bulletFields": ["40002"],
        },
        {
            "title": "2027 Summer Analyst Program (London)",
            "externalPath": "/job/London/XMLNAME-2027-Summer-Analyst-Program--London-_40004",
            "locationsText": "London",
            "postedOn": "Posted Today",
            "bulletFields": ["40004"],
        },
        {
            "title": "Vice President, Private Equity",
            "externalPath": "/job/New-York/VP_40003",
            "locationsText": "New York",
            "postedOn": "Posted 30+ Days Ago",
            "bulletFields": ["40003"],
        },
    ],
}

COMPANIES = [
    {"name": "Acme", "slug": "acme", "source": "greenhouse", "board_token": "acme", "category": "fintech"},
    {"name": "Beta", "slug": "beta", "source": "lever", "board_token": "beta", "category": "tech"},
    {"name": "Gamma", "slug": "gamma", "source": "ashby", "board_token": "gamma", "category": "tech"},
    {"name": "Delta", "slug": "delta", "source": "greenhouse", "board_token": "delta", "category": "media"},
    {"name": "Omega", "slug": "omega", "source": "workday", "board_token": "omega.wd1.myworkdayjobs.com/Campus", "category": "pe"},
]


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "companies.json").write_text(json.dumps(COMPANIES))
    monkeypatch.setattr(scrape, "COMPANIES_PATH", tmp_path / "companies.json")
    monkeypatch.setattr(scrape, "SEEN_PATH", tmp_path / "seen.json")
    monkeypatch.setattr(scrape, "README_PATH", tmp_path / "README.md")
    monkeypatch.setattr(base, "REQUEST_DELAY_SECONDS", 0)
    return tmp_path


def fake_get_json(responses: dict[str, Any]):
    def _get(url: str, params: dict[str, Any] | None = None) -> Any:
        for key, value in responses.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise base.SourceError(f"HTTP 404 from {url}")
    return _get


def patch_sources(monkeypatch: pytest.MonkeyPatch, responses: dict[str, Any]) -> None:
    getter = fake_get_json(responses)
    for module in ("sources.greenhouse", "sources.lever", "sources.ashby"):
        monkeypatch.setattr(f"{module}.get_json", getter)
    monkeypatch.setattr("sources.workday.post_json", lambda url, body: getter(url))


def test_first_run_seeds_and_renders(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_sources(monkeypatch, {"acme": GREENHOUSE, "beta": LEVER, "gamma": ASHBY})
    assert scrape.main(["--no-notify"]) == 0
    seen = json.loads((repo / "seen.json").read_text())
    assert set(seen) == {"greenhouse:acme:111", "lever:beta:abc-123", "ashby:gamma:uuid-1"}
    assert seen["ashby:gamma:uuid-1"]["location"] == "New York, NY (HQ); San Francisco, CA"
    assert seen["greenhouse:acme:111"]["posted_at"] == "2026-08-30"
    assert seen["lever:beta:abc-123"]["posted_at"] == "2026-09-02"
    readme = (repo / "README.md").read_text()
    assert render.MARKER in readme
    assert "| Acme | Finance Intern, Summer 2027 | New York, NY | 2026-08-30 | [Apply](https://boards.greenhouse.io/acme/jobs/111) |" in readme
    assert "3 active postings" in readme
    assert "Software Engineer Intern" not in readme


def test_second_run_marks_inactive_but_keeps_failed_company(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_sources(monkeypatch, {"acme": GREENHOUSE, "beta": LEVER, "gamma": ASHBY})
    scrape.main(["--no-notify"])
    # Acme drops its posting, Beta's endpoint fails, Gamma unchanged.
    patch_sources(monkeypatch, {"acme": {"jobs": []}, "beta": base.SourceError("HTTP 500"), "gamma": ASHBY})
    scrape.main(["--no-notify"])
    seen = json.loads((repo / "seen.json").read_text())
    assert seen["greenhouse:acme:111"]["active"] is False
    assert seen["lever:beta:abc-123"]["active"] is True
    assert seen["ashby:gamma:uuid-1"]["active"] is True
    readme = (repo / "README.md").read_text()
    assert "Acme" not in readme.split(render.MARKER)[1]
    assert "2 active postings" in readme


def test_readme_header_preserved(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / "README.md").write_text("# My custom header\n\nkeep me\n\n" + render.MARKER + "\nold table\n")
    patch_sources(monkeypatch, {"acme": GREENHOUSE})
    scrape.main(["--no-notify"])
    readme = (repo / "README.md").read_text()
    assert readme.startswith("# My custom header\n\nkeep me\n\n" + render.MARKER)
    assert "old table" not in readme


def test_notify_sends_one_message_per_posting(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setenv(notify.ENV_VAR, "https://discord.test/hook")
    monkeypatch.setattr(notify, "DELAY_BETWEEN_MESSAGES", 0)
    monkeypatch.setattr(notify, "post", lambda url, content: sent.append(content) or True)
    postings = [Posting(id=f"x:{i}", company="Acme", title=f"Finance Intern {i}", location="NY", url=f"https://a/{i}", source="greenhouse") for i in range(3)]
    assert notify.send(postings) == 3
    assert sent[0].startswith("**New: Acme**")


def test_notify_batches_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setenv(notify.ENV_VAR, "https://discord.test/hook")
    monkeypatch.setattr(notify, "DELAY_BETWEEN_MESSAGES", 0)
    monkeypatch.setattr(notify, "post", lambda url, content: sent.append(content) or True)
    postings = [Posting(id=f"x:{i}", company="Acme", title=f"Finance Intern {i}", location="NY", url=f"https://a/{i}", source="greenhouse") for i in range(25)]
    notify.send(postings)
    assert len(sent) == 1
    assert sent[0].startswith("**25 new finance internship postings**")
    assert all(len(m) <= notify.DISCORD_MAX_CHARS for m in sent)


def test_missing_webhook_fails_loud(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(notify.ENV_VAR, raising=False)
    with pytest.raises(SystemExit):
        scrape.main([])


def test_bad_companies_json_fails_loud(repo: Path) -> None:
    (repo / "companies.json").write_text(json.dumps([{"name": "Nope", "slug": "nope"}]))
    with pytest.raises(SystemExit):
        scrape.main(["--no-notify"])


def test_workday_relaxed_filter(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_sources(monkeypatch, {"omega": WORKDAY_PAGE})
    scrape.main(["--no-notify"])
    seen = json.loads((repo / "seen.json").read_text())
    assert set(seen) == {"workday:omega:40001"}  # London one is dropped by the US filter
    entry = seen["workday:omega:40001"]
    assert entry["url"] == "https://omega.wd1.myworkdayjobs.com/Campus/job/New-York/XMLNAME-2027-Summer-Analyst-Program_40001"
    assert entry["posted_at"] is not None
    assert SOURCES["workday"].implemented is True


def test_render_empty() -> None:
    table = render.build_table({}, datetime(2026, 9, 9, tzinfo=timezone.utc))
    assert "No active postings" in table
    assert "0 active postings" in table
