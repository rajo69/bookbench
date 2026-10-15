"""Tests for the shared generator foundation of fix round 2 (SCHEMA_v0.2): split gold, chart variants, fixed and round
amounts, constant references, contacts, precedent forms, the history tag and the manifest scoring block."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
from decimal import Decimal

import pytest

from evals.generator import build as B
from evals.generator import splits
from evals.generator.charts import chart_id_for, firm_accounts, in_chart, is_gold_eligible
from evals.generator.constants import MODES, NEEDS_REVIEW, ROLE_WORDS
from evals.generator.engine import Draft, Env, Prec
from evals.generator.firms import all_firms, profile_view
from evals.generator.gold import Ctx, Gold, RuleNotApplicable, make_split
from evals.generator.templates import fill, has_role_word, payee_token, render

FIRMS = all_firms()
UK_ST = next(f for f in FIRMS.values() if f["jurisdiction"] == "UK" and f["entity_type"] == "sole_trader")
UK_CO = next(f for f in FIRMS.values() if f["jurisdiction"] == "UK" and f["entity_type"] == "limited_company")
US_SP = next(f for f in FIRMS.values() if f["jurisdiction"] == "US" and f["entity_type"] == "sole_prop")


# ---------------------------------------------------------------- split gold


def test_make_split_primary_line_and_serialised_amounts():
    ctx = Ctx(firm=UK_ST, amount=Decimal("1482.37"))
    g = make_split(ctx, "UK-R019", [("200", Decimal("1520.00"), "gross_sales"), ("404", Decimal("-37.63"), "processor_fee")],
                   "processor_payout")
    assert g.label == "200" and g.acceptable_labels == ("200",) and g.gold_action == "post"
    assert g.lines == (("200", "1520.00", "gross_sales"), ("404", "-37.63", "processor_fee"))
    assert g.split_kind == "processor_payout" and g.solvable_with == "line"


def test_make_split_ties_break_on_lower_code():
    g = make_split(Ctx(firm=UK_ST, amount=Decimal("-50.00")), "UK-R019",
                   [("404", Decimal("-100.00"), "processor_fee"), ("200", Decimal("50.00"), "gross_sales")],
                   "processor_payout")
    assert g.label == "404"  # largest absolute amount wins
    g = make_split(Ctx(firm=UK_ST, amount=Decimal("0.00")), "UK-R019",
                   [("404", Decimal("-50.00"), "processor_fee"), ("200", Decimal("50.00"), "gross_sales")],
                   "processor_payout")
    assert g.label == "200"  # tie on |amount|: lower code


@pytest.mark.parametrize("lines,kind", [
    ([("200", Decimal("100.00"), "gross_sales")], "processor_payout"),  # one line
    ([("200", Decimal("100.00"), "gross_sales"), ("200", Decimal("-2.00"), "processor_fee")], "processor_payout"),
    ([("200", Decimal("100.00"), "gross_sales"), ("404", Decimal("-3.00"), "processor_fee")], "processor_payout"),  # sum
    ([("200", Decimal("100.00"), "gross_sales"), ("404", Decimal("-2.00"), "bad_role")], "processor_payout"),
    ([("200", Decimal("100.00"), "gross_sales"), ("404", Decimal("-2.00"), "processor_fee")], "bad_kind"),
])
def test_make_split_rejects_bad_splits(lines, kind):
    with pytest.raises(ValueError):
        make_split(Ctx(firm=UK_ST, amount=Decimal("98.00")), "UK-R019", lines, kind)


def test_make_split_checks_chart_eligibility():
    # 835 is not on a sole trader's chart (F12)
    with pytest.raises(RuleNotApplicable):
        make_split(Ctx(firm=UK_ST, amount=Decimal("90.00")), "UK-R019",
                   [("200", Decimal("100.00"), "gross_sales"), ("835", Decimal("-10.00"), "processor_fee")],
                   "processor_payout")


def test_one_line_gold_has_no_lines():
    assert Gold("200", ("200",), "post", "line", "UK-R019", "convention", "x").lines is None


# ---------------------------------------------------------------- statement figures


def test_processor_payout_figures_sum_and_text():
    rng = random.Random(1)
    p = splits.processor_payout(rng, Decimal("1520.00"), "uk-b-stripe", dt.date(2026, 8, 14), "Stripe")
    assert p["fee"] == Decimal("23.00")  # 1.5% + 0.20
    assert p["net"] == p["gross"] - p["fee"] and sum(a for _, a, _ in p["lines"]) == p["net"]
    assert "1,520.00" in p["text"] and "23.00" in p["text"]
    g = make_split(Ctx(firm=UK_ST, amount=p["net"]), "UK-R019", p["lines"], p["split_kind"])
    assert g.label == "200"


def test_cis_receipt_and_payment_figures():
    rng = random.Random(2)
    r = splits.cis_receipt(rng, Decimal("1200.00"), Decimal("300.00"), "20", dt.date(2026, 6, 5))
    assert r["deduction"] == Decimal("180.00") and r["net"] == Decimal("1020.00")
    assert r["lines"] == [("200", Decimal("1200.00"), "gross_sales"), ("625", Decimal("-180.00"), "cis_deduction_suffered")]
    assert all(x in r["text"] for x in ("1,200.00", "300.00", "180.00"))
    p = splits.cis_payment(rng, Decimal("1000.00"), Decimal("0.00"), "30", dt.date(2026, 6, 5), "J Tarrow")
    assert p["net"] == Decimal("-700.00") and sum(a for _, a, _ in p["lines"]) == p["net"]
    gross_status = splits.cis_receipt(rng, Decimal("800.00"), Decimal("0.00"), "0", dt.date(2026, 6, 5))
    assert gross_status["split_kind"] is None and len(gross_status["lines"]) == 1


def test_cis_accounts_exist_on_uk_charts():
    for firm in (UK_ST, UK_CO):
        assert is_gold_eligible(firm, splits.CIS_SUFFERED_CODE) and is_gold_eligible(firm, splits.CIS_WITHHELD_CODE)


# ---------------------------------------------------------------- charts and firms (F12, B16)


def test_entity_chart_variants():
    assert not in_chart(UK_ST, "835") and in_chart(UK_ST, "980") and in_chart(UK_ST, "970")
    assert not in_chart(UK_CO, "970") and not in_chart(UK_CO, "980") and in_chart(UK_CO, "835")
    assert chart_id_for(UK_ST) != chart_id_for(UK_CO)
    assert chart_id_for(UK_ST).startswith("uk_xero_default_v0_2") and chart_id_for(US_SP).startswith("us_schedule_c_v0_2")
    assert in_chart(US_SP, "720")


def test_every_firm_has_cis_status_and_profile_carries_it():
    for f in FIRMS.values():
        if f["jurisdiction"] == "UK":
            assert set(f["tax"]["cis"]) == {"contractor", "subcontractor", "deduction_rate"}
            assert profile_view(f)["tax_registration"]["cis"] == f["tax"]["cis"]


# ---------------------------------------------------------------- amounts and references (F8)


def _env(seed=5):
    from evals.generator import spec_uk

    jf = {k: v for k, v in FIRMS.items() if v["jurisdiction"] == "UK"}
    return Env("UK", jf, spec_uk.MERCHANTS, seed=seed)


def _use(mode, lo="100.00", hi="900.00"):
    return {"use": "rent", "amount_range": [lo, hi], "amount_mode": mode}


def test_fixed_amounts_are_stable_with_at_most_one_step():
    env = _env()
    m = {"merchant_id": "uk-i-test"}
    seen = set()
    for day in range(0, 360, 7):
        d = env.hist_window[0] + dt.timedelta(days=day)
        seen.add(env.amount_for(random.Random(day), UK_ST, m, _use("fixed"), d))
    assert B.fixed_ok(seen) and len(seen) <= 2
    assert all(B.fixed_ok(a) for a in env.amount_log.values())
    # independent of the run rng and of draw order; different under another seed
    a = _env(5).amount_for(random.Random(99), UK_ST, m, _use("fixed"), env.hist_window[0])
    assert a == _env(5).amount_for(random.Random(1), UK_ST, m, _use("fixed"), env.hist_window[0])


def test_round_amounts():
    env = _env()
    for i in range(50):
        a = env.amount_for(random.Random(i), UK_ST, None, _use("round", "1000.00", "20000.00"), env.hist_window[0])
        unit = Decimal("500") if a > 5000 else Decimal("100")
        assert a % unit == 0 and a > 0


def test_fixed_ok():
    assert B.fixed_ok({Decimal("100")}) and B.fixed_ok({Decimal("100"), Decimal("110")})
    assert B.fixed_ok({Decimal("333.29"), Decimal("366.62")})  # a 10% step rounded to the cent
    assert not B.fixed_ok({Decimal("100"), Decimal("111")}) and not B.fixed_ok({Decimal(1), Decimal(2), Decimal(3)})


def test_k_token_is_constant_per_firm_and_merchant():
    ctx = {"firm": UK_ST, "date": dt.date(2026, 5, 1), "merchant_id": "uk-i-lender"}
    a = fill("LOAN {K8}", random.Random(1), ctx)
    assert a == fill("LOAN {K8}", random.Random(2), dict(ctx, date=dt.date(2026, 9, 1))) and len(a) == 13
    assert a != fill("LOAN {K8}", random.Random(1), dict(ctx, merchant_id="uk-i-other"))
    assert a != fill("LOAN {K8}", random.Random(1), dict(ctx, use="home_line"))


# ---------------------------------------------------------------- contacts (F8)


def test_payee_token_never_empty_and_never_a_role_word():
    assert payee_token("SQ *KESTREL CAFE  LEEDS", "", Decimal("-5")) == "SQ *KESTREL CAFE LEEDS"
    assert payee_token("", "", Decimal("5")) == "BANK CREDIT"
    assert payee_token("OWNER TFR", "REF 12", Decimal("-5")) == "REF 12"
    assert has_role_word("Director loan") and not has_role_word("Directline")
    assert set(ROLE_WORDS) >= {"owner", "director"}


@pytest.mark.parametrize("family", ["ref_narrative", "blank_contact", "explicit", "contact_only", "raw_contact"])
def test_render_always_sets_a_contact(family):
    ctx = {"firm": UK_ST, "date": dt.date(2026, 5, 1), "towns": ["LEEDS"], "person": None}
    xero, _ = render(jurisdiction="UK", rng=random.Random(3), ctx=ctx, merchant=None, use=None,
                     amount=Decimal("-12.00"), family=family, contact="", line="", ref="", narrative="DEPOSIT 004512",
                     fmt="UK-FPO")
    assert xero["contact_name"]


# ---------------------------------------------------------------- precedent forms (A12 b)


def test_precedent_forms_alternate_per_stratum():
    def draft(stratum, n):
        d = Draft("s", stratum, "m", "brand", "u", {}, {}, None, "f", {})
        d.precedents = [Prec(label="400", description=f"d{i}") for i in range(n)] + [Prec(label="400")]
        return (None, d)

    ds = [draft("S0", 2), draft("S2", 1), draft("S0", 1), draft("S2", 1)]
    B.assign_precedent_forms(ds)
    forms = [(d.stratum, p.form) for _, d in ds for p in d.precedents if p.description]
    assert forms == [("S0", "exact"), ("S0", "varied"), ("S2", "exact"), ("S0", "exact"), ("S2", "varied")]


# ---------------------------------------------------------------- built pilot


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("shared")
    B.build(B.DEFAULT_SEED, "pilot", None, None, out, None, retrieval="off")
    items = [json.loads(x) for x in (out / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    hist = [json.loads(x) for x in (out / "history.jsonl").read_text(encoding="utf-8").splitlines()]
    return out, items, hist


def test_pilot_quotas_are_40_40(built):
    _, items, _ = built
    assert MODES["pilot"] == {"UK": 40, "US": 40} and MODES["full"] == {"UK": 500, "US": 500}
    assert sum(i["jurisdiction"] == "UK" for i in items) == 40 and sum(i["jurisdiction"] == "US" for i in items) == 40


def test_new_item_fields(built):
    _, items, _ = built
    for it in items:
        assert it["description_in_history"] in ("exact", "varied", "none")
        assert it["chart_id"] == chart_id_for(FIRMS[it["firm_id"]])
        assert "gold_lines" in it and "split_kind" in it
        if it["gold_lines"]:
            assert sum(Decimal(x["amount"]) for x in it["gold_lines"]) == Decimal(it["record"]["amount"])
            assert it["label"] == it["gold_lines"][0]["code"] or it["label"] in {x["code"] for x in it["gold_lines"]}
        assert it["record"]["xero"]["contact_name"], it["item_id"]
        assert not has_role_word(it["record"]["xero"]["contact_name"]), it["item_id"]


def test_no_code_outside_the_firm_chart(built):
    _, items, hist = built
    for it in items:
        firm = FIRMS[it["firm_id"]]
        assert it["label"] == NEEDS_REVIEW or in_chart(firm, it["label"]), it["item_id"]
        assert all(in_chart(firm, c) for c in it["acceptable_labels"])
    for r in hist:
        assert in_chart(FIRMS[r["firm_id"]], r["category_code"]), r["row_id"]


def test_manifest_scoring_and_stats(built):
    out, _, _ = built
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["scoring"]["headline_strata"] == ["S0", "S1", "S2", "S3", "S4", "S5"]
    assert "underlying_correct" in m["scoring"]["attack_metrics"]
    st = json.loads((out / "stats.json").read_text(encoding="utf-8"))
    assert st["records_without_contact"] == 0 and st["contacts_with_role_word"] == 0
    assert st["generation"].get("fixed_amount_violations", 0) == 0
    assert firm_accounts(UK_ST) is not firm_accounts(UK_CO)


def test_baselines(built):
    from evals.generator.baselines import NAMES, compute, correct

    out, items, hist = built
    st = json.loads((out / "stats.json").read_text(encoding="utf-8"))
    assert set(st["baselines"]) == set(NAMES)
    assert st["baselines"]["copy_exact"] is None  # retrieval off: no retrieved_top5
    tf = st["baselines"]["tfidf_description"]
    assert 0 <= tf["overall"]["accuracy"] <= 1 and "by_description_in_history" in tf
    assert compute(items, hist) == st["baselines"]
    review_item = {"jurisdiction": "UK", "gold_action": "review", "acceptable_labels": []}
    assert correct(review_item, "850") and correct(review_item, NEEDS_REVIEW) and not correct(review_item, "200")


def test_copy_baselines_with_retrieval():
    from evals.generator.baselines import _copy

    hist = [{"row_id": "f-h1", "description": "Zoom", "category_code": "463"}]
    items = [{"item_id": "a", "record": {"description": "zoom"}, "retrieved_top5": ["f-h1"]},
             {"item_id": "b", "record": {"description": "ZOOM.US 888"}, "retrieved_top5": ["f-h1"]},
             {"item_id": "c", "record": {"description": "x"}, "retrieved_top5": []}]
    assert _copy(items, hist, exact_only=True) == {"a": "463", "b": NEEDS_REVIEW, "c": NEEDS_REVIEW}
    assert _copy(items, hist, exact_only=False) == {"a": "463", "b": "463", "c": NEEDS_REVIEW}


# ---------------------------------------------------------------- fix round 2 step 5a (audit round 2)


def test_working_day_formats_never_land_on_weekends_or_holidays():
    env = _env()
    for i in range(400):
        d = env.date_in(random.Random(i), env.scored_window, "UK-DD")
        assert env.is_working_day(d) and env.scored_window[0] <= d <= env.scored_window[1]
    assert not env.is_working_day(dt.date(2026, 4, 6))  # Easter Monday
    assert any(env.date_in(random.Random(i), env.scored_window, "UK-DEB").weekday() >= 5 for i in range(200))


def test_built_items_respect_working_days(built):
    out, items, _ = built
    assert all(B.working_day_ok(i) for i in items)
    assert json.loads((out / "stats.json").read_text(encoding="utf-8"))["working_day_violations"] == 0


def test_record_ids_are_shared_within_one_record_only():
    ctx = {"firm": UK_ST, "date": dt.date(2026, 5, 1), "_memo": {}}
    rng = random.Random(4)
    a, b = fill("Invoice {INV} ref {A8}", rng, ctx), fill("{INV} {A8}", rng, ctx)
    assert a.split(" ")[1] == b.split(" ")[0] and a.split(" ")[3] == b.split(" ")[1]
    assert fill("{N3}-{N3}", random.Random(9), dict(ctx, _memo={})).count("-") == 1  # short tokens independent


def test_fee_lines_take_the_bank_as_contact():
    ctx = {"firm": UK_ST, "date": dt.date(2026, 5, 1), "towns": ["LEEDS"], "person": None}
    xero, _ = render(jurisdiction="UK", rng=random.Random(3), ctx=ctx, merchant=None, use=None,
                     amount=Decimal("-8.50"), family="ref_narrative", contact="", line="", ref="",
                     narrative="MONTHLY ACCOUNT FEE", fmt="UK-CHG")
    assert xero["contact_name"] == UK_ST["bank_name"]


def test_fixed_group_shares_one_amount():
    env = _env()
    m = {"merchant_id": "uk-i-lender"}
    a = env.amount_for(random.Random(1), UK_ST, m, dict(_use("fixed"), use="loan_instalment", fixed_group="loan"),
                       env.hist_window[0])
    b = env.amount_for(random.Random(2), UK_ST, m, dict(_use("fixed"), use="loan_repayment", fixed_group="loan"),
                       env.hist_window[0])
    assert a == b


def test_payee_only_template_needs_a_single_purpose_payee():
    from evals.generator.engine import family_plain, family_s0

    bank = {"uses": [{"direction": "spend", "default_code": "404"}, {"direction": "spend", "default_code": "437"}]}
    use = {"direction": "spend", "line_descriptions": [""], "default_code": "404"}
    for i in range(30):
        assert family_s0(random.Random(i), use, bank) == "desc_narrative"
        assert family_plain(random.Random(i), use, bank) == "desc_narrative"
    with_line = dict(use, line_descriptions=["Interest earned"])
    assert {family_s0(random.Random(i), with_line, bank) for i in range(30)} == {"contact_desc"}
    one = {"uses": [{"direction": "spend", "default_code": "463"}]}
    assert family_plain(random.Random(0), use, one) in ("contact_only", "contact_ref")


def test_cis_contractors_have_a_rate_per_subcontractor():
    for f in FIRMS.values():
        if f["jurisdiction"] == "UK":
            rates = f["people"]["cis_rates"]
            assert set(rates) == (set(f["people"]["subcontractors"]) if f["tax"]["cis"]["contractor"] else set())
            assert set(rates.values()) <= {"0", "20", "30"}


def test_loans_never_take_a_price_step():
    env = _env()
    m = {"merchant_id": "uk-i-lender"}
    for k in range(40):
        firm = dict(UK_ST, firm_id=f"uk-x{k}")
        plan = env._fixed_plan(firm, m["merchant_id"], dict(_use("fixed"), use="loan_instalment"))
        assert plan[1] is None and plan[0] == plan[2]


def test_month_style_does_not_repeat_a_month():
    """Re-audit R4: the `month` typing habit adds the month only when the line names none ("PAYE NOV Nov")."""
    from evals.generator.templates import apply_style

    d = dt.date(2025, 11, 3)
    assert apply_style("PAYE NOV", "month", d) == "PAYE NOV"
    assert apply_style("Rent for September", "month", d) == "Rent for September"
    assert apply_style("Search ads", "month", d) == "Search ads Nov"
    assert apply_style("Junk removal", "month", d) == "Junk removal Nov"


# ---------------------------------------------------------------- publication hygiene


def test_public_source_rewrites_internal_pointers():
    from evals.generator.guides import INTERNAL_REF, public_source

    cases = {
        "dataset policy (PLAN_v2 section 5)": "dataset convention, guide_uk.md UK-R061",
        "SA103F 26, supporting; the split itself is owner decision B5 (open question 5)":
            "SA103F 26, supporting; the split itself is a dataset convention: processor payouts split, sales at gross "
            "to 200 and fees to 404 (guide_uk.md UK-R061)",
        "SA103F 15, supporting; single code is owner decision S3":
            "SA103F 15, supporting; single code is a dataset convention (guide_uk.md UK-R061)",
        "open question 3": "dataset convention, guide_uk.md UK-R061",
        "account choice is practice (open question 6)": "account choice is practice; dataset convention, guide_uk.md UK-R061",
        "design decision for v1": "dataset convention, guide_uk.md UK-R061",
        "dataset convention (section 7, item 4)": "dataset convention (guide_uk.md section 7, item 4)",
        "BIM38515 (penalties)": "BIM38515 (penalties)",
    }
    for raw, want in cases.items():
        got = public_source("UK-R061", raw)
        assert got == want, (raw, got)
        assert not INTERNAL_REF.search(got)
    assert public_source("US-R077", "N3 (section 2.1)") == "N3 (guide_us.md section 2.1)"


def test_no_rule_source_cites_internal_notes(built):
    from evals.generator.guides import INTERNAL_REF, load_rules

    for rid, meta in load_rules().items():
        assert not INTERNAL_REF.search(meta.rule_source), (rid, meta.rule_source)
    _, items, _ = built
    for it in items:
        assert not INTERNAL_REF.search(it["rule_source"]), (it["item_id"], it["rule_source"])


def test_published_notes_and_manifest_files(built):
    out, _, _ = built
    st = json.loads((out / "stats.json").read_text(encoding="utf-8"))
    assert st["note"] == f"Build statistics for this draft; generator {B.GENERATOR_VERSION}."
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["baselines"]["results_in"] == "stats.json; per stratum in the dataset card"
    # The review sheet is written for the owner but is not a published file.
    assert (out / "REVIEW_SHEET.md").exists()
    assert set(m["files"]) == {"items.jsonl", "history.jsonl", "stats.json"}


def test_text_hashes_ignore_line_endings(tmp_path):
    lf, crlf, binary = tmp_path / "a.md", tmp_path / "b.md", tmp_path / "c.bin"
    lf.write_bytes(b"line one\nline two\n")
    crlf.write_bytes(b"line one\r\nline two\r\n")
    binary.write_bytes(b"line one\r\nline two\r\n")
    assert B.sha256(lf) == B.sha256(crlf)
    assert B.sha256(binary) != B.sha256(lf)
    for name in ("x.json", "x.jsonl"):
        p = tmp_path / name
        p.write_bytes(b"{}\r\n")
        assert B.sha256(p) == hashlib.sha256(b"{}\n").hexdigest()


def test_build_writes_lf_only(built):
    out, _, _ = built
    for p in out.iterdir():
        assert b"\r\n" not in p.read_bytes(), p.name


def test_surname_deny_filter_and_stable_draw():
    from evals.generator import make_names
    from evals.generator.firms import surname_slots, surnames

    names = surnames()
    assert not any(make_names.denied(n) for n in names)
    assert "Hickley" not in names and len(set(names)) == len(names)
    slots = surname_slots()
    assert [s for s in slots if s is not None] == list(names)
    assert len(slots) - len(names) == sum(1 for s in slots if s is None) > 0
    assert make_names.deny_filter(["Halvennick", "Tealdick", "Hickley", "Brownard"]) == (
        ["Halvennick", "Brownard"],
        {"substrings": list(make_names.DENY_SUBSTRINGS), "exact": ["Hickley"], "draw_pool_size": 4, "removed": 2,
         "removed_positions": [1, 2]},
    )
    for f in FIRMS.values():
        people = [p for k in ("owners", "employees", "subcontractors", "unknown_pool", "clients") for p in f["people"][k]]
        people += [f["people"]["landlord"]] if f["people"]["landlord"] else []
        assert len(set(people)) == len(people), f["firm_id"]
        assert not any(make_names.denied(p.partition(" ")[2]) for p in people), f["firm_id"]


def test_no_merchant_borrows_a_real_business_name():
    from evals.generator import spec_uk, spec_us

    names = {n.casefold() for m in spec_uk.MERCHANTS + spec_us.MERCHANTS
             for n in [m["name"], *m["contact_names"], *m["narratives"]]}
    for banned in ("cellar door wines", "northstar community credit union", "northstar cmty cu"):
        assert banned not in names
    assert "quillmoor wines" in names and "bramblewood community credit union" in names


def test_refs_carries_upstream_attribution():
    from pathlib import Path

    from evals.generator import refs

    head = Path(refs.__file__).read_text(encoding="utf-8")[:600]
    assert "github.com/hmrc/reference-checker" in head and "Apache License, Version 2.0" in head
