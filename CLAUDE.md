# FinTern (working name): Finance Internship Tracker

## What this is

A scraper that watches company career pages for finance internship postings and publishes them to a README table plus a Discord alert when something new appears. Built for finance students targeting strategic finance, FP&A, corp dev, and finance roles at tech companies and fintechs. Think the SimplifyJobs / Pitt CSC internship list, but for finance kids who want tech, not tax and audit.

The scraper is not the product. The curated company list is. Every existing finance list on GitHub (Jobright's auto-generated repo, Zapply) is a firehose of every posting with "finance" in the title. This one is opinionated and small.

## Who is building it

Shayne, finance major at CSULB, currently an FP&A intern at NBCUniversal. Comfortable with Python at a builder level, not a CS student. Has shipped iOS apps solo. Prefers working code over clean abstractions. Explain tradeoffs briefly when they matter, then make the call and move on.

## Goals for v1

1. Runs unattended on a GitHub Actions cron every hour. Zero hosting cost.
2. Pulls postings from Greenhouse, Lever, Ashby, and Workday JSON endpoints for a curated list of companies.
3. Filters to internships and finance roles by title keywords.
4. Dedupes against previously seen postings.
5. Regenerates a README.md table (Company, Role, Location, Date Posted, Apply link) and commits it.
6. Fires a Discord webhook for each new posting.

Done means: I open the repo and see current finance internships, and my phone buzzes when a new one goes up.

## Non-goals for v1

* No LinkedIn, Handshake, Glassdoor, or Indeed scraping. They block, break, or require login. Do not attempt.
* Workday was originally a v2 item. It was pulled forward on 2026-09-09 because banks, PE, and consulting are almost entirely Workday. It uses the unofficial cxs endpoint, so it is the one source that could break without warning.
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
    workday.py              unofficial cxs JSON endpoint, targeted searches
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

`category` is one of: `fintech`, `tech`, `media`, `bank`, `pe`, `consulting`, `wealth`, `other`. Used for README grouping later and by the relaxed filter (see below).

Workday `board_token` is the careers URL minus the scheme: `blackstone.wd1.myworkdayjobs.com/Blackstone_Campus_Careers` or `wd1.myworkdaysite.com/recruiting/wf/WellsFargoJobs`. Verify by opening it in a browser before adding. Extra keys are ignored by the loader.

## ATS endpoints

* Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`
* Lever: `https://api.lever.co/v0/postings/{company}?mode=json`
* Ashby: `https://api.ashbyhq.com/posting-api/job-board/{board_name}`
* Workday: `POST https://{host}/wday/cxs/{tenant}/{site}/jobs` with `{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "intern"}`. Unofficial. Big tenants have thousands of jobs, so workday.py runs a couple of targeted searches (`intern`, `summer analyst`) capped at 15 pages each instead of paging the whole board.

All four return JSON with no auth. Each source module handles its own response shape and returns a list of `Posting`. If a company's endpoint 404s or errors, log it and continue. One bad company must never kill the run.

Be polite. Small delay between requests, a real User-Agent string, and retries with backoff on 429 or 5xx. All of that lives in `sources/base.py::get_json`.

## Filter logic (filters.py)

A posting passes if ALL of these are true:

1. Title contains an internship signal: `intern`, `internship`, `co-op`, `summer analyst`, `summer {this year}`, `summer {next year}`.
2. Title contains at least one finance keyword (case insensitive): see `FINANCE_KEYWORDS`.
3. Title does NOT contain an exclude keyword: see `EXCLUDE_KEYWORDS`.

Companies in `RELAXED_CATEGORIES` (`bank`, `pe`, `wealth`) skip check 2. At those firms every summer analyst is a finance hire and the title rarely says so. The exclude list still applies, and it carries `technology`, `quantitative`, `marketing`, `legal`, `human resources`, `communications`, and `actuarial` mainly for this case. Consulting is not relaxed: Accenture and PwC post hundreds of non-finance internships, so those titles must say finance, consulting, or similar.

Keywords match at the start of a word, so `intern` catches `Internship` but `tax` does not catch `Syntax`. `Internal` and `International` are explicitly excluded from the intern signal.

Include and exclude lists are module-level constants. Filtered-out titles log at debug level (`python scrape.py -v`) so we can tune.

Location: `US_ONLY = True` in filters.py. A posting is dropped only when its location names somewhere outside the US (`NON_US_SIGNALS`) and nothing in it points to the US (`US_SIGNALS`, a two-letter state code). Blank, "Remote", and unrecognized locations are kept, since dropping what we cannot read would lose real US roles. Location strings are messy ("WI-Milwaukee", "Toronto - 18 York Street", "Berkeley Square House London"), so the lists are long on purpose.

## Dedupe

`seen.json` is a dict keyed by `Posting.id`. Any posting whose id is not in `seen.json` is new. Add it with `first_seen` set to today. Never remove entries automatically. Postings that disappear from a board we successfully fetched are marked `"active": false`, not deleted. If a company's fetch failed this run, its postings are left untouched so a flaky endpoint does not flip everything inactive.

## README rendering (render.py)

README has a hand-written header above `<!-- TABLE_START -->`. Everything below the marker is regenerated on every run. Sorted by `first_seen` descending. Only active postings. Columns: Company | Role | Location | Posted | Apply. Last-updated timestamp (Pacific time) and total count at the bottom.

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

v1 steps 1 through 8 are built and live at github.com/ShayneNSG/fintern, running hourly. Workday support was added the same day. `companies.json` has 91 entries: 48 Greenhouse, 8 Ashby, 3 Lever, 32 Workday. Every non-Workday board token was checked live against its ATS endpoint on 2026-09-09. Every Workday tenant/site was confirmed to resolve the same day, but the JSON endpoint itself could not be exercised from the build environment, so the first hourly run is the real test. Check the Actions log for "fetch failed" lines.

Not trackable because they run a custom or unsupported ATS: Goldman Sachs, JPMorgan (Oracle), Morgan Stanley, Bank of America, Citi, Barclays, Deutsche Bank, UBS, Evercore, Lazard, Jefferies, Centerview, KKR, McKinsey, BCG, Bain, Deloitte, EY, KPMG, Kearney, Uber, Snap, Netflix (Eightfold), NBCUniversal (SmartRecruiters), Paramount, Activision, Rippling, Marqeta, Canva, Snowflake.

## v2 ideas (do not build yet)

* SmartRecruiters support (NBCUniversal) and Eightfold (Netflix).
* Category tabs or grouping in README.
* Off-season (fall, spring) view.
* Simple GitHub Pages site with filters.
* Location filter (CA, NY, remote).
* Accept community PRs to companies.json.
