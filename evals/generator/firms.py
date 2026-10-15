"""Expand the firm specs into full firm profiles.

Everything here is derived from the firm id alone (a sha256-seeded random.Random), never from the run seed, so
firms.json is identical for every run. Tax references are synthetic and fail their check rules (refs.py).
Person payees are '<initial> <invented surname>' (data/pseudo_surnames.json), drawn at random per firm.
"""

from __future__ import annotations

import hashlib
import json
import random
from functools import lru_cache
from pathlib import Path

from . import spec_uk, spec_us
from .charts import chart_id_for
from .constants import FIRM_SEED_SALT
from .templates import MEMO_STYLES
from .refs import fake_ct_reference, fake_ein, fake_paye_aoref, fake_utr, fake_vrn

UK_BANKS = ["uk-b-barclays", "uk-b-hsbc", "uk-b-natwest", "uk-b-bank-of-scotland", "uk-b-starling-bank", "uk-b-monzo"]
UK_CARD_BANKS = [b for b in UK_BANKS if b not in ("uk-b-starling-bank", "uk-b-monzo")]
US_BANKS = ["us-b-bank-of-america", "us-b-wells-fargo", "us-b-capital-one", "us-b-pnc-bank", "us-b-u-s-bank",
            "us-b-citibank"]


def firm_rng(firm_id: str, salt: str = "") -> random.Random:
    seed = int(hashlib.sha256(f"{FIRM_SEED_SALT}:{firm_id}:{salt}".encode()).hexdigest()[:16], 16)
    return random.Random(seed)


def _short(name: str) -> str:
    words = [w for w in name.replace("and", "").split() if w[0].isalpha() and w not in ("Ltd", "LLC", "Inc", "Co")]
    return "".join(w[0] for w in words[:3]).upper()


@lru_cache(maxsize=None)
def _surname_doc() -> dict:
    path = Path(__file__).parent / "data" / "pseudo_surnames.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def surnames() -> tuple[str, ...]:
    """Frozen invented surnames (data/pseudo_surnames.json, built by make_names.py), after its deny filter."""
    return tuple(_surname_doc()["surnames"])


@lru_cache(maxsize=None)
def surname_slots() -> tuple[str | None, ...]:
    """The surname list at its pre-filter positions, None where make_names.py's deny filter dropped a name.

    Firms draw positions from this pre-filter pool, so the deny filter does not change how the firm's random stream
    is consumed: initials, owner counts and every surviving name stay where they were."""
    doc = _surname_doc()
    kept = iter(doc["surnames"])
    deny = doc.get("deny_filter") or {"draw_pool_size": len(doc["surnames"]), "removed_positions": []}
    removed = set(deny["removed_positions"])
    return tuple(None if i in removed else next(kept) for i in range(deny["draw_pool_size"]))


INITIALS = "ABCDEFGHJKLMNPRSTW"


def _people(firm_id: str, entity: str, employees: int, subcontractors: int, landlord: bool) -> dict:
    """Person payees as '<initial> <invented surname>'. Names are drawn at random per firm and never encode a role."""
    rng = firm_rng(firm_id, "people")
    names: list[str] = []
    slots = surname_slots()
    picks = [slots[i] for i in rng.sample(range(len(slots)), 14)]
    if None in picks:
        # A position the deny filter emptied takes a replacement from a separate stream, so `rng` is untouched.
        spare_rng = firm_rng(firm_id, "people-replace")
        spare = [s for s in surnames() if s not in picks]
        picks = [p if p is not None else spare.pop(spare_rng.randrange(len(spare))) for p in picks]
    for sn in picks:
        names.append(f"{rng.choice(INITIALS)} {sn}")
    owners_n = {"partnership": 2, "limited_company": rng.choice([1, 2])}.get(entity, 1)
    owners = names[:owners_n]
    rest = names[owners_n:]
    emp = rest[:employees]
    rest = rest[employees:]
    subs = rest[:subcontractors]
    rest = rest[subcontractors:]
    land = [rest.pop(0)] if landlord else []
    clients, rest = rest[-3:], rest[:-3]
    role = {"limited_company": "director", "s_corp": "officer"}.get(entity, "owner")
    role_of = {t: role for t in owners}
    role_of.update({t: "employee" for t in emp})
    role_of.update({t: "subcontractor" for t in subs})
    role_of.update({t: "landlord" for t in land})
    return {
        "owners": owners,
        "owner_role": role,
        "employees": emp,
        "subcontractors": subs,
        "landlord": land[0] if land else None,
        "unknown_pool": rest,  # never appear in history: used for NEEDS_REVIEW person payees
        "clients": clients,  # private clients who pay by bank transfer under their own name (re-audit R4)
        "role_of": role_of,
    }


CIS_NONE = {"contractor": False, "subcontractor": False, "deduction_rate": None}


def _cis(p: dict) -> dict:
    """UK CIS status (B16): who deducts, who suffers deductions and at what rate ("0" = gross payment status)."""
    cis = dict(CIS_NONE, **(p.get("cis") or {}))
    assert cis["deduction_rate"] in (None, "0", "20", "30"), cis
    assert not cis["subcontractor"] or cis["deduction_rate"] is not None, cis
    return cis


def _bank_name(bank_brand: str, merchants: list[dict]) -> str:
    return next(m["name"] for m in merchants if m["merchant_id"] == bank_brand)


def _cis_rates(firm_id: str, people: dict, cis: dict) -> dict:
    """Deduction rate per subcontractor of a CIS contractor (R7): one rate per person, mostly 20%, some gross
    payment status, rarely 30% (unregistered)."""
    if not cis["contractor"]:
        return {}
    rng = firm_rng(firm_id, "cis-rates")
    return {t: rng.choices(["20", "0", "30"], weights=[7, 2, 1])[0] for t in people["subcontractors"]}


def _uk_firm(firm_id: str, name: str, split: str, p: dict) -> dict:
    rng = firm_rng(firm_id, "tax")
    entity = p["entity_type"]
    utr = fake_utr(rng)
    tax = {
        "vat_registered": p["vat_registered"],
        "vrn": fake_vrn(rng) if p["vat_registered"] else None,
        "utr": utr,
        "paye_aoref": fake_paye_aoref(rng) if (p["employees"] or entity == "limited_company" or _cis(p)["contractor"]) else None,
        "ct_reference": fake_ct_reference(utr, rng) if entity == "limited_company" else None,
        "cis": _cis(p),
    }
    # A firm with a business credit card banks where cards are issued (re-audit R3, N2: Starling and Monzo issue no
    # business credit card).
    banks = UK_CARD_BANKS if p["policies"]["card_account"] in ("092", "811") else UK_BANKS
    bank_brand = banks[firm_rng(firm_id, "bank").randrange(len(banks))]
    banks = [{"code": "090", "name": "Business Current Account", "provider": bank_brand}]
    if p["policies"]["savings_account"]:
        banks.append({"code": "091", "name": "Business Savings Account", "provider": bank_brand})
    if p["policies"]["card_account"] == "092":
        banks.append({"code": "092", "name": "Business Credit Card", "provider": bank_brand})
    firm = {
        "firm_id": firm_id,
        "name": name,
        "short": _short(name),
        "jurisdiction": "UK",
        "entity_type": entity,
        "split": split,
        "trade": p["trade"],
        "town": p["town"],
        "accounting_basis": p["accounting_basis"],
        "tax": tax,
        "policies": dict(p["policies"]),
        "bank_accounts": banks,
        "bank_brand": bank_brand,
        "card4": f"{firm_rng(firm_id, 'card').randint(1000, 9999)}",
        "memo_style": firm_rng(firm_id, "style").choice(MEMO_STYLES),
        "people": _people(firm_id, entity, p["employees"], p["subcontractors"], p["landlord_person"]),
        "policy_gaps": p["policy_gaps"],
    }
    firm["chart_id"] = chart_id_for(firm)
    firm["bank_name"] = _bank_name(bank_brand, spec_uk.MERCHANTS)
    firm["people"]["cis_rates"] = _cis_rates(firm_id, firm["people"], tax["cis"])
    return firm


def _us_firm(firm_id: str, name: str, split: str, p: dict) -> dict:
    rng = firm_rng(firm_id, "tax")
    entity = p["entity_type"]
    tax = {"ein": fake_ein(rng), "sales_tax": p["policies"]["sales_tax"]}
    bank_brand = US_BANKS[firm_rng(firm_id, "bank").randrange(len(US_BANKS))]
    banks = [{"code": "1000", "name": "Business checking", "provider": bank_brand}]
    if p["policies"]["savings_account"]:
        banks.append({"code": "1010", "name": "Business savings", "provider": bank_brand})
    if p["policies"]["card_account"] == "2000":
        banks.append({"code": "2000", "name": "Business credit card", "provider": bank_brand})
    firm = {
        "firm_id": firm_id,
        "name": name,
        "short": _short(name),
        "jurisdiction": "US",
        "entity_type": entity,
        "split": split,
        "trade": p["trade"],
        "state": p["state"],
        "city": p["city"],
        "accounting_basis": p["accounting_basis"],
        "tax": tax,
        "policies": dict(p["policies"]),
        "bank_accounts": banks,
        "bank_brand": bank_brand,
        "card4": f"{firm_rng(firm_id, 'card').randint(1000, 9999)}",
        "memo_style": firm_rng(firm_id, "style").choice(MEMO_STYLES),
        "people": _people(firm_id, entity, p["employees"], p["subcontractors"], False),
        "policy_gaps": p["policy_gaps"],
        "state_revenue": list(spec_us.STATE_REVENUE[p["state"]]),
    }
    firm["chart_id"] = chart_id_for(firm)
    firm["bank_name"] = _bank_name(bank_brand, spec_us.MERCHANTS)
    return firm


@lru_cache(maxsize=None)
def _all() -> dict:
    out = {}
    for fid, (name, split, p) in sorted(spec_uk.FIRMS.items()):
        out[fid] = _uk_firm(fid, name, split, p)
    for fid, (name, split, p) in sorted(spec_us.FIRMS.items()):
        out[fid] = _us_firm(fid, name, split, p)
    return out


def all_firms() -> dict[str, dict]:
    import copy

    return copy.deepcopy(_all())


def profile_view(firm: dict) -> dict:
    """The metadata copy stored on each item (`firm_profile`); used only by the profile-injected arm."""
    keep = ("firm_id", "name", "jurisdiction", "entity_type", "trade", "accounting_basis", "policies")
    view = {k: firm[k] for k in keep}
    view["tax_registration"] = (
        {"vat_registered": firm["tax"]["vat_registered"], "employer": firm["tax"]["paye_aoref"] is not None,
         "cis": firm["tax"]["cis"]}
        if firm["jurisdiction"] == "UK"
        else {"sales_tax": firm["tax"]["sales_tax"], "payroll": firm["policies"]["payroll"]}
    )
    view["bank_accounts"] = [b["code"] for b in firm["bank_accounts"]]
    view["owners"] = firm["people"]["owners"]
    view["employees"] = len(firm["people"]["employees"])
    return view
