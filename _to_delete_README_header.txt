# FinTern: Finance Internships at Tech, Fintech, and Media Companies

A curated, auto-updated list of finance internship postings (FP&A, strategic
finance, corp dev, treasury, bizops, and similar) at companies finance students
actually want to work for. Not a firehose. The company list is hand-picked.

Refreshes every hour straight from company career pages (Greenhouse, Lever,
Ashby, and Workday boards). Newest postings on top. New postings also fire a Discord alert.

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

## What's covered

About 90 companies across fintech, tech, media, banks, private equity, and
consulting. Fintech and tech boards come from Greenhouse, Lever, and Ashby.
Banks, PE, and consulting mostly run on Workday, which has no official API,
so those go through the same JSON feed the Workday careers pages use
themselves. For bank, PE, consulting, and wealth firms the title only has to
look like an internship or summer analyst role, since "2027 Summer Analyst"
at Blackstone is the finance job.

## Companies not covered yet

These run custom career portals with no public feed: Goldman Sachs, JPMorgan,
Morgan Stanley, Bank of America, Citi, Barclays, Deutsche Bank, UBS, Evercore,
Lazard, Jefferies, Centerview, KKR, McKinsey, BCG, Bain, Deloitte, EY, KPMG,
Uber, Snap, Netflix, NBCUniversal, Paramount, Activision, Rippling, Marqeta,
Canva, and Snowflake.

Want a company added? Open a PR against `companies.json`.


