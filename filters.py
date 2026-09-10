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
    "corporate banking",
    "commercial banking",
    "capital markets",
    "sales & trading",
    "sales and trading",
    "global markets",
    "restructuring",
    "m&a",
    "mergers",
    "private credit",
    "consulting",
    "consultant",
]

EXCLUDE_KEYWORDS: list[str] = [
    "software",
    "engineer",
    "engineering",
    "data science",
    "machine learning",
    "technology",
    "quantitative",
    "quant ",
    "marketing",
    "legal",
    "human resources",
    "communications",
    "tax",
    "audit",
    "assurance",
    "payroll",
    "accounts payable",
    "accounts receivable",
    "bookkeep",
    "actuarial",
]

# Banks, PE, and wealth firms hire interns almost entirely into finance roles,
# and their titles rarely say "finance" ("2027 Summer Analyst"). For them the
# finance keyword check is skipped; the exclude list still applies. Consulting
# is deliberately not here: Accenture and PwC post hundreds of non-finance
# internships, so those must say finance, consulting, or similar in the title.
RELAXED_CATEGORIES: set[str] = {"bank", "pe", "wealth"}

# Location filter. A posting is dropped only when its location names somewhere
# outside the US and nothing in it points to the US. Blank or unrecognizable
# locations are kept. Set US_ONLY = False to turn this off.
US_ONLY = True

US_SIGNALS: list[str] = [
    "united states", "usa", "u.s.", "us-", "remote - us", "us remote",
    "new york", "nyc", "san francisco", "los angeles", "chicago", "boston",
    "seattle", "austin", "dallas", "houston", "atlanta", "miami", "denver",
    "charlotte", "washington", "philadelphia", "phoenix", "minneapolis",
    "menlo park", "palo alto", "mountain view", "san jose", "sunnyvale",
    "irvine", "santa monica", "culver city", "burbank", "universal city",
    "salt lake", "nashville", "st. louis", "milwaukee", "louisville",
    "pittsburgh", "detroit", "columbus", "baltimore", "portland", "san diego",
    "richmond", "mclean", "tampa", "orlando", "jersey city", "stamford",
]

US_STATES: list[str] = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

NON_US_SIGNALS: list[str] = [
    # countries and regions
    "canada", "united kingdom", "uk", "england", "scotland", "ireland", "india",
    "germany", "france", "spain", "italy", "netherlands", "belgium", "switzerland",
    "austria", "poland", "czech", "hungary", "romania", "portugal", "sweden",
    "denmark", "norway", "finland", "luxembourg", "greece", "turkey", "israel",
    "uae", "united arab emirates", "saudi", "qatar", "egypt", "south africa",
    "nigeria", "kenya", "china", "japan", "korea", "taiwan", "hong kong",
    "singapore", "malaysia", "indonesia", "thailand", "vietnam", "philippines",
    "australia", "new zealand", "brazil", "brasil", "mexico", "argentina",
    "colombia", "chile", "peru", "costa rica", "emea", "apac", "latam",
    # cities
    "london", "toronto", "vancouver", "montreal", "calgary", "ottawa", "dublin",
    "paris", "frankfurt", "munich", "berlin", "hamburg", "amsterdam", "brussels",
    "zurich", "geneva", "madrid", "barcelona", "milan", "milano", "rome", "lisbon",
    "warsaw", "prague", "budapest", "bucharest", "vienna", "stockholm",
    "copenhagen", "oslo", "helsinki", "athens", "istanbul", "tel aviv", "dubai",
    "abu dhabi", "riyadh", "doha", "cairo", "johannesburg", "cape town", "lagos",
    "nairobi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai", "pune",
    "gurgaon", "gurugram", "noida", "delhi", "kolkata", "shanghai", "beijing",
    "shenzhen", "tokyo", "osaka", "seoul", "taipei", "kuala lumpur", "jakarta",
    "bangkok", "manila", "ho chi minh", "hanoi", "sydney", "melbourne", "brisbane",
    "auckland", "sao paulo", "são paulo", "rio de janeiro", "mexico city",
    "monterrey", "guadalajara", "buenos aires", "bogota", "bogotá", "santiago",
    "lima", "san jose, costa rica", "belfast", "manchester", "edinburgh",
    "glasgow", "birmingham, uk", "leeds", "krakow", "gdansk", "wroclaw",
    "lyon", "montreal", "quebec", "halifax", "winnipeg", "edmonton",
]


def _compile(keywords: list[str]) -> re.Pattern[str]:
    parts = [re.escape(k) for k in keywords]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + ")", re.IGNORECASE)


_INTERN_RE = _compile(INTERN_KEYWORDS)
_FINANCE_RE = _compile(FINANCE_KEYWORDS)
_EXCLUDE_RE = _compile(EXCLUDE_KEYWORDS)
_US_RE = _compile(US_SIGNALS)
_NON_US_RE = re.compile(
    r"(?<![a-z])(?:" + "|".join(re.escape(k) for k in NON_US_SIGNALS) + r")(?![a-z])",
    re.IGNORECASE,
)
# State codes must be whole uppercase tokens: "NY", "WI-Milwaukee", "Austin, TX".
_STATE_RE = re.compile(r"(?<![A-Za-z])(?:" + "|".join(US_STATES) + r")(?![A-Za-z])")


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


def passes(title: str, relaxed: bool = False) -> bool:
    """True when the title is an internship, is finance, and hits no exclude word.

    relaxed=True skips the finance check (see RELAXED_CATEGORIES).
    """
    if not is_internship(title):
        log.debug("filtered (not internship): %s", title)
        return False
    if not relaxed and not is_finance(title):
        log.debug("filtered (not finance): %s", title)
        return False
    if is_excluded(title):
        log.debug("filtered (excluded keyword): %s", title)
        return False
    return True


def is_us_location(location: str) -> bool:
    """False only when the location clearly points outside the US.

    Blank, "Remote", and unrecognized strings count as US so we never drop a
    real posting just because a company formats locations strangely.
    """
    text = (location or "").strip()
    if not text:
        return True
    if _US_RE.search(text) or _STATE_RE.search(text):
        return True
    if _NON_US_RE.search(text):
        return False
    return True


def apply(postings: list[Posting], relaxed_companies: set[str] | None = None) -> list[Posting]:
    """Filter postings. relaxed_companies holds company names in RELAXED_CATEGORIES."""
    relaxed = relaxed_companies or set()
    kept: list[Posting] = []
    for p in postings:
        if not passes(p.title, p.company in relaxed):
            continue
        if US_ONLY and not is_us_location(p.location):
            log.debug("filtered (non-US location %r): %s", p.location, p.title)
            continue
        kept.append(p)
    log.info("filter: %d of %d postings passed", len(kept), len(postings))
    return kept
