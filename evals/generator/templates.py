"""Templates: fill placeholders, render the Xero-like record and the bank line, derive the scored record.

Formats follow the documented shapes in notes/r2_uk.md section 3 and notes/r3_us.md section 3. The scored record
is derived exactly as production does (contract.md 3.1): description = first line description, else contact name,
else reference, else "Unknown".
"""

from __future__ import annotations

import datetime as dt
import random
import re
import string
from decimal import Decimal

from .constants import AWAY_USES, CURRENCY, LIMITS, ROLE_WORDS

_TOKEN = re.compile(r"\{([A-Z_]+?)(\d*)\}")
_ALNUM = string.ascii_uppercase + string.digits
# Trip and meeting purposes by trade, so unrelated firms do not share typed memos.
PURPOSES = {
    "construction": ["site visit", "job survey", "supplier visit", "installation job", "quote visit"],
    "trades": ["site visit", "job survey", "supplier visit", "customer job"],
    "manufacturing": ["supplier audit", "trade fair", "customer install", "factory visit"],
    "catering": ["event", "supplier visit", "catering job", "food fair"],
    "events": ["venue visit", "event setup", "client event", "supplier visit"],
    "creative": ["client pitch", "photo shoot", "client workshop", "design review"],
    "professional": ["client meeting", "training day", "conference", "client review"],
    "education": ["exam board meeting", "training day", "conference"],
    "health": ["training course", "conference", "home visit"],
    "default": ["supplier visit", "trade fair", "stock buying trip", "craft fair"],
}
MEMO_STYLES = ("plain", "lower", "month", "slash", "upper")


def apply_style(line: str, style: str, date: dt.date) -> str:
    """Per-firm typing habit for memos the bookkeeper types."""
    if not line:
        return line
    if style == "lower":
        return line.lower().replace(",", "")
    if style == "month":
        if any(w.upper() in MONTH_WORDS for w in re.findall(r"[A-Za-z]+", line)):
            return line  # the line already names a month ("PAYE NOV" stays as typed, re-audit R4)
        return f"{line} {MONTHS[date.month - 1].title()}"
    if style == "slash":
        return line.replace(", ", " / ")
    if style == "upper":
        return line.upper()
    return line


MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_WORDS = frozenset(MONTHS) | {"SEPT"} | {dt.date(2000, m, 1).strftime("%B").upper() for m in range(1, 13)}


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def draw_amount(rng: random.Random, lo: str, hi: str) -> Decimal:
    lo_c, hi_c = int(Decimal(lo) * 100), int(Decimal(hi) * 100)
    cents = rng.randint(lo_c, hi_c)
    # Small business lines cluster on round and .99 values; keep a share of them.
    roll = rng.random()
    if roll < 0.15 and hi_c - lo_c > 1000:
        cents = (cents // 100) * 100
    elif roll < 0.22 and hi_c - lo_c > 1000:
        cents = (cents // 100) * 100 - 1 if cents >= 100 else cents
    cents = max(lo_c, min(hi_c, cents))
    return (Decimal(cents) / 100).quantize(Decimal("0.01"))


def uk_tax_month(date: dt.date) -> str:
    """YYMM suffix for early or late PAYE payments: tax year end year and tax month (6 April is month 1)."""
    year_end = date.year + 1 if (date.month, date.day) >= (4, 6) else date.year
    start = dt.date(year_end - 1, 4, 6)
    months = (date.year - start.year) * 12 + date.month - start.month + (0 if date.day >= 6 else -1)
    return f"{year_end % 100:02d}{months + 1:02d}"


def fill(pattern: str, rng: random.Random, ctx: dict) -> str:
    """Replace {N4}, {A6}, {TOWN} and friends. `ctx` carries firm, date and person context."""
    if not pattern:
        return ""

    memo = ctx.get("_memo")

    def repl(m: re.Match) -> str:
        key, n = m.group(1), m.group(2)
        k = int(n) if n else 0
        # One id per record (R12, R13): an invoice number or a long transfer id repeated across the line, the
        # reference and the bank narrative of one record is the same value. Short tokens stay independent.
        if memo is not None and (key == "INV" or (key in ("A", "N") and k >= 6)):
            if m.group(0) not in memo:
                memo[m.group(0)] = _value(key, k)
            return memo[m.group(0)]
        return _value(key, k)

    def _value(key: str, k: int) -> str:
        date: dt.date = ctx["date"]
        firm = ctx["firm"]
        if key == "N":
            return "".join(str(rng.randint(0, 9)) for _ in range(k))
        if key == "A":
            return "".join(rng.choice(_ALNUM) for _ in range(k))
        if key == "K":
            # Constant per firm, merchant and use (loan and contract account numbers, F8): never changes month to
            # month, and two accounts at one payee (business and home line) get different numbers.
            kr = random.Random(f"{firm['firm_id']}:{ctx.get('merchant_id', '')}:{ctx.get('use', '')}:K")
            return "".join(kr.choice(_ALNUM) for _ in range(k or 8))
        if key == "TOWN":
            if ctx.get("away_town"):
                return ctx["away_town"]
            return firm.get("town", "LEEDS") if rng.random() < 0.7 else rng.choice(ctx["towns"])
        city, state = ctx.get("away_city") or (firm.get("city", ""), firm.get("state", ""))
        if key in ("CITY", "CITY_UP"):
            return city.upper()
        if key == "CITY_NAME":
            return city
        if key == "ST":
            return state
        if key == "STATE_REV":
            return ctx["state_revenue"][0]
        if key == "STATE_REV_SHORT":
            return ctx["state_revenue"][1]
        if key == "MMM":
            return MONTHS[date.month - 1]
        if key == "YY":
            return f"{date.year % 100:02d}"
        if key == "YEAR":
            return str(date.year)
        if key == "Q":
            return str((date.month - 1) // 3 + 1)
        if key == "YYMM":
            return uk_tax_month(date)
        if key == "INV":
            return f"INV-{rng.randint(1000, 9999)}"
        if key == "FIRMREF":
            return f"{firm['short']} {rng.randint(100, 9999)}"
        if key == "CARD":
            return firm["card4"]
        if key == "VRN":
            return firm["tax"]["vrn"]
        if key == "UTR":
            return firm["tax"]["utr"]
        if key == "AOREF":
            return firm["tax"]["paye_aoref"]
        if key == "CTREF":
            return firm["tax"]["ct_reference"]
        if key == "PURPOSE":
            return rng.choice(PURPOSES.get(firm["trade"]["tag"], PURPOSES["default"]))
        if key == "PERSON":
            return ctx.get("person", "[PERSON]")
        raise KeyError(f"unknown placeholder {{{key}{k or ''}}}")

    return _TOKEN.sub(repl, pattern)


def _cap(text: str, n: int) -> str:
    return text[:n].rstrip()


def bank_narrative(jurisdiction: str, fmt: str, base: str, ref: str) -> str:
    if jurisdiction == "UK":
        if fmt in ("UK-DEB", "UK-CHG", "UK-INT", "UK-CPT"):
            return _cap(base, LIMITS["narrative_UK"])
        # Payee field 18 characters then reference 18 characters (Bacs / Faster Payments).
        out = _cap(base, 18) + (" " + _cap(ref, 18) if ref else "")
        return out.strip()
    if fmt in ("US-ACH", "US-WIRE") and ref and ref not in base and "ID:" not in base:
        return _cap(f"{base} {ref}", LIMITS["narrative_US"])
    return _cap(base, LIMITS["narrative_US"])


def has_role_word(text: str) -> bool:
    words = set(re.findall(r"[a-z]+", (text or "").casefold()))
    return any(w in words for w in ROLE_WORDS)


def payee_token(narrative: str, ref: str, amount: Decimal) -> str:
    """Contact for a record whose source gives none (F8: Xero needs a contact): the payee as the statement shows it."""
    for cand in (narrative, ref):
        token = _cap(re.sub(r"\s+", " ", cand or "").strip(), 25)
        if token and not has_role_word(token):
            return token
    return "BANK CREDIT" if amount > 0 else "BANK PAYMENT"


def _away(rng: random.Random, jurisdiction: str, firm: dict, towns: list[str]) -> dict:
    """Another town (UK) or another city and state (US) for spending away from base."""
    if jurisdiction == "UK":
        others = [t for t in towns if t != firm.get("town")]
        return {"away_town": rng.choice(others)} if others else {}
    from .spec_us import FIRMS

    cities = sorted({(p["city"], p["state"]) for _n, _s, p in FIRMS.values() if p["city"] != firm.get("city")})
    return {"away_city": cities[rng.randrange(len(cities))]} if cities else {}


def derive_record(xero: dict) -> dict:
    """The four fields production reads (xero_adapter.py:302-313, categoriser.py:356-362)."""
    description = xero["line_description"] or xero["contact_name"] or xero["reference"] or "Unknown"
    amount = Decimal(xero["total"])
    if xero["type"].startswith("SPEND"):
        amount = -abs(amount)
    return {
        "date": xero["date"],
        "amount": money(amount),
        "description": description,
        "reference": xero["reference"],
    }


FEE_FORMATS = ("UK-CHG", "UK-INT", "US-FEE", "US-INT")
FAMILIES_S0 = ("contact_desc", "contact_only", "contact_ref")
FAMILIES_S1 = ("ref_narrative", "desc_narrative", "raw_contact")


def render(
    *,
    jurisdiction: str,
    rng: random.Random,
    ctx: dict,
    merchant: dict | None,
    use: dict | None,
    amount: Decimal,
    family: str,
    contact: str | None = None,
    line: str | None = None,
    ref: str | None = None,
    narrative: str | None = None,
    fmt: str | None = None,
) -> tuple[dict, dict]:
    """Render one transaction. Returns (xero_fields, bank_line)."""
    fmt = fmt or (use or {}).get("bank_format") or (merchant or {}).get("bank_format") or (
        "UK-DEB" if jurisdiction == "UK" else "US-CARD"
    )
    ctx = dict(ctx, _memo={})
    if (use or {}).get("use") in AWAY_USES and not (ctx.get("away_town") or ctx.get("away_city")):
        ctx.update(_away(rng, jurisdiction, ctx["firm"], ctx.get("towns") or []))
    if merchant:
        ctx.update(merchant_id=merchant["merchant_id"], use=(use or {}).get("use", ""))
    if narrative is None:
        pats = (use or {}).get("narratives") or (merchant or {}).get("narratives") or [""]
        narrative = fill(rng.choice(pats), rng, ctx)
    if ref is None:
        rpats = (use or {}).get("reference_patterns") or (merchant or {}).get("reference_patterns") or [""]
        ref = fill(rng.choice(rpats), rng, ctx)
    ref_limit = LIMITS["reference_UK"] if jurisdiction == "UK" else LIMITS["reference_US"]
    ref = _cap(ref, ref_limit) if ref else ""
    if contact is None:
        contact = fill(rng.choice(merchant["contact_names"]), rng, ctx) if merchant else ""
    if line is None:
        options = [x for x in (use or {}).get("line_descriptions", [""]) if x] or [""]
        line = fill(rng.choice(options), rng, ctx)
        if line and fmt not in FEE_FORMATS:
            line = apply_style(line, ctx["firm"].get("memo_style", "plain"), ctx["date"])
        if line and fmt in FEE_FORMATS:
            # Bank charge and interest lines: a bookkeeper copies the bank's own wording.
            line = re.sub(r"\s+", " ", re.sub(r"[:#]| REF .*$", "", narrative)).strip().capitalize()

    bank = {"narrative": bank_narrative(jurisdiction, fmt, narrative, ref), "bank_format": fmt}

    xero_contact, xero_line, xero_ref = contact, line, ref
    if family == "contact_desc":
        pass
    elif family == "contact_only":
        xero_line = ""
    elif family == "contact_ref":
        xero_line = ""
        if not xero_ref:
            xero_ref = _cap(narrative, ref_limit)
    elif family == "ref_narrative":
        xero_contact, xero_line = "", ""
        xero_ref = _cap(narrative, ref_limit)
    elif family == "desc_narrative":
        xero_line = narrative
    elif family == "raw_contact":
        xero_contact = _cap(narrative, 25)
        xero_line = ""
    elif family == "blank_contact":
        xero_contact, xero_line = "", ""
    elif family == "explicit":
        pass  # caller supplied every field verbatim
    else:
        raise ValueError(family)
    if not xero_contact:
        if fmt in FEE_FORMATS and ctx["firm"].get("bank_name"):
            xero_contact = ctx["firm"]["bank_name"]  # bank charges and interest: the bank is the contact (R15)
        else:
            xero_contact = payee_token(narrative, ref, amount)

    total = abs(amount)
    xero = {
        "type": "SPEND" if amount < 0 else "RECEIVE",
        "contact_name": xero_contact or None,
        "line_description": xero_line,
        "reference": xero_ref or None,
        "total": money(total),
        "currency_code": CURRENCY[jurisdiction],
        "date": ctx["date"].isoformat(),
    }
    if xero["contact_name"] and len(xero["contact_name"]) > LIMITS["contact_name"]:
        raise ValueError("contact name too long")
    return xero, bank
