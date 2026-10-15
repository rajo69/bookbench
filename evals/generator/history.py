"""Per-firm history ledgers: earlier, confirmed transactions that carry the firm's policies into the prompt.

A ledger holds four kinds of row, each tagged in `source`:
- `entity`: owner, director, employee, subcontractor and landlord payments that show the entity type and roles;
- `policy`: rows that evidence each firm policy (vehicle method, phone, threshold, card, processors, CIS, ...),
  except the policies listed in the firm's `policy_gaps`;
- `background`: routine lines from single-purpose merchants that fit the firm's trade, and customer receipts;
- `precedent`: the rows scored items rely on. A deciding precedent (`Prec.description` set) has an earlier date and
  either repeats the scored description (`precedent_form` `exact`, a recurring payee as in real books) or names the
  same payee another recognisable way (`varied`, A12 b): a catalogue contact, raw contact, narrative or other line of
  the same use, or for a person another form of the name. A varied row counts only if it ranks in the top 5 for the
  scored description under simulated retrieval (checked in a final pass when an embedder is given); otherwise the
  next candidate is tried, then the exact form (counted in `varied_fallbacks`). Other precedent rows are tagged
  from the data: `exact` when their description is a scored description of the firm, else `varied`.
Leakage rules (fix round 1, replacing the earlier "no scored description anywhere in history" rule):
- no history row equals a scored record (description, amount and date together);
- no row in a firm's history repeats the description of a NEEDS_REVIEW item of that firm;
- no row repeats a deciding precedent's description with a different account.
Added in fix round 2: no row other than an exact precedent repeats the scored description of a varied precedent
(otherwise the item would still find its own description in history), a varied candidate is never another scored
description of the firm, and precedent rows sharing a description share one account.
Amounts (F8) go through `Env.amount_for`, so `fixed` uses show one amount (plus at most one price step) across
history and scored items, and owner capital injections are round. Split rows (B5, B16) carry `lines` in the
`gold_lines` shape with `category_code` the primary line: UK processor payouts (UK-R019) and CIS receipts and
payments under deduction (UK-R067, UK-R069). Every row has `lines` and `precedent_form` (null when not applicable).
Memos never contain the account name (the old `account_name().lower()` fallback is gone).

Audit round 2 fixes:
- R1: every date goes through `Env.date_in(rng, window, fmt)` with the row's bank format, so Bacs, ACH, wire and check
  rows fall on working days. A precedent whose format is unknown (a person or bank token) is rolled to a working day,
  which is valid for every channel. `row_fmt` keeps each row's format for the checks.
- R9: monthly rows on one day of the month (give or take a working-day roll) for rent, loan instalments, the phone
  or broadband contract, salaries, PAYE and payroll runs; a sales stream (processor payouts, customer receipts, CIS
  receipts) sized against the firm's costs; background merchants filtered by trade and never a second landlord or
  phone provider.
- R5: one premises landlord per firm: the person landlord of firms.py, or one landlord merchant (the one scored
  items use when there is one). Person rent goes through `amount_for` with a fixed pseudo-use keyed on the landlord,
  the key the person scenarios use.
- R14: owner capital injections are round on every path (person rows and deciding precedents).
- R17: a payout is split or single from its use's facts (`split`), never from a merchant id list.
- R19, R7: CIS rates per subcontractor (`people.cis_rates`); gross payment status gives a plain remittance line.
- F3, F6: a precedent varies only when the scored description names the payee, and every varied candidate names
  the same payee; the retrieval check runs on the full stored text and on description-only text.
- F8: memo pools filtered by entity type (no "partners lunch" at a company).
- F9: precedent amounts keep the rule's label (thresholds); one description means one account across all non-person
  rows of a ledger, policy rows included.
"""

from __future__ import annotations

import calendar
import datetime as dt
import random
import re
from collections import Counter
from decimal import Decimal

from . import spec_uk, spec_us, splits
from .charts import account_name, firm_accounts, in_chart
from .constants import WORKING_DAY_FORMATS
from .engine import RULES, Env, Prec, _payee_only_ok
from .gold import Ctx, RuleNotApplicable
from .retrieval import TOP_K, doc_text, provisional_row_ids, rank_rows
from .templates import FEE_FORMATS, MONTHS, apply_style, derive_record, draw_amount, fill, money, render

# Memo words per account, written without the account's own name.
LABEL_MEMOS = {
    "461": ["printer paper", "toner", "envelopes"], "310": ["stock", "ingredients", "job materials"],
    "463": ["licence renewal"], "489": ["phone bill", "broadband"], "449": ["van fuel", "van costs"],
    "980": ["personal"], "835": ["director personal"], "3010": ["personal"],
    "670": ["shop consumables"], "645": ["paper and toner"], "605": ["truck fuel"],
}

BACKGROUND_PER_FIRM = 14
# Total rows a ledger aims at (R9: about 40 to 90): background rows shrink when the monthly rows already fill it.
TARGET_ROWS = 78
MIN_BACKGROUND = 3
# Sales stream (R9): at least one income row a month, more until income covers costs, at most this many rows.
MAX_SALES = 16
GAP_EXCLUDES = {"phone": {"telecom"}, "vehicle_method": {"fuel", "vehicle_parts_repair"}}
# Owner money paid in (UK 970, US 3000): round amounts (F8, R14).
CAPITAL_CODES = {"970", "3000"}
# Codes left out of the cost total the sales stream is sized against: owner, savings and loan movements.
NOT_COSTS = {"980", "835", "3010", "970", "3000", "091", "1010", "900", "2300"}
# Rent and office-space uses: only the firm's one landlord stream pays them (R5).
RENT_USES = {"rent", "space_rent"}
# Background merchants that only fit some trades (R9). A merchant may also carry its own `trades` list.
OFFICE_TRADES = ["creative", "professional", "education", "events", "health"]
BACKGROUND_TRADES = {
    "amazon-web-services": OFFICE_TRADES, "slack": OFFICE_TRADES, "atlassian": OFFICE_TRADES,
    "salesforce": OFFICE_TRADES, "hubspot": OFFICE_TRADES, "calendly": OFFICE_TRADES + ["beauty", "services"],
    "docusign": OFFICE_TRADES, "zoom": OFFICE_TRADES, "dropbox": OFFICE_TRADES, "bluehost": OFFICE_TRADES,
    "shopify": ["retail", "crafts", "catering"],
}
BACKGROUND_CATEGORY_TRADES = {
    "airline": OFFICE_TRADES + ["manufacturing", "transport"],
    "workspace": [],
}
# UK firms keep their books in Xero: no rival accounting package in the background.
UK_ACCOUNTING_OK = {"uk-b-xero"}
# Bank-text abbreviations for payees that are only a bank token (payer:, payee:, atm, own:, check:): the varied form
# of "PAYMENT 3369" is "PMT 3369". Each pair works both ways.
ABBREV = {"PAYMENT": "PMT", "TRANSFER": "TFR", "DEPOSIT": "DEP", "CREDIT": "CR", "RECEIVED": "RCVD",
          "SAVINGS": "SAV", "BUSINESS": "BUS", "ONLINE": "ONLN", "MOBILE": "MOB", "LNK": "LINK", "CHECK": "CHK",
          "WITHDRAWAL": "WDL", "ACCOUNT": "ACCT", "FROM": "FRM"}
ABBREV.update({v: k for k, v in list(ABBREV.items())})
# Invented contractors paying a CIS subcontractor firm, used only when the catalogue has no CIS payer use. Both
# names returned no Companies House result and no web match on 2026-10-13 (L1, audit round 2).
CIS_CONTRACTORS = ("Thrandle Contracting Ltd", "Marlstone Build Ltd", "Vorthmoor Construction Ltd")
# Plain remittance lines for gross payment status (R19): no deduction figures.
GROSS_REMITTANCES = ("Remittance {d}: valuation {N2}", "Payment advice {d}, stage payment", "Remittance {d}, plot {N2}")
GROSS_PAYMENTS = ("{s} invoice {N3}", "Payment to {s}, job {N4}", "{s} remittance {d}")
_MONTH_WORDS = {m.casefold() for m in MONTHS}
# Role words and the entity types they fit (F8): a memo naming a role the firm cannot have is never used.
ROLE_ENTITIES = {
    "partner": {"partnership"}, "partners": {"partnership"},
    "director": {"limited_company"}, "directors": {"limited_company"},
    "officer": {"s_corp"}, "officers": {"s_corp"}, "shareholder": {"s_corp"},
    "proprietor": {"sole_trader", "sole_prop"},
    "owner": {"sole_trader", "partnership", "sole_prop", "smllc"},
    "llc": {"smllc"},
}
# Words that do not identify a payee (F3, F6): legal forms, generic trade nouns and bank-feed tokens.
PAYEE_STOP = set("""
ltd limited plc llp llc inc co company corp the and of uk us usa group services service solutions systems
business bank banking council borough city county state department revenue tax trust centre center practice
school studio partners management mgmt payments payment pay paid card credit debit loan loans finance savings
account accounts water gas energy electric electricity power broadband phone mobile media net online digital
store stores shop shops supplies supply office home house international national express direct plus one
cafe kitchen restaurant bistro brasserie bar tavern bbq hire rental rentals auto car cars motor motors tools
tyres garage legal accountancy accountants accounting advisory cleaning catering equipment workplace personal
commercial apartments apts community union cu cmty properties property park estates lettings leasing insurance
pensions pension health fees fee des id ppd web ach pos pmt tfr dd so bgc fpo fpi ref inv invoice transfer
deposit sq tst pp paypal ccd www com uk ref limited monthly annual subscription
""".split())


_MONTH_RE = re.compile(r"\b(JANUARY|FEBRUARY|MARCH|APRIL|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|"
                       r"JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", re.IGNORECASE)
_MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]


def redate(text: str | None, date: dt.date) -> str | None:
    """Replace month words in `text` with `date`'s month, keeping the form (abbreviation or full) and the case."""
    if not text:
        return text

    def sub(m: re.Match) -> str:
        word = m.group(0)
        new = _MONTH_FULL[date.month - 1] if len(word) > 3 else MONTHS[date.month - 1].title()
        if word.isupper():
            return new.upper()
        return new.lower() if word.islower() else new

    return _MONTH_RE.sub(sub, text)


def norm(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def form_key(text: str | None) -> str:
    """`norm` without the firm's memo styling (commas, slashes, a trailing month), so a styled copy of the scored
    line does not pass as a varied form."""
    words = norm(text).replace(" / ", " ").replace(",", "").split()
    if len(words) > 1 and words[-1] in _MONTH_WORDS:
        words = words[:-1]
    return " ".join(words)


def role_ok(text: str | None, firm: dict) -> bool:
    """F8: a memo naming a role (partner, director, owner, officer, LLC) fits the firm's entity type."""
    ent = firm["entity_type"]
    return all(ent in ROLE_ENTITIES[w] for w in re.findall(r"[a-z]+", (text or "").casefold()) if w in ROLE_ENTITIES)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").casefold())


def _word_match(a: str, b: str) -> bool:
    return a == b or (len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)))


def names_payee(text: str | None, payee_words: set[str]) -> bool:
    return any(_word_match(w, x) for x in _words(text or "") for w in payee_words)


def _swap_abbrev(text: str, first_only: bool) -> str:
    out, done = [], False
    for tok in text.split(" "):
        key = tok.upper()
        if key in ABBREV and not (first_only and done):
            new = ABBREV[key]
            out.append(new if tok.isupper() else new.title())
            done = True
        else:
            out.append(tok)
    return " ".join(out)


class HistoryBuilder:
    def __init__(self, env: Env, firm: dict, rng: random.Random, scored_records: set[tuple], embedder=None):
        self.env, self.firm, self.rng = env, firm, rng
        self.scored_records = scored_records  # (firm_id, description, amount, date) of scored items
        self.embedder = embedder  # retrieval.Embedder or None (retrieval off: the first valid candidate is kept)
        st = env.state[firm["firm_id"]]
        self.review_desc = st.review_desc
        self.required_desc = st.required_desc
        self.required = st.required
        self.scored_desc = {d for f, d, _a, _t in scored_records if f == firm["firm_id"]}
        self.rows: list[dict] = []
        self.jur = env.jur
        self.blocked: set[str] = set()  # scored descriptions of varied precedents: no other row may repeat them
        self.prec_desc: dict[str, str] = {}  # description -> account of precedent rows written so far
        self.desc_label: dict[str, str] = {}  # description -> account of every non-person row (F9 one-account)
        self.row_fmt: dict[int, str | None] = {}  # id(row) -> bank format the row was dated with (R1)
        self.varied: list[dict] = []  # pending varied rows: {"row", "prec", "cands"}
        self.deciding: list[dict] = []  # deciding precedent rows, in the order written
        self.plan: dict[int, str] = {}  # id(prec) -> planned form (exact / varied) after the F3 check
        self.varied_fallbacks = 0
        self.varied_dated = 0  # exact precedents whose month words were re-dated, so they count as varied
        self.varied_promoted = 0
        self.fallback_reasons: Counter = Counter()  # why planned varied rows ended exact (diagnostics)
        self.deciding_forms: Counter = Counter()  # final form of each deciding precedent row
        self.sales_rows_written = 0
        self.deciding_prec: dict[int, Prec] = {}  # id(deciding row) -> its precedent
        self.dropped = 0  # rows removed so a deciding precedent stays in the top 5
        self.streams: dict[tuple[str, str], list[dict]] = {}  # (payee id, account) -> its monthly rows
        self.replaced = 0  # monthly rows a deciding precedent took over (one bill or pay a month, re-audit R4)

    # ------------------------------------------------------------------ dates and formats (R1)
    def _fmt(self, m: dict | None, u: dict | None, fmt: str | None = None) -> str:
        return self.env.fmt_for(m, u, fmt, self.jur)

    def _date(self, fmt: str | None, window=None) -> dt.date:
        return self.env.date_in(self.rng, window or self.env.hist_window, fmt)

    def _roll(self, d: dt.date, fmt: str | None) -> dt.date:
        """The working-day roll of `Env.date_in` for a fixed date: forward, or back when the window ends first."""
        a, b = self.env.hist_window
        if fmt not in WORKING_DAY_FORMATS:
            return d
        step = 1
        while not self.env.is_working_day(d):
            d += dt.timedelta(days=step)
            if d > b:
                d, step = b, -1
        return d

    def _months(self) -> list[tuple[dt.date, dt.date]]:
        a, b = self.env.hist_window
        out, y, mo = [], a.year, a.month
        while (y, mo) <= (b.year, b.month):
            start = max(a, dt.date(y, mo, 1))
            end = min(b, dt.date(y, mo, calendar.monthrange(y, mo)[1]))
            if (end - start).days >= 14:  # a stub month (5 April) gets no row of its own
                out.append((start, end))
            y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
        return out

    def _month_dates(self, day: int, fmt: str | None) -> list[dt.date]:
        """One date a month on `day` (R9), rolled to a working day for working-day formats."""
        out = []
        for start, end in self._months():
            d = dt.date(start.year, start.month, min(day, calendar.monthrange(start.year, start.month)[1]))
            if start <= d <= end:
                out.append(self._roll(d, fmt))
        return out

    def _unknown_fmt(self) -> str:
        """Format used to date a row whose channel is unknown: a working-day roll is valid for every channel."""
        return "UK-DD" if self.jur == "UK" else "US-ACH"

    def working_day_violations(self) -> int:
        n = 0
        for r in self.rows:
            if self.row_fmt.get(id(r)) in WORKING_DAY_FORMATS:
                n += int(not self.env.is_working_day(dt.date.fromisoformat(r["date"])))
        return n

    # ------------------------------------------------------------------ leakage and one-account checks
    def _allowed(self, desc: str, label: str, amount: str, date: str, source: str = "", person: bool = False) -> bool:
        n = norm(desc)
        if n in self.review_desc or n in self.blocked:
            return False
        if self.required_desc.get(n, label) != label:
            return False
        if source == "precedent" and self.prec_desc.get(n, label) != label:
            return False
        if not person and self.desc_label.get(n, label) != label:
            return False
        return (self.firm["firm_id"], n, amount, date) not in self.scored_records

    # ------------------------------------------------------------------ row primitives
    def _row(self, rec: dict, label: str, merchant_id: str, source: str, rule_id: str | None, *,
             lines: list | None = None, form: str | None = None, fmt: str | None = None,
             person: bool = False) -> dict:
        if not in_chart(self.firm, label):
            raise ValueError(f"{self.firm['firm_id']}: history row code {label} is not on the firm's chart")
        row = {
            "firm_id": self.firm["firm_id"],
            "date": rec["date"],
            "amount": rec["amount"],
            "description": rec["description"],
            "reference": rec["reference"],
            "category": account_name(self.firm, label),
            "category_code": label,
            "categorisation_status": "confirmed" if self.rng.random() < 0.85 else "auto_categorised",
            "merchant_id": merchant_id,
            "source": source,
            "rule_id": rule_id,
            "lines": lines,
            "precedent_form": form,
        }
        self.rows.append(row)
        self.row_fmt[id(row)] = fmt
        n = norm(rec["description"])
        if source == "precedent":
            self.prec_desc.setdefault(n, label)
        if not person:
            self.desc_label.setdefault(n, label)
        return row

    def _lines(self, lines) -> list[dict]:
        return splits.lines_json(lines, lambda c: account_name(self.firm, c))

    def _line_pool(self, u: dict) -> list[str]:
        return [x for x in u["line_descriptions"] if x and role_ok(x, self.firm)]

    def _payroll_kind(self, m: dict | None, u: dict | None) -> str | None:
        """US payroll provider uses whose amount the US catalogue sizes per firm (R18): "net" or "tax"."""
        if self.jur != "US" or m is None or u is None or getattr(spec_us, "payroll_amount", None) is None:
            return None
        return {"net_pay": "net", "payroll_tax": "tax"}.get(u["use"])

    def _amount(self, m: dict | None, u: dict, date: dt.date) -> Decimal:
        """Unsigned amount of one line of a catalogue use: US payroll from `spec_us.payroll_amount` when the
        catalogue has it (history pay then matches the scored items, R18), else `Env.amount_for`."""
        kind = self._payroll_kind(m, u)
        if kind:
            return abs(Decimal(spec_us.payroll_amount(self.env, self.firm, m, kind, date)))
        before = getattr(spec_uk, "CS01_FEE_BEFORE", None) if self.jur == "UK" else None
        if before and m is not None and m["merchant_id"] == "uk-g-companies-house" and u["use"] == "confirmation" \
                and date.isoformat() < before[1]:
            return Decimal(before[0])  # R10: the confirmation statement fee in force on that date
        return self.env.amount_for(self.rng, self.firm, m, u, date)

    def _render_use(self, m: dict, u: dict, line_pat: str) -> dict:
        """The use as render sees it: one line pattern, and when that line carries an invoice number, only the
        reference patterns that repeat it (R12: one invoice number per record)."""
        refs = (u.get("reference_patterns") or m["reference_patterns"]) or [""]
        if "{INV}" in line_pat:
            refs = [r for r in refs if "{INV}" in r or not r] or [""]
        return dict(u, line_descriptions=[line_pat], reference_patterns=refs)

    def merchant_row(self, m: dict, u: dict, label: str, source: str, *, sign: int | None = None,
                     amount: Decimal | None = None, rule_id: str | None = None, window=None) -> dict | None:
        rng = self.rng
        fmt = self._fmt(m, u)
        pool = self._line_pool(u)
        for _attempt in range(12):
            ruse = self._render_use(m, u, rng.choice(pool) if pool else "")
            date = self._date(fmt, window)
            ctx = self.env.fill_ctx(self.firm, date)
            amt = amount if amount is not None else self._amount(m, u, date)
            s = sign if sign is not None else (-1 if u["direction"] == "spend" else 1)
            choice = rng.random()
            line = None
            if pool and choice < 0.5:
                fam = "contact_desc"
            elif label in LABEL_MEMOS and choice < 0.7 and role_ok(" ".join(LABEL_MEMOS[label]), self.firm):
                # Only a kitchen buys ingredients (re-audit R4: "Buildbase ingredients" at a plasterer).
                memo = rng.choice([w for w in LABEL_MEMOS[label]
                                   if w != "ingredients" or self.firm["trade"]["tag"] == "catering"])
                fam, line = "contact_desc", f"{fill(rng.choice(m['contact_names']), rng, ctx)} {memo}"
            else:
                fam = rng.choice(["contact_only", "contact_ref", "desc_narrative"])
                if fam != "desc_narrative" and not _payee_only_ok(u, m):
                    fam = "desc_narrative"
            xero, _bank = render(jurisdiction=self.jur, rng=rng, ctx=ctx, merchant=m, use=ruse, amount=abs(amt) * s,
                                 family=fam, line=line)
            rec = derive_record(xero)
            if self._allowed(rec["description"], label, rec["amount"], rec["date"], source):
                return self._row(rec, label, m["merchant_id"], source, rule_id, fmt=fmt)
        return None

    def merchant_stream(self, m: dict, u: dict, label: str, source: str, rule_id: str | None, *,
                        sign: int | None = None, amount: Decimal | None = None) -> int:
        """Monthly rows of one recurring payee (R9): one day of the month, one fixed amount (one price step allowed),
        one description style. A use drawn per line elsewhere is fixed here (rent, loans, contracts, payroll)."""
        rng = self.rng
        fmt = self._fmt(m, u)
        dates = self._month_dates(rng.randint(1, 28), fmt)
        amount_use = dict(u, amount_mode="fixed") if u.get("amount_mode", "range") == "range" else u
        s = sign if sign is not None else (-1 if u["direction"] == "spend" else 1)
        pool = self._line_pool(u)
        narrs = (u.get("narratives") or m["narratives"]) or [""]
        refs = (u.get("reference_patterns") or m["reference_patterns"]) or [""]
        # A bank rule keeps one description: the typed line first, then the payee, then the bank's own text.
        families = (["contact_desc"] if pool else []) + (
            ["contact_only", "contact_ref"] if _payee_only_ok(u, m) else []) + ["desc_narrative"]
        for fam in families:
            mm = dict(m, contact_names=[rng.choice(m["contact_names"])])
            uu = self._render_use(m, u, rng.choice(pool) if pool else "")
            uu = dict(uu, narratives=[rng.choice(narrs)], reference_patterns=[rng.choice(uu["reference_patterns"])])
            recs = []
            for d in dates:
                amt = amount if amount is not None else self._amount(m, amount_use, d)
                xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=self.env.fill_ctx(self.firm, d), merchant=mm,
                                 use=uu, amount=amt * s, family=fam)
                recs.append(derive_record(xero))
            if recs and self._allowed(recs[0]["description"], label, recs[0]["amount"], recs[0]["date"], source):
                n = 0
                for rec in recs:
                    if self._allowed(rec["description"], label, rec["amount"], rec["date"], source):
                        row = self._row(rec, label, m["merchant_id"], source, rule_id, fmt=fmt)
                        self.streams.setdefault((m["merchant_id"], label), []).append(row)
                        n += 1
                return n
        return 0

    def person_row(self, name: str, label: str, ref: str, source: str, *, sign: int, lo: str, hi: str,
                   merchant_id: str | None = None, rule_id: str | None = None, date: dt.date | None = None,
                   use: str | None = None, line: str = "", role: str | None = None) -> dict | None:
        """A payment to or from a person. `use` makes the amount fixed per person under that pseudo-use name (rent,
        salary), keyed on the person's merchant id as the person scenarios key it."""
        rng = self.rng
        pid = merchant_id or f"person:{self.firm['firm_id']}:{name}"
        contact = name
        if norm(name) in self.blocked:
            # The name is the scored description of a varied precedent: show this payment as "Surname I".
            initial, _, surname = name.partition(" ")
            contact = f"{surname} {initial}" if surname else name
        mode = "round" if label in CAPITAL_CODES and sign > 0 else ("fixed" if use else "range")
        pseudo_use = {"use": use or f"person:{label}", "amount_range": [lo, hi], "amount_mode": mode}
        shared = getattr(spec_uk, "PERSON_FIXED_UK", None) if self.jur == "UK" else None
        if use and role and shared and role in shared:
            # The scored person items' plan (scenarios_uk.person_amount): same pseudo-use, same person key.
            pseudo_use = shared[role]
        fmt = "UK-FPO" if self.jur == "UK" else "US-XFER"
        for _attempt in range(1 if date else 6):
            d = date or self._date(fmt)
            ctx = self.env.fill_ctx(self.firm, d, name)
            amt = self.env.amount_for(rng, self.firm, {"merchant_id": pid} if use else None, pseudo_use, d)
            xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=ctx, merchant=None, use=None, amount=amt * sign,
                             family="explicit", contact=contact, line=fill(line, rng, ctx), ref=fill(ref, rng, ctx),
                             narrative=name.upper(), fmt=fmt)
            rec = derive_record(xero)
            if self._allowed(rec["description"], label, rec["amount"], rec["date"], source, person=True):
                return self._row(rec, label, pid, source, rule_id, fmt=fmt, person=True)
        return None

    def person_stream(self, name: str, label: str, ref: str, source: str, *, sign: int, lo: str, hi: str,
                      use: str, rule_id: str | None, line: str = "", role: str | None = None) -> int:
        """Monthly payments to one person (salary, rent) on one day of the month, one fixed amount. A salary line
        (`Salary {MMM}`) is what a payroll bank rule types; rent to a landlord shows the landlord's name."""
        self.rng.randint(1, 28)  # the day is Env.pay_day now; the draw is kept so later history draws stay put
        pid = f"person:{self.firm['firm_id']}:{name}"
        n = 0
        day = self.env.pay_day(self.firm, name)
        for start, end in self._months():
            d = self.env.pay_date(start.year, start.month, day)
            if not start <= d <= end:
                continue
            row = self.person_row(name, label, ref, source, sign=sign, lo=lo, hi=hi, rule_id=rule_id, date=d,
                                  use=use, line=line, role=role)
            if row is not None:
                self.streams.setdefault((pid, label), []).append(row)
                n += 1
        return n

    def own_row(self, label: str, source: str, sign: int) -> None:
        rng = self.rng
        fmt = "UK-TFR" if self.jur == "UK" else "US-XFER"
        date = self._date(fmt)
        memo = rng.choice(["Transfer to savings", "Savings top up", "Move to deposit account", "Reserve for tax"])
        if sign > 0:
            memo = rng.choice(["Back from savings", "Savings withdrawal", "Return from deposit account"])
        # Own-account transfers: the firm's bank is the contact (R15).
        xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=self.env.fill_ctx(self.firm, date), merchant=None,
                         use=None, amount=draw_amount(rng, "300.00", "5000.00") * sign, family="explicit",
                         contact=self.firm.get("bank_name") or "", line=f"{memo} {date:%b}", ref="", narrative=memo,
                         fmt=fmt)
        rec = derive_record(xero)
        if self._allowed(rec["description"], label, rec["amount"], rec["date"], source):
            self._row(rec, label, "own:savings", source, None, fmt=fmt)

    # ------------------------------------------------------------------ split rows (B5, B16)
    def payout_row(self, m: dict, u: dict, source: str, rule_id: str = "UK-R019", window=None) -> dict | None:
        """A processor payout split 200 + 404: the statement text is the line, the amount is the net."""
        rng = self.rng
        fmt = self._fmt(m, u)
        for _attempt in range(8):
            date = self._date(fmt, window)
            gross = self.env.amount_for(rng, self.firm, m, u, date)
            try:
                pay = splits.processor_payout(rng, gross, m["merchant_id"], date, m["name"], u.get("facts"))
            except ValueError:
                continue
            ctx = self.env.fill_ctx(self.firm, date)
            xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=ctx, merchant=m, use=u, amount=pay["net"],
                             family="explicit", contact=fill(rng.choice(m["contact_names"]), rng, ctx),
                             line=pay["text"])
            rec = derive_record(xero)
            if self._allowed(rec["description"], "200", rec["amount"], rec["date"], source):
                return self._row(rec, "200", m["merchant_id"], source, rule_id, lines=self._lines(pay["lines"]),
                                 fmt=fmt)
        return None

    def processor_row(self, m: dict, u: dict, source: str, window=None) -> dict | None:
        """One payout of a processor or marketplace. UK: split or single from the use's own facts (R17); US: the
        sales recording policy decides the code."""
        if self.jur == "UK":
            if (u.get("facts") or {}).get("split") == "processor_payout":
                return self.payout_row(m, u, source, window=window)
            got = self.rule_label(m, u)
            if got is None:
                return None
            return self.merchant_row(m, u, got[0], source, rule_id=got[1], window=window)
        lab = "1100" if self.firm["policies"]["sales_recording"] == "processor_gross" else "400"
        return self.merchant_row(m, u, lab, source, rule_id="US-R120" if lab == "1100" else "US-R121", window=window)

    def _cis_payers(self, gross_status: bool = False) -> list[tuple[dict, dict]]:
        want = "UK-R068" if gross_status else "UK-R067"
        return self.uses(lambda m, u: u["direction"] == "receive" and want in u["rule_ids"])

    def cis_receipt_row(self, rate: str, source: str, payer: tuple[dict, dict] | None = None,
                        window=None) -> dict | None:
        """A CIS subcontractor paid by a contractor: split 200 + 625 under deduction, single 200 with a plain
        remittance line at gross payment status (R19)."""
        rng = self.rng
        gross_status = rate == "0"
        payers = [payer] if payer else self._cis_payers(gross_status)
        for _attempt in range(8):
            if payers:
                m, u = payers[rng.randrange(len(payers))]
                fmt = self._fmt(m, u)
            else:
                m = u = None
                fmt = "UK-FPI"
            date = self._date(fmt, window)
            ctx = self.env.fill_ctx(self.firm, date)
            if m is not None:
                gross = self.env.amount_for(rng, self.firm, m, u, date)
                contact, mid, narrative = fill(rng.choice(m["contact_names"]), rng, ctx), m["merchant_id"], None
            else:
                name = CIS_CONTRACTORS[rng.randrange(len(CIS_CONTRACTORS))]
                gross = draw_amount(rng, "600.00", "4800.00")
                contact, mid, narrative = name, f"cis:{self.firm['firm_id']}:{name}", name.upper()
            if gross_status:
                lines = [x for x in (u or {}).get("line_descriptions", []) if x and "CIS" not in x.upper()]
                pat = rng.choice(lines) if lines else rng.choice(GROSS_REMITTANCES).replace(
                    "{d}", splits.statement_date(date))
                text, amount, split_lines = fill(pat, rng, ctx), gross, None
            else:
                materials = Decimal(0) if rng.random() < 0.3 else (gross * Decimal(rng.randint(5, 40)) / 100).quantize(splits.Q)
                rec_cis = splits.cis_receipt(rng, gross, materials, rate, date)
                text, amount = rec_cis["text"], rec_cis["net"]
                split_lines = rec_cis["lines"] if rec_cis["split_kind"] is not None else None
            xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=ctx, merchant=m, use=u, amount=amount,
                             family="explicit", contact=contact, line=text, narrative=narrative,
                             ref=None if m else "", fmt=None if m else "UK-FPI")
            rec = derive_record(xero)
            if self._allowed(rec["description"], "200", rec["amount"], rec["date"], source):
                return self._row(rec, "200", mid, source, "UK-R067" if split_lines else "UK-R068",
                                 lines=self._lines(split_lines) if split_lines else None, fmt=fmt)
        return None

    def cis_rate(self, name: str) -> str:
        """R7: one deduction rate per subcontractor (firms.py `people.cis_rates`), 20% when the firm has none."""
        return (self.firm["people"].get("cis_rates") or {}).get(name, "20")

    def cis_payment_row(self, name: str, source: str, rate: str | None = None) -> dict | None:
        """A CIS contractor paying a subcontractor: split 321 + 827 under deduction; a single 321 with a plain
        remittance line when the subcontractor has gross payment status (rate 0)."""
        rng = self.rng
        rate = rate or self.cis_rate(name)
        fmt = "UK-FPO"
        for _attempt in range(8):
            date = self._date(fmt)
            ctx = self.env.fill_ctx(self.firm, date, name)
            gross = draw_amount(rng, "400.00", "3600.00")
            if rate == "0":
                pat = rng.choice(GROSS_PAYMENTS).replace("{d}", splits.statement_date(date)).replace("{s}", name)
                text, amount, split_lines = fill(pat, rng, ctx), -gross, None
            else:
                materials = Decimal(0) if rng.random() < 0.4 else (gross * Decimal(rng.randint(5, 35)) / 100).quantize(splits.Q)
                pay = splits.cis_payment(rng, gross, materials, rate, date, name)
                text, amount = pay["text"], pay["net"]
                split_lines = pay["lines"] if pay["split_kind"] is not None else None
            xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=ctx, merchant=None, use=None, amount=amount,
                             family="explicit", contact=name, line=text,
                             ref=fill("CIS {MMM}" if split_lines else "INV {N3}", rng, ctx),
                             narrative=name.upper(), fmt=fmt)
            rec = derive_record(xero)
            if self._allowed(rec["description"], "321", rec["amount"], rec["date"], source):
                return self._row(rec, "321", f"person:{self.firm['firm_id']}:{name}", source,
                                 "UK-R069" if split_lines else "UK-R055",
                                 lines=self._lines(split_lines) if split_lines else None, fmt=fmt)
        return None

    def _runs_payroll(self) -> bool:
        """UK-R070: the history shows payroll through net pay to employees (477) or a director's salary (478)."""
        return bool(self.firm["people"]["employees"]) or self.firm["entity_type"] == "limited_company"

    def cis_hmrc_row(self) -> None:
        """A contractor paying withheld CIS to HMRC with its Accounts Office reference: 827, or 825 with payroll."""
        rng = self.rng
        label = "825" if self._runs_payroll() else "827"
        m = self.env.by_id["uk-g-hmrc-cumbernauld"]
        aoref = self.firm["tax"].get("paye_aoref")
        if not aoref:
            from .refs import fake_paye_aoref

            aoref = fake_paye_aoref(random.Random(f"{self.firm['firm_id']}:cis-aoref"))
        fmt = "UK-FPO"
        for _attempt in range(8):
            date = self._date(fmt)
            ctx = self.env.fill_ctx(self.firm, date)
            ref = aoref + (fill("{YYMM}", rng, ctx) if rng.random() < 0.5 else "")
            xero, _ = render(jurisdiction=self.jur, rng=rng, ctx=ctx, merchant=m, use=None,
                             amount=-draw_amount(rng, "120.00", "2400.00"), family="explicit",
                             contact=m["contact_names"][0], line="" if rng.random() < 0.6 else fill("CIS {MMM}", rng, ctx),
                             ref=ref, fmt=fmt)
            rec = derive_record(xero)
            if self._allowed(rec["description"], label, rec["amount"], rec["date"], "policy"):
                self._row(rec, label, m["merchant_id"], "policy", "UK-R070", fmt=fmt)
                return

    # ------------------------------------------------------------------ deciding precedents (A12 b)
    def _catalogue_use(self, p: Prec) -> tuple[dict | None, dict | None]:
        m = self.env.by_id.get(p.merchant_id or "")
        u = next((x for x in m["uses"] if x["use"] == p.use), None) if m else None
        return m, u

    def _label_at(self, p: Prec, m: dict | None, u: dict | None, amount: Decimal) -> str | None:
        if m is None or u is None or not p.rule_id or p.rule_id not in RULES:
            return None
        ctx = Ctx(firm=self.firm, facts=dict(u["facts"]), merchant=m, use=u, amount=amount * p.sign)
        try:
            return RULES[p.rule_id](ctx).label
        except Exception:  # noqa: BLE001 - the rule needs facts only the scored item has
            return None

    def _precedent_amount(self, p: Prec, m: dict | None, u: dict | None, date: dt.date) -> Decimal:
        """Unsigned amount of a deciding precedent row: the use's fixed (or round) amount when it has one (F8),
        else the scored amount times 0.7 to 1.3 and never equal to it. Owner capital injections are round (R14),
        and the amount keeps the rule's label (F9: no precedent across the de minimis or capitalisation threshold)."""
        pid = p.person or p.merchant_id or ""
        shared = getattr(spec_uk, "PERSON_FIXED_UK", None) if self.jur == "UK" else None
        if shared and pid.startswith("person:") and p.label in ("469", "477", "478"):
            # A salary or rent precedent is one of the person's fixed monthly payments (re-audit R3, N3).
            role = self.firm["people"]["role_of"].get(pid.split(":", 2)[2])
            if role in shared:
                return self.env.amount_for(self.rng, self.firm, {"merchant_id": pid}, shared[role], date)
        mode = (u or {}).get("amount_mode", "range")
        tariff = u is not None and u["amount_range"][0] == u["amount_range"][1]
        if u is not None and (mode != "range" or tariff or self._payroll_kind(m, u)):
            return self._amount(m, u, date)
        base = Decimal(p.amount or "100.00")
        if (p.description or "").startswith("SO "):
            return base  # a standing order pays one fixed amount
        if p.label in CAPITAL_CODES and p.sign > 0:
            lo, hi = base * Decimal("0.7"), base * Decimal("1.3")
            pseudo = {"use": "capital", "amount_range": [f"{lo:.2f}", f"{hi:.2f}"], "amount_mode": "round"}
            amt = self.env.amount_for(self.rng, self.firm, None, pseudo, date)
            return amt + (Decimal("500") if amt > 5000 else Decimal("100")) if amt == base else amt
        check = self._label_at(p, m, u, base) == p.label
        amt = base
        for _attempt in range(8):
            amt = (base * Decimal(self.rng.randint(70, 130)) / 100).quantize(Decimal("0.01"))
            if amt == base:
                amt += Decimal("1.00")
            if not check or self._label_at(p, m, u, amt) == p.label:
                return amt
        for amt in (base - Decimal("1.00"), base + Decimal("1.00")):
            if amt > 0 and self._label_at(p, m, u, amt) == p.label:
                return amt
        return amt

    def payee_words(self, p: Prec) -> set[str]:
        """Words that name the precedent's payee (F3, F6): the surname of a person, the distinctive words of a
        catalogue merchant's name and contacts, the number of a bank token."""
        mid = p.merchant_id or p.person or ""
        if mid.startswith("person:"):
            surname = mid.split(":", 2)[2].partition(" ")[2]
            return {surname.casefold()} if surname else set()
        m = self.env.by_id.get(mid)
        if m is None:
            return set(re.findall(r"\d{3,}", p.description or ""))
        ctx = dict(self.env.fill_ctx(self.firm, self.env.hist_window[0]), merchant_id=m["merchant_id"])
        frng = random.Random(0)
        texts = [m["name"]] + [fill(x, frng, ctx) for x in m["contact_names"] + m["raw_contact_names"]
                               if "{PERSON}" not in x]
        for x in m["narratives"]:
            first = next((w for w in _words(re.sub(r"\{[A-Z_]+\d*\}", " ", x)) if w not in PAYEE_STOP), None)
            if first:
                texts.append(first)
        return {w for t in texts for w in _words(t) if w not in PAYEE_STOP and not w.isdigit()}

    def _usable(self, desc: str, p: Prec) -> bool:
        n = norm(desc)
        if not n or form_key(desc) == form_key(p.description) or n in self.scored_desc:
            return False
        if n in self.review_desc or n in self.blocked or self.required_desc.get(n, p.label) != p.label:
            return False
        if self.prec_desc.get(n, p.label) != p.label or self.desc_label.get(n, p.label) != p.label:
            return False
        if not role_ok(desc, self.firm):
            return False
        low = desc.casefold()
        return not any(" " in a["name"] and a["name"].casefold() in low for a in firm_accounts(self.firm).values())

    def varied_candidates(self, p: Prec, date: dt.date) -> list[str]:
        """Other forms of the precedent's payee that name the payee (F3, F6), in a fixed order, each filled once and
        filtered."""
        mid = p.merchant_id or p.person or ""
        rng = self.rng
        m, u = self._catalogue_use(p)
        if mid.startswith("person:"):
            name = mid.split(":", 2)[2]
            initial, _, surname = name.partition(" ")
            word = (p.reference or "").split(" ")[0]
            word = word if word.isalpha() and word.isupper() and len(word) <= 8 else ""
            prefix = ""
            at = (p.description or "").find(f"{initial} {surname[:3]}")
            if at > 0:
                prefix = p.description[:at]  # "Zelle Payment To ", "Cash App*"
            raw = [f"{prefix}{surname} {initial}" if prefix else "", name, f"{surname} {initial}",
                   f"{name} {word}" if word else "", f"{initial}. {surname}"]
        elif m is not None:
            ctx = dict(self.env.fill_ctx(self.firm, date), merchant_id=m["merchant_id"])
            pats = list(m["contact_names"]) + list(m["raw_contact_names"])
            pats += list((u or {}).get("narratives") or m["narratives"])
            raw = [fill(x, rng, ctx).strip() for x in pats if x and "{PERSON}" not in x]
            fmt = self._fmt(m, u)
            for x in (u or {}).get("line_descriptions", []):
                if x and "{PERSON}" not in x:
                    line = fill(x, rng, ctx)
                    if fmt not in FEE_FORMATS:
                        line = apply_style(line, self.firm.get("memo_style", "plain"), date)
                    raw.append(line.strip())
        else:
            raw = [_swap_abbrev(p.description, False), _swap_abbrev(p.description, True)]
        words = self.payee_words(p)
        seen, cands = set(), []
        for desc in raw:
            n = norm(desc)
            if n not in seen and names_payee(desc, words) and self._usable(desc, p):
                seen.add(n)
                cands.append(desc)
        return cands

    def can_vary(self, p: Prec) -> bool:
        """F3, F6: a precedent varies only when the scored description itself names the payee (a payee-free memo
        such as "Refund" or "Card payment" stays exact) and is not a split statement."""
        if p.lines:
            return False
        words = self.payee_words(p)
        return bool(words) and names_payee(p.description, words)

    def _prec_fmt(self, p: Prec, m: dict | None, u: dict | None) -> str:
        if m is not None:
            return self._fmt(m, u)
        desc = (p.description or "").upper()
        if self.jur == "US" and desc.startswith(("ZELLE", "CASH APP", "VENMO")):
            return "US-P2P"
        if self.jur == "US" and desc.startswith(("CHECK", "CHK")):
            return "US-CHECK"
        return self._unknown_fmt()

    def identical_row(self, p: Prec) -> None:
        """A deciding precedent: earlier date, the use's fixed amount or a different amount, and the scored
        description (`exact`) or another form of the same payee (`varied`, falling back to exact)."""
        rng = self.rng
        m, u = self._catalogue_use(p)
        mid = p.merchant_id or p.person
        want_varied = self.plan.get(id(p)) == "varied"
        if want_varied and norm(p.description) not in self.blocked:
            # A description also placed exact for another item cannot vary.
            want_varied = False
            self.varied_fallbacks += 1
            self.fallback_reasons["shared_exact"] += 1
        fmt = self._prec_fmt(p, m, u)
        # A payee billed or paid monthly gets no second payment in a month: the precedent takes over one month's
        # row, with its date and amount (re-audit R4: second salary, second phone bill, second card payment).
        live = {id(r) for r in self.rows}
        stream = [r for r in self.streams.get((mid or "", p.label), []) if id(r) in live and not p.lines]
        for _attempt in range(10):
            month = stream[rng.randrange(len(stream))] if stream else None
            date = dt.date.fromisoformat(month["date"]) if month else self._date(fmt)
            if p.lines:
                amt = sum(Decimal(a) for _c, a, _r in p.lines)  # the statement figures fix the amount
                lines = self._lines(p.lines)
            elif month:
                amt, lines = Decimal(month["amount"]), None
            else:
                amt, lines = self._precedent_amount(p, m, u, date) * p.sign, None
            # A month row taken over keeps its own reference: the scored one can be event-specific ("UNPAID DD" on a
            # reversal, re-audit R5).
            rec = {"date": date.isoformat(), "amount": money(amt), "description": p.description,
                   "reference": month["reference"] if month else p.reference}
            if want_varied:
                cands = self.varied_candidates(p, date)
                ref = month["reference"] if month else (None if norm(p.reference) == norm(p.description) else p.reference)
                while cands:
                    desc = cands.pop(0)
                    if (self.firm["firm_id"], norm(desc), rec["amount"], rec["date"]) in self.scored_records:
                        continue
                    row = self._row(dict(rec, description=desc, reference=ref), p.label, mid, "precedent",
                                    p.rule_id, form="varied", fmt=fmt)
                    self.varied.append({"row": row, "prec": p, "cands": cands})
                    self.deciding.append(row)
                    self.deciding_prec[id(row)] = p
                    self._take_over(month)
                    return
                want_varied = False
                self.varied_fallbacks += 1
                self.fallback_reasons["no_candidate"] += 1
            # A month word copied onto another date reads wrong ("SALARY APR" paid in November, re-audit R3 N3): the
            # earlier row names its own month, so it is a dated form of the payee, not an identical description.
            rec["description"], rec["reference"] = redate(rec["description"], date), redate(rec["reference"], date)
            form = "exact" if rec["description"] == p.description else "varied"
            self.varied_dated += form == "varied"
            if (self.firm["firm_id"], norm(rec["description"]), rec["amount"], rec["date"]) not in self.scored_records:
                row = self._row(rec, p.label, mid, "precedent", p.rule_id, lines=lines, form=form, fmt=fmt)
                self.deciding.append(row)
                self.deciding_prec[id(row)] = p
                self._take_over(month)
                return

    def _take_over(self, month: dict | None) -> None:
        """Remove the monthly row a deciding precedent replaced (`streams` keeps it; readers filter on live rows)."""
        if month is None:
            return
        self.rows = [r for r in self.rows if r is not month]
        self.row_fmt.pop(id(month), None)
        self.replaced += 1

    def _to_exact(self, entry: dict) -> None:
        row, p = entry["row"], entry["prec"]
        row.update(description=p.description, reference=p.reference, precedent_form="exact")
        self.varied_fallbacks += 1
        self.fallback_reasons["retrieval"] += 1

    def check_varied(self) -> None:
        """Final pass (A12 b retrieval check): every varied row must rank in the top 5 for its scored description
        against the firm's full history, with ties broken by the row ids build.py will assign, both on the stored
        text (date, description, reference, amount) and on the description alone, so a shared reference never
        carries the match (F3). A failing row takes its next candidate, then the exact form. Repeats until stable,
        since one change can move another row."""
        if self.embedder is None or not self.varied:
            return
        emb, active = self.embedder, list(self.varied)
        while active:
            ids = provisional_row_ids(self.rows, self.firm["firm_id"])
            ranked = [dict(r, row_id=i) for r, i in zip(self.rows, ids)]
            vecs = [emb.vector(doc_text(r)) for r in ranked]
            dvecs = [emb.vector(r["description"]) for r in ranked]
            pos = {id(r): k for k, r in enumerate(self.rows)}
            failing = []
            for entry in active:
                q = emb.vector(entry["prec"].description)
                k = pos[id(entry["row"])]
                top = [i for i, _sim in rank_rows(q, ranked, vecs)[:TOP_K]]
                top_d = [i for i, _sim in rank_rows(q, ranked, dvecs)[:TOP_K]]
                if k not in top or k not in top_d:
                    failing.append(entry)
            if not failing:
                return
            for entry in failing:
                row = entry["row"]
                while entry["cands"]:
                    desc = entry["cands"].pop(0)
                    key = (self.firm["firm_id"], norm(desc), row["amount"], row["date"])
                    if key not in self.scored_records and self._usable(desc, entry["prec"]):
                        row["description"] = desc
                        self.prec_desc.setdefault(norm(desc), row["category_code"])
                        self.desc_label.setdefault(norm(desc), row["category_code"])
                        break
                else:
                    self._to_exact(entry)
                    active.remove(entry)

    def protect_deciding(self) -> None:
        """Final pass after `check_varied`: a deciding precedent (same account and same payee or rule) must stay in the
        top 5 for its scored description. When monthly rows of another account crowd it out (a payroll run above a
        payroll tax payment, a salary above a director's loan transfer), the best-ranked crowding row that is not a
        precedent is dropped, one at a time, until every deciding precedent ranks 5 or better."""
        if self.embedder is None or not self.deciding:
            return
        emb = self.embedder
        for _round in range(4 * len(self.deciding) + 10):
            ids = provisional_row_ids(self.rows, self.firm["firm_id"])
            ranked = [dict(r, row_id=i) for r, i in zip(self.rows, ids)]
            vecs = [emb.vector(doc_text(r)) for r in ranked]
            victim = None
            for row in self.deciding:
                p = self.deciding_prec[id(row)]
                mid = p.merchant_id or p.person
                order = rank_rows(emb.vector(p.description), ranked, vecs)
                rank = next((k for k, (i, _s) in enumerate(order) if self.rows[i]["category_code"] == p.label
                             and (self.rows[i]["merchant_id"] == mid or self.rows[i]["rule_id"] == p.rule_id)), None)
                if rank is not None and rank < TOP_K:
                    continue
                victim = next((self.rows[i] for i, _s in order[:TOP_K] if self.rows[i]["source"] != "precedent"
                               and self.rows[i]["category_code"] != p.label), None)
                if victim is not None:
                    break
            if victim is None:
                return
            self.rows.remove(victim)
            self.row_fmt.pop(id(victim), None)
            self.dropped += 1

    def rule_label(self, m, u, facts=None, amount=None) -> tuple[str, str] | None:
        f = dict(u["facts"])
        f.update(facts or {})
        sign = -1 if u["direction"] == "spend" else 1
        ctx = Ctx(firm=self.firm, facts=f, merchant=m, use=u, amount=(amount or Decimal("10.00")) * sign)
        try:
            g = self.env.rule(u["rule_ids"][0], ctx)
        except Exception:  # noqa: BLE001 - Skip or RuleNotApplicable: the use does not apply to this firm
            return None
        if g.label == "NEEDS_REVIEW":
            return None
        return g.label, g.rule_id

    def uses(self, pred):
        st = self.env.state[self.firm["firm_id"]]
        return [(m, u) for m, u in self.env.uses(self.firm, pred) if m["merchant_id"] not in st.forbidden]

    def _stream_choice(self, cands: list[tuple[dict, dict]], label: str | None = None) -> tuple[dict, dict] | None:
        """One payee for a recurring stream: a merchant scored items already use for the same use comes first (so
        the firm has one landlord, one phone provider), then one no item relies on."""
        if not cands:
            return None
        req = self.required
        same = [(m, u) for m, u in cands if (m["merchant_id"], u["use"]) in req
                and (label is None or req[(m["merchant_id"], u["use"])] == label)]
        if same:
            return same[0]
        used = {k[0] for k in req}
        free = [(m, u) for m, u in cands if m["merchant_id"] not in used]
        pool = free or cands
        return pool[self.rng.randrange(len(pool))]

    def salary_line(self, director: bool) -> str:
        """The firm's one memo for monthly pay (R9): staff and directors differ, so one memo keeps one account."""
        r = random.Random(f"{self.firm['firm_id']}:salary-line:{director}")
        if director:
            return r.choice(["Director salary {MMM}", "Directors salary {MMM}", "Director net pay {MMM}"])
        return r.choice(["Salary {MMM}", "Wages {MMM}", "Net pay {MMM}", "Staff wages {MMM}"])

    # ------------------------------------------------------------------ sections
    def entity_rows(self) -> None:
        f, ppl, uk = self.firm, self.firm["people"], self.jur == "UK"
        ent = f["entity_type"]
        cis = (f["tax"].get("cis") or {}) if uk else {}
        for t in ppl["owners"]:
            if uk and ent in ("sole_trader", "partnership"):
                for _ in range(2):
                    self.person_row(t, "980", self.rng.choice(["TFR", "DRAWINGS", "TRANSFER"]), "entity", sign=-1,
                                    lo="200.00", hi="2500.00", rule_id="UK-R002")
                self.person_row(t, "970", "TFR", "entity", sign=1, lo="300.00", hi="4000.00", rule_id="UK-R004")
            elif uk:
                # Directors draw one fixed net salary a month (R9, R18); the loan account shows separately.
                self.person_stream(t, "478", "SALARY", "entity", sign=-1, lo="700.00", hi="1100.00", use="salary",
                                   rule_id="UK-R006", line=self.salary_line(director=True), role="director")
                self.person_row(t, "835", "TFR", "entity", sign=-1, lo="200.00", hi="3000.00", rule_id="UK-R003")
            elif ent == "s_corp":
                for _ in range(2):
                    self.person_row(t, "3010", "TRANSFER", "entity", sign=-1, lo="1000.00", hi="6000.00",
                                    rule_id="US-R076")
            else:
                for _ in range(2):
                    self.person_row(t, "3010", "TRANSFER", "entity", sign=-1, lo="300.00", hi="4000.00",
                                    rule_id="US-R070")
                self.person_row(t, "3000", "TRANSFER", "entity", sign=1, lo="300.00", hi="5000.00",
                                rule_id="US-R071")
        if uk:
            for t in ppl["employees"]:
                self.person_stream(t, "477", "SALARY {MMM}", "entity", sign=-1, lo="600.00", hi="2600.00",
                                   use="salary", rule_id="UK-R006", line=self.salary_line(director=False),
                                   role="employee")
            if not cis.get("contractor"):
                # A CIS contractor's subcontractor payments are the CIS rows in cis_rows.
                for t in ppl["subcontractors"]:
                    self.person_row(t, "321", "INV {N3}", "entity", sign=-1, lo="300.00", hi="2200.00",
                                    rule_id="UK-R048")
            if ppl["landlord"]:
                # The firm's one landlord (R5): same pseudo-use key as the person scenarios ("rent", 450 to 1600).
                self.person_stream(ppl["landlord"], "469", "RENT {MMM}", "entity", sign=-1, lo="450.00",
                                   hi="1600.00", use="rent", rule_id="UK-R048", role="landlord")
            if ent == "limited_company":
                m = self.env.by_id["uk-g-hmrc-cumbernauld"]
                u = next(x for x in m["uses"] if x["use"] == "corporation_tax")
                self.merchant_row(m, u, "830", "entity", rule_id="UK-R010")
        else:
            for t in ppl["subcontractors"]:
                self.person_row(t, "615", "{A8}", "entity", sign=-1, lo="200.00", hi="2400.00", rule_id="US-R141")

    def _rows_for(self, pred, n, source, label=None, facts=None, amount_fn=None):
        cands = self.uses(pred)
        if not cands:
            return
        for _ in range(n):
            m, u = cands[self.rng.randrange(len(cands))]
            amount = amount_fn() if amount_fn else None
            lab, rid = label, None
            if lab is None:
                got = self.rule_label(m, u, facts, amount)
                if got is None:
                    continue
                lab, rid = got
            self.merchant_row(m, u, lab, source, amount=amount, rule_id=rid)

    def _stream_for(self, pred, source: str, label: str | None = None, rule_id: str | None = None) -> int:
        """A monthly stream from one payee of the uses matching `pred` (label from the use's rule when not given)."""
        cands = []
        for m, u in self.uses(pred):
            got = (label, rule_id) if label else self.rule_label(m, u)
            if got is not None:
                cands.append((m, u, got))
        pick = self._stream_choice([(m, u) for m, u, _g in cands])
        if pick is None:
            return 0
        lab, rid = next(g for m, u, g in cands if (m, u) == pick)
        return self.merchant_stream(pick[0], pick[1], lab, source, rid)

    def recurring_rows(self) -> None:
        """R9: rent to the firm's one landlord, loan instalments, the phone or broadband contract and payroll, each
        monthly across the history window."""
        f, pol, gaps = self.firm, self.firm["policies"], set(self.firm["policy_gaps"])
        uk = self.jur == "UK"
        if pol.get("premises") and "premises" not in gaps and not f["people"].get("landlord"):
            self._stream_for(lambda m, u: u["use"] == "rent", "policy")
        if "phone" not in gaps:
            if uk and f["entity_type"] in ("sole_trader", "partnership") and pol["phone"] in (
                    "mixed_use_claimed", "personal_not_claimed"):
                self._stream_for(lambda m, u: u["use"] == "personal_contract", "policy")
            elif uk:
                self._stream_for(lambda m, u: u["use"] == "business_contract", "policy")
            else:
                self._stream_for(lambda m, u: u["use"] == "business_line", "policy")
        if uk:
            if pol.get("lender"):
                m, u = self.env.use_named(pol["lender"], "loan_instalment")
                self.merchant_stream(m, u, "900", "policy", "UK-R016")
            if f["people"]["employees"]:
                m, u = self.env.use_named("uk-g-hmrc-cumbernauld", "paye")
                self.merchant_stream(m, u, "825", "policy", "UK-R009", amount=self._payroll_share(("477", "478"), 25, 40))
        else:
            if pol["payroll"] != "none" and "payroll" not in gaps:
                prov = pol["payroll"].replace("us-", "us-b-")
                if f["entity_type"] == "s_corp" and not f["people"]["employees"]:
                    labs = ["696"]
                elif f["entity_type"] == "s_corp":
                    labs = ["695", "696"]
                else:
                    labs = ["695"]
                m, u = self.env.use_named(prov, "net_pay")
                for lab in labs:
                    # Officers and staff booked apart each carry their own pay, not the whole run (re-audit R4).
                    part = None
                    if len(labs) > 1:
                        who = "officer" if lab == "696" else "staff"
                        part = spec_us.payroll_amount(self.env, self.firm, m, "net", self.env.hist_window[0], who)
                    self.merchant_stream(m, u, lab, "policy", "US-R075" if lab == "696" else "US-R084", amount=part)
                m, u = self.env.use_named(prov, "payroll_tax")
                tax = None if self._payroll_kind(m, u) else self._payroll_share(("695", "696"), 30, 45)
                self.merchant_stream(m, u, "2200", "policy", "US-R083", amount=tax)
            if pol.get("business_property_mortgage"):
                m, u = self.env.use_named("us-i-cedar-valley-savings", "mortgage_interest")
                self.merchant_stream(m, u, "630", "policy", "US-R102")

    def _payroll_share(self, codes: tuple[str, ...], lo: int, hi: int) -> Decimal | None:
        """Monthly PAYE or payroll tax sized to the monthly net pay already in the ledger (R9, R18): lo to hi percent
        of it, one amount per firm."""
        net = sum((-Decimal(r["amount"]) for r in self.rows if r["category_code"] in codes), Decimal(0))
        months = len(self._months())
        if net <= 0 or not months:
            return None
        r = random.Random(f"{self.env.seed}:{self.firm['firm_id']}:payroll-share")
        return (net / months * Decimal(r.randint(lo, hi)) / 100).quantize(Decimal("0.01"))

    def cis_rows(self) -> None:
        """UK CIS (B16): a contractor's earlier payments to its subcontractors and its HMRC payment. A
        subcontractor's CIS receipts are part of the sales stream."""
        cis = self.firm["tax"].get("cis") or {}
        if "cis" in self.firm["policy_gaps"]:
            return
        if cis.get("contractor"):
            subs = self.firm["people"]["subcontractors"]
            for k in range(2 if subs else 0):
                self.cis_payment_row(subs[k % len(subs)], "policy")
            self.cis_hmrc_row()

    def policy_rows(self) -> None:
        f, pol, gaps = self.firm, self.firm["policies"], set(self.firm["policy_gaps"])
        uk = self.jur == "UK"
        if pol.get("vehicle_method", "none") != "none" and "vehicle_method" not in gaps:
            self._rows_for(lambda m, u: u["use"] == "fuel", 2, "policy")
        if pol.get("savings_account"):
            self.own_row("091" if uk else "1010", "policy", -1)
        if pol.get("premises") and "premises" not in gaps:
            self._rows_for(lambda m, u: u["use"] in ("premises_energy", "premises_utility"), 1, "policy")
        self.recurring_rows()
        if uk:
            self.cis_rows()
            card = pol.get("card_account")
            if card in ("092", "811") and "card_account" not in gaps:
                m, u = self.env.use_named(f["bank_brand"], "card_repayment")
                for _ in range(2):
                    self.merchant_row(m, u, card, "policy", rule_id="UK-R046")
            if pol.get("threshold_in_history") and "capitalisation_threshold" not in gaps:
                t = Decimal(pol["capitalisation_threshold"])
                pred = lambda m, u: u["use"] in ("computer", "furniture", "tools")  # noqa: E731
                self._rows_for(pred, 1, "policy", amount_fn=lambda: draw_amount(self.rng, f"{t * Decimal('0.6'):.2f}", f"{t * Decimal('0.9'):.2f}"))
                self._rows_for(pred, 1, "policy", amount_fn=lambda: draw_amount(self.rng, f"{t * Decimal('1.1'):.2f}", f"{t * Decimal('1.6'):.2f}"))
            if f["tax"].get("vat_registered"):
                m, u = self.env.use_named("uk-g-hmrc-vat", "vat_payment")
                self.merchant_row(m, u, "820", "policy", rule_id="UK-R008")
        else:
            if "de_minimis_election" not in gaps:
                # Guide v0.2 (US-R050, D62 P2): capital items under the election go to 720 (Part V), not 670.
                lab = "720" if pol["de_minimis_election"] else "1500"
                self._rows_for(lambda m, u: u["use"] == "equipment", 1, "policy", label=lab,
                               amount_fn=lambda: draw_amount(self.rng, "400.00", "2300.00"))
            if "inventory" not in gaps:
                self._rows_for(lambda m, u: u["use"] == "job_materials", 2, "policy")
            if pol.get("card_account") == "2000" and "card_account" not in gaps:
                m, u = self.env.use_named(f["bank_brand"], "card_payment")
                for _ in range(2):
                    self.merchant_row(m, u, "2000", "policy", rule_id="US-R110")
            if pol.get("sales_tax") == "collects_buyer_imposed":
                m, u = self.env.use_named("us-g-state-revenue", "sales_tax")
                self.merchant_row(m, u, "2100", "policy", rule_id="US-R091")

    def _trade_ok(self, m: dict) -> bool:
        tag = self.firm["trade"]["tag"]
        trades = m.get("trades")
        if trades is None:
            trades = BACKGROUND_TRADES.get(m["merchant_id"].split("-", 2)[-1])
        if trades is None:
            trades = BACKGROUND_CATEGORY_TRADES.get(m["category"])
        if trades is not None and tag not in trades:
            return False
        if self.jur == "UK" and m["category"] == "accounting_payroll" and m["merchant_id"] not in UK_ACCOUNTING_OK:
            return False
        # Bank charges and interest come from the firm's own bank only.
        return m["category"] != "bank" or m["merchant_id"] == self.firm["bank_brand"]

    def background_rows(self, n: int | None = None) -> None:
        gaps = set(self.firm["policy_gaps"])
        excluded = set().union(*[GAP_EXCLUDES.get(g, set()) for g in gaps]) if gaps else set()
        excluded.add("telecom")  # the firm's one phone or broadband contract is a monthly stream (R9)
        st = self.env.state[self.firm["firm_id"]]
        required_m = {k[0] for k in st.required}
        cands = [(m, u) for m, u in self.uses(lambda m, u: u["routine"] and u["direction"] == "spend")
                 if m["category"] not in excluded and m["merchant_id"] not in required_m
                 and u["use"] not in RENT_USES and self._trade_ok(m)]
        if not cands:
            return
        for _ in range(BACKGROUND_PER_FIRM if n is None else n):
            m, u = cands[self.rng.randrange(len(cands))]
            got = self.rule_label(m, u)
            if got is None:
                continue
            self.merchant_row(m, u, got[0], "background", rule_id=got[1])

    def _costs(self) -> Decimal:
        return sum((-Decimal(r["amount"]) for r in self.rows
                    if Decimal(r["amount"]) < 0 and r["category_code"] not in NOT_COSTS), Decimal(0))

    def sales_rows(self) -> None:
        """R9: income across the window. Processor payouts (split or single from the use, R17), CIS receipts at the
        firm's rate and receipts from a few regular customers: at least one a month, then more until income covers
        the ledger's costs, at most MAX_SALES rows. The first two rows of each processor and of CIS evidence the
        policy (`policy`); customer receipts are `background`."""
        f, pol, gaps = self.firm, self.firm["policies"], set(self.firm["policy_gaps"])
        uk = self.jur == "UK"
        sources: list[tuple[int, object]] = []
        evidence: list[object] = []
        if "sales_recording" not in gaps:
            for proc in pol.get("processors", []):
                m = self.env.by_id[proc.replace(f"{self.jur.lower()}-", f"{self.jur.lower()}-b-", 1)]
                u = next(x for x in m["uses"] if x["use"] == "payout")
                fn = (lambda m, u: lambda src, w: self.processor_row(m, u, src, window=w))(m, u)
                evidence += [fn, fn]
                sources.append((4, fn))
        cis = (f["tax"].get("cis") or {}) if uk else {}
        if cis.get("subcontractor") and "cis" not in gaps:
            fn = lambda src, w: self.cis_receipt_row(cis["deduction_rate"], src, window=w)  # noqa: E731
            evidence += [fn, fn]
            sources.append((4, fn))
        customers = [(m, u) for m, u in self.uses(lambda m, u: u["use"] == "customer_receipt")
                     if (m["merchant_id"], u["use"]) not in self.required or self.required[(m["merchant_id"], u["use"])] in ("200", "400")]
        if customers:
            used = {k[0] for k in self.required}
            customers.sort(key=lambda mu: (mu[0]["merchant_id"] not in used, mu[0]["merchant_id"]))
            k = min(len(customers), self.rng.randint(2, 3))
            regular = customers[:1] + self.rng.sample(customers[1:], k - 1) if k > 1 else customers[:1]
            for m, u in regular:
                got = self.rule_label(m, u)
                if got is not None:
                    fn = (lambda m, u, g: lambda src, w: self.merchant_row(m, u, g[0], src, rule_id=g[1], window=w,
                                                                          amount=self._customer_amount(u)))(m, u, got)
                    sources.append((2 if evidence else 4, fn))
        if not sources:
            return
        months = self._months()
        income, n, i = Decimal(0), 0, 0
        target = self._costs() * Decimal(self.rng.randint(105, 140)) / 100
        self._sales_behind = True
        for fn in evidence:
            row = fn("policy", months[i % len(months)])
            i += 1
            if row is not None:
                income += Decimal(row["amount"])
                n += 1
        total = sum(w for w, _ in sources)
        for _attempt in range(3 * MAX_SALES):
            if n >= MAX_SALES or (i >= len(months) and income >= target):
                break
            x = self.rng.random() * total
            fn = sources[-1][1]
            for w, cand in sources:
                x -= w
                if x <= 0:
                    fn = cand
                    break
            src = "background" if all(fn is not e for e in evidence) else "policy"
            self._sales_behind = income < target / 2
            row = fn(src, months[i % len(months)])
            i += 1
            if row is not None:
                income += Decimal(row["amount"])
                n += 1
        self.sales_rows_written = n

    def _customer_amount(self, u: dict) -> Decimal | None:
        """A customer receipt from the upper half of the use's range while income is far behind costs."""
        if not getattr(self, "_sales_behind", False):
            return None
        lo, hi = (Decimal(x) for x in u["amount_range"])
        return draw_amount(self.rng, f"{(lo + hi) / 2:.2f}", f"{hi:.2f}")

    def _split_precedent(self, p: Prec, m: dict | None, u: dict | None) -> bool:
        """Earlier rows for a split scored item show the same split (UK-R019, UK-R067, UK-R069)."""
        cis = self.firm["tax"].get("cis") or {}
        if p.split_kind == "processor_payout" and m and u:
            return self.payout_row(m, u, "precedent") is not None
        if p.split_kind == "cis_receipt" and cis.get("deduction_rate"):
            return self.cis_receipt_row(cis["deduction_rate"], "precedent", (m, u) if m and u else None) is not None
        if p.split_kind == "cis_payment" and (p.person or p.merchant_id or "").startswith("person:"):
            return self.cis_payment_row((p.person or p.merchant_id).split(":", 2)[2], "precedent") is not None
        return False

    def precedent_rows(self, precs: list[Prec]) -> None:
        for p in precs:
            if p.description:
                self.identical_row(p)
                continue
            if (p.person or p.merchant_id or "", p.label) in self.streams:
                continue  # the payee's monthly rows already show it at this account; no extra bill (re-audit R4)
            for _ in range(p.count):
                m, u = self._catalogue_use(p)
                if p.split_kind and self._split_precedent(p, m, u):
                    continue
                if p.person:
                    name = p.person.split(":", 2)[2]
                    self.person_row(name, p.label, "{A6}", "precedent", sign=p.sign, lo="150.00", hi="1800.00",
                                    merchant_id=p.person)
                elif p.merchant_id == "own:savings":
                    self.own_row(p.label, "precedent", p.sign)
                else:
                    m = self.env.by_id[p.merchant_id]
                    u = next(x for x in m["uses"] if x["use"] == p.use)
                    self.merchant_row(m, u, p.label, "precedent", sign=p.sign)

    def plan_forms(self, precs: list[Prec]) -> None:
        """Planned form of each deciding precedent. A requested varied form whose scored description does not name
        the payee (F3, F6) falls back to exact; to keep the firm's varied share, the same number of exact requests
        that can vary (named payee, a usable candidate, a description no other item places exact) are promoted."""
        deciding = [p for p in precs if p.description]
        exact_desc = Counter(norm(p.description) for p in deciding)
        exact_req = {norm(p.description) for p in deciding if p.form != "varied"}
        start = self.env.hist_window[0]
        deficit = 0
        for p in deciding:
            reason = None
            if p.form == "varied":
                if not self.can_vary(p):
                    reason = "split" if p.lines else "payee_not_named"
                elif norm(p.description) in exact_req:
                    reason = "shared_exact"  # another item places the same description exact
                elif not self.varied_candidates(p, start):
                    reason = "no_candidate"
            if reason:
                self.plan[id(p)] = "exact"
                self.varied_fallbacks += 1
                self.fallback_reasons[reason] += 1
                deficit += 1
            else:
                self.plan[id(p)] = p.form
        for p in deciding:
            if deficit <= 0:
                break
            if (p.form == "exact" and self.can_vary(p) and exact_desc[norm(p.description)] == 1
                    and self.required_desc.get(norm(p.description)) == p.label
                    and self.varied_candidates(p, start)):
                self.plan[id(p)] = "varied"
                self.varied_promoted += 1
                deficit -= 1

    def build(self, precs: list[Prec]) -> list[dict]:
        self.plan_forms(precs)
        exact = {norm(p.description) for p in precs if p.description and self.plan[id(p)] != "varied"}
        self.blocked = {norm(p.description) for p in precs
                        if p.description and self.plan[id(p)] == "varied" and not p.lines} - exact
        self.entity_rows()
        self.policy_rows()
        n_prec = sum(p.count if not p.description else 1 for p in precs)
        self.background_rows(max(MIN_BACKGROUND, min(BACKGROUND_PER_FIRM,
                                                     TARGET_ROWS - len(self.rows) - n_prec - MAX_SALES // 2)))
        self.sales_rows()
        self.precedent_rows(precs)
        self.check_varied()
        self.protect_deciding()
        for r in self.rows:
            if r["source"] == "precedent" and r["precedent_form"] is None:
                r["precedent_form"] = "exact" if norm(r["description"]) in self.scored_desc else "varied"
        self.deciding_forms = Counter(r["precedent_form"] for r in self.deciding)
        return self.rows


__all__ = ["HistoryBuilder", "norm", "form_key", "role_ok", "names_payee", "RuleNotApplicable"]
