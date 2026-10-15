"""Helpers for the merchant catalogue and firm specs.

The Python spec modules (`spec_uk.py`, `spec_us.py`) are the source of truth; `build` serialises them to
`catalogue_uk.json`, `catalogue_us.json` and `firms.json` in the draft folder. Edit the spec modules, not the JSON.
"""

from __future__ import annotations

import json
from functools import lru_cache

from .constants import AMOUNT_MODES, CHART_ID, SOURCES_DIR


@lru_cache(maxsize=None)
def brands(jurisdiction: str) -> dict[str, dict]:
    name = "brands_uk.json" if jurisdiction == "UK" else "brands_us.json"
    data = json.loads((SOURCES_DIR / name).read_text(encoding="utf-8"))
    return {b["brand_id"]: b for b in data}


def U(
    use: str,
    direction: str,
    lo: str,
    hi: str,
    code: str,
    rules: list[str] | str,
    lines: list[str],
    *,
    facts: dict | None = None,
    hooks: list[str] | None = None,
    routine: bool = False,
    needs_line: bool = False,
    only: dict | None = None,
    refs: list[str] | None = None,
    fmt: str | None = None,
    narratives: list[str] | None = None,
    amount_mode: str = "range",
    fixed_group: str | None = None,
    amount_choices: list[str] | None = None,
) -> dict:
    """One use of a merchant: what the line is for, its amount range, default code and governing rules.

    `amount_mode` (F8): `range` draws a fresh amount per line; `fixed` keeps one amount per firm for this use (rent,
    loan instalments, contracts, subscriptions), with at most one price step; `round` rounds to 100 (500 above
    5,000) for drawdowns and capital injections; `whole` rounds to whole currency units (flat bank fees). `Env.amount_for`
    applies it. `fixed_group` makes several uses
    of one payee share one fixed amount (R6: "monthly instalment" and "loan repayment" of the same loan).
    """
    if isinstance(rules, str):
        rules = [rules]
    assert direction in ("spend", "receive")
    assert amount_mode in AMOUNT_MODES, amount_mode
    return {
        "use": use,
        "direction": direction,
        "amount_range": [lo, hi],
        "default_code": code,
        "rule_ids": rules,
        "line_descriptions": lines,
        "facts": facts or {},
        "policy_hooks": hooks or [],
        "routine": routine,
        "needs_line": needs_line,
        "only": only or {},
        "reference_patterns": refs,
        "bank_format": fmt,
        "narratives": narratives,
        "amount_mode": amount_mode,
        "fixed_group": fixed_group,
        "amount_choices": amount_choices,
    }


def _merchant(
    jurisdiction: str,
    merchant_id: str,
    kind: str,
    name: str,
    brand_id: str | None,
    contacts: list[str],
    narratives: list[str],
    uses: list[dict],
    refs: list[str],
    fmt: str,
    category: str,
    raw_contacts: list[str] | None,
) -> dict:
    chart_ids = [CHART_ID["UK_ST"], CHART_ID["UK_CO"]] if jurisdiction == "UK" else [CHART_ID["US"], CHART_ID["US_S_CORP"]]
    for u in uses:
        u["default_code_per_chart"] = {cid: u["default_code"] for cid in chart_ids}
        u["typical_direction"] = u["direction"]
    hooks = sorted({h for u in uses for h in u["policy_hooks"]})
    rule_ids = sorted({r for u in uses for r in u["rule_ids"]})
    return {
        "merchant_id": merchant_id,
        "kind": kind,
        "brand_id": brand_id,
        "name": name,
        "category": category,
        "jurisdiction": jurisdiction,
        "contact_names": contacts,
        "raw_contact_names": raw_contacts or [],
        "narratives": narratives,
        "reference_patterns": refs,
        "bank_format": fmt,
        "uses": uses,
        "policy_hooks": hooks,
        "rule_ids": rule_ids,
    }


def make_builders(jurisdiction: str):
    prefix = jurisdiction.lower()

    def B(brand_id, contacts, narratives, uses, *, refs=("",), fmt=None, category=None, raw=None, name=None):
        b = brands(jurisdiction)[brand_id]
        mid = f"{prefix}-b-{brand_id[len(prefix) + 1:]}"
        return _merchant(
            jurisdiction, mid, "brand", name or b["name"], brand_id, list(contacts), list(narratives), uses,
            list(refs), fmt or ("UK-DEB" if jurisdiction == "UK" else "US-CARD"), category or b["category_family"],
            raw,
        )

    def I(slug, name, contacts, narratives, uses, *, refs=("",), fmt=None, category="local", raw=None,
          kind="invented"):
        mid = f"{prefix}-{'i' if kind == 'invented' else 'g'}-{slug}"
        return _merchant(
            jurisdiction, mid, kind, name, None, list(contacts), list(narratives), uses, list(refs),
            fmt or ("UK-FPO" if jurisdiction == "UK" else "US-ACH"), category, raw,
        )

    return B, I
