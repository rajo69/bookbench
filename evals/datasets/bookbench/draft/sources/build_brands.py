"""Build licence-clean UK and US national brand lists for the bookbench eval dataset (named ledgerline when the lists were built).

Sources
  * Name Suggestion Index (NSI) dist/json/nsi.json, BSD-3-Clause.
  * Wikidata (CC0) via the SPARQL endpoint: one metadata query per chunk of Q-ids
    (sitelinks, English label, human check, dissolved check, industry, country).

Three steps, paths always passed as arguments; only `fetch` touches the network:

  py -3.13 -I build_brands.py qids  --nsi NSI_JSON --out QIDS_TXT
  py -3.13 -I build_brands.py fetch --qids QIDS_TXT --out-dir WD_DIR
  py -3.13 -I build_brands.py build --nsi NSI_JSON --wd-dir WD_DIR --out-dir OUT_DIR

`build` writes brands_uk.json, brands_us.json and one brands_<cc>_excluded.log per country (every
candidate dropped by a rule, with the reason). It is deterministic: the same nsi.json and the same
saved SPARQL responses give byte-identical output. Selection rules and provenance: ATTRIBUTION.md.
Downloaded files are data only; nothing downloaded is executed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

RETRIEVED = '2026-10-13'
NSI_LICENCE = 'BSD-3-Clause (name-suggestion-index)'
WD_LICENCE = 'CC0-1.0 (Wikidata)'
UA = 'LedgerlineEvalDatasetBuild/0.1 (https://github.com/rajo69/Agentic_AI_Accounting)'
CHUNK = 250

# --------------------------------------------------------------------------------------------
# NSI categories relevant to small-business spend: (nsi key, family, cap UK, cap US).
# Order is priority order for de-duplication (a brand is kept in the first category it reaches).
# --------------------------------------------------------------------------------------------
NSI_CATEGORIES = [
    ('shop/supermarket', 'groceries_supermarket', 6, 9),
    ('shop/wholesale', 'wholesale_club', 3, 4),
    ('shop/doityourself', 'diy_hardware_trade', 4, 4),
    ('shop/hardware', 'diy_hardware_trade', 2, 2),
    ('shop/trade', 'diy_hardware_trade', 3, 4),
    ('shop/electrical', 'diy_hardware_trade', 2, 2),
    ('shop/paint', 'diy_hardware_trade', 1, 2),
    ('shop/tool_hire', 'equipment_hire', 3, 0),
    ('shop/plant_hire', 'equipment_hire', 0, 4),
    ('shop/stationery', 'office_supplies_print', 3, 3),
    ('shop/copyshop', 'office_supplies_print', 2, 2),
    ('shop/electronics', 'electronics_it', 4, 2),
    ('shop/computer', 'electronics_it', 0, 1),
    ('amenity/fuel', 'fuel', 5, 4),
    ('amenity/charging_station', 'ev_charging', 2, 3),
    ('shop/furniture', 'furniture', 3, 3),
    ('shop/department_store', 'general_retail', 3, 3),
    ('shop/catalogue', 'general_retail', 1, 0),
    ('shop/variety_store', 'general_retail', 3, 3),
    ('shop/convenience', 'groceries_convenience', 4, 4),
    ('amenity/pharmacy', 'pharmacy_health', 4, 4),
    ('shop/chemist', 'pharmacy_health', 2, 2),
    ('shop/mobile_phone', 'telecom', 5, 3),
    ('shop/telecommunication', 'telecom', 1, 2),
    ('shop/car_parts', 'vehicle_parts_repair', 3, 4),
    ('shop/car_repair', 'vehicle_parts_repair', 3, 2),
    ('shop/tyres', 'vehicle_parts_repair', 1, 2),
    ('amenity/car_rental', 'car_rental', 5, 6),
    ('amenity/parking', 'parking', 1, 0),
    ('amenity/cafe', 'food_drink', 3, 3),
    ('amenity/fast_food', 'food_drink', 5, 6),
    ('amenity/restaurant', 'food_drink', 3, 3),
    ('amenity/pub', 'food_drink', 2, 0),
    ('tourism/hotel', 'hotel_accommodation', 3, 3),
    ('amenity/bank', 'bank', 4, 5),
    ('amenity/post_office', 'courier_post', 2, 2),
    ('amenity/post_depot', 'courier_post', 1, 1),
    ('amenity/parcel_locker', 'courier_post', 1, 1),
    ('office/logistics', 'courier_post', 0, 2),
    ('office/insurance', 'insurance', 2, 2),
    ('office/tax_advisor', 'accountancy_tax', 1, 2),
    ('office/employment_agency', 'recruitment', 2, 2),
    ('office/coworking', 'workspace', 1, 2),
    ('shop/storage_rental', 'storage', 3, 4),
    ('shop/craft', 'craft_supplies', 1, 3),
    ('shop/books', 'books', 1, 1),
    ('leisure/fitness_centre', 'fitness', 2, 3),
]

COUNTRIES = {'uk': ('gb', 'Q145'), 'us': ('us', 'Q30')}

# NSI items kept regardless of the per-category cap, keyed by Q-id with the expected NSI brand tag
# (guards against NSI items that reuse another brand's Q-id). Worldwide-scoped ("001") items are kept
# for a country ONLY when listed here (global chains that trade nationally there); a few home brands
# are listed because their descriptor is observed in the research notes. For 001 items a rule based
# on Wikidata P17 was tried and rejected: it
# admits brands headquartered in a country that do not trade there (Esso in the US) and rejects
# global chains that do (McDonald's in the UK). Checked against NSI 8.0.20260918 by name and Q-id.
GLOBAL_OK = {
    'uk': {
        'Q487494':    'Tesco',
        'Q151954':    'Lidl',
        'Q610492':    'Spar',
        'Q714491':    'Marks & Spencer',
        'Q152057':    'BP',
        'Q775060':    'Texaco',
        'Q867662':    'Esso',
        'Q110716465': 'Shell',
        'Q478214':    'Tesla',
        'Q37158':     'Starbucks',
        'Q608845':    'Costa',
        'Q38076':     "McDonald's",
        'Q177054':    'Burger King',
        'Q524757':    'KFC',
        'Q244457':    'Subway',
        'Q839466':    "Domino's",
        'Q191615':    'Pizza Hut',
        'Q598884':    'Hilton',
        'Q2717882':   'Holiday Inn',
        'Q830334':    'Best Western',
        'Q920166':    'Ibis',
        'Q3918608':   'Marriott',
        'Q489815':    'DHL',
        'Q459477':    'FedEx',
        'Q155026':    'UPS',
        'Q3884':      'Amazon',
        'Q190464':    'HSBC',
        'Q245343':    'Barclays',
        'Q1543874':   'Hertz',
        'Q791136':    'Avis',
        'Q17085454':  'Enterprise',
        'Q705664':    'Sixt',
        'Q1376256':   'Europcar',
        'Q1001437':   'Budget',
        'Q130240418': 'Regus',
        'Q19995004':  'WeWork',
        'Q41171672':  'Aldi',
        'Q54078':     'IKEA',
        'Q715583':    'Costco',
        'Q487292':    'Allianz',
        'Q407009':    'Three',
        'Q122141':    'Vodafone',
        'Q2109109':   'Pret A Manger',
        'Q503715':    'Wagamama',
        'Q1548712':   'WHSmith',
        'Q7824103':   'Toolstation',  # home brand; kept because its descriptor is observed in r2_uk.md section 5
    },
    'us': {
        'Q319642':    'Chevron',
        'Q775060':    'Texaco',
        'Q110716465': 'Shell',
        'Q152057':    'BP',
        'Q259340':    '7-Eleven',
        'Q3268010':   'Circle K',
        'Q478214':    'Tesla',
        'Q37158':     'Starbucks',
        'Q38076':     "McDonald's",
        'Q177054':    'Burger King',
        'Q524757':    'KFC',
        'Q244457':    'Subway',
        'Q839466':    "Domino's",
        'Q191615':    'Pizza Hut',
        'Q847743':    "Dunkin'",
        'Q550258':    "Wendy's",
        'Q1330910':   'Popeyes',
        'Q1141226':   'Dairy Queen',
        'Q1043486':   "Carl's Jr.",
        'Q1585088':   "Hardee's",
        'Q598884':    'Hilton',
        'Q2717882':   'Holiday Inn',
        'Q830334':    'Best Western',
        'Q1425063':   'Hyatt',
        'Q634831':    'Sheraton',
        'Q3918608':   'Marriott',
        'Q1543874':   'Hertz',
        'Q791136':    'Avis',
        'Q17085454':  'Enterprise',
        'Q705664':    'Sixt',
        'Q1001437':   'Budget',
        'Q489815':    'DHL',
        'Q459477':    'FedEx',
        'Q155026':    'UPS',
        'Q3884':      'Amazon',
        'Q857063':    'Citibank',
        'Q130240418': 'Regus',
        'Q19995004':  'WeWork',
        'Q41171672':  'Aldi',
        'Q54078':     'IKEA',
        'Q1337797':   'Office Depot',
    },
}

# Country-home test for NSI items not on GLOBAL_OK: the item's Wikidata country (P17) must be the
# country; when Wikidata gives no P17, every NSI include code must be in this home set.
HOME = {'uk': {'gb', 'ie', 'im', 'je', 'gg'}, 'us': {'us', 'ca', 'pr', 'gu', 'vi', 'as', 'mp'}}

# Wikidata marks the original company dissolved but the brand still trades on forecourts (NSI 2026).
DISSOLVED_OK = {
    'Q775060': 'Texaco: company merged into Chevron (P576) but the fuel brand still trades in the UK and US',
    'Q465952': 'Amoco: company merged into BP (P576) but the fuel brand still trades in the US',
}

# NSI brand names whose Wikidata English label shares no word with the name but is the same entity
# (abbreviation or operator name). Every other NSI item whose label shares no word with its name is
# dropped: this caught an NSI item reusing another brand's Q-id (Life Time tagged with WeWork's) and a
# Wikidata item whose label no longer matches the brand (Manpower, Q1472539, 2026-10-13).
LABEL_OK = {'NatWest', 'RBS', 'Three', 'UPS', 'Clarion Pointe', 'United Healthcare'}

# NSI entries removed by judgement, with the reason.
DENY = {
    'Q1181484': 'Debenhams: department stores closed in 2021 (online only)',
    'Q1523089': 'Laura Ashley: shops closed in 2020',
    'Q4970039': 'British Heart Foundation: a charity (charity shops), not a supplier brand',
    'Q6206793': 'Jobcentre Plus: government service',
    'Q5137069': 'Clydebank Co-operative: local co-operative society, not national',
    'Q1753080': 'Kmart: US store estate almost entirely closed',
    'Q6499202': 'Sears: US store estate almost entirely closed',
    'Q55604609': 'b8ta: closed in 2022',
    'Q27415': 'Buick: car marque (dealer network), not a service chain',
    'Q22671741': 'Karma Automotive: car maker, not a service chain',
}

# Brands excluded by rule, with the reason recorded in ATTRIBUTION.md.
GOVERNMENT_QIDS = {
    'Q668687': 'United States Postal Service: federal agency, not a company (generator uses a government-payee template)',
    'Q682520': 'Transport for London: local government body',
    'Q973587': 'Internal Revenue Service: government',
}

# --------------------------------------------------------------------------------------------
# Wikidata seeds: national platforms and service companies that NSI does not cover (no shop
# fronts). Names chosen from the merchant tables in notes/r2_uk.md section 5 and notes/r3_us.md
# section 5 plus the task's platform list; Q-ids resolved with wbsearchentities on 2026-10-13 and
# re-checked by the metadata query (not human, not dissolved).
# (country, family, display name, Q-id)
# --------------------------------------------------------------------------------------------
SEEDS = [
    # ---------------- shared platforms (both countries) ----------------
    *[(c, f, n, q) for c in ('uk', 'us') for (f, n, q) in [
        ('payments', 'Stripe', 'Q7624104'),
        ('payments', 'PayPal', 'Q483959'),
        ('payments', 'Square', 'Q110778747'),
        ('marketplace', 'Amazon', 'Q3884'),
        ('marketplace', 'eBay', 'Q58024'),
        ('marketplace', 'Etsy', 'Q1353939'),
        ('marketplace', 'Shopify', 'Q7501150'),
        ('ride_food_delivery', 'Uber', 'Q780442'),
        ('ride_food_delivery', 'Uber Eats', 'Q21462723'),
        ('travel_booking', 'Booking.com', 'Q4035313'),
        ('travel_booking', 'Airbnb', 'Q63327'),
        ('travel_booking', 'Expedia', 'Q1418432'),
        ('software_saas', 'Google Workspace', 'Q509284'),
        ('advertising', 'Google Ads', 'Q271982'),
        ('software_saas', 'Microsoft 365', 'Q775811'),
        ('software_saas', 'Adobe', 'Q11463'),
        ('software_saas', 'Apple', 'Q312'),
        ('software_saas', 'Amazon Web Services', 'Q456157'),
        ('software_saas', 'Zoom', 'Q17460900'),
        ('software_saas', 'Slack', 'Q17130715'),
        ('software_saas', 'Dropbox', 'Q142539'),
        ('software_saas', 'Canva', 'Q23498528'),
        ('software_saas', 'Mailchimp', 'Q6735673'),
        ('software_saas', 'Squarespace', 'Q7582097'),
        ('software_saas', 'Wix.com', 'Q420506'),
        ('software_saas', 'GoDaddy', 'Q1416215'),
        ('software_saas', 'HubSpot', 'Q5926631'),
        ('software_saas', 'Atlassian', 'Q757307'),
        ('software_saas', 'Docusign', 'Q5287613'),
        ('software_saas', 'Salesforce', 'Q941127'),
        ('software_saas', 'Calendly', 'Q111946817'),
        ('software_saas', 'LinkedIn', 'Q213660'),
        ('advertising', 'Meta Platforms', 'Q380'),
        ('advertising', 'Vistaprint', 'Q2128566'),
        ('advertising', 'Eventbrite', 'Q5416738'),
        ('accounting_payroll', 'Xero', 'Q8043794'),
        ('accounting_payroll', 'QuickBooks', 'Q7271951'),
        ('accounting_payroll', 'Intuit', 'Q1318848'),
        ('courier_post', 'DHL', 'Q489815'),
        ('courier_post', 'UPS', 'Q155026'),
        ('courier_post', 'FedEx', 'Q459477'),
        ('insurance', 'Hiscox', 'Q821058'),
    ]],
    # ---------------- UK ----------------
    ('uk', 'payments', 'SumUp', 'Q30589666'),
    ('uk', 'payments', 'Zettle', 'Q16325128'),
    ('uk', 'payments', 'GoCardless', 'Q111418549'),
    ('uk', 'payments', 'Wise', 'Q7833987'),
    ('uk', 'payments', 'Worldpay', 'Q7915220'),
    ('uk', 'marketplace', 'Vinted', 'Q11935495'),
    ('uk', 'ride_food_delivery', 'Deliveroo', 'Q22000919'),
    ('uk', 'ride_food_delivery', 'Just Eat', 'Q6315697'),
    ('uk', 'ride_food_delivery', 'Bolt', 'Q20529164'),
    ('uk', 'ride_food_delivery', 'Addison Lee', 'Q4681264'),
    ('uk', 'travel_booking', 'Trainline', 'Q7783585'),
    ('uk', 'accounting_payroll', 'Sage', 'Q1469903'),
    ('uk', 'accounting_payroll', 'FreeAgent', 'Q16992487'),
    ('uk', 'software_saas', '123 Reg', 'Q23680145'),
    ('uk', 'advertising', 'Yell', 'Q26389854'),
    ('uk', 'fintech_bank', 'Starling Bank', 'Q19903669'),
    ('uk', 'fintech_bank', 'Monzo', 'Q25206290'),
    ('uk', 'fintech_bank', 'Revolut', 'Q22908307'),
    ('uk', 'telecom', 'BT', 'Q593786'),
    ('uk', 'telecom', 'O2', 'Q7072245'),
    ('uk', 'telecom', 'Sky', 'Q2033167'),
    ('uk', 'telecom', 'Virgin Media', 'Q1199764'),
    ('uk', 'telecom', 'TalkTalk', 'Q3514518'),
    ('uk', 'telecom', 'Plusnet', 'Q7205652'),
    ('uk', 'telecom', 'giffgaff', 'Q5559900'),
    ('uk', 'utility_energy', 'British Gas', 'Q2925725'),
    ('uk', 'utility_energy', 'Octopus Energy', 'Q63242134'),
    ('uk', 'utility_energy', 'EDF', 'Q3045865'),
    ('uk', 'utility_energy', 'E.ON', 'Q3045727'),
    ('uk', 'utility_energy', 'OVO Energy', 'Q7114191'),
    ('uk', 'utility_energy', 'ScottishPower', 'Q1778417'),
    ('uk', 'utility_energy', 'Good Energy', 'Q5582545'),
    ('uk', 'utility_water', 'Severn Trent', 'Q503077'),
    ('uk', 'utility_water', 'Thames Water', 'Q2408951'),
    ('uk', 'utility_water', 'United Utilities', 'Q503038'),
    ('uk', 'utility_water', 'Anglian Water', 'Q4763422'),
    ('uk', 'utility_water', 'Yorkshire Water', 'Q8055763'),
    ('uk', 'utility_water', 'Welsh Water', 'Q7982011'),
    ('uk', 'utility_water', 'Water Plus', 'Q55394458'),
    ('uk', 'insurance', 'Simply Business', 'Q7520987'),
    ('uk', 'insurance', 'AXA', 'Q160054'),
    ('uk', 'insurance', 'Direct Line', 'Q5280285'),
    ('uk', 'insurance', 'Zurich', 'Q230426'),
    ('uk', 'insurance', 'Aviva', 'Q791179'),
    ('uk', 'insurance', 'LV=', 'Q140882580'),
    ('uk', 'insurance', 'Admiral', 'Q267417'),
    ('uk', 'insurance', 'NFU Mutual', 'Q6953815'),
    ('uk', 'courier_post', 'Royal Mail', 'Q638098'),
    ('uk', 'courier_post', 'Parcelforce', 'Q15077740'),
    ('uk', 'courier_post', 'DPD', 'Q137945677'),
    ('uk', 'courier_post', 'Evri', 'Q123762135'),
    ('uk', 'courier_post', 'InPost', 'Q3182097'),
    ('uk', 'courier_post', 'Yodel', 'Q17020712'),
    ('uk', 'airline', 'British Airways', 'Q8766'),
    ('uk', 'airline', 'easyJet', 'Q191551'),
    ('uk', 'airline', 'Ryanair', 'Q170614'),
    ('uk', 'airline', 'Jet2.com', 'Q1140807'),
    ('uk', 'airline', 'Virgin Atlantic', 'Q32277'),
    ('uk', 'airline', 'Loganair', 'Q934983'),
    ('uk', 'rail_coach', 'LNER', 'Q53649859'),
    ('uk', 'rail_coach', 'Avanti West Coast', 'Q68441695'),
    ('uk', 'rail_coach', 'Great Western Railway', 'Q1419438'),
    ('uk', 'rail_coach', 'CrossCountry', 'Q1141120'),
    ('uk', 'rail_coach', 'Northern', 'Q85789775'),
    ('uk', 'rail_coach', 'TransPennine Express', 'Q119806220'),
    ('uk', 'rail_coach', 'Southeastern', 'Q1696490'),
    ('uk', 'rail_coach', 'ScotRail', 'Q107980329'),
    ('uk', 'rail_coach', 'Transport for Wales Rail', 'Q104878180'),
    ('uk', 'rail_coach', 'East Midlands Railway', 'Q65090907'),
    ('uk', 'rail_coach', 'Chiltern Railways', 'Q139915897'),
    ('uk', 'rail_coach', 'Greater Anglia', 'Q131717275'),
    ('uk', 'rail_coach', 'West Midlands Trains', 'Q136418841'),
    ('uk', 'rail_coach', 'Lumo', 'Q24993335'),
    ('uk', 'rail_coach', 'Eurostar', 'Q156013'),
    ('uk', 'rail_coach', 'National Express', 'Q13479582'),
    ('uk', 'parking', 'RingGo', 'Q7334684'),
    ('uk', 'parking', 'JustPark', 'Q17143517'),
    ('uk', 'parking', 'PayByPhone', 'Q16669343'),
    # ---------------- US ----------------
    ('us', 'payments', 'Venmo', 'Q24839341'),
    ('us', 'payments', 'Cash App', 'Q55633750'),
    ('us', 'payments', 'Zelle', 'Q22907300'),
    ('us', 'payments', 'Toast', 'Q25025312'),
    ('us', 'payments', 'Clover', 'Q16988376'),
    ('us', 'ride_food_delivery', 'Lyft', 'Q17077936'),
    ('us', 'ride_food_delivery', 'DoorDash', 'Q20714323'),
    ('us', 'ride_food_delivery', 'Grubhub', 'Q17019647'),
    ('us', 'ride_food_delivery', 'Instacart', 'Q22909236'),
    ('us', 'travel_booking', 'Vrbo', 'Q17091141'),
    ('us', 'accounting_payroll', 'Gusto', 'Q20540697'),
    ('us', 'accounting_payroll', 'ADP', 'Q489080'),
    ('us', 'accounting_payroll', 'Paychex', 'Q946080'),
    ('us', 'accounting_payroll', 'FreshBooks', 'Q5502916'),
    ('us', 'accounting_payroll', 'Wave', 'Q7975268'),
    ('us', 'accounting_payroll', 'Bill.com', 'Q106221738'),
    ('us', 'software_saas', 'Twilio', 'Q7858039'),
    ('us', 'software_saas', 'Constant Contact', 'Q5163620'),
    ('us', 'software_saas', 'Bluehost', 'Q4930366'),
    ('us', 'advertising', 'Yelp', 'Q2299611'),
    ('us', 'electronics_it', 'B&H Photo Video', 'Q2919722'),
    ('us', 'electronics_it', 'Dell', 'Q27500963'),
    ('us', 'telecom', 'AT&T', 'Q35476'),
    ('us', 'telecom', 'Verizon', 'Q467752'),
    ('us', 'telecom', 'T-Mobile', 'Q3511885'),
    ('us', 'telecom', 'Xfinity', 'Q5151002'),
    ('us', 'telecom', 'Spectrum', 'Q7805197'),
    ('us', 'telecom', 'Cox Communications', 'Q5179879'),
    ('us', 'telecom', 'Frontier Communications', 'Q2974454'),
    ('us', 'utility_energy', 'PG&E', 'Q1815011'),
    ('us', 'utility_energy', 'Southern California Edison', 'Q1706317'),
    ('us', 'utility_energy', 'Con Edison', 'Q1127536'),
    ('us', 'utility_energy', 'Duke Energy', 'Q1264404'),
    ('us', 'utility_energy', 'Florida Power & Light', 'Q1430055'),
    ('us', 'utility_energy', 'Georgia Power', 'Q5547666'),
    ('us', 'utility_energy', 'Dominion Energy', 'Q677464'),
    ('us', 'utility_energy', 'ComEd', 'Q2986833'),
    ('us', 'utility_energy', 'Xcel Energy', 'Q1486956'),
    ('us', 'insurance', 'State Farm', 'Q2007336'),
    ('us', 'insurance', 'GEICO', 'Q1498689'),
    ('us', 'insurance', 'Progressive', 'Q7248721'),
    ('us', 'insurance', 'Allstate', 'Q2645636'),
    ('us', 'insurance', 'Liberty Mutual', 'Q1516450'),
    ('us', 'insurance', 'Nationwide', 'Q6979886'),
    ('us', 'insurance', 'Next Insurance', 'Q105724944'),
    ('us', 'insurance', 'The Hartford', 'Q444110'),
    ('us', 'insurance', 'Travelers', 'Q942471'),
    ('us', 'insurance', 'Farmers Insurance', 'Q1396863'),
    ('us', 'airline', 'Delta Air Lines', 'Q188920'),
    ('us', 'airline', 'United Airlines', 'Q174769'),
    ('us', 'airline', 'American Airlines', 'Q32396'),
    ('us', 'airline', 'Southwest Airlines', 'Q503308'),
    ('us', 'airline', 'JetBlue', 'Q161086'),
    ('us', 'airline', 'Alaska Airlines', 'Q822614'),
    ('us', 'airline', 'Spirit Airlines', 'Q1190598'),
    ('us', 'airline', 'Frontier Airlines', 'Q1139541'),
    ('us', 'rail_coach', 'Amtrak', 'Q23239'),
]

# --------------------------------------------------------------------------------------------
# Descriptor hints: ONLY strings observed verbatim in a public source recorded in the research
# notes (r2_uk.md sections 3.4 and 5, r3_us.md sections 3.3 to 3.5 and 5). Forms marked typical
# or unverified in the notes are NOT used. Key: (country, brand display name as emitted).
# Value: (hint, source tag). Source tags: MV = MoneyVis CC BY 4.0 (r2 4.1); PC = UK parish or
# council statement, reading reference (r2 4.2); DOC = vendor or bank documentation; LA = LA
# City Controller p-card data, public domain; DE = Delaware p-card data, public domain;
# DEN = Denver p-card data, public domain.
# --------------------------------------------------------------------------------------------
HINTS = {
    ('uk', 'Amazon'): ('AMZNMktplace', 'MV via r2_uk.md 3.4'),
    ('uk', 'Google Workspace'): ('GOOGLE *GSUITE_', 'DOC Google Workspace help via r2_uk.md 3.4'),
    ('uk', 'Uber'): ('UBER   *TRIP', 'MV via r2_uk.md 3.4'),
    ('uk', 'Square'): ('SQ *', 'DOC Square docs and MV via r2_uk.md 3.4'),
    ('uk', 'PayPal'): ('PAYPAL PAYMENT', 'MV via r2_uk.md 3.4'),
    ('uk', 'SumUp'): ('SUMUP  *', 'MV via r2_uk.md 3.4'),
    ('uk', 'Zettle'): ('IZ *', 'MV via r2_uk.md 3.4'),
    ('uk', 'Stripe'): ('STRIPE PAYMENTS UK STRIPE', 'PC via r2_uk.md 3.4 and 5'),
    ('uk', 'EE'): ('EE LIMITED', 'PC via r2_uk.md 5'),
    ('uk', 'O2'): ('O2', 'MV via r2_uk.md 5'),
    ('uk', 'Virgin Media'): ('VIRGIN MEDIA PYMTS', 'MV via r2_uk.md 5'),
    ('uk', 'TalkTalk'): ('TALKTALK LIMITED', 'MV via r2_uk.md 5'),
    ('uk', 'Plusnet'): ('PLUSNET PLC PAY AC', 'MV via r2_uk.md 5'),
    ('uk', 'ScottishPower'): ('SCOTTISHPOWER', 'PC via r2_uk.md 5'),
    ('uk', 'Octopus Energy'): ('OCTOPUS ENERGY', 'MV via r2_uk.md 5'),
    ('uk', 'Good Energy'): ('GOOD ENERGY LTD', 'MV via r2_uk.md 5'),
    ('uk', 'Severn Trent'): ('SEVERN TRENT WATER', 'MV via r2_uk.md 5'),
    ('uk', 'Welsh Water'): ('DWR CYMRU W WATER', 'MV via r2_uk.md 5'),
    ('uk', 'Water Plus'): ('WATERPLUS', 'PC via r2_uk.md 5'),
    ('uk', 'Great Western Railway'): ('GWR WEBSALES', 'MV via r2_uk.md 5'),
    ('uk', 'East Midlands Railway'): ('EAST MIDS RAILWAY', 'MV via r2_uk.md 5'),
    ('uk', 'Transport for Wales Rail'): ('TFW RAIL SERVICES', 'MV via r2_uk.md 5'),
    ('uk', 'Ryanair'): ('RYANAIR', 'MV via r2_uk.md 5'),
    ('uk', 'Booking.com'): ('Hotel on Booking.c', 'MV via r2_uk.md 5'),
    ('uk', 'Hilton'): ('HILTON HOTELS', 'MV via r2_uk.md 5'),
    ('uk', 'Post Office'): ('POST OFFICE COUNTE', 'MV via r2_uk.md 5'),
    ('uk', 'WHSmith'): ('WH SMITH', 'MV via r2_uk.md 5'),
    ('uk', 'IKEA'): ('IKEA LTD SHOP ONLI', 'MV via r2_uk.md 3.3 and 5'),
    ('uk', 'Toolstation'): ('TOOLSTATION LTD', 'PC via r2_uk.md 5'),
    ('uk', 'Travis Perkins'): ('TRAVIS PERKINS', 'PC via r2_uk.md 5'),
    ('uk', 'Zurich'): ('ZURICH', 'MV via r2_uk.md 5'),
    ('uk', 'Greggs'): ('GREGGS PLC', 'MV via r2_uk.md 5'),
    ('uk', 'Pret A Manger'): ('PRET A MANGER', 'MV via r2_uk.md 5'),
    ('uk', 'Starbucks'): ('STARBUCKS', 'MV via r2_uk.md 5'),
    ('uk', 'Caffè Nero'): ('CAFFE NERO', 'MV via r2_uk.md 5'),
    ('uk', 'Deliveroo'): ('DELIVEROOCOUK', 'MV via r2_uk.md 5'),
    ('uk', 'PizzaExpress'): ('PIZZA EXPRESS', 'MV via r2_uk.md 5'),
    ('uk', 'Wagamama'): ('WAGAMAMA', 'MV via r2_uk.md 5'),
    ('uk', 'Subway'): ('Subway', 'MV via r2_uk.md 5'),
    ('uk', 'Apple'): ('APPLE.COM/BILL', 'Apple developer forum via r2_uk.md 3.4'),
    ('us', 'Staples'): ('STAPLES', 'LA via r3_us.md 3.3'),
    ('us', 'Office Depot'): ('OFFICE DEPOT #', 'LA via r3_us.md 3.3'),
    ('us', 'The UPS Store'): ('THE UPS STORE', 'LA via r3_us.md 3.3'),
    ('us', 'FedEx Office'): ('FEDEX OFFIC', 'LA via r3_us.md 3.3'),
    ('us', 'Google Workspace'): ('GOOGLE  GSUITE_', 'LA via r3_us.md 3.3'),
    ('us', 'Microsoft 365'): ('Microsoft Subscription', 'LA via r3_us.md 3.3'),
    ('us', 'Adobe'): ('ADOBE ACROPRO SUBS', 'LA via r3_us.md 3.3'),
    ('us', 'Zoom'): ('ZOOM.US', 'LA via r3_us.md 3.3'),
    ('us', 'Dropbox'): ('DROPBOX', 'LA via r3_us.md 3.3'),
    ('us', 'Canva'): ('CANVA', 'LA via r3_us.md 3.3'),
    ('us', 'Intuit'): ('INTUIT *', 'DE via r3_us.md 3.3'),
    ('us', 'Twilio'): ('TWILIO INC', 'DEN via r3_us.md 3.3'),
    ('us', 'GoDaddy'): ('DNH GODADDY.COM', 'LA via r3_us.md 3.3'),
    ('us', 'Wix.com'): ('WIX.COM', 'LA via r3_us.md 3.3'),
    ('us', 'Squarespace'): ('SQUARESPACE INC.', 'LA via r3_us.md 3.3'),
    ('us', 'Mailchimp'): ('MAILCHIMP', 'LA via r3_us.md 5'),
    ('us', 'Constant Contact'): ('EIG CONSTANTCONTACT.CO', 'LA via r3_us.md 3.3'),
    ('us', 'Meta Platforms'): ('FACEBK', 'LA via r3_us.md 3.3'),
    ('us', 'Vistaprint'): ('VISTAPRINT', 'LA via r3_us.md 3.3'),
    ('us', 'Eventbrite'): ('EB ADS CAMPAIGN', 'LA via r3_us.md 5'),
    ('us', 'Starbucks'): ('STARBUCKS STORE', 'LA via r3_us.md 3.3'),
    ('us', 'DoorDash'): ('DD DOORDASH', 'LA via r3_us.md 3.3'),
    ('us', 'Uber Eats'): ('UBER   EATS', 'LA via r3_us.md 3.3'),
    ('us', 'Grubhub'): ('GRUBHUB', 'LA via r3_us.md 3.3'),
    ('us', 'Toast'): ('TST*', 'DE via r3_us.md 3.3'),
    ('us', 'Chevron'): ('CHEVRON', 'LA via r3_us.md 3.3'),
    ('us', 'Shell'): ('SHELL OIL', 'LA via r3_us.md 3.3'),
    ('us', 'AutoZone'): ('AUTOZONE #', 'DE via r3_us.md 3.3'),
    ('us', 'The Home Depot'): ('THE HOME DEPOT #', 'LA via r3_us.md 3.3'),
    ("us", "Lowe's"): ('LOWES #', 'DE via r3_us.md 3.3'),
    ('us', "Sam's Club"): ('SAMSCLUB #', 'LA via r3_us.md 5'),
    ('us', 'Walmart'): ('WAL-MART #', 'LA via r3_us.md 5'),
    ('us', 'Target'): ('TARGET', 'LA via r3_us.md 3.3'),
    ('us', 'Costco'): ('WWW COSTCO COM', 'LA via r3_us.md 5'),
    ('us', 'Spectrum'): ('SPECTRUM', 'LA via r3_us.md 3.3'),
    ('us', 'AT&T'): ('AT&T PAYMENT', 'LA via r3_us.md 3.3'),
    ('us', 'Verizon'): ('VERIZON ONEPOS', 'LA via r3_us.md 5'),
    ('us', 'T-Mobile'): ('T-MOBILE STORE #', 'LA via r3_us.md 5'),
    ('us', 'Apple'): ('APPLE.COM/BILL', 'LA via r3_us.md 3.3'),
    ('us', 'CVS Pharmacy'): ('CVS/PHARMACY #', 'LA via r3_us.md 3.3'),
    ('us', 'Walgreens'): ('WALGREENS #', 'LA via r3_us.md 5'),
    ('us', 'Square'): ('SQ *', 'DOC Square developer docs and DE via r3_us.md 3.3'),
    ('us', 'PayPal'): ('PAYPAL *', 'DE via r3_us.md 3.3'),
    ('us', 'Amazon'): ('AMZN Mktp US', 'LA and DEN via r3_us.md 3.3'),
    ('us', 'Cash App'): ('Cash App*', 'DOC Cash App help via r3_us.md 3.4'),
    ('us', 'Stripe'): ('STRIPE', 'DOC Stripe payout docs via r3_us.md 3.5'),
    ('us', 'Uber'): ('UBER   TRIP', 'LA via r3_us.md 5'),
}


def slug(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = s.replace('&', ' and ').replace('+', ' plus ')
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def location_codes(it: dict) -> tuple[set, set]:
    ls = it.get('locationSet', {})
    inc = {x for x in ls.get('include', []) if isinstance(x, str)}
    exc = {x for x in ls.get('exclude', []) if isinstance(x, str)}
    return inc, exc


def load_nsi(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def nsi_candidates(nsi: dict):
    """Yield (category, item) for NSI brand items in the selected categories scoped gb/us/001."""
    tree = nsi['nsi']
    for cat, *_ in NSI_CATEGORIES:
        node = tree.get('brands/' + cat)
        if not node:
            continue
        for it in node['items']:
            inc, _ = location_codes(it)
            if inc & {'gb', 'us', '001'}:
                yield cat, it


def item_qid(it: dict) -> str | None:
    q = it.get('tags', {}).get('brand:wikidata')
    if not q:
        return None
    return q.split(';')[0].strip()


# ------------------------------------------------------------------ subcommands

def cmd_qids(a):
    nsi = load_nsi(Path(a.nsi))
    q = {item_qid(it) for _, it in nsi_candidates(nsi)} - {None}
    q |= {s[3] for s in SEEDS}
    Path(a.out).write_text('\n'.join(sorted(q, key=lambda x: int(x[1:]))) + '\n', encoding='utf-8')
    print(f'{len(q)} Q-ids -> {a.out}')


META_QUERY = """SELECT ?item (SAMPLE(?sl0) AS ?sitelinks) (SAMPLE(?lab0) AS ?label)
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
"""


def cmd_fetch(a):
    qids = [l.strip() for l in Path(a.qids).read_text(encoding='utf-8').splitlines() if l.strip()]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(qids), CHUNK):
        n = i // CHUNK
        q = META_QUERY % ' '.join('wd:' + x for x in qids[i:i + CHUNK])
        (out / f'meta_{n:03d}.rq').write_text(q, encoding='utf-8')
        body = urllib.parse.urlencode({'query': q, 'format': 'json'}).encode()
        req = urllib.request.Request('https://query.wikidata.org/sparql', data=body, headers={
            'User-Agent': UA, 'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded'})
        data = urllib.request.urlopen(req, timeout=110).read()
        (out / f'meta_{n:03d}.json').write_bytes(data)
        print(f'chunk {n}: {len(data)} bytes')
        time.sleep(2)


def load_meta(wd_dir: Path) -> dict:
    meta = {}
    for p in sorted(wd_dir.glob('meta_*.json')):
        for b in json.loads(p.read_text(encoding='utf-8'))['results']['bindings']:
            q = b['item']['value'].rsplit('/', 1)[-1]
            g = lambda k: b.get(k, {}).get('value', '')
            meta[q] = {
                'sitelinks': int(g('sitelinks') or 0),
                'label': g('label'),
                'human': g('human') == '1',
                'dissolved': g('dissolved') == '1',
                'industries': sorted(x for x in g('industries').split('|') if x),
                'countries': sorted(x for x in g('countries').split('|') if x),
            }
    return meta


def word_prefix(a: str, b: str) -> bool:
    """True when normalised a is a whole-word prefix of normalised b (or equal)."""
    a, b = norm(a), norm(b)
    return b == a or b.startswith(a + ' ')


def cmd_build(a):
    nsi = load_nsi(Path(a.nsi))
    meta = load_meta(Path(a.wd_dir))
    out_dir = Path(a.out_dir)
    log = {'uk': [], 'us': []}
    nsi_meta = nsi.get('_meta', {})

    for cc, (iso, country_q) in COUNTRIES.items():
        rows, seen_q, seen_names = [], set(), []

        def excluded(q: str, name: str) -> str | None:
            m = meta.get(q)
            if m is None:
                return 'no Wikidata metadata returned'
            if m['human']:
                return 'Wikidata item is a human (Q5)'
            if m['dissolved'] and q not in DISSOLVED_OK:
                return 'Wikidata item has a dissolution date (P576)'
            if q in DENY:
                return DENY[q]
            if q in GOVERNMENT_QIDS:
                return GOVERNMENT_QIDS[q]
            return None

        # ---- Wikidata seeds first (curated family wins over an NSI shop category)
        for scc, family, name, q in SEEDS:
            if scc != cc:
                continue
            why = excluded(q, name)
            if why:
                log[cc].append(f'wikidata {q} {name}: {why}')
                continue
            if q in seen_q:
                log[cc].append(f'wikidata {q} {name}: duplicate seed')
                continue
            seen_q.add(q)
            seen_names.append((name, family))
            m = meta[q]
            rows.append({
                'brand_id': f'{cc}-{slug(name)}',
                'name': name,
                'source': 'wikidata',
                'source_id': q,
                'wikidata_qid': q,
                'licence': WD_LICENCE,
                'category': '; '.join(m['industries']) if m['industries'] else family.replace('_', ' '),
                'category_family': family,
                'country': cc.upper(),
                'country_basis': 'curated seed (notes r2/r3 section 5)',
                'sitelinks': m['sitelinks'],
            })

        # ---- NSI
        for cat, family, cap_uk, cap_us in NSI_CATEGORIES:
            cap = cap_uk if cc == 'uk' else cap_us
            if cap == 0:
                continue
            node = nsi['nsi'].get('brands/' + cat)
            if not node:
                continue
            cands = []
            for it in node['items']:
                inc, exc = location_codes(it)
                q = item_qid(it)
                name = it.get('tags', {}).get('brand') or it.get('displayName')
                if not q or not name:
                    continue
                if iso in exc or not (iso in inc or '001' in inc):
                    continue  # other countries, or sub-national scope only (us-ca.geojson, gb-sct)
                m = meta.get(q, {})
                if GLOBAL_OK[cc].get(q) == name:
                    basis = 'allowlist ' + ('001' if iso not in inc else iso)
                elif iso in inc and (country_q in m.get('countries', []) or
                                     (not m.get('countries') and inc <= HOME[cc])):
                    basis = iso + ' home brand'
                else:
                    continue
                cands.append((-meta.get(q, {}).get('sitelinks', 0), norm(name), q, it['id'], name, it, basis))
            taken = 0
            for _, _, q, _, name, it, basis in sorted(cands, key=lambda c: c[:4]):
                allow = basis.startswith('allowlist')
                if taken >= cap and not allow:
                    continue
                why = excluded(q, name)
                if why:
                    log[cc].append(f'nsi {it["id"]} {name} ({q}): {why}')
                    continue
                lab = set(norm(meta[q]['label']).split()) - {'the'}
                if lab and not (lab & (set(norm(name).split()) - {'the'})) and name not in LABEL_OK:
                    log[cc].append(f'nsi {it["id"]} {name} ({q}): Wikidata label "{meta[q]["label"]}" does not match the name')
                    continue
                if q in seen_q:
                    log[cc].append(f'nsi {it["id"]} {name} ({q}): already kept (seed or earlier category)')
                    continue
                if any(f == family and (word_prefix(s, name) or word_prefix(name, s)) for s, f in seen_names):
                    log[cc].append(f'nsi {it["id"]} {name} ({q}): sub-brand or duplicate name of a kept brand')
                    continue
                seen_q.add(q)
                seen_names.append((name, family))
                taken += 0 if allow else 1
                rows.append({
                    'brand_id': f'{cc}-{slug(name)}',
                    'name': name,
                    'source': 'nsi',
                    'source_id': it['id'],
                    'wikidata_qid': q,
                    'licence': NSI_LICENCE,
                    'category': cat.replace('/', '='),
                    'category_family': family,
                    'country': cc.upper(),
                    'country_basis': f'nsi locationSet, {basis}',
                    'sitelinks': meta[q]['sitelinks'],
                })

        # ---- hints, uniqueness, sort
        ids = {}
        for r in rows:
            h = HINTS.get((cc, r['name']))
            r['descriptor_hint'] = h[0] if h else None
            # The hint tables cite the research notes they came from; only the source tag is published.
            r['descriptor_hint_source'] = re.sub(r' via r\d_u[ks]\.md [\d.]+(?: and [\d.]+)?$', '', h[1]) if h else None
            if r['brand_id'] in ids:
                r['brand_id'] += '-' + r['wikidata_qid'].lower()
            ids[r['brand_id']] = 1
        rows.sort(key=lambda r: (r['category_family'], r['brand_id']))
        rows = [{k: r[k] for k in sorted(r)} for r in rows]
        (out_dir / f'brands_{cc}.json').write_text(
            json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (out_dir / f'brands_{cc}_excluded.log').write_text('\n'.join(log[cc]) + '\n', encoding='utf-8')
        fam = {}
        for r in rows:
            fam[r['category_family']] = fam.get(r['category_family'], 0) + 1
        print(cc, len(rows), 'nsi', sum(r['source'] == 'nsi' for r in rows),
              'wikidata', sum(r['source'] == 'wikidata' for r in rows),
              'hints', sum(r['descriptor_hint'] is not None for r in rows))
        print('  ', json.dumps(fam, sort_keys=True))
    print('nsi version', nsi_meta.get('version'), nsi_meta.get('generated'))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('qids'); s.add_argument('--nsi', required=True); s.add_argument('--out', required=True)
    s.set_defaults(fn=cmd_qids)
    s = sub.add_parser('fetch'); s.add_argument('--qids', required=True); s.add_argument('--out-dir', required=True)
    s.set_defaults(fn=cmd_fetch)
    s = sub.add_parser('build'); s.add_argument('--nsi', required=True); s.add_argument('--wd-dir', required=True)
    s.add_argument('--out-dir', required=True)
    s.set_defaults(fn=cmd_build)
    a = p.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    a.fn(a)


if __name__ == '__main__':
    main()
