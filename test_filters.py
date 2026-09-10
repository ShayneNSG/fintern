"""Quick sanity checks for filters.py. Run with: python -m pytest -q  or  python test_filters.py"""

from __future__ import annotations

from filters import passes

RELAXED_SHOULD_PASS = [
    "2027 Summer Analyst Program",
    "2027 Investment Banking Summer Analyst",
    "Summer Intern, Corporate Banking",
]

RELAXED_SHOULD_FAIL = [
    "2027 Technology Summer Analyst",
    "Software Engineer Summer Analyst",
    "Marketing Intern",
    "Investment Banking Analyst",
]

SHOULD_PASS = [
    "Finance Intern (Summer 2027)",
    "FP&A Intern",
    "Strategic Finance Intern",
    "Corporate Development Intern",
    "Summer Analyst, Investment Banking",
    "Intern, Treasury",
    "BizOps Intern - Summer 2027",
    "Accounting Co-op",
    "Strategy & Finance Internship",
    "Business Operations Intern, Summer 2027",
    "Corporate Banking Summer 2027 Analyst",
    "2027 Intern - Corporate Finance Consulting",
]

SHOULD_FAIL = [
    "Software Engineer Intern",
    "Tax Intern",
    "Internal Audit Intern",
    "Finance Manager",
    "Financial Analyst",
    "Marketing Intern",
    "Data Science Intern, Finance",
    "Payroll Intern",
    "International Finance Manager",
    "Syntax Intern",
    "Adventure Guide Intern",
    "Accounts Payable Intern",
    "Finance Engineering Intern",
]


def test_pass() -> None:
    for title in SHOULD_PASS:
        assert passes(title), title


def test_fail() -> None:
    for title in SHOULD_FAIL:
        assert not passes(title), title


def test_relaxed() -> None:
    for title in RELAXED_SHOULD_PASS:
        assert passes(title, relaxed=True), title
    for title in RELAXED_SHOULD_FAIL:
        assert not passes(title, relaxed=True), title


if __name__ == "__main__":
    test_pass()
    test_fail()
    test_relaxed()
    print("filters ok")
