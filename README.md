# FinTern: Finance Internships at Tech, Fintech, and Media Companies

A curated, auto-updated list of finance internship postings (FP&A, strategic
finance, corp dev, treasury, bizops, and similar) at companies finance students
actually want to work for. Not a firehose. The company list is hand-picked.

Refreshes every hour straight from company career pages (Greenhouse, Lever,
and Ashby boards). Newest postings on top. New postings also fire a Discord alert.

## How it works

`scrape.py` pulls every job from each board in `companies.json`, keeps titles
that look like a finance internship (`filters.py`), dedupes against `seen.json`,
rewrites the table below, and pings Discord for anything new. GitHub Actions
runs it on a cron and commits the result.

## Run it yourself

```
pip install -r requirements.txt
python scrape.py --no-notify        # first run: seed seen.json, no Discord
python scrape.py --dry-run -v       # see what would match without writing
export DISCORD_WEBHOOK_URL=...      # then plain `python scrape.py` alerts
python -m pytest -q                 # offline tests, no network needed
```

## Companies not covered yet

These are on the wishlist but use an ATS with no public JSON feed. Workday
companies (Disney, Warner Bros. Discovery, Paramount, Sony Pictures, Live
Nation, Activision, Fox) are already in `companies.json` and will light up
when Workday support lands. Uber, Snap, Netflix, NBCUniversal, Rippling,
Marqeta, Canva, and Snowflake run custom or unsupported career sites.

Want a company added? Open a PR against `companies.json`.

<!-- TABLE_START -->

| Company | Role | Location | Posted | Apply |
|---|---|---|---|---|
| Coinbase | Accounting Intern | Hybrid - New York, NY | 2026-09-08 | [Apply](https://www.coinbase.com/careers/positions/8173991?gh_jid=8173991) |
| Coinbase | FP&A Intern | Hybrid - New York, NY | 2026-09-08 | [Apply](https://www.coinbase.com/careers/positions/8175438?gh_jid=8175438) |
| Coinbase | Finance Operations Intern | Hybrid - New York, NY | 2026-09-08 | [Apply](https://www.coinbase.com/careers/positions/8175569?gh_jid=8175569) |

Last updated: 2026-09-09 23:28 UTC. 3 active postings.
