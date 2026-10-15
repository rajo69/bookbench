"""Chart access per firm.

One chart per entity family (F12): the UK default chart minus the other family's owner accounts (`entity_variants`
in chart_uk.json, with `UK_VARIANT_REMOVE_DEFAULT` as the fallback), and for the US the S corp overlay that renames
three accounts and adds 696.
"""

from __future__ import annotations

import json
from functools import lru_cache

from .constants import CHART_ID, DRAFT_DIR, NEEDS_REVIEW, UK_VARIANT_REMOVE_DEFAULT

UK_VARIANT_ENTITY = {"st": "sole_trader", "co": "limited_company"}


@lru_cache(maxsize=None)
def _raw(jurisdiction: str) -> dict:
    name = "chart_uk.json" if jurisdiction == "UK" else "chart_us.json"
    return json.loads((DRAFT_DIR / name).read_text(encoding="utf-8"))


def _entry(a: dict) -> dict:
    return {
        "code": a["code"],
        "name": a["name"],
        "type": a["type"],
        "bank_hit": a["bank_hit"],
        "class_family": a["class_family"],
    }


def variant_key(firm: dict) -> str:
    """`st` / `co` for UK firms, `base` / `s_corp` for US firms."""
    if firm["jurisdiction"] == "UK":
        return "co" if firm["entity_type"] == "limited_company" else "st"
    return "s_corp" if firm["entity_type"] == "s_corp" else "base"


@lru_cache(maxsize=None)
def uk_variant(variant: str) -> dict:
    """The chart_uk.json `entity_variants` entry for a UK variant key, or the built-in fallback."""
    entity = UK_VARIANT_ENTITY[variant]
    for v in (_raw("UK").get("entity_variants") or {}).values():
        if entity in v.get("applies_to", ()):
            return {"chart_id": v.get("chart_id") or CHART_ID[f"UK_{variant.upper()}"],
                    "remove": tuple(v.get("remove", ()))}
    return {"chart_id": CHART_ID[f"UK_{variant.upper()}"], "remove": UK_VARIANT_REMOVE_DEFAULT[variant]}


@lru_cache(maxsize=None)
def accounts(jurisdiction: str, variant: str = "base") -> dict[str, dict]:
    raw = _raw(jurisdiction)
    out: dict[str, dict] = {}
    for a in raw["accounts"] + raw.get("dataset_added_accounts", []):
        out[a["code"]] = _entry(a)
    if jurisdiction == "UK":
        for code in uk_variant("co" if variant == "co" else "st")["remove"]:
            out.pop(code, None)
    elif variant == "s_corp":
        overlay = raw["entity_variants"]["s_corp"]
        for code, ren in overlay["rename"].items():
            out[code] = dict(out[code], name=ren["name"])
        for add in overlay["add"]:
            out[add["code"]] = _entry(add)
    return out


def chart_id_for(firm: dict) -> str:
    key = variant_key(firm)
    if firm["jurisdiction"] == "UK":
        return uk_variant(key)["chart_id"]
    return CHART_ID["US_S_CORP"] if key == "s_corp" else CHART_ID["US"]


def firm_accounts(firm: dict) -> dict[str, dict]:
    return accounts(firm["jurisdiction"], variant_key(firm))


def account_name(firm: dict, code: str) -> str:
    if code == NEEDS_REVIEW:
        return "needs review (send to a person)"
    return firm_accounts(firm)[code]["name"]


def class_family(firm: dict, code: str) -> str:
    if code == NEEDS_REVIEW:
        return "needs_review"
    return firm_accounts(firm)[code]["class_family"]


def is_gold_eligible(firm: dict, code: str) -> bool:
    if code == NEEDS_REVIEW:
        return True
    acct = firm_accounts(firm).get(code)
    return bool(acct and acct["bank_hit"])


def in_chart(firm: dict, code: str) -> bool:
    """True when the code exists on the firm's chart variant (gold or not)."""
    return code == NEEDS_REVIEW or code in firm_accounts(firm)
