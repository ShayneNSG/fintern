"""Quick sanity checks for filters.py. Run with: python -m pytest -q  or  python test_filters.py"""

from __future__ import annotations

from filters import passes

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


if __name__ == "__main__":
    test_pass()
    test_fail()
    print("filters ok")
