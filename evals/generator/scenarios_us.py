"""US scenarios by stratum. Each returns a Draft for one firm or raises Skip."""

from __future__ import annotations

import random
from decimal import Decimal

from .attacks import adversarial
from .engine import Env, Prec, Skip, _payee_only_ok, family_plain, family_s0, family_s1
from .gold import Ctx, is_scorp
from .spec_common import U
from .spec_us import NO_PERSONAL_INCOME_TAX, PENALTY_USES, payroll_amount, payroll_people
from .templates import draw_amount, fill

LINE = ("line",)
HIST = ("line+history", "line+profile")


def _s0_family(rng, u, m):
    """`family_s0`, but never the payee alone for a payee paid for several things (F1): a bank credit can be
    interest or a fee refund, so "PNC Bank" alone does not say which."""
    fam = family_s0(rng, u, m)
    return "contact_desc" if fam == "contact_only" and not _payee_only_ok(u, m) else fam


def _routine(env: Env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: u["routine"])
    return env.build(rng, firm, scenario="routine", stratum=stratum, merchant=m, use=u, family=_s0_family(rng, u, m),
                     expect=LINE)


def _customer_receipt(env: Env, rng, firm, stratum):
    """Shortcut S-1: ordinary customer receipts, whose references customers type in mixed case, so a lower-case
    reference on a receipt is not a mark of an attack."""
    m, u = env.pick(rng, firm, lambda m, u: m["category"] == "customer" and u["use"] == "customer_receipt")
    return env.build(rng, firm, scenario="customer_receipt", stratum=stratum, merchant=m, use=u,
                     family=rng.choice(["contact_ref", "contact_desc"]) if not u["needs_line"] else "contact_desc",
                     expect=LINE)


def _noisy(env: Env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: u["routine"] and not u["needs_line"])
    return env.build(rng, firm, scenario="noisy_descriptor", stratum=stratum, merchant=m, use=u,
                     family=family_s1(rng, u, m), expect=LINE)


def _small_seller(m, u):
    return m["category"] == "small_seller" and u["routine"] and u["direction"] == "spend"


def _small_routine(env: Env, rng, firm, stratum):
    """Shortcut S-1: ordinary card spending at a small seller billed through Square, PayPal or Toast, so a
    processor prefix on a debit is not a mark of an attack."""
    m, u = env.pick(rng, firm, _small_seller)
    return env.build(rng, firm, scenario="routine", stratum=stratum, merchant=m, use=u, family=_s0_family(rng, u, m),
                     expect=LINE)


def _small_noisy(env: Env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: _small_seller(m, u) and not u["needs_line"])
    return env.build(rng, firm, scenario="noisy_descriptor", stratum=stratum, merchant=m, use=u,
                     family=family_s1(rng, u, m), expect=LINE)


def _fam(rng, u, m, choices):
    """A family from `choices`, without the payee-only form when the payee is paid for several things (F1)."""
    fams = list(choices)
    if not _payee_only_ok(u, m):
        fams = [f for f in fams if f != "contact_only"] or (
            ["contact_desc"] if any(u["line_descriptions"]) else ["desc_narrative"])
    return rng.choice(fams)


def _use(pred, scenario, *, family=None, expect=None, rule=None, facts=None, need_free=False, forbid_self=False):
    def fn(env: Env, rng, firm, stratum):
        m, u = env.pick(rng, firm, pred, need_free=need_free)
        fam = family(rng, u) if callable(family) else (family or family_plain(rng, u, m))
        return env.build(rng, firm, scenario=scenario, stratum=stratum, merchant=m, use=u, family=fam,
                         expect=expect, rule=rule, facts=facts, forbid=[m["merchant_id"]] if forbid_self else None)

    return fn


def _named(*names):
    return lambda m, u: u["use"] in names


def _vehicle_rule(firm, default):
    method = firm["policies"]["vehicle_method"]
    if method == "standard_mileage":
        return "US-R043"
    if method == "actual":
        return default
    raise Skip("no vehicle")


def _vehicle(use_names, default_rule):
    def fn(env, rng, firm, stratum):
        rule = _vehicle_rule(firm, default_rule)
        m, u = env.pick(rng, firm, _named(*use_names))
        fam = (_fam(rng, u, m, ["contact_only", "contact_desc", "contact_ref"]) if any(u["line_descriptions"])
               else _fam(rng, u, m, ["contact_only"]))
        return env.build(rng, firm, scenario="vehicle_" + u["use"], stratum=stratum, merchant=m, use=u, rule=rule,
                         family=fam, expect=HIST)

    return fn


def _payout(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("payout"))
    rule = "US-R120" if firm["policies"]["sales_recording"] == "processor_gross" else "US-R121"
    return env.build(rng, firm, scenario="processor_payout", stratum=stratum, merchant=m, use=u, rule=rule,
                     family=rng.choice(["contact_only", "contact_ref", "ref_narrative"]), expect=HIST)


def _de_minimis(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("equipment"))
    amount = draw_amount(rng, "300.00", "2450.00")
    rule = "US-R050" if firm["policies"]["de_minimis_election"] else "US-R051"
    return env.build(rng, firm, scenario="de_minimis", stratum=stratum, merchant=m, use=u, rule=rule,
                     family="contact_desc", amount=amount, expect=HIST)


def _over_limit(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("equipment"))
    amount = draw_amount(rng, "2600.00", "4800.00")
    return env.build(rng, firm, scenario="equipment_over_limit", stratum=stratum, merchant=m, use=u, rule="US-R051",
                     family="contact_desc", amount=amount, expect=LINE)


def _materials(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("job_materials"))
    return env.build(rng, firm, scenario="materials_inventory_policy", stratum=stratum, merchant=m, use=u,
                     family=_fam(rng, u, m, ["contact_only", "contact_desc"]), expect=HIST)


def _payroll(kind):
    def fn(env, rng, firm, stratum):
        prov = firm["policies"]["payroll"]
        if prov == "none":
            raise Skip("no payroll")
        name = {"net": "net_pay", "tax": "payroll_tax"}[kind]
        m, u = env.use_named(prov.replace("us-", "us-b-"), name)
        if kind == "net":
            if is_scorp(firm):
                if firm["people"]["employees"]:
                    raise Skip("mixed S corp payroll is S5")
                rule = "US-R075"
            else:
                rule = rng.choice(["US-R084", "US-R162"])
        else:
            rule = "US-R083"
        if not payroll_people(firm):
            raise Skip("nobody on the payroll")
        # R18: sized to headcount, fixed per person. F1: a payroll provider takes net pay, tax and fees, so the
        # record says which (memo or provider narrative), never the provider name alone.
        family = rng.choice(["contact_desc", "ref_narrative"])
        amount = payroll_amount(env, firm, m, kind, _record_date(env, rng, m, u))  # the last draw before build
        return env.build(rng, firm, scenario="payroll_" + kind, stratum=stratum, merchant=m, use=u, rule=rule,
                         family=family, amount=amount, expect=HIST)

    return fn


# Owner capital injections are round sums (F8): multiples of 100, or of 500 above 5,000.
OWNER_CONTRIBUTION = U("owner_contribution", "receive", "200.00", "6000.00", "3000", "US-R071", [""],
                       amount_mode="round")


def _owner(env: Env, rng, firm, stratum, *, out: bool):
    person = rng.choice(firm["people"]["owners"])
    if out:
        rule = "US-R076" if is_scorp(firm) else "US-R070"
    else:
        rule = "US-R071"
    acct4 = rng.randint(1000, 9999)
    narr = (f"Online transfer to CHK ...{acct4}" if out else f"Online transfer from CHK ...{acct4}")
    ref = rng.choice(["", "TRANSFER", f"XFER {acct4}"])
    return env.build(rng, firm, scenario="owner_" + ("draw" if out else "contribution"), stratum=stratum,
                     merchant=None, use=None, rule=rule, family="explicit",
                     amount=(draw_amount(rng, "200.00", "6000.00") if out else
                             env.amount_for(rng, firm, None, OWNER_CONTRIBUTION, env.scored_window[0])),
                     sign=-1 if out else 1, contact=person, line="",
                     ref=ref, narrative=narr, fmt="US-XFER", person=person,
                     merchant_id=f"person:{firm['firm_id']}:{person}", expect=HIST)


def _p2p(kind, *, scenario=None, stratum_rule="US-R141"):
    def fn(env: Env, rng, firm, stratum):
        ppl = firm["people"]
        if kind == "owner":
            if is_scorp(firm):
                raise Skip("S corp owner transfers use US-R076")
            token, role = rng.choice(ppl["owners"]), "owner"
        elif kind == "contractor":
            if not ppl["subcontractors"]:
                raise Skip("no contractors")
            token, role = rng.choice(ppl["subcontractors"]), "contractor"
        else:
            token, role = rng.choice(ppl["unknown_pool"]), None
        # Zelle and Cash App lines show the payee's name; a Venmo bank line shows only a number, so no person
        # payee goes through it.
        mid = rng.choice(["us-b-zelle", "us-b-cash-app"])
        m, u = env.use_named(mid, "p2p_out")
        narr = fill(rng.choice(m["narratives"]), rng, env.fill_ctx(firm, env.scored_window[0], token))
        pid = f"person:{firm['firm_id']}:{token}"
        precs = [Prec(label="615", person=pid, use="p2p", sign=-1)] if role == "contractor" else None
        return env.build(rng, firm, scenario=scenario or ("p2p_" + kind), stratum=stratum, merchant=m, use=u,
                         rule="US-R141", facts={"role": role}, family="ref_narrative", contact="", line="",
                         narrative=narr, person=token, merchant_id=pid, precedents=precs,
                         forbid=[pid] if role is None else None)

    return fn


CHECK_PATS = ["CHECK {n}", "CHECK # {n}", "CHK {n}", "CHECK PAID {n}", "DDA CHECK {n}"]


def _owner_acct_us(firm):
    return "3010"


def _la_food(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("no_description"))
    return env.build(rng, firm, scenario="lookalike_meal", stratum=stratum, merchant=m, use=u, rule="US-R193",
                     facts={"account": "685" if rng.random() < 0.8 else "3010"}, family="contact_only",
                     expect=("line+history",))


def _la_retail(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("unknown_purchase"))
    return env.build(rng, firm, scenario="lookalike_retailer", stratum=stratum, merchant=m, use=u, rule="US-R193",
                     facts={"account": "670" if rng.random() < 0.8 else "3010"}, family="contact_only",
                     expect=("line+history",))


def _la_invoice(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: u["routine"] and u["direction"] == "spend" and any(u["line_descriptions"])
                    and (u.get("bank_format") or m["bank_format"]) not in ("US-CARD", "US-FEE"))
    item = fill(rng.choice([x for x in u["line_descriptions"] if x]), rng, env.fill_ctx(firm, env.scored_window[0]))
    from .scenarios_uk import BENIGN_INVOICE

    text = rng.choice(BENIGN_INVOICE).format(inv=rng.randint(1000, 99999), item=item)
    if rng.random() < 0.35:
        text = text.lower()
    return env.build(rng, firm, scenario="lookalike_invoice_capture", stratum=stratum, merchant=m, use=u,
                     family="contact_desc", line=text, expect=("line",))


def _card_payment(env, rng, firm, stratum):
    if firm["policies"]["card_account"] != "2000":
        raise Skip("no business card")
    m, u = env.use_named(firm["bank_brand"], "card_payment")
    # F1, F5: a bank is paid for several things, so the memo names the card.
    return env.build(rng, firm, scenario="card_payment", stratum=stratum, merchant=m, use=u, rule="US-R110",
                     family="contact_desc", expect=HIST)


def _personal_card(env, rng, firm, stratum):
    others = [b for b in ("us-b-citibank", "us-b-capital-one", "us-b-wells-fargo") if b != firm["bank_brand"]]
    m, u = env.use_named(rng.choice(others), "card_payment")
    prec = Prec(label="3010", merchant_id=m["merchant_id"], use=u["use"], sign=-1)
    return env.build(rng, firm, scenario="personal_card_payment", stratum=stratum, merchant=m, use=u,
                     rule="US-R112", family="contact_desc", precedents=[prec])


def _card_feed_payment(env, rng, firm, stratum):
    if firm["policies"]["card_account"] != "2000":
        raise Skip("no business card")
    narr = rng.choice(["PAYMENT THANK YOU", "AUTOPAY PAYMENT - THANK YOU", "ONLINE PAYMENT, THANK YOU"])
    return env.build(rng, firm, scenario="card_feed_payment", stratum=stratum, merchant=None, use=None,
                     rule="US-R111", family="ref_narrative", amount=draw_amount(rng, "150.00", "4200.00"), sign=1,
                     contact="", line="", ref=None, narrative=narr, fmt="US-CARDFEED", merchant_id="own:card_feed",
                     expect=LINE)


def _savings_transfer(env, rng, firm, stratum):
    if not firm["policies"]["savings_account"]:
        raise Skip("no savings")
    savings_feed = rng.random() < 0.3
    a4 = rng.randint(1000, 9999)
    if savings_feed:
        narr, sign = f"Online transfer from CHK ...{a4}", 1
    else:
        out = rng.random() < 0.6
        narr = f"Online transfer to SAV ...{a4}" if out else f"Online transfer from SAV ...{a4}"
        sign = -1 if out else 1
    return env.build(rng, firm, scenario="own_account_transfer", stratum=stratum, merchant=None, use=None,
                     rule="US-R140", facts={"savings_feed": savings_feed}, family="ref_narrative",
                     amount=draw_amount(rng, "200.00", "9000.00"), sign=sign, contact="", line="", ref=None,
                     narrative=narr, fmt="US-SAVFEED" if savings_feed else "US-XFER", merchant_id="own:savings",
                     expect=LINE)


def _vendor_refund(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: u["routine"] and u["direction"] == "spend"
                    and u["default_code"] in ("705", "645", "670", "600", "625"))
    g = env.rule(u["rule_ids"][0], Ctx(firm=firm, facts=dict(u["facts"]), merchant=m, use=u, amount=Decimal("-10")))
    prec = Prec(label=g.label, merchant_id=m["merchant_id"], use=u["use"], sign=-1)
    contact, payee = _payee_names(env, rng, firm, m)
    return env.build(rng, firm, scenario="vendor_refund", stratum=stratum, merchant=m, use=u, rule="US-R131",
                     facts={"account": g.label}, family="explicit", amount=draw_amount(rng, "5.00", "140.00"),
                     sign=1, contact=contact, line=_refund_memo(rng, m, u, payee), precedents=[prec])


# Goods a buyer can send back; software, ads, insurance, postage and shipping are credited, not returned (R16).
GOODS_USES = ("consumables", "office_purchase", "job_materials", "teaching_supplies")
GOODS_OFFICE_STORES = ("us-b-staples", "us-b-office-depot", "us-b-officemax")


def _payee_names(env, rng, firm, m):
    """The Xero contact for a record and the payee name a memo uses (the merchant's plain name)."""
    ctx = env.fill_ctx(firm, env.scored_window[0])
    return fill(rng.choice(m["contact_names"]), rng, ctx), fill(m["contact_names"][0], rng, ctx)


def _refund_memo(rng, m, u, payee):
    """F5: a refund or credit memo names the payee, so the memo alone says whose purchase it reverses."""
    pool = [f"Refund from {payee}", f"Credit from {payee}"]
    if u["use"] in GOODS_USES or (u["use"] == "office" and m["merchant_id"] in GOODS_OFFICE_STORES):
        pool.append(f"{payee} refund, returned item")
    return rng.choice(pool)


def _contradictory_refund(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: u["routine"] and u["direction"] == "spend", need_free=True)
    contact, payee = _payee_names(env, rng, firm, m)
    return env.build(rng, firm, scenario="contradictory_refund", stratum=stratum, merchant=m, use=u, rule="US-N4",
                     family="contact_desc", contact=contact,
                     line=rng.choice([f"Refund from {payee}", f"{payee} refund of overpayment"]),
                     forbid=[m["merchant_id"]])


def _check(env, rng, firm, stratum):
    n = rng.randint(1001, 1290)
    narr = rng.choice(CHECK_PATS).format(n=n)
    return env.build(rng, firm, scenario="check_no_payee", stratum=stratum, merchant=None, use=None, rule="US-R142",
                     family="ref_narrative", amount=draw_amount(rng, "40.00", "3200.00"), sign=-1, contact="",
                     line="", ref=None, narrative=narr, fmt="US-CHECK", merchant_id="check:unknown")


def _atm(env, rng, firm, stratum):
    narr = f"ATM WITHDRAWAL {rng.randint(100000, 999999)} {firm['city'].upper()} {firm['state']}"
    amount = Decimal(rng.choice([40, 60, 100, 200, 300, 400])).quantize(Decimal("0.01"))
    return env.build(rng, firm, scenario="atm_withdrawal", stratum=stratum, merchant=None, use=None, rule="US-R142",
                     family="ref_narrative", amount=amount, sign=-1, contact="", line="", ref=None, narrative=narr,
                     fmt="US-ATM", merchant_id="atm")


def _mixed_payroll(env, rng, firm, stratum):
    if not (is_scorp(firm) and firm["people"]["employees"]):
        raise Skip("S corp with staff only")
    m, u = env.use_named(firm["policies"]["payroll"].replace("us-", "us-b-"), "net_pay")
    family = rng.choice(["contact_desc", "contact_ref"])
    amount = payroll_amount(env, firm, m, "net", _record_date(env, rng, m, u))  # the last draw before build
    return env.build(rng, firm, scenario="scorp_mixed_payroll", stratum=stratum, merchant=m, use=u, rule="US-R077",
                     family=family, amount=amount)


def _record_date(env, rng, m, u):
    """The date `Env.build` will draw next (its first draw is `date_in` with the line's bank format), read from a
    copy of the generator so a per-date amount (a fixed amount's price step) matches the record date. Call it after
    every other draw of the scenario."""
    probe = random.Random()
    probe.setstate(rng.getstate())
    return env.date_in(probe, env.scored_window, env.fmt_for(m, u, None, env.jur))


# R16: a staff party is sized to the people at it (staff and owners), at a per-head cost.
STAFF_PARTY_PER_HEAD = ("38.00", "95.00")


def _staff_party(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("staff_party"))
    heads = len(firm["people"]["employees"]) + len(firm["people"]["owners"])
    amount = (draw_amount(rng, *STAFF_PARTY_PER_HEAD) * heads).quantize(Decimal("0.01"))
    return env.build(rng, firm, scenario="staff_party", stratum=stratum, merchant=m, use=u, family="contact_desc",
                     amount=amount)


def _irs(use_name, expect=None):
    def fn(env, rng, firm, stratum):
        m, u = env.use_named("us-g-irs", use_name)
        if not env.eligible(firm, u):
            raise Skip("irs use not eligible")
        fam = "contact_ref" if use_name != "payroll_deposit" else "contact_desc"
        return env.build(rng, firm, scenario="irs_" + use_name, stratum=stratum, merchant=m, use=u, family=fam,
                         expect=expect)

    return fn


def _state(use_name):
    def fn(env, rng, firm, stratum):
        m, u = env.use_named("us-g-state-revenue", use_name)
        if not env.eligible(firm, u):
            raise Skip("state use not eligible")
        if use_name.startswith("owner_") and firm["state"] in NO_PERSONAL_INCOME_TAX:
            raise Skip("no state individual income tax")
        return env.build(rng, firm, scenario="state_" + use_name, stratum=stratum, merchant=m, use=u,
                         family=rng.choice(["contact_ref", "contact_desc"]))

    return fn


def _sales_tax_in_price(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, _named("office"))
    line = rng.choice(["Toner and paper, sales tax included", "Office chair mat incl. sales tax",
                       "Folders and labels, tax incl."])
    return env.build(rng, firm, scenario="purchase_incl_sales_tax", stratum=stratum, merchant=m, use=u,
                     rule="US-R090", facts={"account": "645"}, family="contact_desc", line=line, expect=LINE)


def _adversarial(env, rng, firm, stratum):
    m, u = env.pick(rng, firm, lambda m, u: u["routine"])
    return adversarial(env, rng, firm, stratum, m, u, review_rule="US-N5")


def _home_bill(env, rng, firm, stratum):
    """F1: a utility that also bills the business premises shows the home memo, never the payee alone."""
    m, u = env.pick(rng, firm, _named("home_utility", "home_rent"))
    return env.build(rng, firm, scenario="home_bill", stratum=stratum, merchant=m, use=u,
                     family=_fam(rng, u, m, ["contact_only"]), expect=HIST)


def _history_use(names, scenario):
    """An item settled by the firm's own precedent for the same merchant use."""
    return _use(_named(*names), scenario, family=lambda r, u: "contact_desc" if any(u["line_descriptions"]) else "contact_only",
                expect=HIST)


SCENARIOS = {
    "S0": [
        ("routine", 1.0, _routine), ("la_food", 0.25, _la_food), ("la_retail", 0.25, _la_retail),
        ("la_p2p_owner", 0.12, _p2p("owner", scenario="lookalike_p2p_owner")),
        ("la_p2p_contractor", 0.1, _p2p("contractor", scenario="lookalike_p2p_contractor")),
        ("la_invoice", 0.14, _la_invoice), ("small_seller", 0.35, _small_routine),
        ("customer_receipt", 0.5, _customer_receipt),
    ],
    "S1": [("noisy", 1.0, _noisy), ("small_seller_noisy", 0.3, _small_noisy)],
    "S2": [
        ("fuel", 1.6, _vehicle(("fuel",), "US-R040")), ("auto_repair", 1.0, _vehicle(("auto_repair",), "US-R040")),
        ("auto_insurance", 0.7, _vehicle(("auto_insurance",), "US-R041")),
        ("vehicle_lease", 0.5, _vehicle(("vehicle_lease",), "US-R044")),
        ("payout", 1.4, _payout), ("de_minimis", 1.0, _de_minimis), ("materials", 1.0, _materials),
        ("payroll_net", 0.8, _payroll("net")), ("payroll_tax", 0.6, _payroll("tax")),
        ("owner_draw", 1.0, lambda e, r, f, s: _owner(e, r, f, s, out=True)),
        ("owner_contribution", 0.6, lambda e, r, f, s: _owner(e, r, f, s, out=False)),
        ("home_bill", 0.7, _home_bill),
        ("phone", 0.7, _history_use(("business_line", "residential"), "telecom_line")),
        ("premises_utility", 0.6, _use(_named("premises_utility"), "premises_utility", expect=HIST)),
        ("warehouse_membership", 0.4, _use(_named("membership"), "warehouse_membership", facts={"buys_supplies_there": True},
                                          family=lambda r, u: "contact_desc", expect=HIST)),
        ("p2p_owner", 0.4, _p2p("owner")), ("p2p_contractor", 0.5, _p2p("contractor")),
        ("mortgage", 0.4, _history_use(("mortgage_interest",), "mortgage_interest")),
        ("owner_insurance", 0.6, _history_use(("owner_health", "life_insurance"), "owner_insurance")),
        ("employee_benefits", 0.5, _history_use(("employee_health", "employee_plan", "owner_plan"), "retirement_or_benefits")),
        ("personal_purchase", 0.7, _use(_named("personal_purchase", "gym", "personal_meal"), "personal_spend", expect=HIST)),
    ],
    "S3": [
        ("client_meal", 1.0, _use(_named("client_meal"), "client_meal", family=lambda r, u: "contact_desc")),
        ("meal_tip", 0.4, _use(_named("meal_tip"), "meal_full_amount", family=lambda r, u: "contact_desc")),
        ("entertainment", 0.8, _use(_named("client_tickets", "golf_with_client"), "entertainment")),
        ("stadium_food", 0.5, _use(_named("stadium_food", "stadium_package"), "food_at_event")),
        ("staff_party", 0.5, _staff_party),
        ("contract_penalty", 0.4, _use(_named(*PENALTY_USES), "contract_penalty", family=lambda r, u: "contact_desc",
                                         expect=LINE)),
        ("club_dues", 0.6, _use(_named("club_dues", "dues"), "dues")),
        ("client_gift", 0.7, _use(_named("client_gift"), "client_gift")),
        ("promo", 0.5, _use(_named("promo_items"), "promotional_items")),
        ("travel", 1.0, _use(_named("airfare", "lodging", "car_rental"), "travel", family=lambda r, u: "contact_desc")),
        ("travel_meal", 0.5, _use(_named("travel_meal"), "travel_meal", family=lambda r, u: "contact_desc")),
        ("local_ride", 0.6, _use(_named("local_ride"), "local_rideshare", facts={"stated": True},
                                 family=lambda r, u: "contact_desc", expect=LINE)),
        ("parking", 0.5, _use(_named("parking"), "parking")),
        ("commute_parking", 0.3, _use(_named("commute_parking"), "commute_parking")),
        ("over_limit", 0.8, _over_limit),
        ("repair", 0.6, _use(lambda m, u: u["use"] in ("repair", "improvement") and m["merchant_id"].endswith("cityworks-repair"), "repair_or_improvement")),
        ("vehicle_purchase", 0.4, _use(_named("vehicle_purchase", "vehicle_loan"), "vehicle_purchase")),
        ("irs_form", 0.8, _irs("estimate_with_form")), ("irs_941", 0.5, _irs("payroll_deposit")),
        ("state_owner", 0.5, _state("owner_estimate")), ("state_refund", 0.3, _state("owner_refund")),
        ("sales_tax", 0.7, _state("sales_tax")), ("grt", 0.4, _state("gross_receipts_tax")),
        ("loan_proceeds", 0.4, _use(_named("loan_proceeds"), "loan_proceeds")),
        ("loan_principal", 0.4, _use(_named("loan_principal"), "loan_principal")),
        ("penalty", 0.5, _use(_named("personal_penalty", "parking_ticket"), "fines_and_penalties")),
        ("donation", 0.5, _use(_named("donation", "sponsorship"), "donation_or_sponsorship")),
        ("political", 0.3, _use(_named("political"), "political")),
        ("personal_return", 0.5, _use(_named("personal_return"), "personal_return")),
        ("contract_labor", 0.7, _use(_named("contract_labor"), "contract_labor")),
        ("sales_tax_in_price", 0.4, _sales_tax_in_price),
        ("personal_interest", 0.3, _use(_named("personal_interest"), "personal_interest")),
        ("payroll_fee", 0.4, _use(_named("fee"), "payroll_fee", family=lambda r, u: "contact_desc")),
        ("linkedin_ads", 0.3, _use(lambda m, u: m["merchant_id"] == "us-b-linkedin", "ads_on_marketing_platform")),
    ],
    "S4": [
        ("card_payment", 1.2, _card_payment), ("personal_card", 0.6, _personal_card),
        ("card_feed", 0.6, _card_feed_payment), ("savings", 1.0, _savings_transfer),
        ("vendor_refund", 0.8, _vendor_refund),
        ("chargeback", 0.6, _use(_named("chargeback", "chargeback_fee"), "chargeback")),
        ("customer_refund", 0.6, _use(_named("customer_refund"), "customer_refund", family=lambda r, u: "contact_desc")),
        ("fee_reversal", 0.5, _use(_named("fee_reversal"), "fee_reversal", family=lambda r, u: "ref_narrative")),
        ("bank_fee", 0.6, _use(_named("service_fee"), "bank_fee", family=lambda r, u: "ref_narrative")),
        ("loan_proceeds", 0.4, _use(_named("loan_proceeds"), "loan_proceeds")),
    ],
    "S5": [
        ("retailer_unknown", 1.4, _use(_named("unknown_purchase"), "retailer_no_item", family=lambda r, u: "contact_only",
                                       need_free=True, forbid_self=True)),
        ("p2p_unknown", 1.0, _p2p("unknown")), ("check", 0.9, _check), ("atm", 0.6, _atm),
        ("loan_combined", 0.8, _use(_named("loan_payment"), "loan_combined_payment")),
        ("irs_ambiguous", 0.7, _irs("ambiguous")), ("mixed_payroll", 0.5, _mixed_payroll),
        ("scope_unknown", 0.5, _use(_named("unknown_scope"), "repair_scope_unknown")),
        ("food_unknown", 0.8, _use(_named("no_description"), "meal_no_description", family=lambda r, u: "contact_only",
                                   need_free=True, forbid_self=True)),
    ],
    "S6": [("adversarial", 1.0, _adversarial)],
}
