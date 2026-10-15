"""Gold answer record and the context a rule function reads."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal

from .charts import is_gold_eligible
from .constants import NEEDS_REVIEW, SPLIT_KINDS, SPLIT_ROLES
from .guides import load_rules


@dataclass
class Ctx:
    """What a rule function may read: the firm (its true policies), the merchant use and item facts."""

    firm: dict
    facts: dict = field(default_factory=dict)
    merchant: dict | None = None
    use: dict | None = None
    amount: Decimal = Decimal("0.00")

    def f(self, key, default=None):
        return self.facts.get(key, default)


@dataclass(frozen=True)
class Gold:
    label: str
    acceptable_labels: tuple[str, ...]
    gold_action: str
    solvable_with: str
    rule_id: str
    rule_basis: str
    rule_source: str
    review_reason: str | None = None
    policy_keys: tuple[str, ...] = ()
    # Split gold (SCHEMA_v0.2 sections 3 and 7): ((code, signed amount "0.00", role), ...); None for one-line items.
    lines: tuple[tuple[str, str, str], ...] | None = None
    split_kind: str | None = None

    def as_tuple(self):
        return (
            self.label,
            list(self.acceptable_labels),
            self.gold_action,
            self.solvable_with,
            self.rule_id,
            self.rule_basis,
            self.rule_source,
        )


class RuleNotApplicable(ValueError):
    """Raised when a rule is asked about a firm or fact pattern it does not cover."""


def make(
    ctx: Ctx,
    rule_id: str,
    label: str,
    solvable: str,
    *,
    also: str | None = None,
    reason: str | None = None,
    policy: tuple[str, ...] | str = (),
) -> Gold:
    meta = load_rules()[rule_id]
    if isinstance(policy, str):
        policy = (policy,)
    # A fact the record states outright makes the item line-solvable.
    if solvable == "line+history" and ctx.f("stated"):
        solvable = "line"
    # A policy the firm's history never shows can only be learnt from the profile.
    if solvable == "line+history" and any(p in ctx.firm.get("policy_gaps", ()) for p in policy):
        solvable = "line+profile"
    if label == NEEDS_REVIEW:
        solvable = "none"
        acceptable: tuple[str, ...] = ()
        action = "review"
        if reason is None:
            raise ValueError(f"{rule_id}: NEEDS_REVIEW needs a review reason")
    else:
        acceptable = (label,) if also is None else (label, also)
        action = "post"
    for code in (label,) + acceptable:
        if not is_gold_eligible(ctx.firm, code):
            raise RuleNotApplicable(f"{rule_id}: {code} is not a gold-eligible account for {ctx.firm['firm_id']}")
    return Gold(
        label=label,
        acceptable_labels=acceptable,
        gold_action=action,
        solvable_with=solvable,
        rule_id=rule_id,
        rule_basis=meta.rule_basis,
        rule_source=meta.rule_source,
        review_reason=reason,
        policy_keys=tuple(policy),
    )


def make_split(
    ctx: Ctx,
    rule_id: str,
    lines: list[tuple[str, Decimal, str]],
    split_kind: str,
    solvable: str = "line",
    *,
    policy: tuple[str, ...] | str = (),
) -> Gold:
    """Split gold: several (code, signed amount, role) lines that sum exactly to the record amount (`ctx.amount`).

    Amounts carry the record's sign convention (receive positive, spend negative); a fee or deduction line has the
    opposite sign. `label` is the line with the largest absolute amount, ties broken by the lower code. A bad split
    is a generator bug, so it raises ValueError rather than RuleNotApplicable.
    """
    if split_kind not in SPLIT_KINDS:
        raise ValueError(f"{rule_id}: unknown split kind {split_kind}")
    if len(lines) < 2:
        raise ValueError(f"{rule_id}: a split needs at least two lines")
    codes = [c for c, _, _ in lines]
    if len(set(codes)) != len(codes):
        raise ValueError(f"{rule_id}: split codes must be distinct")
    q = Decimal("0.01")
    norm_lines = []
    for code, amount, role in lines:
        if role not in SPLIT_ROLES:
            raise ValueError(f"{rule_id}: unknown split role {role}")
        amount = Decimal(amount).quantize(q)
        if amount == 0:
            raise ValueError(f"{rule_id}: zero split line")
        norm_lines.append((code, amount, role))
    total = Decimal(ctx.amount).quantize(q)
    if sum(a for _, a, _ in norm_lines) != total:
        raise ValueError(f"{rule_id}: split lines sum to {sum(a for _, a, _ in norm_lines)}, record is {total}")
    primary = sorted(norm_lines, key=lambda x: (-abs(x[1]), x[0]))[0][0]
    for code in codes:
        if not is_gold_eligible(ctx.firm, code):
            raise RuleNotApplicable(f"{rule_id}: {code} is not a gold-eligible account for {ctx.firm['firm_id']}")
    g = make(ctx, rule_id, primary, solvable, policy=policy)
    return replace(g, lines=tuple((c, f"{a:.2f}", r) for c, a, r in norm_lines), split_kind=split_kind)


def is_st(firm: dict) -> bool:
    return firm["entity_type"] in ("sole_trader", "partnership")


def is_co(firm: dict) -> bool:
    return firm["entity_type"] == "limited_company"


def is_scorp(firm: dict) -> bool:
    return firm["entity_type"] == "s_corp"


def owner_account_uk(firm: dict) -> str:
    """Owner withdrawals: drawings for a sole trader or partnership, director's loan account for a company."""
    return "980" if is_st(firm) else "835"
