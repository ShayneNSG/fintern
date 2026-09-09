# FinTern (working name): Finance Internship Tracker

## What this is

A scraper that watches company career pages for finance internship postings and publishes them to a README table plus a Discord alert when something new appears. Built for finance students targeting strategic finance, FP&A, corp dev, and finance roles at tech companies and fintechs. Think the SimplifyJobs / Pitt CSC internship list, but for finance kids who want tech, not tax and audit.

The scraper is not the product. The curated company list is. Every existing finance list on GitHub (Jobright's auto-generated repo, Zapply) is a firehose of every posting with "finance" in the title. This one is opinionated and small.

## Who is building it

Shayne, finance major at CSULB, currently an FP&A intern at NBCUniversal. Comfortable with Python at a builder level, not a CS student. Has shipped iOS apps solo. Prefers working code over clean abstractions. Explain tradeoffs briefly when they matter, then make the call and move on.

## Goals for v1

1. Runs unattended on a GitHub Actions cron every hour. Zero hosting cost.
2. Pulls postings from Greenhouse, Lever, and Ashby public JSON endpoints for a curated list of companies.
3. Filters to internships and finance roles by title keywords.
4. Dedupes against previously seen postings.
5. Regenerates a README.md table (Company, Role, Location, Date Posted, Apply link) and commits it.
6. Fires a Discord webhook for each new posting.

Done means: I open the repo and see current finance internships, and my phone buzzes when a new one goes up.

## Non-goals for v1

* No LinkedIn, Handshake, Glassdoor, or Indeed scraping. They block, break, or require login. Do not attempt.
* No Workday. It has no public API and every tenant is different. Stub the interface so it can be added in v2, but do not build it now.
* No web UI, no database, no auth, no hosting. JSON files in the repo are the database.
* No AI classification of roles. Keyword matching is enough for v1.
* No applying, no tracking applications, no user accounts.

## Stack

* Python 3.11+
* `requests` for HTTP. No Selenium, no Playwright.
* Standard library for everything else where possible. `json`, `datetime`, `pathlib`.
* GitHub Actions for scheduling and auto-commit.
* Discord webhook (plain POST, no bot library).
* Keep dependencies to `requests` and nothing else unless there is a real reason. `pytest` is dev-only.

## Repo structure

```
fintern/
  CLAUDE.md                 this file
  README.md                 auto-generated below the marker, hand edit above it
  companies.json            the curated company list (the moat)
  seen.json                 dedupe store, keyed by posting id
  filters.py                keyword include/exclude logic
  sources/
    __init__.py             SOURCES registry
    base.py                 Posting dataclass, Source interface, polite get_json
    greenhouse.py
    lever.py
    ashby.py
    workday.py              stub only, raises NotImplementedError
  scrape.py                 main entry: load companies, run sources, filter, dedupe, write outputs
  render.py                 builds README table from seen.json
  notify.py                 Discord webhook
  test_filters.py           keyword sanity checks
  test_pipeline.py          offline end-to-end with canned ATS responses
  .github/workflows/scrape.yml
  requirements.txt
  requirements-dev.txt
```

## Data model

`Posting` (dataclass):

* `id` (str): stable unique id. `{source}:{company_slug}:{ats_job_id}`.
* `company` (str)
* `title` (str)
* `location` (str)
* `url` (str): direct apply link
* `source` (str): greenhouse | lever | ashby | workday
* `first_seen` (ISO date string, set by us on first sight)
* `posted_at` (ISO date string or null, from the ATS if available)
* `active` (bool): false once the posting disappears from the board

`companies.json` entry:

```json
{
  "name": "Ramp",
  "slug": "ramp",
  "source": "ashby",
  "board_token": "ramp",
  "category": "fintech"
}
```

`category` is one of: `fintech`, `tech`, `media`, `bank`, `wealth`, `other`. Used for README grouping later.

Workday entries carry `"verified": false` until someone confirms the tenant URL. Extra keys are ignored by the loader.

## ATS endpoints

* Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`
* Lever: `https://api.lever.co/v0/postings/{company}?mode=json`
* Ashby: `https://api.ashbyhq.com/posting-api/job-board/{board_name}`

All three return JSON with no auth. Each source module handles its own response shape and returns a list of `Posting`. If a company's endpoint 404s or errors, log it and continue. One bad company must never kill the run.

Be polite. Small delay between requests, a real User-Agent string, and retries with backoff on 429 or 5xx. All of that lives in `sources/base.py::get_json`.

## Filter logic (filters.py)

A posting passes if ALL of these are true:

1. Title contains an internship signal: `intern`, `internship`, `co-op`, `summer analyst`, `summer {this year}`, `summer {next year}`.
2. Title contains at least one finance keyword (case insensitive): see `FINANCE_KEYWORDS`.
3. Title does NOT contain an exclude keyword: see `EXCLUDE_KEYWORDS`.

Keywords match at the start of a word, so `intern` catches `Internship` but `tax` does not catch `Syntax`. `Internal` and `International` are explicitly excluded from the intern signal.

Include and exclude lists are module-level constants. Filtered-out titles log at debug level (`python scrape.py -v`) so we can tune.

Location: v1 does not filter by location. Include everything, show location in the table.

## Dedupe

`seen.json` is a dict keyed by `Posting.id`. Any posting whose id is not in `seen.json` is new. Add it with `first_seen` set to today. Never remove entries automatically. Postings that disappear from a board we successfully fetched are marked `"active": false`, not deleted. If a company's fetch failed this run, its postings are left untouched so a flaky endpoint does not flip everything inactive.

## README rendering (render.py)

README has a hand-written header above `<!-- TABLE_START -->`. Everything below the marker is regenerated on every run. Sorted by `first_seen` descending. Only active postings. Columns: Company | Role | Location | Posted | Apply. Last-updated timestamp and total count at the bottom.

## Discord (notify.py)

Webhook URL comes from env var `DISCORD_WEBHOOK_URL`, stored as a GitHub Actions secret. One message per new posting: company, title, location, link. More than 10 new postings in one run get batched into as few messages as fit under Discord's 2000-char limit. `--no-notify` skips Discord entirely; use it for the seed run.

## GitHub Actions (scrape.yml)

Cron every hour plus `workflow_dispatch` (with a `no_notify` checkbox for the seed run). Checkout, setup Python, install requests, run `python scrape.py`, commit and push `seen.json` and `README.md` if changed. Uses the built-in `GITHUB_TOKEN` with `permissions: contents: write`.

## Conventions

* No em dashes anywhere, including comments and README.
* Short functions. If something is over 40 lines, split it.
* Type hints on function signatures.
* `logging` module, not print.
* Fail loud on config errors (missing webhook, bad companies.json), fail soft on network errors per company.
* Commit messages from the bot: `chore: update postings YYYY-MM-DD HH:MM`.
* Run `python -m pytest -q` before pushing. Tests are offline and take under a second.

## Build status

v1 steps 1 through 8 are built. `companies.json` has 66 entries: 48 Greenhouse, 8 Ashby, 3 Lever, 7 Workday (skipped until v2). Every non-Workday board token was checked live against its ATS endpoint on 2026-09-09.

Not trackable yet because they run a custom or unsupported ATS: Uber, Snap, Netflix, NBCUniversal, Rippling, Marqeta, Canva, Snowflake, Whatnot, Patreon.

## v2 ideas (do not build yet)

* Workday support.
* SmartRecruiters support (NBCUniversal) and Eightfold (Netflix).
* Category tabs or grouping in README.
* Off-season (fall, spring) view.
* Simple GitHub Pages site with filters.
* Location filter (CA, NY, remote).
* Accept community PRs to companies.json.
