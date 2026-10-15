# The UK check-digit routines below are a Python port of HMRC's reference-checker
# (https://github.com/hmrc/reference-checker), Copyright 2023 HM Revenue & Customs, licensed under the
# Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0). Changes: ported from Scala to Python and
# used only to make sure synthetic references fail the checks. Distributed on an "AS IS" basis, without warranties
# or conditions of any kind.
"""Synthetic tax references that look real but FAIL the official check rules.

UK check rules are ported from HMRC's own reference checker (https://github.com/hmrc/reference-checker,
`src/main/scala/uk/gov/hmrc/referencechecker/ReferenceChecker.scala`, Apache License 2.0, read 2026-10-13):
- VAT registration number: 9 digits; weights 8,7,6,5,4,3,2 on the first seven; the last two digits must equal
  97 minus the weighted sum reduced by 97 (the "mod 97" scheme) or the same with 55 added first ("mod 9755").
- UTR (self assessment and corporation tax): 10 digits; the first digit is a check digit; weights 6,7,8,9,10,5,4,3,2
  on digits 2 to 10; remainder mod 11 indexes the table "21987654321".
- PAYE Accounts Office reference: 13 characters `ddd P L dddddd cc`; the 5th character is a check letter; weights
  9,10,11,12,0,8,7,6,5,4,3,2,1 with letters mapped to numbers; remainder mod 23 indexes the table
  "ABCDEFGHXJKLMNYPQRSTZVW".
US: EIN prefixes the IRS lists as valid on "How EINs are assigned and valid EIN prefixes" (irs.gov, page last
reviewed 2026-04-09, read 2026-10-13); every synthetic EIN uses a prefix outside that list.

Every generator here loops until the candidate fails the check, so no synthetic reference can be a valid one.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- UK checks (port of HMRC reference-checker)

_EPAYE_LETTERS = {
    "A": 33, "B": 34, "C": 35, "D": 36, "E": 37, "F": 38, "G": 39, "H": 40, "J": 42, "K": 43, "L": 44, "M": 45,
    "N": 46, "P": 48, "Q": 49, "R": 50, "S": 51, "T": 52, "U": 56, "V": 54, "W": 55, "X": 41, "Y": 47, "Z": 53,
}
_LETTER_TABLE = "ABCDEFGHXJKLMNYPQRSTZVW"


def vat_is_valid(vrn: str) -> bool:
    """True when a 9-digit UK VAT registration number passes the mod 97 or mod 9755 check."""
    if len(vrn) != 9 or not vrn.isdigit():
        return False
    weighted = sum(w * int(c) for w, c in zip((8, 7, 6, 5, 4, 3, 2), vrn[:7]))
    expected = int(vrn[7:])

    def check(total: int) -> bool:
        while total > 97:
            total -= 97
        return 97 - total == expected

    return check(weighted) or check(weighted + 55)


def utr_is_valid(utr: str) -> bool:
    """True when a 10-digit UTR passes HMRC's check digit (SA and CT use the same rule)."""
    if utr.endswith("K") or utr.startswith("K"):
        utr = utr.strip("K")
    if len(utr) != 10 or not utr.isdigit():
        return False
    weighted = sum(w * int(c) for w, c in zip((6, 7, 8, 9, 10, 5, 4, 3, 2), utr[1:]))
    return "21987654321"[weighted % 11] == utr[0]


def paye_aoref_is_valid(ref: str) -> bool:
    """True when a 13-character PAYE Accounts Office reference passes the check letter rule."""
    import re

    ref = ref.upper()
    if not re.fullmatch(r"\d{3}P[A-Z]\d{6}[A-Z_0-9]{2}", ref):
        return False
    weights = (9, 10, 11, 12, 0, 8, 7, 6, 5, 4, 3, 2, 1)
    total = 0
    for w, ch in zip(weights, ref):
        # Scala's Char.asDigit (radix 36) is the fallback for letters missing from the map (I, O) and for '_'.
        total += w * _EPAYE_LETTERS.get(ch, int(ch, 36) if ch.isalnum() else -1)
    if _LETTER_TABLE[total % 23] != ref[4]:
        return False
    if ref.startswith("961") and ref[12] == "X" and ref[5] != "0":
        return False
    if ref.startswith("961") and ref[12] != "X" and not re.fullmatch(r"961P[A-Z]\d{8}", ref):
        return False
    return True


# ---------------------------------------------------------------- US EIN prefixes

VALID_EIN_PREFIXES = frozenset(
    "01 02 03 04 05 06 10 11 12 13 14 15 16 20 21 22 23 24 25 26 27 30 31 32 33 34 35 36 37 38 39 40 41 42 43 "
    "44 45 46 47 48 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 71 72 73 74 75 76 77 80 81 82 83 "
    "84 85 86 87 88 90 91 92 93 94 95 98 99".split()
)
NEVER_ASSIGNED_EIN_PREFIXES = tuple(f"{i:02d}" for i in range(100) if f"{i:02d}" not in VALID_EIN_PREFIXES)


def ein_is_assignable(ein: str) -> bool:
    """True when the EIN uses a prefix the IRS lists as valid."""
    digits = ein.replace("-", "")
    return len(digits) == 9 and digits.isdigit() and digits[:2] in VALID_EIN_PREFIXES


# ---------------------------------------------------------------- generators of failing references


def _digits(rng: random.Random, n: int) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


def fake_vrn(rng: random.Random) -> str:
    while True:
        cand = str(rng.randint(1, 9)) + _digits(rng, 8)
        if not vat_is_valid(cand):
            return cand


def fake_utr(rng: random.Random) -> str:
    while True:
        cand = str(rng.randint(1, 9)) + _digits(rng, 9)
        if not utr_is_valid(cand):
            return cand


def fake_paye_aoref(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTVWXYZ"
    while True:
        cand = f"{rng.randint(100, 999)}P{rng.choice(letters)}{_digits(rng, 8)}"
        if not paye_aoref_is_valid(cand):
            return cand


def fake_ct_reference(utr: str, rng: random.Random) -> str:
    """17 characters: failing UTR + 'A001' + 2-digit accounting period + 'A' (gov.uk/pay-corporation-tax)."""
    assert not utr_is_valid(utr)
    return f"{utr}A001{rng.randint(1, 12):02d}A"


def fake_ein(rng: random.Random) -> str:
    prefix = rng.choice(NEVER_ASSIGNED_EIN_PREFIXES)
    return f"{prefix}-{_digits(rng, 7)}"


def paye_payment_reference(aoref: str, yymm: str | None) -> str:
    """Accounts Office reference, optionally with the 4-digit YYMM suffix used for early or late payments."""
    return aoref + (yymm or "")
