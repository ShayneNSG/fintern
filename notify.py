"""Discord webhook alerts. Plain POST, no bot library.

Webhook URL comes from the DISCORD_WEBHOOK_URL env var (a GitHub Actions
secret). One message per new posting; above BATCH_THRESHOLD new postings in
a single run, everything goes into one batched message instead so the very
first run does not spam or trip the rate limit.
"""

from __future__ import annotations

import logging
import os
import time

import requests

from sources.base import USER_AGENT, Posting

log = logging.getLogger(__name__)

ENV_VAR = "DISCORD_WEBHOOK_URL"
BATCH_THRESHOLD = 10
DISCORD_MAX_CHARS = 2000
DELAY_BETWEEN_MESSAGES = 0.6
TIMEOUT_SECONDS = 15


def require_webhook() -> str:
    """Fail loud before we spend a run fetching if the secret is missing."""
    url = os.environ.get(ENV_VAR, "").strip()
    if not url:
        raise SystemExit(f"config error: {ENV_VAR} is not set (use --no-notify to skip Discord)")
    return url


def format_single(p: Posting) -> str:
    location = p.location or "Location not listed"
    return f"**New: {p.company}**\n{p.title}\n{location}\n<{p.url}>"


def format_batch(postings: list[Posting]) -> list[str]:
    """Split a batch into as few messages as fit under Discord's 2000-char cap."""
    lines = [f"- **{p.company}**: {p.title} ({p.location or 'n/a'}) <{p.url}>" for p in postings]
    header = f"**{len(postings)} new finance internship postings**\n"
    messages: list[str] = []
    current = header
    for line in lines:
        if len(current) + len(line) + 1 > DISCORD_MAX_CHARS:
            messages.append(current.rstrip())
            current = ""
        current += line + "\n"
    if current.strip():
        messages.append(current.rstrip())
    return messages


def post(url: str, content: str) -> bool:
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(3):
        try:
            resp = requests.post(url, json={"content": content}, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            log.warning("discord post failed (attempt %d): %s", attempt + 1, exc)
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 2))
            log.warning("discord rate limited, waiting %.1fs", wait)
            time.sleep(wait)
            continue
        if resp.status_code >= 400:
            log.error("discord returned HTTP %s: %s", resp.status_code, resp.text[:200])
            return False
        return True
    return False


def send(new: list[Posting]) -> int:
    """Send alerts for new postings. Returns the number of messages delivered."""
    if not new:
        return 0
    url = require_webhook()
    if len(new) > BATCH_THRESHOLD:
        messages = format_batch(new)
    else:
        messages = [format_single(p) for p in new]
    delivered = 0
    for content in messages:
        if post(url, content):
            delivered += 1
        time.sleep(DELAY_BETWEEN_MESSAGES)
    log.info("discord: %d of %d messages delivered", delivered, len(messages))
    return delivered
