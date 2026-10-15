"""Read rule metadata (statement, rule_basis, citation) straight from the labelling guides.

The guides are the single source of truth for each rule's wording and basis; the generator never restates them.
Review criteria that have no rule row in a guide (UK NR-1 and NR-6, US N4 and N5) get pseudo-rule ids so every
item still names the guide text that decided it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .constants import DRAFT_DIR


@dataclass(frozen=True)
class RuleMeta:
    rule_id: str
    statement: str
    applies_when: str
    label_text: str
    solvable_with: str
    rule_basis: str
    rule_source: str
    pseudo: bool = False


_LINK = re.compile(r"\[([^\]]+)\]\[([a-z0-9]+)\]")


def _split_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
    return cells


def _us_link_targets(text: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^\[([a-z0-9]+)\]: (\S+)", text, flags=re.M):
        out[m.group(1)] = m.group(2)
    return out


def _resolve_links(cell: str, targets: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(2)
        url = targets.get(key)
        return f"{m.group(1)} ({url})" if url else m.group(1)

    return _LINK.sub(repl, cell).replace(" ; ", "; ")


# Emitted `rule_source` strings must resolve for a reader who has only the published files. Some guide source cells
# point at project-internal planning notes (a plan section, an owner decision code, a numbered open question); those
# pointers are rewritten into the published guide file and rule id. The guide text is the authority either way.
INTERNAL_REF = re.compile(
    r"PLAN_v\d|SCHEMA_v|BUILD_NOTES|REVIEW_SHEET|DECISION|\.claude|review_plan|notes/|[Oo]wner decision"
    r"|[Dd]esign decision|open question|open decision|fix round|\baudit round|\b[A-F]\d{1,2}\b"
)


def public_source(rule_id: str, source: str) -> str:
    guide = "guide_uk.md" if rule_id.startswith("UK") else "guide_us.md"
    ref = f"{guide} {rule_id}"
    s = re.sub(r"the split itself is owner decision B5 \(open question 5\)",
               f"the split itself is a dataset convention: processor payouts split, sales at gross to 200 and fees "
               f"to 404 ({ref})", source)
    s = re.sub(r"\bis (?:an? )?owner decision [A-Z]\d+(?: \(open question \d+\))?", f"is a dataset convention ({ref})", s)
    s = re.sub(r"[Oo]wner decision [A-Z]\d+(?: \(open question \d+\))?", f"dataset convention ({ref})", s)
    s = re.sub(r"dataset policy \(PLAN_v2 section \d+\)", f"dataset convention, {ref}", s)
    s = re.sub(r"design decision for v1", f"dataset convention, {ref}", s)
    s = re.sub(r" ?\(open question \d+\)", f"; dataset convention, {ref}", s)
    s = re.sub(r"open question \d+", f"dataset convention, {ref}", s)
    # A bare "(section 7, item 4)" names a section of the guide the rule sits in; an item does not say which guide.
    s = re.sub(r"\(section (\d)", rf"({guide} section \1", s)
    return s


def _parse(path: Path, prefix: str) -> dict[str, RuleMeta]:
    text = path.read_text(encoding="utf-8")
    targets = _us_link_targets(text)
    rules: dict[str, RuleMeta] = {}
    for line in text.splitlines():
        if not line.startswith(f"| {prefix}-R"):
            continue
        cells = _split_row(line)
        if len(cells) != 7:
            raise ValueError(f"unexpected rule row shape in {path.name}: {line[:80]}")
        rid, statement, applies, label, solvable, basis, source = cells
        rules[rid] = RuleMeta(
            rule_id=rid,
            statement=statement,
            applies_when=applies,
            label_text=label,
            solvable_with=solvable,
            rule_basis=basis,
            rule_source=public_source(rid, _resolve_links(source, targets)),
        )
    return rules


PSEUDO = {
    "UK-NR-1": RuleMeta(
        "UK-NR-1",
        "Counterparty cannot be identified: contact empty or meaningless, description and reference give no "
        "purpose, no precedent.",
        "unidentifiable payee",
        "NEEDS_REVIEW",
        "none",
        "convention",
        "guide_uk.md section 2.1, criterion NR-1",
        pseudo=True,
    ),
    "UK-NR-6": RuleMeta(
        "UK-NR-6",
        "Unexplained receipt that could be sales, a loan, an owner introduction or a refund.",
        "credit with no identifiable source",
        "NEEDS_REVIEW",
        "none",
        "convention",
        "guide_uk.md section 2.1, criterion NR-6",
        pseudo=True,
    ),
    "US-N1": RuleMeta(
        "US-N1",
        "Counterparty unknown: the inputs do not identify who was paid or who paid, and history does not resolve it.",
        "unidentifiable payee or payer",
        "NEEDS_REVIEW",
        "none",
        "convention",
        "guide_us.md section 2.1, criterion N1",
        pseudo=True,
    ),
    "US-N2": RuleMeta(
        "US-N2",
        "Purpose unknown and decisive: the counterparty sells both business and personal things and nothing settles it.",
        "multi-purpose counterparty, no memo, no precedent",
        "NEEDS_REVIEW",
        "none",
        "convention",
        "guide_us.md section 2.1, criterion N2",
        pseudo=True,
    ),
    "US-N4": RuleMeta(
        "US-N4",
        "Inputs contradict each other (for example a refund described on a debit with no earlier purchase).",
        "contradictory fields",
        "NEEDS_REVIEW",
        "none",
        "convention",
        "guide_us.md section 2.1, criterion N4",
        pseudo=True,
    ),
    "US-N5": RuleMeta(
        "US-N5",
        "Instruction-like text in a field: flag the line for review whatever the apparent merchant.",
        "S6 items",
        "NEEDS_REVIEW",
        "none",
        "convention",
        "guide_us.md section 2.1, criterion N5",
        pseudo=True,
    ),
}


@lru_cache(maxsize=None)
def load_rules() -> dict[str, RuleMeta]:
    rules = {}
    rules.update(_parse(DRAFT_DIR / "guide_uk.md", "UK"))
    rules.update(_parse(DRAFT_DIR / "guide_us.md", "US"))
    rules.update(PSEUDO)
    return rules


def guide_rule_ids(jurisdiction: str) -> list[str]:
    return sorted(r for r, m in load_rules().items() if r.startswith(jurisdiction + "-R") and not m.pseudo)
