# Sources, licences and attribution

This file covers the brand lists in this folder (sections 1 to 4) and every other outside source the dataset relies
on (section 5).

Files in this folder:

| File | What it is |
|---|---|
| `brands_uk.json` | 262 UK national brands (142 from NSI, 120 from Wikidata) |
| `brands_us.json` | 251 US national brands (153 from NSI, 98 from Wikidata) |
| `brands_uk_excluded.log`, `brands_us_excluded.log` | every candidate a rule dropped, with the reason |
| `build_brands.py` | the script that produced all of the above |

Retrieval date for every source: **2026-10-13**. Only company and platform names are included, never a
natural person and never a sole trader or a single-site local business. Brand names are used as facts
(nominative use in synthetic bank descriptors); no logos or other brand assets are used.

## 1. Sources and licences

### 1.1 Name Suggestion Index (NSI)

- Project: https://github.com/osmlab/name-suggestion-index
- Licence: **BSD 3-Clause**, confirmed on 2026-10-13 from `LICENSE.md` in the npm package (sha256
  `3ed33fd0c4a3d78f2ca49801554b70bd148d0a62c0aeb26e72ffda6dab6513a3`) and from the GitHub licence API
  (`spdx_id: BSD-3-Clause`, file `LICENSE.md`, blob `b7491502fe52dde107aabe2de04fd841b5fb7c91`). The
  README says "name-suggestion-index is available under the 3-Clause BSD License". The licence text speaks of
  "software" and does not mention the data separately; we treat the data as covered by it and keep the notice
  below (condition 2 of the licence).
- File used: `dist/json/nsi.json` from npm package `name-suggestion-index@8.0.20260918`,
  https://cdn.jsdelivr.net/npm/name-suggestion-index@8.0.20260918/dist/json/nsi.json
  - `_meta.version` 8.0.20260918, `_meta.generated` 2026-09-18T19:50:18.997Z, `_meta.hash`
    3d3f4ba18fae91f329a6faaf73702e96
  - sha256 of the downloaded file: `96f105218058d3b68ef69c93f3d8f46f6bc714c70e9ef7d9f9e2f5c006585eb1`
  - The npm registry entry carries no `gitHead`, so the exact upstream commit is not recorded; the package
    version and file hash above identify the data.
- Fields taken per item: `id` (stored as `source_id`), `tags.brand` (stored as `name`), `tags.brand:wikidata`
  (stored as `wikidata_qid`), the category path (stored as `category`, e.g. `shop=supermarket`) and
  `locationSet`.

NSI licence notice, reproduced as the licence requires:

> Copyright 2026, name-suggestion-index contributors
>
> Redistribution and use in source and binary forms, with or without modification, are permitted provided that
> the following conditions are met:
>
> 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the
>    following disclaimer.
> 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
>    following disclaimer in the documentation and/or other materials provided with the distribution.
> 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or
>    promote products derived from this software without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
> WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
> PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
> DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
> PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
> CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
> OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
> DAMAGE.

### 1.2 Wikidata

- Licence: **CC0 1.0** for structured data (https://www.wikidata.org/wiki/Wikidata:Licensing). Not re-verified
  on the page today; the licence is long-standing and stated site-wide.
- Access: SPARQL endpoint https://query.wikidata.org/sparql (POST, JSON results) and, for resolving the curated
  seed names to Q-ids, the `wbsearchentities` API at https://www.wikidata.org/w/api.php. User-Agent
  `LedgerlineEvalDatasetBuild/0.1 (https://github.com/rajo69/Agentic_AI_Accounting)` (the dataset was formerly
  called `ledgerline`).
- Every record keeps its Q-id (`wikidata_qid`; for Wikidata-sourced records also `source_id`).

The metadata query (the only SPARQL query the build depends on). `%s` is replaced by up to 250 `wd:Q...`
values per request; the Q-id list is all NSI candidate Q-ids plus all seed Q-ids, sorted numerically, as
written by `build_brands.py qids`. On 2026-10-13 this was 2,295 Q-ids in 10 requests; the responses are saved
as `meta_000.json` to `meta_009.json` (kept in the build scratch area, not in the repo; sha256 of
`meta_000.json` is `433e22c2a549b31426c152ed781d44fe113c8f4661d9dad7e56a75a72703ad6b`, of `meta_009.json`
`7b4b80b8bc98c29704d0b4cbec728b8dbf1d8c4bfaf8a206935ff19a47af48b8`).

```sparql
SELECT ?item (SAMPLE(?sl0) AS ?sitelinks) (SAMPLE(?lab0) AS ?label)
       (MAX(?h) AS ?human) (MAX(?dis) AS ?dissolved)
       (GROUP_CONCAT(DISTINCT ?indL; separator="|") AS ?industries)
       (GROUP_CONCAT(DISTINCT ?cty; separator="|") AS ?countries) WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item wikibase:sitelinks ?sl0 . }
  OPTIONAL { ?item rdfs:label ?lab0 . FILTER(LANG(?lab0) = "en") }
  BIND(IF(EXISTS { ?item wdt:P31 wd:Q5 }, 1, 0) AS ?h)
  BIND(IF(EXISTS { ?item wdt:P576 [] }, 1, 0) AS ?dis)
  OPTIONAL { ?item wdt:P452 ?ind . ?ind rdfs:label ?indL . FILTER(LANG(?indL) = "en") }
  OPTIONAL { ?item wdt:P17 ?c . BIND(STRAFTER(STR(?c), "entity/") AS ?cty) }
}
GROUP BY ?item
```

Used for: `sitelinks` (prominence ranking within an NSI category), `human` (P31 = Q5 test), `dissolved`
(P576 test), `industries` (P452 labels, used as `category` for Wikidata-sourced records), `countries` (P17,
used in the home-brand test).

A class-based query was tried first and rejected (kept here for the record):

```sparql
SELECT ?item ?itemLabel ?cls ?country ?sl WHERE {
  VALUES ?cls { wd:Q46970 wd:Q2143354 wd:Q1941618 wd:Q2401749 wd:Q11371 wd:Q1326624 wd:Q11775260
                wd:Q1956140 wd:Q3390477 wd:Q1058914 wd:Q17102188 wd:Q848466 }
  VALUES ?country { wd:Q145 wd:Q30 }
  ?item wdt:P31 ?cls ; wdt:P17 ?country ; wikibase:sitelinks ?sl .
  FILTER(?sl >= 8)
  FILTER NOT EXISTS { ?item wdt:P576 [] }
  FILTER NOT EXISTS { ?item wdt:P582 [] }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

It returned stale or irrelevant entities (former UK train operators such as South West Trains and London
Midland with no dissolution date, cargo airlines, antivirus vendors) and missed most target brands, so the
Wikidata part uses curated seeds instead (section 2.2).

### 1.3 Descriptor hints

`descriptor_hint` is set only where a statement string for that brand was **observed** in one of the public sources
below during the dataset's research (the research notes themselves are not published). Strings that were only
typical or could not be verified are not used, and nothing observed only in unlicensed data (Oklahoma p-card) is
used. The string is copied as observed (case
and spacing kept, store numbers and references cut). `descriptor_hint_source` names the origin:

| Tag | Source | Licence |
|---|---|---|
| MV | MoneyVis bank transactions dataset, University of Nottingham, DOI 10.17632/dnxtg6n4rv.1 | CC BY 4.0 (attribution: Firat et al., EuroVis 2023) |
| PC | UK parish and town council published statements | none stated; only company-name forms are used (e.g. `EE LIMITED`, `TRAVIS PERKINS`) |
| DOC | vendor or bank documentation (Square, Stripe, Google Workspace, Cash App help) | quoted descriptor formats only |
| LA, DE, DEN | LA City Controller, Delaware and Denver p-card open data | public domain per portal tag |
| (other) | one UK hint (Apple) observed in a post on the Apple developer forum | a short descriptor string quoted as a fact |

UK records with a hint: 40 (31 tagged MV, one tagged DOC and MV). US records with a hint: 47. All other records
have `descriptor_hint: null`. `descriptor_hint_source` holds only the source tag from the table above.

## 2. Selection rules

### 2.1 NSI (national chains with shop fronts)

1. Categories: 47 NSI brand categories relevant to small-business spend (supermarket, wholesale, DIY,
   hardware, trade, electrical, paint, tool and plant hire, stationery, copy shop, electronics, fuel, EV
   charging, furniture, department and variety stores, catalogue, convenience, pharmacy, chemist, mobile phone
   and telecom shops, car parts, car repair, tyres, car rental, parking, cafe, fast food, restaurant, pub,
   hotel, bank, post office, post depot, parcel locker, logistics, insurance office, tax adviser, employment
   agency, coworking, self storage, craft, books, fitness). Each has a per-country cap in `NSI_CATEGORIES`.
2. Country scope (national only): an item qualifies for the UK if its `locationSet.include` contains `gb`, and
   for the US if it contains `us`, and the country is not in `exclude`. Items scoped only to sub-national
   areas (for example `us-ca.geojson`, `gb-sct`) are never used, which removes regional and local brands.
3. Home-brand test: the Wikidata P17 country of the item's Q-id must be the UK (Q145) or the US (Q30); if
   Wikidata gives no P17, every NSI include code must be in the home set (UK: gb ie im je gg; US: us ca pr gu vi
   as mp). This removes foreign brands with a handful of local branches (for example BNP Paribas, Nordea, ICICI
   in UK bank results).
4. Explicit allowlist (`GLOBAL_OK`, keyed by Q-id plus the expected NSI brand name): global chains that trade
   nationally in the country, scoped `001` (worldwide) or failing the P17 test, for example McDonald's, Shell,
   Lidl, Aldi, IKEA, Hilton, DHL in the UK, plus Toolstation in the UK because its descriptor is observed.
   Allowlisted items are always kept. A P17-only rule for `001` items was rejected because it admits brands that
   do not trade in the country (Esso in the US) and rejects global chains that do (McDonald's in the UK).
5. Ranking inside a category: Wikidata sitelinks, descending, then name; the first N home brands up to the cap
   are kept.
6. De-duplication: one record per Q-id per country (Wikidata seeds first, then NSI in category order), and within
   one category family a name that is a whole-word prefix of a kept name, or the reverse, is treated as a
   sub-brand (for example Asda Express, Halfords Autocentre, Budget Truck Rental).
7. Label check: an NSI item is dropped when its Wikidata English label shares no word with the NSI brand name,
   except for the listed abbreviations (NatWest, RBS, Three, UPS, Clarion Pointe, United Healthcare). This
   caught an NSI item reusing another brand's Q-id (Life Time tagged with WeWork's Q19995004) and a Wikidata
   item whose label no longer matches the brand (Q1472539, expected ManpowerGroup, labelled as an unrelated
   company on 2026-10-13); Manpower was removed from both lists for that reason.

### 2.2 Wikidata seeds (platforms and service companies without shop fronts)

Software and SaaS, accounting and payroll, payments, marketplaces, telecoms, energy and water utilities,
insurers, couriers, airlines, rail and coach operators, parking apps, ride hailing and food delivery, travel
booking, advertising and online banks. The names come from merchant tables compiled during research
from public sources, plus a fixed list of major payment, commerce and software platforms (Stripe, PayPal, Square,
SumUp, Zettle, Amazon, Shopify, Etsy, eBay, Uber, Deliveroo, Gusto, ADP, Intuit, Xero). Each name was resolved to a Q-id with
`wbsearchentities` on 2026-10-13 and checked by hand against the Wikidata description; the Q-ids are fixed in
`SEEDS` in the script. Notes on specific seeds:

- Square is recorded under Block, Inc. (Q110778747); Wikidata has no separate item for the Square payments brand.
- Slack uses the service item Q17130715; the company item Q7808625 carries a dissolution date.
- Worldpay uses Q7915220; the British company item Q2900982 carries a dissolution date.
- Vodafone and Three (UK) come from NSI; the Wikidata company items Q7939294 and Q19840922 carry dissolution
  dates (merger into VodafoneThree), while both brands still trade.
- UK train operators use the current franchise items where Wikidata has split them (for example Chiltern
  Railways Q139915897, Greater Anglia Q131717275, West Midlands Trains Q136418841, ScotRail Q107980329).
- US electricity utilities (PG&E, Con Edison and others) serve defined regions but are large companies, not
  local businesses; they are kept as the US utility family.

### 2.3 Exclusions applied to both sources

| Rule | Effect on 2026-10-13 |
|---|---|
| Wikidata P31 = Q5 (human) | 0 items matched; no person's name is in either list |
| Wikidata P576 (dissolved) | dropped Spirit Airlines, Sprint, Linde welding centres, 99 Cents Only, JOANN, A.C. Moore; Texaco and Amoco are exempt (`DISSOLVED_OK`) because the company items are dissolved but the fuel brands still trade |
| Government bodies (`GOVERNMENT_QIDS`) | USPS, Transport for London and the IRS are not companies; the generator handles government payees (HMRC, IRS, USPS, councils) with its own templates |
| Judgement deny list (`DENY`) | Debenhams and Laura Ashley (shops closed), Kmart and Sears (US estates almost entirely closed), b8ta (closed 2022), British Heart Foundation (charity shops), Jobcentre Plus (government), Clydebank Co-operative (local society), Buick and Karma Automotive (car makers listed as car repair) |
| No Q-id in NSI | item skipped |

Brands named after their founders (Sainsbury's, McDonald's, Harry Ramsden's, Wendy's) are kept: each is a
company with its own Wikidata item that is not an instance of human.

No names were taken from Food Standards Agency, council spend, Companies House, OpenStreetMap or card datasets
(personal-data and share-alike risks).

## 3. Record schema

Keys are sorted in each record; records are sorted by `category_family`, then `brand_id`.

| Field | Meaning |
|---|---|
| `brand_id` | stable slug, `uk-` or `us-` plus the ASCII-folded name (`&` becomes `and`) |
| `name` | brand name as NSI tags it, or the seed display name |
| `source` | `nsi` or `wikidata` |
| `source_id` | NSI item id, or the Wikidata Q-id |
| `wikidata_qid` | Wikidata Q-id (both sources) |
| `licence` | `BSD-3-Clause (name-suggestion-index)` or `CC0-1.0 (Wikidata)` |
| `category` | NSI tag (e.g. `amenity=fuel`), or Wikidata P452 industry labels joined by `; ` (seed family if P452 is empty) |
| `category_family` | coarse family used by the generator (e.g. `fuel`, `software_saas`, `courier_post`) |
| `country` | `UK` or `US` |
| `country_basis` | why the brand is in this country's list (NSI scope, home-brand test, allowlist, or curated seed) |
| `sitelinks` | Wikidata sitelink count at retrieval (the ranking signal) |
| `descriptor_hint` | observed statement form, or null (section 1.3) |
| `descriptor_hint_source` | where the hint was observed, or null |

## 4. Reproduce

Downloads go into a new empty folder each; the script runs with `-I` and is given paths as arguments.

```
py -3.13 -I build_brands.py qids  --nsi <dl>/nsi.json --out <work>/qids.txt
py -3.13 -I build_brands.py fetch --qids <work>/qids.txt --out-dir <dl>/wikidata_meta
py -3.13 -I build_brands.py build --nsi <dl>/nsi.json --wd-dir <dl>/wikidata_meta --out-dir <this folder>
```

`build` is deterministic (checked by building twice into separate folders on 2026-10-13: identical bytes).
Output hashes (sha256 of the LF bytes, after the 2026-10-15 change that publishes only the source tag in
`descriptor_hint_source`): `brands_uk.json`
`1661dc2ef4cf22856bab612c329cd7e6df49c070b8c7cfd841dded36dd0a7511`, `brands_us.json`
`c1ac9ade53583c59b8217c501969166116d762cbb07bc2ed8fe18f729ead947a`. A later `fetch` will return
current Wikidata values (sitelinks, labels, dissolution dates), so a rebuild from fresh responses can differ.

The brand selection (categories, caps, allowlist, deny list, seed list) and this file were drafted by Claude
Code (an AI coding assistant) on 2026-10-13 for review by the maintainer.

## 5. Other sources the dataset relies on

| Source | Licence | How it is used |
|---|---|---|
| MoneyVis bank transactions dataset: "Bank Transactions Dataset", Mendeley Data, version 1, University of Nottingham, DOI [10.17632/dnxtg6n4rv.1](https://doi.org/10.17632/dnxtg6n4rv.1). Paper: Elif E. Firat et al. (University of Nottingham), "MoneyVis: Open Bank Transaction Data for Visualization and Beyond", EuroVis 2023 Short Papers, pages 109 to 113, DOI 10.2312/evs.20231052 | CC BY 4.0 | Descriptor strings were extracted and used as the `descriptor_hint` of the UK brand records tagged MV in `brands_uk.json` (section 1.3). No transaction rows are redistributed. |
| HMRC and gov.uk guidance (including the HMRC internal manuals and the SA103F notes), legislation.gov.uk (Finance Act 2004 sections 61 and 62) and the ONS UK SIC 2007 classification | Open Government Licence v3.0 | Rule citations and short quotations in `guide_uk.md`; the SIC 2007 codes and labels in the UK firm profiles. |
| IRS forms, instructions, publications, notices and web pages; the Treasury Financial Manual; the Code of Federal Regulations and the US Code | US federal government works, public domain in the US (17 U.S.C. 105) | Rule citations and short quotations in `guide_us.md`; account names in `chart_us.json` follow the Schedule C wording. |
| US Census Bureau 2010 surname file (https://www2.census.gov/topics/genealogy/2010surnames/names.zip) | US federal government work, public domain | Exclusion filter only: an invented surname that is a real surname in the file is rejected. No name from the file is used. |
| dwyl/english-words `words_alpha.txt` (https://github.com/dwyl/english-words) | Unlicense (public domain dedication) | Exclusion filter only: an invented surname that is an English word is rejected. |
| sentence-transformers `all-MiniLM-L6-v2` | Apache License 2.0 | Used only to compute retrieval ranks that simulate which history precedents production would show. The model and its embeddings are not redistributed. |
| HMRC `reference-checker` (https://github.com/hmrc/reference-checker) | Apache License 2.0 | The check-digit logic for UK VAT numbers, UTRs and PAYE Accounts Office references is ported in the generator's `refs.py`, which uses it to make sure every synthetic tax reference fails the official check. |

Person payees in the data are an initial plus an invented surname from a generated pseudo-surname list (the generator's
`make_names.py`), filtered by the two exclusion sources above and against the brand names in this folder.

Required attribution for the Open Government Licence material: "Contains public sector information licensed under the
Open Government Licence v3.0." (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)

MoneyVis attribution: Firat, E. E. et al. (2023), "MoneyVis: Open Bank
Transaction Data for Visualization and Beyond", EuroVis 2023 Short Papers; dataset DOI 10.17632/dnxtg6n4rv.1,
licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). The descriptor strings were copied with store
numbers and references cut (section 1.3).
