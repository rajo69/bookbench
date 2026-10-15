"""US merchant catalogue and firm profiles (source of truth for catalogue_us.json and the US half of firms.json).

Brand merchants link to `sources/brands_us.json`. Every other name is invented; government payees (IRS, state
revenue agencies, USPS) use kind `government`. All dates are in tax year 2025 (guide_us.md).

v0.2: account 720 Other business expenses (Part V) for staff parties (US-R014), de minimis capital purchases at
electing firms (US-R050) and contract late-performance penalties (US-R194); consumables stay 670 (D62 P2).
F8: `amount_mode="fixed"` on rent, loan instalments, phone and internet lines, monthly software, insurance premiums,
vehicle leases and the monthly bookkeeping fee; `amount_mode="round"` on loan proceeds. Loan, lease, policy and
utility account references use the {K<n>} token, so they stay constant per firm and payee.
Audit round 2: small sellers billed through Square, PayPal and Toast (`category="small_seller"`, shortcut S-1);
dues, refund, membership and card payment memos name the payee (F2, F5); donations round (R11); client meals at
restaurants and coffee shops only, LLC work only at LLCs (R16); payroll sized per person (R18, `payroll_amount`).
"""

from __future__ import annotations

import random
from decimal import Decimal

from .spec_common import U, make_builders

B, I = make_builders("US")

MERCHANTS: list[dict] = []
CUSTOMER_TRADES = {
    "silver-birch-dental": ["construction", "professional", "creative", "trades"],
    "prairie-wind-realty": ["creative", "professional", "construction", "trades"],
    "lakeside-montessori": ["education", "catering", "construction", "creative", "trades"],
    "ironwood-property-mgmt": ["construction", "trades", "professional"],
    "bayview-veterinary": ["professional", "creative", "construction", "trades", "catering"],
    "crescent-moon-yoga": ["creative", "professional", "education", "retail", "crafts"],
    "timberline-outfitters": ["crafts", "retail", "creative", "professional", "catering"],
    "bramblewood-credit-union": ["professional", "creative", "construction", "education", "retail", "catering", "crafts", "trades"],
}

_SAAS = [
    ("us-google-workspace", ["Google Workspace", "Google"], ["GOOGLE  GSUITE_{A6} 650-253-0000 CA"], ["Google Workspace licenses", "Email and docs subscription"], "7.00", "90.00"),
    ("us-microsoft-365", ["Microsoft"], ["Microsoft Subscription Redmond WA"], ["Microsoft 365 Business", "Office licenses"], "6.00", "70.00"),
    ("us-adobe", ["Adobe"], ["ADOBE ACROPRO SUBS 4085366000 CA", "ADOBE *CREATIVE CLD"], ["Creative Cloud", "Acrobat Pro"], "14.00", "90.00"),
    ("us-canva", ["Canva"], ["CANVA  I0{N4}-{N7} CAMDEN DE"], ["Canva Pro"], "12.00", "40.00"),
    ("us-zoom", ["Zoom"], ["ZOOM.US 888-799-9666 SAN JOSE CA"], ["Zoom Pro"], "14.00", "40.00"),
    ("us-dropbox", ["Dropbox"], ["DROPBOX {A12} DROPBOX.COM CA"], ["Dropbox Business", "Cloud storage"], "11.00", "60.00"),
    ("us-squarespace", ["Squarespace"], ["SQUARESPACE INC. NEW YORK NY"], ["Website plan", "Squarespace annual plan"], "16.00", "280.00"),
    ("us-wix-com", ["Wix"], ["WIX.COM {N10} SAN FRANCISCO CA"], ["Website premium plan"], "17.00", "250.00"),
    ("us-godaddy", ["GoDaddy"], ["DNH GODADDY.COM 480-505-8855 AZ"], ["Domain renewal", "Hosting and domain"], "12.00", "180.00"),
    ("us-bluehost", ["Bluehost"], ["BLUEHOST.COM"], ["Web hosting"], "10.00", "160.00"),
    ("us-slack", ["Slack"], ["SLACK T0{A6}"], ["Slack Pro"], "8.00", "60.00"),
    ("us-atlassian", ["Atlassian"], ["ATLASSIAN {A6}"], ["Jira and Confluence"], "8.00", "90.00"),
    ("us-twilio", ["Twilio"], ["TWILIO INC"], ["SMS reminders service", "Twilio usage"], "5.00", "80.00"),
    ("us-calendly", ["Calendly"], ["CALENDLY"], ["Scheduling software"], "10.00", "20.00"),
    ("us-docusign", ["Docusign"], ["DOCUSIGN INC"], ["E-signature plan"], "10.00", "45.00"),
    ("us-hubspot", ["HubSpot"], ["HUBSPOT {N8}"], ["CRM Starter"], "20.00", "100.00"),
    ("us-quickbooks", ["QuickBooks", "Intuit"], ["INTUIT *QBooks Online CL.INTUIT.COM CA", "INTUIT *"], ["QuickBooks Online", "Bookkeeping software"], "30.00", "90.00"),
    ("us-amazon-web-services", ["Amazon Web Services", "AWS"], ["AWS EMEA SARL", "Amazon web services aws.amazon.co WA"], ["Cloud hosting"], "4.00", "160.00"),
]
# Usage-billed services vary month to month; every other plan is a fixed monthly subscription (F8).
_USAGE_BILLED = {"us-twilio", "us-amazon-web-services"}
for bid, contacts, narrs, lines, lo, hi in _SAAS:
    MERCHANTS.append(B(bid, contacts, narrs, [U("software", "spend", lo, hi, "705", "US-R150", lines, routine=True,
                                                 amount_mode="range" if bid in _USAGE_BILLED else "fixed")]))

MERCHANTS += [
    B("us-mailchimp", ["Mailchimp"], ["MAILCHIMP    MISC MAILCHIMP.COM GA"], [U("email_marketing", "spend", "13.00", "120.00", "705", "US-R151", ["Email newsletter platform", "Mailchimp Standard"], routine=True, amount_mode="fixed")]),
    B("us-constant-contact", ["Constant Contact"], ["EIG CONSTANTCONTACT.CO 855-2295506 MA"], [U("email_marketing", "spend", "12.00", "90.00", "705", "US-R151", ["Email marketing plan"], routine=True, amount_mode="fixed")]),
    B("us-meta-platforms", ["Meta Ads", "Facebook Ads"], ["FACEBK {A10} Menlo Park CA"], [U("ads", "spend", "20.00", "600.00", "600", "US-R001", ["Facebook ads", "Instagram boost campaign"], routine=True, facts={"account": "600"})]),
    B("us-google-ads", ["Google Ads"], ["GOOGLE *ADS{N10} cc@google.com CA"], [U("ads", "spend", "25.00", "800.00", "600", "US-R001", ["Search ads", "Google Ads campaign"], routine=True, facts={"account": "600"})]),
    B("us-yelp", ["Yelp"], ["YELP INC {N8}"], [U("ads", "spend", "50.00", "450.00", "600", "US-R001", ["Yelp ads", "Local ads package"], routine=True, facts={"account": "600"})]),
    B("us-vistaprint", ["Vistaprint"], ["VISTAPRINT 8662074955 MA"], [
        U("print_ads", "spend", "18.00", "280.00", "600", "US-R001", ["Business cards", "Flyers and door hangers", "Yard signs"], routine=True, facts={"account": "600"}),
        U("promo_items", "spend", "60.00", "300.00", "600", "US-R021", ["Logo pens, 500 pack", "Branded tote bags for expo"], needs_line=True),
    ]),
    B("us-linkedin", ["LinkedIn"], ["LINKEDIN *{A8}"], [U("ads", "spend", "40.00", "500.00", "600", "US-R151", ["LinkedIn sponsored content"], routine=True, needs_line=True, facts={"ads": True})]),
    # Office and shipping
    *[B(bid, contacts, narrs, [
        U("office", "spend", lo, hi, "645", "US-R054", lines, routine=True, facts={"office": True}),
    ]) for bid, contacts, narrs, lines, lo, hi in [
        ("us-staples", ["Staples"], ["STAPLES       {N8} {CITY} {ST}"], ["Printer paper and toner", "Office supplies", "Envelopes and folders"], "6.00", "260.00"),
        ("us-office-depot", ["Office Depot"], ["OFFICE DEPOT #{N4} {CITY} {ST}"], ["Ink cartridges", "Office supplies", "File folders and labels"], "5.00", "220.00"),
        ("us-officemax", ["OfficeMax"], ["OFFICEMAX #{N4}"], ["Copy paper", "Office supplies"], "5.00", "160.00"),
        ("us-the-ups-store", ["The UPS Store"], ["THE UPS STORE {N4} {CITY} {ST}"], ["Shipping documents", "Mailing to client", "Packing and shipping"], "8.00", "120.00"),
        ("us-fedex-office", ["FedEx Office"], ["FEDEX OFFIC{N14} {CITY} {ST}"], ["Printing and shipping", "Overnight documents"], "10.00", "140.00"),
        ("us-ups", ["UPS"], ["UPS*{N10}"], ["Shipping", "Ground shipping, orders"], "9.00", "90.00"),
        ("us-fedex", ["FedEx"], ["FEDEX {N9}"], ["Shipping", "Overnight shipping"], "12.00", "110.00"),
        ("us-dhl", ["DHL"], ["DHL EXPRESS USA"], ["International shipping"], "25.00", "160.00"),
    ]],
    # Building supply and tools
    *[B(bid, contacts, narrs, [
        U("job_materials", "spend", "15.00", "900.00", "500", "US-R053", ["Materials, job {N4}", "Pipe and fittings", "Lumber for job {N4}", ""], hooks=["US-R053"], only={"trades": ["construction", "trades"]}),
        U("consumables", "spend", "8.00", "220.00", "670", "US-R054", ["Shop rags and cleaner", "Work gloves and tape", "Cleaning supplies"], needs_line=True, routine=True, only={"trades": ["construction", "trades", "crafts", "catering", "retail"]}),
        U("equipment", "spend", "120.00", "4800.00", "720", "US-R050", ["Miter saw", "Pressure washer", "Generator", "Compressor"], needs_line=True, hooks=["US-R050", "US-R051"], only={"trades": ["construction", "trades", "crafts", "catering", "retail"]}),
    ], category="diy_hardware_trade") for bid, contacts, narrs in [
        ("us-the-home-depot", ["The Home Depot", "Home Depot"], ["THE HOME DEPOT #{N4} {CITY} {ST}", "THE HOME DEPOT PRO"]),
        ("us-lowe-s", ["Lowe's"], ["LOWES #{N5}*"]),
        ("us-menards", ["Menards"], ["MENARDS {CITY} {ST}"]),
        ("us-grainger", ["Grainger"], ["GRAINGER {N9}"]),
        ("us-fastenal", ["Fastenal"], ["FASTENAL COMPANY{N2}"]),
        ("us-harbor-freight-tools", ["Harbor Freight Tools"], ["HARBOR FREIGHT TOOLS {N3}"]),
        ("us-84-lumber", ["84 Lumber"], ["84 LUMBER {N4}"]),
        ("us-city-electric-supply", ["City Electric Supply"], ["CITY ELECTRIC SUPPLY"]),
        ("us-true-value", ["True Value"], ["TRUE VALUE {N5}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("equipment_rental", "spend", "60.00", "1400.00", "655", "US-R062", ["Excavator rental, 2 days", "Scissor lift rental", "Trailer rental"], routine=True, needs_line=True, facts={"equipment": True}),
    ]) for bid, contacts, narrs in [
        ("us-sunbelt-rentals", ["Sunbelt Rentals"], ["SUNBELT RENTALS {N6}"]),
        ("us-herc-rentals", ["Herc Rentals"], ["HERC RENTALS {N6}"]),
        ("us-u-haul", ["U-Haul"], ["U-HAUL {N6}"]),
    ]],
    # Electronics
    *[B(bid, contacts, narrs, [
        U("equipment", "spend", "150.00", "4200.00", "720", "US-R050", lines, needs_line=True, hooks=["US-R050", "US-R051"]),
    ], category="electronics_it") for bid, contacts, narrs, lines in [
        ("us-dell", ["Dell"], ["DELL MARKETING L.P."], ["Laptop for client work", "Workstation and monitors", "Docking station and monitor"]),
        ("us-best-buy", ["Best Buy"], ["BEST BUY {N8}"], ["Laptop", "Camera body", "Monitor"]),
        ("us-b-and-h-photo-video", ["B&H Photo Video"], ["B & H PHOTO-VIDEO.COM"], ["Camera lens", "Lighting kit", "Camera body"]),
        ("us-apple", ["Apple"], ["APPLE STORE #R{N3}"], ["MacBook Pro", "iPad for invoicing", "iMac"]),
    ]],
    # Fuel, auto, parking
    *[B(bid, contacts, narrs, [
        U("fuel", "spend", "25.00", "140.00", "605", "US-R040", ["Fuel", "Gas for truck", ""], hooks=["US-R040", "US-R043"], only={"vehicle": True}),
    ], category="fuel") for bid, contacts, narrs in [
        ("us-shell", ["Shell"], ["SHELL OIL {N11} {CITY} {ST}"]),
        ("us-chevron", ["Chevron"], ["CHEVRON {N7} {CITY} {ST}"]),
        ("us-bp", ["BP"], ["BP#{N7}"]),
        ("us-sunoco", ["Sunoco"], ["SUNOCO {N10}"]),
        ("us-circle-k", ["Circle K"], ["CIRCLE K {N5}"]),
        ("us-phillips-66", ["Phillips 66"], ["PHILLIPS 66 {N8}"]),
        ("us-valero", ["Valero"], ["VALERO {N4}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("auto_repair", "spend", "25.00", "900.00", "605", "US-R040", lines, hooks=["US-R040", "US-R043"], only={"vehicle": True}),
    ]) for bid, contacts, narrs, lines in [
        ("us-autozone", ["AutoZone"], ["AUTOZONE #{N4}"], ["Brake pads, truck", "Battery, work truck", ""]),
        ("us-o-reilly-auto-parts", ["O'Reilly Auto Parts"], ["O'REILLY {N4}"], ["Oil and filters", "Wiper blades"]),
        ("us-advance-auto-parts", ["Advance Auto Parts"], ["ADVANCE AUTO PARTS {N4}"], ["Truck parts"]),
        ("us-firestone", ["Firestone"], ["FIRESTONE {N6}"], ["Tires, work van", "Alignment"]),
        ("us-goodyear", ["Goodyear"], ["GOODYEAR AUTO SVC {N4}"], ["Tires and rotation"]),
        ("us-big-o-tires", ["Big O Tires"], ["BIG O TIRES {N3}"], ["Tire repair"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("auto_insurance", "spend", "60.00", "260.00", "605", "US-R041", ["Truck insurance", "Auto policy", ""], hooks=["US-R041", "US-R043"], only={"vehicle": True}, amount_mode="fixed"),
    ], fmt="US-ACH", refs=["{K9}"]) for bid, contacts, narrs in [
        ("us-geico", ["GEICO"], ["GEICO DES:PREM COLL ID:{N9}"]),
        ("us-progressive", ["Progressive"], ["PROGRESSIVE INS DES:INS PREM"]),
        ("us-allstate", ["Allstate"], ["ALLSTATE DES:INS PREM ID:{N8}"]),
    ]],
    # Business insurance
    *[B(bid, contacts, narrs, [
        U("business_insurance", "spend", "35.00", "480.00", "625", "US-R170", ["General liability premium", "Business owner's policy", "Workers comp premium", "Professional liability"], routine=True, needs_line=True, amount_mode="fixed"),
    ], fmt="US-ACH", refs=["POL{K8}"]) for bid, contacts, narrs in [
        ("us-hiscox", ["Hiscox"], ["HISCOX INC DES:PREMIUM"]),
        ("us-next-insurance", ["Next Insurance"], ["NEXT INSURANCE DES:PREMIUM"]),
        ("us-the-hartford", ["The Hartford"], ["THE HARTFORD DES:NWTBPREM"]),
        ("us-travelers", ["Travelers"], ["TRAVELERS DES:PREMIUM"]),
        ("us-liberty-mutual", ["Liberty Mutual"], ["LIBERTY MUTUAL DES:PREM"]),
    ]],
    B("us-state-farm", ["State Farm"], ["STATE FARM RO {N2} SFPP"], [
        U("business_insurance", "spend", "40.00", "300.00", "625", "US-R170", ["Business liability policy"], routine=True, needs_line=True, amount_mode="fixed"),
        U("auto_insurance", "spend", "70.00", "240.00", "605", "US-R041", ["Truck insurance", ""], hooks=["US-R041", "US-R043"], only={"vehicle": True}, amount_mode="fixed"),
    ], fmt="US-ACH", refs=["{K10}"]),
    B("us-united-healthcare", ["UnitedHealthcare"], ["UHC DES:PREMIUM ID:{N9}"], [
        U("owner_health", "spend", "320.00", "980.00", "3010", "US-R072", ["Health insurance, owner", ""], amount_mode="fixed"),
        U("employee_health", "spend", "450.00", "2600.00", "620", "US-R171", ["Group health premium, staff", "Employee health plan"], only={"employer": True}, amount_mode="fixed"),
    ], fmt="US-ACH", refs=["GRP{K6}"]),
    B("us-nationwide", ["Nationwide"], ["NATIONWIDE LIFE DES:PREM"], [
        U("life_insurance", "spend", "25.00", "140.00", "3010", "US-R074", ["Life insurance", ""], amount_mode="fixed"),
    ], fmt="US-ACH", refs=["{K9}"]),
    # Telecom and utilities
    *[B(bid, contacts, narrs, [
        U("business_line", "spend", lo, hi, "690", "US-R061", ["Business internet", "Business phone line", "Business mobile plan"], needs_line=True, facts={"line_type": "business", "line_states": True}, amount_mode="fixed"),
        U("residential", "spend", lo, hi, "3010", "US-R061", ["Home landline", ""], facts={"line_type": "residential", "line_states": True}, amount_mode="fixed", refs=["{N10}"]),
    ], fmt="US-ACH", refs=["{K10}"]) for bid, contacts, narrs, lo, hi in [
        ("us-at-and-t", ["AT&T"], ["AT&T PAYMENT 800-288-2020 TX"], "35.00", "180.00"),
        ("us-verizon", ["Verizon"], ["VERIZON ONEPOS {N6} 800-922-0204 FL"], "40.00", "190.00"),
        ("us-t-mobile", ["T-Mobile"], ["T-MOBILE PCS SVC DES:AUTOPAY"], "30.00", "160.00"),
        ("us-spectrum", ["Spectrum"], ["SPECTRUM 855-707-7328 MO"], "50.00", "160.00"),
        ("us-xfinity", ["Xfinity", "Comcast"], ["COMCAST CABLE COMM 800-COMCAST"], "50.00", "180.00"),
        ("us-cox-communications", ["Cox Communications"], ["COX COMM SVCS DES:PAYMENT"], "50.00", "170.00"),
    ]],
    *[B(bid, contacts, narrs, [
        U("premises_utility", "spend", "60.00", "900.00", "690", "US-R190", ["Electric, shop", "Power, warehouse unit", ""], facts={"line_states": True}, hooks=["US-R190"], only={"premises": True, "states": states}),
        U("home_utility", "spend", "50.00", "260.00", "3010", "US-R060", ["", "Home electric"], refs=["{N10}"], only={"states": states}),
    ], fmt="US-ACH", refs=["{K10}"]) for bid, contacts, narrs, states in [
        # Each utility only where it serves (re-audit R3: ComEd at a Boise firm); firms elsewhere have none.
        ("us-comed", ["ComEd"], ["COMED DES:UTIL PYMT"], ["IL"]),
        ("us-con-edison", ["Con Edison"], ["CON ED OF NY DES:INTELL CK"], ["NY"]),
        ("us-duke-energy", ["Duke Energy"], ["DUKE ENERGY DES:BILL PAY"], ["NC", "SC", "OH", "IN", "KY", "FL"]),
        ("us-pg-and-e", ["PG&E"], ["PGANDE DES:WEB ONLINE"], ["CA"]),
        ("us-georgia-power", ["Georgia Power"], ["GEORGIA POWER DES:BILL PAY"], ["GA"]),
        ("us-xcel-energy", ["Xcel Energy"], ["XCEL ENERGY DES:XCELENERGY"], ["CO", "MN", "WI", "ND", "SD", "MI"]),
        ("us-dominion-energy", ["Dominion Energy"], ["DOMINION ENERGY DES:BILLPAY"], ["VA", "UT", "SC"]),
        ("us-florida-power-and-light", ["Florida Power & Light", "FPL"], ["FPL DIRECT DEBIT DES:ELEC PYMT"], ["FL"]),
    ]],
    # Travel
    *[B(bid, contacts, narrs, [
        U("airfare", "spend", lo, hi, "680", "US-R030", ["Flight to Denver, {PURPOSE}", "Airfare, {PURPOSE}", "Flight, {PURPOSE}"], routine=True, needs_line=True),
    ]) for bid, contacts, narrs, lo, hi in [
        ("us-delta-air-lines", ["Delta Air Lines", "Delta"], ["DELTA AIR {N13}"], "120.00", "900.00"),
        ("us-united-airlines", ["United Airlines", "United"], ["UNITED {N13}"], "110.00", "850.00"),
        ("us-southwest-airlines", ["Southwest Airlines"], ["SOUTHWES {N10}"], "80.00", "520.00"),
        ("us-american-airlines", ["American Airlines"], ["AMERICAN AIR{N10}"], "100.00", "800.00"),
        ("us-jetblue", ["JetBlue"], ["JETBLUE {N13}"], "90.00", "600.00"),
        ("us-alaska-airlines", ["Alaska Airlines"], ["ALASKA AIR {N10}"], "90.00", "560.00"),
        ("us-amtrak", ["Amtrak"], ["AMTRAK .COM {N10}"], "40.00", "320.00"),
    ]],
    *[B(bid, contacts, narrs, [
        U("lodging", "spend", "110.00", "720.00", "680", "US-R030", ["Hotel, {PURPOSE}", "Lodging, {PURPOSE}", "Hotel, two nights {PURPOSE}"], routine=True, needs_line=True),
    ]) for bid, contacts, narrs in [
        ("us-marriott", ["Marriott"], ["MARRIOTT {CITY} {ST}"]),
        ("us-hilton", ["Hilton"], ["HILTON HOTELS {CITY}"]),
        ("us-hyatt", ["Hyatt"], ["HYATT HOTELS {CITY}"]),
        ("us-hampton-inn-and-suites", ["Hampton Inn"], ["HAMPTON INN {CITY} {ST}"]),
        ("us-holiday-inn", ["Holiday Inn"], ["HOLIDAY INN {CITY}"]),
        ("us-airbnb", ["Airbnb"], ["AIRBNB * HM{A8}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("car_rental", "spend", "70.00", "520.00", "680", "US-R030", ["Rental car, {PURPOSE}", "Car rental, {PURPOSE}"], routine=True, needs_line=True),
    ]) for bid, contacts, narrs in [
        ("us-hertz", ["Hertz"], ["HERTZ RENT-A-CAR {N6}"]),
        ("us-enterprise", ["Enterprise"], ["ENTERPRISE RENT-A-CAR"]),
        ("us-avis", ["Avis"], ["AVIS RENT A CAR {N6}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("local_ride", "spend", "8.00", "65.00", "605", "US-R033", ["Ride, {PURPOSE}", "Rideshare, {PURPOSE}", ""], ),
    ]) for bid, contacts, narrs in [
        ("us-uber", ["Uber"], ["UBER   TRIP {A6} HELP.UBER.COM CA"]),
        ("us-lyft", ["Lyft"], ["LYFT   *RIDE {A3} {N1}PM"]),
    ]],
]

# R16 (audit round 2): client meals at sit-down restaurants and coffee shops, never through a delivery app or a
# quick-service counter; one-person delivery orders stay small. Kinds: restaurant, coffee, quick, delivery.
_FOOD_US = [
    ("us-starbucks", ["Starbucks"], ["STARBUCKS STORE {N5} {CITY} {ST}"], "4.00", "70.00", "coffee"),
    ("us-dunkin", ["Dunkin'"], ["DUNKIN #{N6}"], "4.00", "50.00", "coffee"),
    ("us-peet-s-coffee", ["Peet's Coffee"], ["PEETS {N5}"], "4.00", "45.00", "coffee"),
    ("us-chick-fil-a", ["Chick-fil-A"], ["CHICK-FIL-A #{N5}"], "8.00", "120.00", "quick"),
    ("us-subway", ["Subway"], ["SUBWAY {N8}"], "7.00", "90.00", "quick"),
    ("us-the-cheesecake-factory", ["The Cheesecake Factory"], ["THE CHEESECAKE FACTORY {N4}"], "35.00", "320.00", "restaurant"),
    ("us-doordash", ["DoorDash"], ["DD DOORDASH {A10} 8559731040 CA"], "15.00", "95.00", "delivery"),
    ("us-uber-eats", ["Uber Eats"], ["UBER   EATS 8005928996 CA"], "15.00", "90.00", "delivery"),
    ("us-grubhub", ["Grubhub"], ["GRUBHUB{A10} 8775851085 NY"], "15.00", "95.00", "delivery"),
]
_CLIENT_MEAL_LINES = {
    "restaurant": ["Lunch with client re proposal", "Dinner with client, project review",
                   "Client dinner, project kickoff"],
    "coffee": ["Coffee with prospective client", "Coffee meeting with client"],
}
_TRAVEL_MEAL_LINES = {
    "restaurant": ["Dinner while away, {PURPOSE}", "Meal on trip, {PURPOSE}"],
    "coffee": ["Breakfast while away, {PURPOSE}"],
    "quick": ["Lunch on the road, {PURPOSE}", "Meal on trip, {PURPOSE}"],
    "delivery": ["Meal delivered to hotel, {PURPOSE}"],
}


def _food_uses_us(lo: str, hi: str, kind: str = "restaurant", *, routine: bool = False) -> list[dict]:
    """Meal uses for one food merchant. `routine` marks the client meal as an ordinary S0 line (small sellers)."""
    out = []
    if kind in _CLIENT_MEAL_LINES:
        out.append(U("client_meal", "spend", lo, hi, "685", "US-R010", _CLIENT_MEAL_LINES[kind], needs_line=True,
                     facts={"stated": True}, routine=routine))
    if kind == "restaurant":
        out.append(U("meal_tip", "spend", lo, hi, "685", "US-R011", ["Client lunch incl tip", "Business dinner with client, tip included"], needs_line=True))
    out += [
        U("travel_meal", "spend", lo, hi, "685", "US-R031", _TRAVEL_MEAL_LINES[kind], needs_line=True, facts={"stated": True}),
        U("personal_meal", "spend", lo, hi, "3010", "US-R002", ["Family dinner", "Personal lunch"] if kind != "coffee" else ["Personal coffee and pastry"], needs_line=True),
        U("no_description", "spend", lo, hi, "NEEDS_REVIEW", "US-N2", [""]),
    ]
    return out


for bid, contacts, narrs, lo, hi, kind in _FOOD_US:
    MERCHANTS.append(B(bid, contacts, narrs, _food_uses_us(lo, hi, kind), category="food_drink"))

_RETAIL_US = [
    ("us-amazon", ["Amazon"], ["AMZN Mktp US {A9} Amzn.com/bill WA", "Amazon.com {A9} Amzn.com/bill WA"]),
    ("us-walmart", ["Walmart"], ["WAL-MART #{N4} {CITY} {ST}", "WALMART.COM 800-966-6546 AR"]),
    ("us-target", ["Target"], ["TARGET        {N8} {CITY} {ST}"]),
    ("us-costco", ["Costco"], ["COSTCO WHSE #{N4}", "WWW COSTCO COM 800-955-2292 WA"]),
    ("us-sam-s-club", ["Sam's Club"], ["SAMSCLUB #{N4} {CITY} {ST}"]),
    ("us-kroger", ["Kroger"], ["KROGER #{N3}"]),
    ("us-whole-foods-market", ["Whole Foods Market"], ["WHOLEFDS {A3} {N5}"]),
    ("us-cvs-pharmacy", ["CVS Pharmacy"], ["CVS/PHARMACY #{N5} {CITY} {ST}"]),
    ("us-walgreens", ["Walgreens"], ["WALGREENS #{N4} {CITY} {ST}"]),
]
for bid, contacts, narrs in _RETAIL_US:
    uses = [
        U("unknown_purchase", "spend", "12.00", "260.00", "NEEDS_REVIEW", "US-R143", [""], hooks=["US-R143"]),
        U("personal_purchase", "spend", "15.00", "220.00", "3010", "US-R002", ["Groceries", "Household items", "Personal items"], needs_line=True),
        U("office_purchase", "spend", "8.00", "160.00", "645", "US-R054", ["Printer ink", "Copy paper", "Desk organizers"], needs_line=True, facts={"office": True}),
    ]
    if bid in ("us-costco", "us-sam-s-club"):
        # F5: the memo names the club, so "Annual membership" never stands alone.
        uses.append(U("membership", "spend", "50.00", "130.00", "670", "US-R152", [f"{contacts[0]} annual membership", f"{contacts[0]} membership renewal"], hooks=["US-R152"]))
    MERCHANTS.append(B(bid, contacts, narrs, uses, category="retail_general"))

MERCHANTS += [
    *[B(bid, contacts, narrs, [
        U("gym", "spend", "10.00", "60.00", "3010", "US-R002", ["", "Gym membership"], amount_mode="fixed"),
    ], fmt="US-ACH", refs=["{K8}"]) for bid, contacts, narrs in [
        ("us-planet-fitness", ["Planet Fitness"], ["PLANET FIT CLUB FEES"]),
        ("us-la-fitness", ["LA Fitness"], ["LA FITNESS DES:DUES"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("storage_rent", "spend", "60.00", "420.00", "660", "US-R062", ["Storage unit rent", "Storage, equipment", ""], routine=True, amount_mode="fixed"),
    ], fmt="US-ACH", refs=["{K8}"]) for bid, contacts, narrs in [
        ("us-public-storage", ["Public Storage"], ["PUBLIC STORAGE {N5}"]),
        ("us-extra-space-storage", ["Extra Space Storage"], ["EXTRA SPACE {N4}"]),
        ("us-cubesmart", ["CubeSmart"], ["CUBESMART {N4}"]),
        ("us-regus", ["Regus"], ["REGUS MANAGEMENT GRP"]),
        ("us-wework", ["WeWork"], ["WEWORK {N9} NY"]),
    ]],
    # Processors and payment apps
    # R13: the transfer id is one {A12} token, so the reference and the bank line show the same id in one record.
    B("us-stripe", ["Stripe"], ["STRIPE DES:TRANSFER ID:ST-{A12}"], [
        U("payout", "receive", "120.00", "6200.00", "1100", "US-R120", ["Stripe payout", ""], hooks=["US-R120", "US-R121"], only={"processor": "us-stripe"}),
        U("fee", "spend", "15.00", "90.00", "700", "US-R122", ["Stripe monthly fee", "Stripe billing fee"], routine=True, only={"processor": "us-stripe"}, narratives=["STRIPE DES:BILLING ID:ST-{A12}"]),
    ], fmt="US-ACH", refs=["ST-{A12}"]),
    B("us-square", ["Square"], ["SQUARE INC DES:SQ{N6} ID:{A12}", "SQUARE INC DIRECT DEPOSIT"], [
        U("payout", "receive", "80.00", "4800.00", "1100", "US-R120", ["Square deposit", ""], hooks=["US-R120", "US-R121"], only={"processor": "us-square"}, narratives=["SQUARE INC DES:SQ{N6} ID:{A12}", "SQUARE INC DIRECT DEPOSIT"]),
        U("chargeback", "spend", "20.00", "300.00", "405", "US-R130", ["Chargeback, disputed sale", "Refund to customer"], needs_line=True, only={"processor": "us-square"}, narratives=["SQUARE INC DES:SQ CHGBCK ID:{A12}", "SQUARE INC DES:SQ REFUND ID:{A12}"]),
    ], fmt="US-ACH", refs=["SQ{N6}"]),
    B("us-paypal", ["PayPal"], ["PAYPAL DES:TRANSFER ID:{N12}"], [
        U("payout", "receive", "40.00", "3200.00", "1100", "US-R120", ["PayPal transfer"], hooks=["US-R120", "US-R121"], only={"processor": "us-paypal"}),
    ], fmt="US-ACH", refs=["{N12}"]),
    B("us-etsy", ["Etsy"], ["ETSY.COM - {A8}", "ETSY INC DES:SELLER FEE"], [
        U("seller_fees", "spend", "6.00", "180.00", "610", "US-R123", ["Etsy listing and transaction fees", "Etsy fees"], routine=True, only={"goods": True}),
    ], fmt="US-ACH", refs=["{N9}"]),
    B("us-ebay", ["eBay"], ["EBAY O*{N2}-{N5}-{N5}", "EBAY INC DES:SELLER FEE"], [
        U("seller_fees", "spend", "5.00", "160.00", "610", "US-R123", ["eBay final value fees"], routine=True, only={"goods": True}),
    ], fmt="US-ACH", refs=["{N9}"]),
    B("us-shopify", ["Shopify"], ["SHOPIFY* {N9}"], [
        U("software", "spend", "29.00", "120.00", "705", "US-R150", ["Shopify plan", "Online store subscription"], routine=True, amount_mode="fixed"),
    ]),
    B("us-venmo", ["Venmo"], ["VENMO PAYMENT {N10}"], [
        U("p2p_out", "spend", "40.00", "900.00", "NEEDS_REVIEW", "US-R141", [""], fmt="US-P2P"),
    ], fmt="US-P2P", refs=["{N10}"]),
    B("us-zelle", ["Zelle"], ["Zelle Payment To {PERSON} {A11}"], [
        U("p2p_out", "spend", "40.00", "1800.00", "NEEDS_REVIEW", "US-R141", [""], fmt="US-P2P"),
    ], fmt="US-P2P", refs=["{A11}"]),
    B("us-cash-app", ["Cash App"], ["Cash App*{PERSON}"], [
        U("p2p_out", "spend", "20.00", "600.00", "NEEDS_REVIEW", "US-R141", [""], fmt="US-P2P"),
    ], fmt="US-P2P", refs=[""]),
    # Payroll providers
    *[B(bid, contacts, narrs, [
        U("net_pay", "spend", "900.00", "14000.00", "695", "US-R084", ["Payroll net pay", ""], hooks=["US-R084", "US-R075", "US-R077"], only={"payroll": bid}, refs=["NET {N6}", "{N4} NET PAY"], narratives=[n_net]),
        U("payroll_tax", "spend", "250.00", "5200.00", "2200", "US-R083", ["Payroll taxes", ""], hooks=["US-R083"], only={"payroll": bid}, refs=["TAX {N6}"], narratives=[n_tax]),
        U("fee", "spend", "45.00", "220.00", "640", "US-R084", ["Payroll service fee", "Payroll software fee"], needs_line=True, facts={"fee": True}, only={"payroll": bid}, refs=["FEE {N6}", "INV {N6}"], narratives=[n_fee]),
    ], fmt="US-ACH") for bid, contacts, n_net, n_tax, n_fee in [
        ("us-gusto", ["Gusto"], "GUSTO DES:NET ID:{A10}", "GUSTO DES:TAX ID:{A10}", "GUSTO DES:FEE ID:{A10}"),
        ("us-adp", ["ADP"], "ADP WAGE PAY DES:WAGE PAY", "ADP TAX DES:ADP TAX", "ADP PAYROLL FEES DES:ADP FEES"),
        ("us-paychex", ["Paychex"], "PAYCHEX INC. DES:PAYROLL", "PAYCHEX TPS DES:TAXES", "PAYCHEX EIB DES:INVOICE"),
    ] for narrs in [[n_net]]],
    B("us-h-and-r-block", ["H&R Block"], ["H&R BLOCK {N5}"], [
        U("personal_return", "spend", "90.00", "450.00", "3010", "US-R161", ["Personal tax return prep", "Owner 1040 preparation"], needs_line=True, facts={"personal_return": True, "line_states": True}),
        U("business_return", "spend", "200.00", "900.00", "640", "US-R161", ["Schedule C preparation", "Business tax return prep"], needs_line=True, routine=True),
    ]),
    B("us-liberty-tax", ["Liberty Tax"], ["LIBERTY TAX {N4}"], [
        U("personal_return", "spend", "80.00", "350.00", "3010", "US-R161", ["Personal return, owner"], needs_line=True, facts={"personal_return": True, "line_states": True}),
    ]),
]

_BANKS_US = [
    ("us-bank-of-america", ["Bank of America"], "BANK OF AMERICA"),
    ("us-wells-fargo", ["Wells Fargo"], "WELLS FARGO"),
    ("us-capital-one", ["Capital One"], "CAPITAL ONE"),
    ("us-pnc-bank", ["PNC Bank"], "PNC"),
    ("us-u-s-bank", ["U.S. Bank"], "US BANK"),
    ("us-citibank", ["Citibank"], "CITI"),
]
for bid, contacts, short in _BANKS_US:
    MERCHANTS.append(B(bid, contacts, [short], [
        U("service_fee", "spend", "5.00", "35.00", "700", "US-R122", ["Monthly service fee", ""], routine=True, narratives=["MONTHLY SERVICE FEE", "DOMESTIC WIRE FEE", "OVERDRAFT FEE"], fmt="US-FEE", amount_mode="whole"),
        U("fee_reversal", "receive", "5.00", "35.00", "700", "US-R132", ["Fee reversal", ""], narratives=["MONTHLY SERVICE FEE REVERSAL", "OVERDRAFT FEE REFUND"], fmt="US-FEE", amount_mode="whole"),
        U("interest_earned", "receive", "0.10", "45.00", "410", "US-R192", ["Interest", ""], routine=True, narratives=["INTEREST PAYMENT", "INTEREST EARNED"], fmt="US-INT"),
        U("loc_interest", "spend", "8.00", "240.00", "635", "US-R101", ["Line of credit interest", ""], routine=True, narratives=["LOC INTEREST CHARGE", "LINE OF CREDIT INTEREST"], fmt="US-FEE"),
        # F5, F9: the memo and the bank line name the card issuer, so a business card payment and a personal card
        # payment never share one memo.
        U("card_payment", "spend", "150.00", "4200.00", "2000", "US-R110", [f"{contacts[0]} card payment", f"Payment to {contacts[0]} card"], hooks=["US-R110"], narratives=["ONLINE PAYMENT TO " + short + " CARD ...{N4}", short + " CRCARDPMT DES:CRCARDPMT"], fmt="US-ACH", refs=["CC PMT"]),
        U("loan_proceeds", "receive", "5000.00", "60000.00", "2300", "US-R100", ["SBA loan proceeds", "Term loan funding"], narratives=[short + " LOAN DISB"], fmt="US-ACH", refs=["LN {K8}"], amount_mode="round"),
        U("loan_payment", "spend", "250.00", "2200.00", "NEEDS_REVIEW", "US-R103", ["Loan payment", ""], narratives=[short + " LOAN PMT"], fmt="US-ACH", refs=["LN {K8}"], amount_mode="fixed"),
        # Card interest is charged to the card balance, never debited from checking (re-audit R3): the personal
        # interest a business account pays by ACH is on a personal loan.
        U("personal_interest", "spend", "15.00", "160.00", "3010", "US-R104", ["Personal loan interest", "Interest, personal loan"], needs_line=True, narratives=[short + " PERS LOAN PMT"], fmt="US-ACH", refs=["PL {K8}"]),
        U("loan_principal", "spend", "500.00", "9000.00", "2300", "US-R101", ["Principal-only payment, term loan", "Extra principal payment"], needs_line=True, facts={"principal_only": True}, narratives=[short + " LOAN PRIN PMT"], fmt="US-ACH", refs=["LN {K8}"]),
    ], category="bank"))

# US-R194: a penalty the contract sets for late or missed performance, paid to the customer (not a refund of the
# price, which is US-R130, and not a government fine, which is US-R086). Wording follows the firm's kind of work.
_PENALTY_KINDS = [
    ("late_completion_penalty", ("construction", "trades"),
     ["Liquidated damages, late completion per contract", "Late completion penalty per contract"]),
    ("late_delivery_penalty", ("crafts", "retail", "catering"),
     ["Late delivery penalty per contract", "Penalty for late order delivery per agreement"]),
    ("missed_deadline_penalty", ("creative", "professional"),
     ["Penalty for missed contract deadline", "Late deliverable penalty per agreement"]),
]


PENALTY_USES = tuple(k for k, _, _ in _PENALTY_KINDS)


def _penalty_uses(slug: str) -> list[dict]:
    out = []
    for use, trades, lines in _PENALTY_KINDS:
        fit = [t for t in CUSTOMER_TRADES[slug] if t in trades]
        if fit:
            out.append(U(use, "spend", "100.00", "2400.00", "720", "US-R194", lines, needs_line=True,
                         refs=["CONTRACT {K6}", "PO {N5}"], only={"trades": fit}))
    return out


RECEIPT_LINES = ["Invoice {N6}", "Payment, invoice {N6}", ""]
# Half the references typed in lower case, as customers do.
RECEIPT_REFS = ["INV {N6}", "INV-{N6}", "{N6}", "inv {N6}", "invoice {N6} thanks", "pmt for inv {N6}"]
LENDER_LIKE_CUSTOMERS = {"bramblewood-credit-union"}

# Small sellers (shortcut S-1, audit round 2): local businesses billed through a card processor, so their card
# lines carry the processor prefix (`SQ *` Square, `PAYPAL *` PayPal, `TST*` Toast, restaurants only) in ordinary
# spending. Names are invented (web-checked 2026-10-13: no business of that name found). The Xero contact is the
# plain name or the descriptor a bank rule copied. Each has a routine spend use with line descriptions, which S6
# card-descriptor attacks host on. Only the sign and banner makers are single-purpose enough to be read from the
# payee alone; every other use needs its line.
SMALL_SELLER_TRADES_ALL = ["construction", "trades", "professional", "creative", "crafts", "catering", "education", "retail"]


def _small(slug: str, name: str, descriptor: str, uses: list[dict]) -> dict:
    return I(slug, name, [name, descriptor], [descriptor], uses, fmt="US-CARD", category="small_seller")


SMALL_SELLERS = [
    _small("brindlewood-grill", "Brindlewood Grill", "TST* BRINDLEWOOD GRILL",
           _food_uses_us("22.00", "240.00", "restaurant", routine=True)),
    _small("marrowfield-cafe", "Marrowfield Cafe", "TST* MARROWFIELD CAFE",
           _food_uses_us("14.00", "160.00", "restaurant", routine=True)),
    _small("thistledown-coffee", "Thistledown Coffee", "SQ *THISTLEDOWN COFFEE",
           _food_uses_us("5.00", "48.00", "coffee", routine=True)),
    _small("kettleby-hardware", "Kettleby Hardware", "SQ *KETTLEBY HARDWARE", [
        U("consumables", "spend", "8.00", "180.00", "670", "US-R054", ["Work gloves and tape", "Caulk and sealant", "Shop rags and cleaner"], routine=True, needs_line=True, only={"trades": ["construction", "trades", "crafts", "retail"]}),
    ]),
    _small("bramblegate-signs", "Bramblegate Signs", "SQ *BRAMBLEGATE SIGNS", [
        U("print_ads", "spend", "35.00", "650.00", "600", "US-R001", ["Yard signs", "Vinyl banner for shop front", "Vehicle door magnets with logo", "A-frame sidewalk sign"], routine=True, facts={"account": "600"}, only={"trades": SMALL_SELLER_TRADES_ALL}),
    ]),
    _small("tallowmark-print", "Tallowmark Print Co", "PAYPAL *TALLOWMRK PRNT", [
        U("print_ads", "spend", "25.00", "380.00", "600", "US-R001", ["Postcards for mailing", "Flyers and door hangers", "Business cards"], routine=True, needs_line=True, facts={"account": "600"}, only={"trades": SMALL_SELLER_TRADES_ALL}),
    ]),
    _small("larkvane-banners", "Larkvane Banners", "PAYPAL *LARKVANEBANNER", [
        U("print_ads", "spend", "40.00", "420.00", "600", "US-R001", ["Event banner with logo", "Feather flag banners", "Trade show backdrop banner"], routine=True, facts={"account": "600"}, only={"trades": SMALL_SELLER_TRADES_ALL}),
    ]),
    _small("fixfinch-phone-repair", "Fixfinch Phone Repair", "SQ *FIXFINCH PHONE REP", [
        U("device_repair", "spend", "45.00", "260.00", "665", "US-R052", ["Phone screen repair, work phone", "Battery replacement, work phone", "Tablet screen repair, invoicing tablet"], routine=True, needs_line=True, facts={"scope": "repair"}),
    ]),
    _small("quillfern-kitchen-supply", "Quillfern Kitchen Supply", "SQ *QUILLFERN KITCHEN", [
        U("consumables", "spend", "12.00", "240.00", "670", "US-R054", ["Deli containers and lids", "Parchment and foil", "Food safe gloves and towels"], routine=True, needs_line=True, only={"trades": ["catering"]}),
    ]),
    _small("pellwood-commons", "Pellwood Commons", "SQ *PELLWOOD COMMONS", [
        U("day_office", "spend", "15.00", "180.00", "660", "US-R062", ["Coworking day pass", "Meeting room hire, client session", "Hot desk day pass"], routine=True, needs_line=True, only={"trades": ["professional", "creative", "education"]}),
    ]),
    _small("wrenfield-plugins", "Wrenfield Plugins", "PAYPAL *WRENFIELD", [
        U("software", "spend", "29.00", "199.00", "705", "US-R150", ["Website plugin license, annual", "Booking plugin renewal", "Store theme license renewal"], routine=True, needs_line=True, amount_mode="fixed", only={"trades": ["professional", "creative", "crafts", "retail"]}),
    ]),
    _small("hushbrook-press", "Hushbrook Press", "PAYPAL *HUSHBROOKPRESS", [
        U("teaching_supplies", "spend", "18.00", "220.00", "670", "US-R054", ["Practice test workbooks", "SAT prep books for students"], routine=True, needs_line=True, only={"trades": ["education"]}),
    ]),
]
MERCHANTS += SMALL_SELLERS

# Invented merchants, customers, government payees.
MERCHANTS += [
    I("cedar-ridge-plumbing-supply", "Cedar Ridge Plumbing Supply", ["Cedar Ridge Plumbing Supply"], ["CEDAR RIDGE PLUMBING SUP"], [
        U("job_materials", "spend", "30.00", "1800.00", "500", "US-R053", ["Water heater for customer job", "Fittings, job {N4}", ""], hooks=["US-R053"], only={"trades": ["construction", "trades"]}),
    ], fmt="US-CARD"),
    I("northgate-drywall", "Northgate Drywall LLC", ["Northgate Drywall LLC"], ["NORTHGATE DRYWALL"], [
        U("contract_labor", "spend", "400.00", "6000.00", "615", "US-R160", ["Drywall subcontract, job {N4}", "Taping and finishing, sub"], needs_line=True),
    ], refs=["INV {N4}"]),
    I("bluecrest-electric", "Bluecrest Electric LLC", ["Bluecrest Electric LLC"], ["BLUECREST ELECTRIC"], [
        U("contract_labor", "spend", "300.00", "4800.00", "615", "US-R160", ["Electrical subcontract", "Panel upgrade, subcontractor"], needs_line=True),
    ], refs=["BCE{N5}"]),
    I("pinewood-web-freelance", "Pinewood Web Studio LLC", ["Pinewood Web Studio LLC"], ["PINEWOOD WEB STUDIO"], [
        U("contract_labor", "spend", "250.00", "3500.00", "615", "US-R160", ["Website build, freelance", "Freelance design work"], needs_line=True),
    ], refs=["PWS-{N4}"]),
    I("riverside-tax-and-bookkeeping", "Riverside Tax and Bookkeeping", ["Riverside Tax and Bookkeeping"], ["RIVERSIDE TAX & BKPG"], [
        U("bookkeeping_fee", "spend", "150.00", "650.00", "640", "US-R161", ["Monthly bookkeeping", "Bookkeeping, {MMM}"], routine=True, amount_mode="fixed"),
        U("professional", "spend", "250.00", "1800.00", "640", "US-R161", ["Business tax return", "Quarterly review"], routine=True),
        U("personal_return", "spend", "200.00", "600.00", "3010", "US-R161", ["Personal return for owner only", "Owner 1040, personal"], needs_line=True, facts={"personal_return": True, "line_states": True}),
    ], refs=["INV {N4}"]),
    I("hollis-park-legal", "Hollis Park Legal Group", ["Hollis Park Legal Group"], ["HOLLIS PARK LEGAL"], [
        U("professional", "spend", "250.00", "4200.00", "640", "US-R161", ["Contract review", "Collections letter, unpaid invoice", "Customer terms and conditions review"], routine=True),
        # R16: LLC paperwork only at an LLC.
        U("llc_legal", "spend", "250.00", "1800.00", "640", "US-R161", ["LLC operating agreement update", "LLC annual compliance review"], routine=True, only={"entity": ["smllc"]}),
    ], refs=["HPL{N5}"]),
    I("harbor-lane-coworking", "Harbor Lane Coworking", ["Harbor Lane Coworking"], ["HARBOR LANE COWORK"], [
        U("rent", "spend", "250.00", "1200.00", "660", "US-R062", ["Desk membership", "Private office rent {MMM}"], routine=True, amount_mode="fixed"),
    ], refs=["HLC{K5}"]),
    I("maplewood-commercial", "Maplewood Commercial Properties LLC", ["Maplewood Commercial Properties LLC"], ["MAPLEWOOD COMMERCIAL"], [
        U("rent", "spend", "1200.00", "5200.00", "660", "US-R062", ["Shop rent {MMM}", "Warehouse rent", "Lease payment, unit {K2}"], routine=True, amount_mode="fixed"),
    ], refs=["LEASE {K4}"]),
    I("oak-terrace-apartments", "Oak Terrace Apartments LLC", ["Oak Terrace Apartments LLC"], ["OAK TERRACE APTS"], [
        U("home_rent", "spend", "900.00", "2400.00", "3010", "US-R060", ["", "Rent"], amount_mode="fixed"),
    ], refs=["UNIT {K3}"]),
    I("cedar-valley-savings", "Cedar Valley Savings Bank", ["Cedar Valley Savings Bank"], ["CEDAR VALLEY SVGS"], [
        U("mortgage_interest", "spend", "300.00", "2400.00", "630", "US-R102", ["Mortgage interest, shop building", "Commercial mortgage interest"], needs_line=True, hooks=["US-R102"]),
    ], refs=["MTG {K8}"]),
    I("granite-peak-lending", "Granite Peak Business Lending", ["Granite Peak Business Lending"], ["GRANITE PEAK LENDING"], [
        U("loan_proceeds", "receive", "8000.00", "75000.00", "2300", "US-R100", ["Equipment loan funding", "Loan proceeds"], refs=["LN {K8}"], amount_mode="round"),
        U("loan_payment", "spend", "300.00", "2600.00", "NEEDS_REVIEW", "US-R103", ["Loan payment", ""], refs=["LN {K8}"], amount_mode="fixed"),
        U("vehicle_loan", "receive", "12000.00", "48000.00", "2300", "US-R045", ["Truck loan funding", "Vehicle loan proceeds"], needs_line=True, refs=["VL {N8}"], amount_mode="round"),
    ]),
    I("ridgeline-auto-sales", "Ridgeline Auto Sales", ["Ridgeline Auto Sales"], ["RIDGELINE AUTO SALES"], [
        U("vehicle_purchase", "spend", "6000.00", "42000.00", "1510", "US-R045", ["Work truck purchase", "Cargo van purchase", "Down payment, work truck"], needs_line=True),
    ], fmt="US-WIRE", refs=["VIN {A6}"]),
    I("pinecrest-auto-leasing", "Pinecrest Auto Leasing", ["Pinecrest Auto Leasing"], ["PINECREST AUTO LEASE"], [
        U("vehicle_lease", "spend", "280.00", "760.00", "655", "US-R044", ["Truck lease payment", "Van lease {MMM}", ""], hooks=["US-R044", "US-R043"], only={"vehicle": True}, amount_mode="fixed"),
    ], refs=["LSE{K7}"]),
    I("golden-basket-gift-co", "Golden Basket Gift Co", ["Golden Basket Gift Co"], ["GOLDEN BASKET GIFT"], [
        U("client_gift", "spend", "40.00", "420.00", "715", "US-R020", ["Holiday gift baskets for clients", "Thank you basket, client referral"], needs_line=True, facts={"stated": True}),
    ], fmt="US-CARD"),
    I("bloom-and-stem-florist", "Bloom and Stem Florist", ["Bloom and Stem Florist", "SQ *BLOOM AND STEM"], ["SQ *BLOOM AND STEM"], [
        U("client_gift", "spend", "45.00", "180.00", "715", "US-R020", ["Flowers for client opening", "Sympathy flowers, client"], routine=True, needs_line=True, facts={"stated": True}),
    ], fmt="US-CARD", category="small_seller"),
    I("brightline-promo", "Brightline Promo Products", ["Brightline Promo Products"], ["BRIGHTLINE PROMO"], [
        U("promo_items", "spend", "80.00", "600.00", "600", "US-R021", ["Imprinted pens for customers", "Logo koozies for expo", "Counter display rack for retailer"], needs_line=True),
    ], fmt="US-CARD"),
    I("fairway-hills-country-club", "Fairway Hills Country Club", ["Fairway Hills Country Club"], ["FAIRWAY HILLS CC"], [
        U("club_dues", "spend", "150.00", "900.00", "790", "US-R015", ["Country club dues", "Quarterly country club dues", "Fairway Hills club dues"], needs_line=True, facts={"club": True}),
        U("golf_with_client", "spend", "90.00", "480.00", "790", "US-R012", ["Golf with client", "Green fees, client outing"], needs_line=True),
    ], fmt="US-CARD"),
    I("mountain-states-builders-assn", "Mountain States Builders Association", ["Mountain States Builders Association"], ["MTN STATES BLDRS ASSN"], [
        U("dues", "spend", "120.00", "650.00", "710", "US-R015", ["Builders association annual dues", "Trade association membership dues"], routine=True, facts={"club": False}, only={"trades": ["construction", "trades"]}),
    ]),
    I("chamber-of-commerce-maple-ridge", "Maple Ridge Chamber of Commerce", ["Maple Ridge Chamber of Commerce"], ["MAPLE RIDGE CHAMBER"], [
        U("dues", "spend", "150.00", "500.00", "710", "US-R191", ["Chamber of commerce membership", "Annual chamber dues"], routine=True, amount_mode="whole"),
    ]),
    I("summit-continuing-ed", "Summit Continuing Education", ["Summit Continuing Education"], ["SUMMIT CONT ED"], [
        U("course", "spend", "90.00", "650.00", "710", "US-R191", ["Continuing education course", "License renewal CE hours", "Bookkeeping certificate course"], routine=True),
    ], fmt="US-CARD"),
    I("lakeshore-ballpark", "Lakeshore Ballpark Box Office", ["Lakeshore Ballpark Box Office"], ["LAKESHORE BALLPARK"], [
        U("client_tickets", "spend", "80.00", "600.00", "790", "US-R012", ["Game tickets with client", "Suite tickets, client night"], needs_line=True),
        U("stadium_food", "spend", "25.00", "180.00", "685", "US-R013", ["Food at game with client, billed separately", "Concessions with client, separate receipt"], needs_line=True, facts={"separately_stated": True}),
        U("stadium_package", "spend", "180.00", "900.00", "790", "US-R013", ["Suite package with food and drinks, client"], needs_line=True, facts={"separately_stated": False}),
    ], fmt="US-CARD"),
    # Staff party amounts are drawn per head in scenarios_us (R16); the range here only bounds history rows.
    I("copper-bell-tavern", "Copper Bell Tavern", ["Copper Bell Tavern", "TST* COPPER BELL TAVERN"], ["TST* COPPER BELL TAVERN"], _food_uses_us("20.00", "260.00", routine=True) + [
        U("staff_party", "spend", "120.00", "900.00", "720", "US-R014", ["Team holiday party", "Staff summer picnic catering"], needs_line=True, only={"employer": True}),
    ], fmt="US-CARD", category="small_seller"),
    I("blue-heron-bistro", "Blue Heron Bistro", ["Blue Heron Bistro", "SQ *BLUE HERON BISTRO"], ["SQ *BLUE HERON BISTRO"], _food_uses_us("18.00", "220.00", routine=True), fmt="US-CARD", category="small_seller"),
    I("prairie-smoke-bbq", "Prairie Smoke BBQ", ["Prairie Smoke BBQ", "TST* PRAIRIE SMOKE BBQ"], ["TST* PRAIRIE SMOKE BBQ"], _food_uses_us("15.00", "380.00", routine=True) + [
        U("staff_party", "spend", "120.00", "900.00", "720", "US-R014", ["Staff summer picnic, crew and families", "Team holiday party catering"], needs_line=True, only={"employer": True}),
    ], fmt="US-CARD", category="small_seller"),
    I("riverbend-food-pantry", "Riverbend Food Pantry", ["Riverbend Food Pantry"], ["RIVERBEND FOOD PANTRY"], [
        U("donation", "spend", "100.00", "500.00", "3010", "US-R180", ["Donation to Riverbend Food Pantry", "Year end donation, food pantry"], routine=True, only={"entity": ["sole_prop", "smllc"]}, amount_mode="round"),
        U("sponsorship", "spend", "200.00", "900.00", "600", "US-R181", ["Sponsorship, logo on 5K banner", "Program ad, gala"], needs_line=True, amount_mode="round"),
    ], fmt="US-CARD"),
    I("committee-to-elect", "Citizens for Maple Ridge Parks", ["Citizens for Maple Ridge Parks"], ["CITIZENS FOR MAPLE"], [
        U("political", "spend", "100.00", "500.00", "3010", "US-R182", ["Campaign contribution", "Ballot measure committee donation"], needs_line=True, amount_mode="round"),
    ], fmt="US-CARD"),
    I("keystone-retirement-plans", "Keystone Retirement Plans", ["Keystone Retirement Plans"], ["KEYSTONE RETIREMENT"], [
        U("employee_plan", "spend", "200.00", "2400.00", "650", "US-R073", ["SIMPLE IRA employer match", "Employer contributions, staff plan"], needs_line=True, only={"employer": True}),
        U("owner_plan", "spend", "300.00", "6000.00", "3010", "US-R073", ["SEP-IRA contribution, owner", "Solo 401k deferral, owner"], needs_line=True, facts={"for_owner": True}, only={"entity": ["sole_prop", "smllc"]}),
    ], refs=["PLAN {N6}"]),
    I("metro-park-garages", "Metro Park Garages", ["Metro Park Garages"], ["METRO PARK GARAGE {N4} {CITY} {ST}"], [
        U("parking", "spend", "4.00", "38.00", "605", "US-R042", ["Parking, client meeting downtown", "Parking at job site", "Garage, supplier visit"], routine=True, needs_line=True),
        U("commute_parking", "spend", "90.00", "260.00", "3010", "US-R032", ["Monthly parking, own office building", "Monthly garage pass at office"], needs_line=True),
    ], fmt="US-CARD"),
    I("cityworks-repair", "Cityworks Equipment Repair", ["Cityworks Equipment Repair"], ["CITYWORKS EQUIP REPAIR"], [
        U("repair", "spend", "60.00", "900.00", "665", "US-R052", ["Repair of commercial mixer", "Compressor repair", "HVAC service call, shop"], needs_line=True, facts={"scope": "repair"}),
        U("improvement", "spend", "3000.00", "14000.00", "1500", "US-R052", ["New rooftop HVAC unit", "Replace walk-in cooler compressor system"], needs_line=True, facts={"scope": "improvement"}),
        U("unknown_scope", "spend", "2800.00", "12000.00", "NEEDS_REVIEW", "US-R052", ["", "Work per estimate"], facts={"scope": "unknown"}),
    ], refs=["INV {N5}"]),
    # Customers. One invoice number per record ({N6} is shared by the line, the reference and the bank line), and
    # the reference is typed by the customer, so part of it is lower case (shortcut S-1, audit round 2). A credit
    # union is also a lender, so its receipts always carry the invoice line (F2).
    *[I(slug, name, [name], [narr], [
        U("customer_receipt", "receive", lo, hi, "400", "US-R001", RECEIPT_LINES if slug not in LENDER_LIKE_CUSTOMERS else RECEIPT_LINES[:2], routine=True, needs_line=slug in LENDER_LIKE_CUSTOMERS, facts={"account": "400"}, refs=RECEIPT_REFS, only={"trades": CUSTOMER_TRADES[slug]}),
        U("customer_refund", "spend", "25.00", "600.00", "405", "US-R130", ["Refund to customer, {INV}", "Partial refund, damaged order"], needs_line=True, refs=["REFUND {N4}"], only={"trades": CUSTOMER_TRADES[slug]}),
        *_penalty_uses(slug),
    ], category="customer") for slug, name, narr, lo, hi in [
        ("silver-birch-dental", "Silver Birch Dental Group", "SILVER BIRCH DENTAL", "200.00", "4800.00"),
        ("prairie-wind-realty", "Prairie Wind Realty", "PRAIRIE WIND REALTY", "150.00", "3600.00"),
        ("lakeside-montessori", "Lakeside Montessori School", "LAKESIDE MONTESSORI", "300.00", "5200.00"),
        ("ironwood-property-mgmt", "Ironwood Property Management", "IRONWOOD PROPERTY", "250.00", "7800.00"),
        ("bayview-veterinary", "Bayview Veterinary Clinic", "BAYVIEW VETERINARY", "120.00", "2800.00"),
        ("crescent-moon-yoga", "Crescent Moon Yoga Studio", "CRESCENT MOON YOGA", "80.00", "1600.00"),
        ("timberline-outfitters", "Timberline Outfitters", "TIMBERLINE OUTFITTERS", "200.00", "6400.00"),
        # Renamed from a name close to a real credit union; the new name was web-checked (2026-10-15).
        ("bramblewood-credit-union", "Bramblewood Community Credit Union", "BRAMBLEWOOD CMTY CU", "400.00", "9000.00"),
    ]],
    # Government payees
    I("irs", "Internal Revenue Service", ["Internal Revenue Service", "IRS"], ["IRS DES:USATAXPYMT ID:{N15}", "IRS USATAXPYMT"], [
        U("estimate_with_form", "spend", "400.00", "9000.00", "3010", "US-R080", ["Estimated tax payment", ""], refs=["1040ES {YEAR} Q{Q}", "1040-ES Q{Q}"], facts={"form_id": True}),
        U("estimate_no_form", "spend", "400.00", "8000.00", "3010", "US-R080", [""], refs=["", "{N15}"], only={"payroll": "none"}),
        U("payroll_deposit", "spend", "300.00", "6500.00", "2200", "US-R083", ["941 deposit", "Form 941 tax deposit"], needs_line=True, only={"payroll_any": True}),
        U("ambiguous", "spend", "300.00", "6000.00", "NEEDS_REVIEW", "US-R082", [""], refs=["", "{N15}"], only={"payroll_any": True}),
        U("personal_penalty", "spend", "40.00", "600.00", "3010", "US-R086", ["Penalty on personal 1040 balance", "Late payment penalty, owner 1040"], needs_line=True, facts={"personal_tax_penalty": True, "line_states": True}),
    ], kind="government", category="government"),
    I("state-revenue", "State Department of Revenue", ["{STATE_REV}"], ["{STATE_REV_SHORT} DES:TAX PYMT"], [
        U("sales_tax", "spend", "120.00", "4800.00", "2100", "US-R091", ["Sales tax return {MMM}", "Sales and use tax"], only={"sales_tax": "collects_buyer_imposed"}, refs=["SALES TAX {N8}", "ST {N9}"]),
        U("gross_receipts_tax", "spend", "150.00", "3800.00", "675", "US-R092", ["Gross receipts tax", "GRT return"], only={"sales_tax": "seller_imposed"}, refs=["GRT {N9}"]),
        U("owner_estimate", "spend", "200.00", "3000.00", "3010", "US-R081", ["Individual estimated tax", ""], facts={"line_states": True}, refs=["IND EST {N8}"]),
        U("owner_refund", "receive", "60.00", "1800.00", "3000", "US-R081", ["Individual income tax refund", ""], facts={"line_states": True}, refs=["IND REFUND {N8}"]),
    ], kind="government", category="government"),
    I("city-licensing", "City Business Licensing Office", ["City of {CITY_NAME}"], ["CITY OF {CITY_UP} LICENSE"], [
        U("licence", "spend", "50.00", "650.00", "675", "US-R085", ["Business license renewal", "Annual business license", "City business license fee"], routine=True),
        U("parking_ticket", "spend", "35.00", "120.00", "790", "US-R086", ["Parking ticket, work truck", "Parking citation"], needs_line=True),
    ], kind="government", category="government", fmt="US-CARD"),
    I("usps", "United States Postal Service", ["USPS"], ["USPS PO {N10} {CITY} {ST}", "USPS KIOSK {N10} {CITY} {ST}"], [
        U("postage", "spend", "3.00", "90.00", "645", "US-R054", ["Postage", "Stamps", "Certified mail"], routine=True, facts={"office": True}),
    ], kind="government", category="government", fmt="US-CARD"),
]


def _p(entity, naics, label, state, city, *, sector, vehicle="none", de_minimis=True, sales_recording="bank_deposit_net",
       sales_tax="none", payroll="none", inventory=False, mortgage=False, card="2000", savings=True, processors=(),
       premises=False, home_office="none", employees=0, contractors=0, gaps=(), goods=False):
    return {
        "entity_type": entity,
        "trade": {"naics_2022": naics, "label": label, "tag": sector},
        "state": state,
        "city": city,
        "accounting_basis": "cash",
        "policies": {
            "vehicle_method": vehicle,
            "de_minimis_election": de_minimis,
            "sales_recording": sales_recording,
            "sales_tax": sales_tax,
            "payroll": payroll,
            "inventory": inventory,
            "business_property_mortgage": mortgage,
            "card_account": card,
            "savings_account": savings,
            "processors": list(processors),
            "premises": premises,
            "home_office": home_office,
            "goods": goods or inventory,
        },
        "employees": employees,
        "subcontractors": contractors,
        "policy_gaps": list(gaps),
    }


FIRMS = {
    "us-01": ("Prairie Lantern Design LLC", "dev", _p("smllc", "541430", "Graphic design services", "CO", "Fort Collins", sector="creative", vehicle="standard_mileage", sales_recording="processor_gross", processors=["us-stripe"], home_office="simplified_method", contractors=1)),
    "us-02": ("Bluegill Plumbing and Drain", "dev", _p("sole_prop", "238220", "Plumbing, heating, and air-conditioning contractors", "OH", "Dayton", sector="construction", vehicle="actual", processors=["us-square"], inventory=True, contractors=1, card="none")),
    "us-03": ("Summit Ridge Consulting Inc", "dev", _p("s_corp", "541611", "Administrative management consulting services", "TX", "Austin", sector="professional", vehicle="standard_mileage", payroll="us-gusto", processors=["us-stripe"])),
    "us-04": ("Cedar Hollow Candle Co LLC", "test", _p("smllc", "339999", "All other miscellaneous manufacturing", "VT", "Burlington", sector="crafts", sales_recording="processor_gross", sales_tax="collects_buyer_imposed", processors=["us-stripe", "us-paypal"], inventory=True, premises=True)),
    "us-05": ("Northfork Landscaping", "test", _p("sole_prop", "561730", "Landscaping services", "GA", "Macon", sector="trades", vehicle="actual", payroll="us-adp", employees=2, de_minimis=False, gaps=["vehicle_method"])),
    "us-06": ("Tall Pines Bakery LLC", "test", _p("smllc", "311811", "Retail bakeries", "WA", "Spokane", sector="catering", sales_tax="collects_buyer_imposed", payroll="us-gusto", employees=3, processors=["us-square"], inventory=True, premises=True)),
    "us-07": ("Granite Bay Builders Inc", "test", _p("s_corp", "236118", "Residential remodelers", "AZ", "Flagstaff", sector="construction", vehicle="actual", de_minimis=False, payroll="us-paychex", employees=4, inventory=True, mortgage=True, premises=True, contractors=2)),
    "us-08": ("Kettle Creek Photography", "dev", _p("sole_prop", "541921", "Photography studios, portrait", "OR", "Bend", sector="creative", vehicle="standard_mileage", sales_recording="processor_gross", processors=["us-paypal"])),
    "us-09": ("Lumen Tutoring Services", "test", _p("sole_prop", "611691", "Exam preparation and tutoring", "IL", "Peoria", sector="education", home_office="regular_method", card="none", savings=False)),
    "us-10": ("Copperline HVAC Inc", "test", _p("s_corp", "238220", "Plumbing, heating, and air-conditioning contractors", "NM", "Las Cruces", sector="construction", vehicle="actual", sales_tax="seller_imposed", payroll="us-gusto", employees=3, inventory=True, premises=True)),
    "us-11": ("Riverstone Bookkeeping LLC", "dev", _p("smllc", "541219", "Other accounting services", "MN", "Duluth", sector="professional", processors=["us-stripe"], home_office="simplified_method")),
    "us-12": ("Maple and Moss Floral Studio", "test", _p("sole_prop", "459310", "Florists", "NC", "Asheville", sector="retail", vehicle="actual", sales_recording="processor_gross", sales_tax="collects_buyer_imposed", processors=["us-square"], inventory=True, premises=True, gaps=["sales_recording"])),
    # v0.2 (choice S6): 18 firms, dev 7 and test 11; 6 processor_gross and 12 bank_deposit_net, both in each split.
    "us-13": ("Quarry Lane Pressure Washing", "dev", _p("sole_prop", "561790", "Other services to buildings and dwellings", "MO", "Springfield", sector="trades", vehicle="actual", processors=["us-square"])),
    "us-14": ("Gristmill Hill Soap Works LLC", "dev", _p("smllc", "325620", "Toilet preparation manufacturing", "PA", "Lancaster", sector="crafts", sales_recording="processor_gross", sales_tax="collects_buyer_imposed", processors=["us-stripe"], inventory=True, home_office="simplified_method")),
    "us-15": ("Larkspur Network Solutions Inc", "test", _p("s_corp", "541512", "Computer systems design services", "WI", "Eau Claire", sector="professional", vehicle="standard_mileage", payroll="us-adp", employees=2, processors=["us-stripe"], premises=True)),
    "us-16": ("Sagebrush Skillet Food Truck", "test", _p("sole_prop", "722330", "Mobile food services", "UT", "Ogden", sector="catering", vehicle="actual", sales_recording="processor_gross", sales_tax="collects_buyer_imposed", payroll="us-gusto", employees=1, processors=["us-square"], inventory=True)),
    "us-17": ("Juniper Reel Video LLC", "test", _p("smllc", "512110", "Motion picture and video production", "ID", "Boise", sector="creative", vehicle="standard_mileage", processors=["us-paypal"], home_office="simplified_method", contractors=1)),
    "us-18": ("Kinnick Hill Handyman Services", "test", _p("sole_prop", "238990", "All other specialty trade contractors", "ME", "Bangor", sector="trades", vehicle="actual", de_minimis=False, card="none", contractors=1)),
}

STATE_REVENUE = {
    "CO": ("Colorado Department of Revenue", "CO DEPT REVENUE"),
    "OH": ("Ohio Department of Taxation", "OHIO DEPT TAX"),
    "TX": ("Texas Comptroller", "TX COMPTROLLER"),
    "VT": ("Vermont Department of Taxes", "VT DEPT OF TAXES"),
    "GA": ("Georgia Department of Revenue", "GA DEPT OF REV"),
    "WA": ("Washington Department of Revenue", "WA ST DEPT REV"),
    "AZ": ("Arizona Department of Revenue", "AZ DEPT OF REV"),
    "OR": ("Oregon Department of Revenue", "OREGON DOR"),
    "IL": ("Illinois Department of Revenue", "IL DEPT OF REV"),
    "NM": ("New Mexico Taxation and Revenue", "NM TAXATION REV"),
    "MN": ("Minnesota Department of Revenue", "MN DEPT OF REV"),
    "NC": ("North Carolina Department of Revenue", "NC DEPT REVENUE"),
    "MO": ("Missouri Department of Revenue", "MO DEPT OF REV"),
    "PA": ("Pennsylvania Department of Revenue", "PA DEPT REVENUE"),
    "WI": ("Wisconsin Department of Revenue", "WI DEPT REVENUE"),
    "UT": ("Utah State Tax Commission", "UT STATE TAX COMM"),
    "ID": ("Idaho State Tax Commission", "ID STATE TAX COMM"),
    "ME": ("Maine Revenue Services", "MAINE REVENUE SVCS"),
}
# States with no individual income tax on wages and business income in 2025: no owner estimate or refund there.
NO_PERSONAL_INCOME_TAX = {"AK", "FL", "NV", "NH", "SD", "TN", "TX", "WA", "WY"}

# R18 (audit round 2): payroll is sized to headcount and fixed per person. One pay run's net pay is the sum of a
# fixed amount per person on the payroll (each with at most one price step, as for other `fixed` uses), and the
# payroll tax debit is a firm-constant share of that net. The S corp officer is on the payroll; a sole proprietor
# or SMLLC owner never is. Ranges are net pay per person per biweekly run, by trade.
NET_PAY_PER_PERSON = {
    "catering": ("620.00", "1150.00"),
    "retail": ("620.00", "1150.00"),
    "trades": ("850.00", "1600.00"),
    "construction": ("1050.00", "2000.00"),
    "professional": ("1600.00", "3000.00"),
    "creative": ("1100.00", "2200.00"),
}
NET_PAY_DEFAULT = ("850.00", "1700.00")
NET_PAY_OFFICER = ("2400.00", "5200.00")
PAYROLL_TAX_SHARE = (30, 42)  # percent of net pay: withholding plus both halves of FICA and unemployment


def payroll_people(firm: dict) -> list[tuple[str, tuple[str, str]]]:
    ppl = firm["people"]
    out = [(o, NET_PAY_OFFICER) for o in ppl["owners"]] if firm["entity_type"] == "s_corp" else []
    staff = NET_PAY_PER_PERSON.get(firm["trade"]["tag"], NET_PAY_DEFAULT)
    return out + [(e, staff) for e in ppl["employees"]]


def payroll_amount(env, firm: dict, merchant: dict, kind: str, date, who: str | None = None) -> Decimal:
    """Unsigned net pay (`kind="net"`) or payroll tax (`kind="tax"`) of one pay run on `date`; `who` ("officer" or
    "staff") keeps only that part of the net pay, for an S corp that books officers and staff apart.

    Each person's net pay follows the engine's fixed plan (`Env._fixed_plan`, seeded by run, firm, provider and
    person), so it is constant per firm with at most one price step. The plan is read, not logged: the F8 log keys
    on catalogue uses. History rows for the payroll provider should call this too, so they agree with the items.
    """
    people = payroll_people(firm)
    if who is not None:
        officers = set(firm["people"]["owners"]) if firm["entity_type"] == "s_corp" else set()
        people = [(n, r) for n, r in people if (n in officers) == (who == "officer")]
    if not people:
        raise ValueError(f"{firm['firm_id']} has nobody on the payroll")
    net = Decimal("0.00")
    for name, (lo, hi) in people:
        pseudo = {"use": f"net_pay:{name}", "amount_range": [lo, hi], "amount_mode": "fixed"}
        base, step_date, stepped = env._fixed_plan(firm, merchant["merchant_id"], pseudo)
        net += stepped if step_date is not None and date >= step_date else base
    if kind == "net":
        return net
    share = random.Random(f"{firm['firm_id']}:payroll_tax_share").randint(*PAYROLL_TAX_SHARE)
    return (net * share / 100).quantize(Decimal("0.01"))
