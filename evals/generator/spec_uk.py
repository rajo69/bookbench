"""UK merchant catalogue and firm profiles (source of truth for catalogue_uk.json and the UK half of firms.json).

Brand merchants link to `sources/brands_uk.json` by `brand_id`. Every other name is invented. Government payees
(HMRC, DVLA, ICO, Companies House) use kind `government`. Placeholders in braces are filled by templates.py.
"""

from __future__ import annotations

from decimal import Decimal

from .spec_common import U, make_builders

B, I = make_builders("UK")

CONSTRUCTION = ["construction", "trades"]
GOODS = ["catering", "retail", "crafts", "construction", "trades", "manufacturing"]

_SAAS = [
    ("uk-google-workspace", ["Google Workspace", "Google"], ["GOOGLE *GSUITE_{A6}"], ["Google Workspace licences", "Email and storage, {MMM}", "Workspace subscription"], "5.00", "60.00"),
    ("uk-microsoft-365", ["Microsoft 365", "Microsoft"], ["MSFT *{A8}", "MICROSOFT*365"], ["Microsoft 365 Business", "Office licences {MMM}"], "5.00", "75.00"),
    ("uk-adobe", ["Adobe"], ["ADOBE *CREATIVE CLOUD"], ["Creative Cloud subscription", "Acrobat Pro monthly"], "12.00", "65.00"),
    ("uk-canva", ["Canva"], ["CANVA* I0{N7}"], ["Canva Pro", "Canva team plan"], "10.00", "30.00"),
    ("uk-zoom", ["Zoom"], ["ZOOM.US 888-799-9666"], ["Zoom Pro licence", "Video calls subscription"], "12.00", "40.00"),
    ("uk-dropbox", ["Dropbox"], ["DROPBOX*{A4}"], ["Dropbox Business", "Cloud storage {MMM}"], "9.00", "45.00"),
    ("uk-slack", ["Slack"], ["SLACK T0{A5}"], ["Slack Pro seats"], "6.00", "40.00"),
    ("uk-squarespace", ["Squarespace"], ["SQSP* INV{N6}"], ["Website plan", "Squarespace annual site plan"], "15.00", "220.00"),
    ("uk-wix-com", ["Wix.com", "Wix"], ["WIX.COM {N8}"], ["Website premium plan"], "10.00", "180.00"),
    ("uk-godaddy", ["GoDaddy"], ["GODADDY.COM"], ["Domain renewal", "Domain and hosting"], "12.00", "160.00"),
    ("uk-123-reg", ["123 Reg"], ["123-REG.CO.UK"], ["Domain renewal .co.uk", "Hosting package"], "9.00", "90.00"),
    ("uk-mailchimp", ["Mailchimp"], ["MAILCHIMP *MONTHLY"], ["Newsletter platform", "Mailchimp Standard"], "12.00", "60.00"),
    ("uk-calendly", ["Calendly"], ["CALENDLY"], ["Booking software"], "8.00", "16.00"),
    ("uk-docusign", ["Docusign"], ["DOCUSIGN INC"], ["E-signature plan"], "10.00", "45.00"),
    ("uk-hubspot", ["HubSpot"], ["HUBSPOT {N8}"], ["CRM Starter"], "15.00", "90.00"),
    ("uk-atlassian", ["Atlassian"], ["ATLASSIAN {A6}"], ["Jira licences"], "7.00", "70.00"),
    ("uk-amazon-web-services", ["Amazon Web Services", "AWS"], ["AWS EMEA"], ["Cloud hosting {MMM}", "AWS hosting"], "3.00", "140.00"),
    ("uk-salesforce", ["Salesforce"], ["SALESFORCE UK"], ["CRM licences"], "20.00", "150.00"),
]
_ACCOUNTING_SW = [
    ("uk-xero", ["Xero"], ["XERO UK"], ["Xero subscription", "Accounting software {MMM}"], "15.00", "65.00"),
    ("uk-quickbooks", ["QuickBooks", "Intuit"], ["INTUIT *QBOOKS ONLINE"], ["QuickBooks Online"], "12.00", "50.00"),
    ("uk-freeagent", ["FreeAgent"], ["FREEAGENT"], ["FreeAgent subscription"], "19.00", "40.00"),
    ("uk-sage", ["Sage"], ["SAGE UK LTD"], ["Sage Accounting plan"], "12.00", "45.00"),
]

MERCHANTS: list[dict] = []
CUSTOMER_REFS = ["{INV}", "{INV} thanks", "paid {INV}", "{FIRMREF}", "{FIRMREF} thanks"]
# Which firms (by trade tag) each business customer plausibly buys from. The `services` firm is a personal service
# (dog grooming), so only the holiday lets buy from it (re-audit R3, N4).
CUSTOMER_TRADES = {
    "kestrel-print-co": ["creative", "professional", "events", "education", "crafts"],
    "ashcombe-dental": ["construction", "trades", "professional", "health", "creative", "manufacturing"],
    "fairhaven-cafe": ["catering", "crafts", "retail", "creative", "trades"],
    "moorside-veterinary": ["health", "trades", "construction", "catering"],
    "elmstead-academy-trust": ["education", "catering", "construction", "trades", "events", "creative"],
    "rookwood-estates": ["construction", "trades", "professional", "manufacturing"],
    "pennant-engineering": ["manufacturing", "construction", "trades", "professional", "transport"],
    "bluebell-day-nursery": ["catering", "education", "health", "construction"],
    "tidewater-marine": ["manufacturing", "trades", "transport", "professional", "events"],
    "lakeview-holiday-lets": ["services", "catering", "trades", "creative", "beauty", "events", "transport", "retail", "crafts"],
}

# Monthly subscriptions bill one amount per firm (F8); annual plans, domains and usage-billed hosting do not.
_NOT_MONTHLY = {"uk-squarespace", "uk-wix-com", "uk-godaddy", "uk-123-reg", "uk-amazon-web-services"}
for bid, contacts, narrs, lines, lo, hi in _SAAS:
    MERCHANTS.append(B(bid, contacts, narrs, [U("software", "spend", lo, hi, "463", "UK-R041", lines, routine=True,
                                                 amount_mode="range" if bid in _NOT_MONTHLY else "fixed")]))
for bid, contacts, narrs, lines, lo, hi in _ACCOUNTING_SW:
    MERCHANTS.append(B(bid, contacts, narrs, [U("software", "spend", lo, hi, "463", "UK-R041", lines, routine=True,
                                                 facts={"accounting_software": True}, amount_mode="fixed")]))

MERCHANTS += [
    B("uk-shopify", ["Shopify"], ["SHOPIFY* {N9}"], [U("software", "spend", "19.00", "89.00", "463", "UK-R041", ["Shopify plan", "Online shop plan {MMM}"], routine=True, amount_mode="fixed")]),
    # Advertising
    B("uk-google-ads", ["Google Ads", "Google Ireland"], ["GOOGLE *ADS{N10}"], [
        U("ads", "spend", "25.00", "600.00", "400", ["UK-R043", "UK-R056"], ["Google Ads campaign", "Search ads {MMM}", "Pay per click ads"], routine=True, facts={"account": "400"}),
    ], refs=["ADS {N4}", ""]),
    B("uk-meta-platforms", ["Meta Ads", "Facebook Ads"], ["FACEBK *{A9}"], [
        U("ads", "spend", "20.00", "450.00", "400", ["UK-R043", "UK-R056"], ["Facebook and Instagram ads", "Social ads boost"], routine=True, facts={"account": "400"}),
    ]),
    B("uk-yell", ["Yell"], ["YELL LTD"], [U("ads", "spend", "30.00", "180.00", "400", "UK-R056", ["Directory listing", "Yell advert monthly"], routine=True)], fmt="UK-DD", refs=["YL{N8}"]),
    B("uk-vistaprint", ["Vistaprint"], ["VISTAPRINT"], [
        U("print_marketing", "spend", "18.00", "240.00", "400", "UK-R056", ["Leaflets for marketing", "Business cards", "Flyers, spring offer"], routine=True),
        U("branded_gifts", "spend", "40.00", "260.00", "400", "UK-R030", ["Branded pens for customers", "Logo mugs for trade show giveaways", "Branded notepads"], needs_line=True),
    ]),
    B("uk-linkedin", ["LinkedIn"], ["LINKEDIN *{A8}"], [
        U("ads", "spend", "40.00", "400.00", "400", ["UK-R043", "UK-R056"], ["LinkedIn sponsored posts", "LinkedIn ads campaign"], routine=True, needs_line=True, facts={"account": "400"}),
        U("learning", "spend", "25.00", "40.00", "480", "UK-R052", ["LinkedIn Learning, staff course"], needs_line=True),
    ]),
    # Telecoms
    *[B(bid, contacts, narrs, [
        U("business_contract", "spend", lo, hi, "489", "UK-R033", ["Business broadband", "Office phone line", "Business mobile plan", "Fibre broadband"], facts={"contract": "business"}, routine=True, needs_line=True, amount_mode="fixed"),
        U("personal_contract", "spend", lo, hi, "489", "UK-R033", ["Mobile contract", ""], hooks=["UK-R033"], facts={"contract": "personal"}, amount_mode="fixed"),
        U("director_contract", "spend", lo, hi, "489", "UK-R033", ["Mobile, director", "Director phone contract", "Phone for director", "Mobile contract, director use", ""], hooks=["UK-R033"], facts={"contract": "director_personal"}, only={"entity": ["limited_company"]}, amount_mode="fixed"),
    ], fmt="UK-DD", refs=refs) for bid, contacts, narrs, lo, hi, refs in [
        ("uk-bt", ["BT", "BT Business"], ["BT GROUP PLC"], "28.00", "95.00", ["{K10}"]),
        ("uk-ee", ["EE"], ["EE LIMITED"], "12.00", "65.00", ["{K10}"]),
        ("uk-o2", ["O2"], ["O2"], "10.00", "55.00", ["{K9}"]),
        ("uk-vodafone", ["Vodafone"], ["VODAFONE LTD"], "12.00", "60.00", ["{K10}"]),
        ("uk-three", ["Three"], ["THREE"], "10.00", "40.00", ["{K9}"]),
        ("uk-sky", ["Sky", "Sky Broadband"], ["SKY DIGITAL"], "25.00", "80.00", ["{K10}"]),
        ("uk-virgin-media", ["Virgin Media"], ["VIRGIN MEDIA PYMTS"], "30.00", "90.00", ["{K9}"]),
        ("uk-talktalk", ["TalkTalk"], ["TALKTALK LIMITED"], "22.00", "50.00", ["{K10}"]),
        ("uk-plusnet", ["Plusnet"], ["PLUSNET PLC PAY AC"], "20.00", "45.00", ["{K8}"]),
        ("uk-giffgaff", ["giffgaff"], ["GIFFGAFF"], "8.00", "25.00", [""]),
    ]],
    # Energy and water
    *[B(bid, contacts, narrs, [
        U("premises_energy", "spend", lo, hi, "445", "UK-R037", ["Electricity, workshop", "Gas, business unit", "Energy, shop premises"], facts={"account": "445", "line_states": True}, needs_line=True, only={"premises": True}, hooks=["UK-R037"]),
        U("household_energy", "spend", "45.00", "190.00", "980", "UK-R036", ["", "Home energy"], hooks=["UK-R036"]),
    ], fmt="UK-DD", refs=["{K11}"]) for bid, contacts, narrs, lo, hi in [
        ("uk-british-gas", ["British Gas"], ["BRITISH GAS"], "60.00", "420.00"),
        ("uk-edf", ["EDF"], ["EDF ENERGY"], "60.00", "380.00"),
        ("uk-octopus-energy", ["Octopus Energy"], ["OCTOPUS ENERGY"], "50.00", "350.00"),
        ("uk-ovo-energy", ["OVO Energy"], ["OVO ENERGY"], "50.00", "300.00"),
        ("uk-e-on", ["E.ON Next", "E.ON"], ["EON NEXT"], "55.00", "340.00"),
        ("uk-scottishpower", ["ScottishPower"], ["SCOTTISHPOWER"], "60.00", "360.00"),
        ("uk-good-energy", ["Good Energy"], ["GOOD ENERGY LTD"], "45.00", "260.00"),
    ]],
    B("uk-water-plus", ["Water Plus"], ["WATERPLUS"], [U("premises_water", "spend", "25.00", "140.00", "445", "UK-R037", ["Water, business premises", "Water and sewerage, unit"], facts={"account": "445", "line_states": True}, only={"premises": True}, hooks=["UK-R037"])], fmt="UK-DD", refs=["{K10}"]),
    *[B(bid, contacts, narrs, [
        U("household_water", "spend", "25.00", "70.00", "980", "UK-R036", ["", "Water bill"], hooks=["UK-R036"]),
    ], fmt="UK-DD", refs=["{K10}"]) for bid, contacts, narrs in [
        ("uk-thames-water", ["Thames Water"], ["THAMES WATER"]),
        ("uk-severn-trent", ["Severn Trent"], ["SEVERN TRENT WATER"]),
        ("uk-anglian-water", ["Anglian Water"], ["ANGLIAN WATER"]),
        ("uk-yorkshire-water", ["Yorkshire Water"], ["YORKSHIRE WATER"]),
        ("uk-welsh-water", ["Welsh Water", "Dwr Cymru"], ["DWR CYMRU W WATER"]),
    ]],
    # Fuel, EV charging, vehicle running costs
    *[B(bid, contacts, narrs, [
        U("fuel", "spend", "20.00", "110.00", "449", "UK-R034", ["Fuel", "Diesel", "Diesel for van", "Petrol", ""], hooks=["UK-R034"], only={"vehicle": True}),
    ], category="fuel") for bid, contacts, narrs in [
        ("uk-shell", ["Shell"], ["SHELL {TOWN}", "SHELL {N4} {TOWN}"]),
        ("uk-bp", ["BP"], ["BP {TOWN}", "BP CONNECT {N4}"]),
        ("uk-esso", ["Esso"], ["ESSO {TOWN}"]),
        ("uk-texaco", ["Texaco"], ["TEXACO {TOWN}"]),
        ("uk-applegreen", ["Applegreen"], ["APPLEGREEN {N4}"]),
        ("uk-murco", ["Murco"], ["MURCO {TOWN}"]),
        ("uk-eg-on-the-move", ["EG On the Move"], ["EG {TOWN}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("ev_charging", "spend", "8.00", "45.00", "449", "UK-R034", ["EV charging", "Charging, van", ""], hooks=["UK-R034"], only={"vehicle": True}),
    ], category="fuel") for bid, contacts, narrs in [
        ("uk-bp-pulse", ["bp pulse"], ["BP PULSE {N6}"]),
        ("uk-gridserve", ["Gridserve"], ["GRIDSERVE {TOWN}"]),
        ("uk-tesla", ["Tesla"], ["TESLA SUPERCHARGER"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("repair", "spend", lo, hi, "449", "UK-R001", lines, facts={"account": "449"}, routine=True, only={"vehicle_methods": ["actual_costs", "taxi_cost_of_sales"]}),
    ]) for bid, contacts, narrs, lines, lo, hi in [
        ("uk-kwik-fit", ["Kwik Fit"], ["KWIK FIT {N4}"], ["Two tyres, van", "MOT and brake pads", "Tyre replacement"], "45.00", "420.00"),
        ("uk-halfords", ["Halfords"], ["HALFORDS {N4}"], ["Wiper blades and bulbs, van", "Car service"], "15.00", "260.00"),
        ("uk-euro-car-parts", ["Euro Car Parts"], ["EURO CAR PARTS"], ["Brake discs, van", "Oil and filters, van"], "20.00", "240.00"),
        ("uk-ats-euromaster", ["ATS Euromaster"], ["ATS EUROMASTER"], ["Van tyres"], "80.00", "380.00"),
        ("uk-protyre", ["Protyre"], ["PROTYRE {TOWN}"], ["Tyre and tracking, van"], "60.00", "320.00"),
    ]],
    *[B(bid, contacts, narrs, [
        U("parking", "spend", "1.80", "24.00", "449", "UK-R001", ["Parking, client visit", "Parking", ""], facts={"account": "449"}, routine=True, only={"vehicle": True}),
    ]) for bid, contacts, narrs in [
        ("uk-ringgo", ["RingGo"], ["RINGGO"]),
        ("uk-justpark", ["JustPark"], ["JUSTPARK"]),
        ("uk-paybyphone", ["PayByPhone"], ["PAYBYPHONE"]),
    ]],
    # Post and couriers
    *[B(bid, contacts, narrs, [
        U("postage", "spend", lo, hi, "425", "UK-R057", lines, routine=True),
    ]) for bid, contacts, narrs, lines, lo, hi in [
        ("uk-royal-mail", ["Royal Mail"], ["ROYAL MAIL"], ["Postage", "Stamps", "Parcel postage"], "1.50", "60.00"),
        ("uk-post-office", ["Post Office"], ["POST OFFICE COUNTE"], ["Postage", "Special delivery"], "2.00", "45.00"),
        ("uk-parcelforce", ["Parcelforce"], ["PARCELFORCE"], ["Parcel collection"], "9.00", "55.00"),
        ("uk-dpd", ["DPD"], ["DPD GROUP UK"], ["Courier, order dispatch", "DPD collection"], "6.00", "40.00"),
        ("uk-evri", ["Evri"], ["EVRI"], ["Parcel postage", "Courier"], "3.00", "25.00"),
        ("uk-dhl", ["DHL"], ["DHL PARCEL UK"], ["Courier, samples to client", "Express courier"], "10.00", "90.00"),
        ("uk-ups", ["UPS"], ["UPS*{N10}"], ["Courier"], "9.00", "70.00"),
        ("uk-inpost", ["InPost"], ["INPOST UK"], ["Locker parcel"], "2.50", "12.00"),
        ("uk-yodel", ["Yodel"], ["YODEL"], ["Parcel postage"], "3.00", "15.00"),
        ("uk-fedex", ["FedEx"], ["FEDEX UK"], ["International courier"], "18.00", "120.00"),
    ]],
    # Stationery
    B("uk-ryman", ["Ryman"], ["RYMAN {N4}"], [U("stationery", "spend", "4.00", "120.00", "461", "UK-R057", ["Printer paper", "Stationery", "Ink cartridges", "Envelopes and labels"], routine=True, facts={"stationery": True})]),
    B("uk-whsmith", ["WHSmith"], ["WH SMITH"], [U("stationery", "spend", "3.00", "60.00", "461", "UK-R057", ["Stationery", "Notebooks and pens", "Diary"], routine=True, needs_line=True, facts={"stationery": True})]),
    # Rail, coach, air, taxi, hotels, car hire
    *[B(bid, contacts, narrs, [
        U("rail", "spend", lo, hi, "493", "UK-R053", ["Rail fare, {PURPOSE}", "Train to {PURPOSE}", "Return ticket, {PURPOSE}"], routine=True),
        U("commute", "spend", "40.00", "160.00", "980", "UK-R054", ["Weekly season ticket", "Season ticket, home to work", "Monthly season ticket"], only={"entity": ["sole_trader", "partnership"]}, needs_line=True, facts={"line_states": True}),
    ]) for bid, contacts, narrs, lo, hi in [
        ("uk-trainline", ["Trainline"], ["TRAINLINE.COM"], "12.00", "190.00"),
        ("uk-lner", ["LNER"], ["LNER"], "25.00", "210.00"),
        ("uk-avanti-west-coast", ["Avanti West Coast"], ["AVANTI WEST COAST"], "25.00", "230.00"),
        ("uk-great-western-railway", ["GWR"], ["GWR WEBSALES"], "12.00", "160.00"),
        ("uk-crosscountry", ["CrossCountry"], ["CROSSCOUNTRY"], "15.00", "140.00"),
        ("uk-northern", ["Northern"], ["NORTHERN TRAINS"], "5.00", "60.00"),
        ("uk-scotrail", ["ScotRail"], ["SCOTRAIL"], "6.00", "80.00"),
        ("uk-transpennine-express", ["TransPennine Express"], ["TRANSPENNINE EXPRE"], "10.00", "90.00"),
        ("uk-east-midlands-railway", ["East Midlands Railway"], ["EAST MIDS RAILWAY"], "10.00", "120.00"),
    ]],
    B("uk-national-express", ["National Express"], ["NATIONAL EXPRESS"], [U("rail", "spend", "8.00", "65.00", "493", "UK-R053", ["Coach fare, {PURPOSE}", "Coach to {PURPOSE}"], routine=True)]),
    B("uk-eurostar", ["Eurostar"], ["EUROSTAR"], [U("international", "spend", "60.00", "420.00", "494", "UK-R053", ["Eurostar to Paris, {PURPOSE}", "Eurostar to Brussels, {PURPOSE}"], routine=True, facts={"international": True})]),
    B("uk-british-airways", ["British Airways"], ["BRITISH A {N10}"], [
        U("flight_domestic", "spend", "60.00", "260.00", "493", "UK-R053", ["Flight London to Edinburgh, {PURPOSE}", "Flight to Belfast, {PURPOSE}"], needs_line=True, routine=True),
        U("flight_international", "spend", "120.00", "900.00", "494", "UK-R053", ["Flight to Madrid, {PURPOSE}", "Flight to New York, {PURPOSE}"], needs_line=True, routine=True, facts={"international": True}),
    ]),
    B("uk-easyjet", ["easyJet"], ["EASYJET {A6}"], [
        U("flight_domestic", "spend", "35.00", "180.00", "493", "UK-R053", ["Flight Bristol to Glasgow, {PURPOSE}"], needs_line=True, routine=True),
        U("flight_international", "spend", "45.00", "320.00", "494", "UK-R053", ["Flight to Amsterdam, {PURPOSE}", "Flight to Lisbon, {PURPOSE}"], needs_line=True, routine=True, facts={"international": True}),
    ]),
    B("uk-ryanair", ["Ryanair"], ["RYANAIR   {N6}"], [U("flight_international", "spend", "30.00", "260.00", "494", "UK-R053", ["Flight to Dublin, {PURPOSE}", "Flight to Krakow, {PURPOSE}"], routine=True, facts={"international": True})]),
    B("uk-jet2-com", ["Jet2"], ["JET2.COM"], [U("flight_international", "spend", "60.00", "380.00", "494", "UK-R053", ["Flight to Malaga, {PURPOSE}"], routine=True, facts={"international": True})]),
    B("uk-loganair", ["Loganair"], ["LOGANAIR"], [U("flight_domestic", "spend", "60.00", "240.00", "493", "UK-R053", ["Flight to Kirkwall, {PURPOSE}"], routine=True)]),
    *[B(bid, contacts, narrs, [
        U("taxi", "spend", "7.00", "65.00", "493", "UK-R053", ["Taxi, {PURPOSE}", "Taxi from station, {PURPOSE}", ""], routine=True),
    ]) for bid, contacts, narrs in [
        ("uk-uber", ["Uber"], ["UBER   *TRIP", "UBER* TRIP"]),
        ("uk-addison-lee", ["Addison Lee"], ["ADDISON LEE"]),
        ("uk-bolt", ["Bolt"], ["BOLT.EU/O/{N10}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("hotel", "spend", "55.00", "240.00", "493", "UK-R028", ["Hotel, overnight {PURPOSE}", "Overnight stay, {PURPOSE}", "Hotel, two nights {PURPOSE}"], routine=True, needs_line=True, facts={"trip": "overnight_uk"}),
    ]) for bid, contacts, narrs in [
        ("uk-premier-inn", ["Premier Inn"], ["PREMIER INN {N5}"]),
        ("uk-holiday-inn", ["Holiday Inn"], ["HOLIDAY INN {TOWN}"]),
        ("uk-ibis", ["Ibis"], ["IBIS {TOWN}"]),
        ("uk-hilton", ["Hilton"], ["HILTON HOTELS"]),
        ("uk-marriott", ["Marriott"], ["MARRIOTT {TOWN}"]),
        ("uk-best-western", ["Best Western"], ["BEST WESTERN {TOWN}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("hotel_abroad", "spend", "70.00", "520.00", "494", "UK-R028", ["Hotel in Dublin, {PURPOSE}", "Apartment in Berlin, {PURPOSE}", "Hotel in Lyon, {PURPOSE}"], routine=True, needs_line=True, facts={"trip": "overnight_abroad"}),
    ]) for bid, contacts, narrs in [
        ("uk-booking-com", ["Booking.com"], ["Hotel on Booking.c"]),
        ("uk-airbnb", ["Airbnb"], ["AIRBNB * HM{A8}"]),
    ]],
    *[B(bid, contacts, narrs, [
        U("car_hire", "spend", "35.00", "260.00", "493", "UK-R053", ["Car hire, {PURPOSE}", "Hire car, two days {PURPOSE}"], routine=True, needs_line=True),
    ]) for bid, contacts, narrs in [
        ("uk-enterprise", ["Enterprise Rent-A-Car", "Enterprise"], ["ENTERPRISE RENT-A-"]),
        ("uk-hertz", ["Hertz"], ["HERTZ UK"]),
        ("uk-europcar", ["Europcar"], ["EUROPCAR {N6}"]),
    ]],
]

_FOOD = [
    ("uk-pret-a-manger", ["Pret A Manger", "Pret"], ["PRET A MANGER"], "4.00", "60.00"),
    ("uk-greggs", ["Greggs"], ["GREGGS PLC"], "3.00", "40.00"),
    ("uk-costa", ["Costa Coffee", "Costa"], ["COSTA COFFEE {N5}"], "3.00", "35.00"),
    ("uk-starbucks", ["Starbucks"], ["STARBUCKS"], "3.00", "35.00"),
    ("uk-caffe-nero", ["Caffe Nero"], ["CAFFE NERO {N3} {TOWN}"], "3.00", "30.00"),
    ("uk-pizzaexpress", ["PizzaExpress"], ["PIZZA EXPRESS"], "18.00", "190.00"),
    ("uk-wagamama", ["Wagamama"], ["WAGAMAMA {TOWN}"], "15.00", "180.00"),
    ("uk-prezzo", ["Prezzo"], ["PREZZO {TOWN}"], "18.00", "170.00"),
]
# Delivery apps (R16): home and office delivery, so no client entertainment there (client meals are at restaurants).
_DELIVERY = [
    ("uk-deliveroo", ["Deliveroo"], ["DELIVEROOCOUK"], "12.00", "140.00"),
    ("uk-just-eat", ["Just Eat"], ["JUST EAT.CO.UK LTD"], "12.00", "120.00"),
    ("uk-uber-eats", ["Uber Eats"], ["UBER   *EATS"], "12.00", "110.00"),
]
# One-person meals (R16): a working-day lunch or an overnight dinner for one stays at a plausible amount.
_DAY_MEAL_CAP, _OVERNIGHT_MEAL_CAP = "25.00", "60.00"


def _capped(lo: str, hi: str, cap: str) -> tuple[str, str]:
    top = min(Decimal(hi), Decimal(cap))
    return (lo if Decimal(lo) < top else f"{top / 2:.2f}"), f"{top:.2f}"


def _food_uses(lo: str, hi: str, *, delivery: bool = False) -> list[dict]:
    """Uses of a food merchant. Owner-only meal memos follow the entity (F8: directors at a company, partners at a
    partnership, the owner at a sole trader); one-person meals are capped and delivery apps carry no client meal
    (R16)."""
    day_lo, day_hi = _capped(lo, hi, _DAY_MEAL_CAP)
    ovn_lo, ovn_hi = _capped(lo, hi, _OVERNIGHT_MEAL_CAP)
    uses = [] if delivery else [
        U("client_meal", "spend", lo, hi, "424", "UK-R025", ["Lunch with client", "Coffee with prospective client", "Dinner with supplier", "Client lunch, {PURPOSE}"], needs_line=True),
    ]
    uses += [
        U("staff_meal", "spend", lo, hi, "420", "UK-R026", ["Team lunch, project wrap", "Staff lunch for team day", "Team breakfast meeting"], needs_line=True, only={"employer": True}),
        U("overnight_meal", "spend", ovn_lo, ovn_hi, "493", "UK-R028", ["Dinner in {TOWN}, overnight {PURPOSE}", "Evening meal, two day {PURPOSE} in {TOWN}"], needs_line=True, facts={"trip": "overnight_uk"}),
        U("owner_meal_co", "spend", lo, hi, "420", "UK-R027", ["Directors lunch", "Lunch, directors only", "Directors working dinner"], needs_line=True, only={"entity": ["limited_company"]}),
        U("owner_meal_partners", "spend", lo, hi, "980", "UK-R027", ["Partners lunch", "Lunch, partners only", "Partners dinner, no guests"], needs_line=True, only={"entity": ["partnership"]}),
        U("owner_meal_sole", "spend", day_lo, day_hi, "980", "UK-R027", ["Lunch, owner only", "Dinner, no guests"], needs_line=True, only={"entity": ["sole_trader"]}),
        U("day_meal", "spend", day_lo, day_hi, "980", "UK-R028", ["Lunch", "Sandwich, working day"], needs_line=True, facts={"trip": "day_meal"}, only={"entity": ["sole_trader", "partnership"]}),
        U("no_description", "spend", lo, hi, "NEEDS_REVIEW", "UK-R029", [""]),
    ]
    return uses


for bid, contacts, narrs, lo, hi in _FOOD:
    MERCHANTS.append(B(bid, contacts, narrs, _food_uses(lo, hi), category="food_drink"))
for bid, contacts, narrs, lo, hi in _DELIVERY:
    MERCHANTS.append(B(bid, contacts, narrs, _food_uses(lo, hi, delivery=True), category="food_delivery"))

_RETAIL = [
    ("uk-tesco", ["Tesco"], ["TESCO STORES {N4}"], "groceries"),
    ("uk-sainsbury-s", ["Sainsbury's"], ["SAINSBURYS S/MKTS"], "groceries"),
    ("uk-asda", ["Asda"], ["ASDA STORES {N4}"], "groceries"),
    ("uk-aldi", ["Aldi"], ["ALDI {N2} {TOWN}"], "groceries"),
    ("uk-lidl", ["Lidl"], ["LIDL GB {TOWN}"], "groceries"),
    ("uk-morrisons", ["Morrisons"], ["MORRISONS {N4}"], "groceries"),
    ("uk-waitrose", ["Waitrose"], ["WAITROSE {N3}"], "groceries"),
    ("uk-marks-and-spencer", ["Marks & Spencer", "M&S"], ["M&S {TOWN}"], "groceries"),
    ("uk-booker-wholesale", ["Booker"], ["BOOKER {TOWN}"], "wholesale"),
    ("uk-costco", ["Costco"], ["COSTCO WHOLESALE"], "wholesale"),
    ("uk-amazon", ["Amazon"], ["AMZNMktplace", "Amazon UK Marketpl", "AMAZON.CO.UK"], "general"),
    ("uk-ebay", ["eBay"], ["EBAY O*{N2}-{N5}-{N5}"], "general"),
    ("uk-argos", ["Argos"], ["ARGOS LTD"], "general"),
    ("uk-john-lewis", ["John Lewis"], ["JOHN LEWIS {N3}"], "general"),
    ("uk-b-and-m", ["B&M"], ["B&M {N3}"], "general"),
]


def _retail_uses(kind: str) -> list[dict]:
    uses = [
        U("unknown_purchase", "spend", "8.00", "180.00", "NEEDS_REVIEW", "UK-R049", [""], hooks=["UK-R049"]),
        U("precedent_purchase", "spend", "8.00", "180.00", "310", "UK-R049", [""], hooks=["UK-R049"]),
        U("office_items", "spend", "6.00", "90.00", "461", "UK-R049", ["Printer paper and toner", "Envelopes and labels", "Desk stationery"], needs_line=True, facts={"item_named": True, "account": "461"}),
        U("private_shop", "spend", "15.00", "160.00", "980", "UK-R002", ["Weekly shop", "Household shopping", "Personal shopping"], needs_line=True),
    ]
    if kind in ("groceries", "wholesale"):
        uses.append(U("stock", "spend", "20.00", "420.00", "310", "UK-R049", ["Milk and eggs for cafe", "Ingredients for orders", "Stock for kitchen"], needs_line=True, facts={"item_named": True, "account": "310"}, only={"trades": ["catering"]}))
    return uses


for bid, contacts, narrs, kind in _RETAIL:
    MERCHANTS.append(B(bid, contacts, narrs, _retail_uses(kind), category="retail_" + kind))

# Supermarket fuel brands share a name with groceries: separate merchant ids with the fuel contact form.
MERCHANTS += [
    B("uk-tesco", ["Tesco Petrol"], ["TESCO PFS {N4}"], [U("fuel", "spend", "20.00", "100.00", "449", "UK-R034", ["Fuel", "Diesel", ""], hooks=["UK-R034"], only={"vehicle": True})], category="fuel", name="Tesco Petrol"),
    B("uk-sainsbury-s", ["Sainsbury's Petrol"], ["SAINSBURYS PETROL"], [U("fuel", "spend", "20.00", "100.00", "449", "UK-R034", ["Fuel", "Petrol", ""], hooks=["UK-R034"], only={"vehicle": True})], category="fuel", name="Sainsbury's Petrol"),
    B("uk-asda", ["Asda Petrol"], ["ASDA PETROL {TOWN}"], [U("fuel", "spend", "20.00", "100.00", "449", "UK-R034", ["Fuel", ""], hooks=["UK-R034"], only={"vehicle": True})], category="fuel", name="Asda Petrol"),
    B("uk-morrisons", ["Morrisons Fuel"], ["MORRISONS PFS {N4}"], [U("fuel", "spend", "20.00", "100.00", "449", "UK-R034", ["Fuel", "Diesel"], hooks=["UK-R034"], only={"vehicle": True})], category="fuel", name="Morrisons Fuel"),
]
for m in MERCHANTS[-4:]:
    m["merchant_id"] += "-fuel"

_TRADE = [
    ("uk-toolstation", ["Toolstation"], ["TOOLSTATION LTD"]),
    ("uk-travis-perkins", ["Travis Perkins"], ["TRAVIS PERKINS"]),
    ("uk-wickes", ["Wickes"], ["WICKES {N4}"]),
    ("uk-jewson", ["Jewson"], ["JEWSON {TOWN}"]),
    ("uk-buildbase", ["Buildbase"], ["BUILDBASE {TOWN}"]),
    ("uk-wolseley", ["Wolseley"], ["WOLSELEY UK"]),
    ("uk-cef", ["CEF"], ["CEF {TOWN}"]),
    ("uk-yesss-electrical", ["YESSS Electrical"], ["YESSS ELECTRICAL"]),
    ("uk-homebase", ["Homebase"], ["HOMEBASE {N3}"]),
    ("uk-bradfords-building-supplies", ["Bradfords"], ["BRADFORDS {TOWN}"]),
]
for bid, contacts, narrs in _TRADE:
    MERCHANTS.append(B(bid, contacts, narrs, [
        U("materials", "spend", "12.00", "650.00", "310", "UK-R055", ["Materials, job {N4}", "Timber and fixings", "Cable and fittings for job", "Plaster and sand, kitchen job", ""], routine=True, only={"trades": CONSTRUCTION}),
        U("tools", "spend", "60.00", "1400.00", "764", "UK-R022", ["Cordless drill set", "Mitre saw", "Laser level", "Tool kit"], needs_line=True, hooks=["UK-R022"], facts={"asset_kind": "tools"}, only={"trades": CONSTRUCTION}),
        U("workwear", "spend", "25.00", "140.00", "429", "UK-R062", ["Safety boots", "Hi-vis jackets", "Protective gloves and goggles"], needs_line=True, only={"trades": CONSTRUCTION}),
    ], category="diy_hardware_trade"))

MERCHANTS += [
    *[B(bid, contacts, narrs, [
        U("job_hire", "spend", "35.00", "480.00", "310", "UK-R055", ["Hire, mini digger for job", "Tower scaffold hire, job {N4}", "Floor sander hire"], routine=True, needs_line=True, facts={"service": True}, only={"trades": CONSTRUCTION}),
    ], fmt="UK-FPO", refs=["INV {N6}"]) for bid, contacts, narrs in [
        ("uk-speedy", ["Speedy Hire", "Speedy"], ["SPEEDY ASSET SERV"]),
        ("uk-hss-hire", ["HSS Hire"], ["HSS HIRE SERVICE"]),
        ("uk-brandon-hire-station", ["Brandon Hire Station"], ["BRANDON HIRE STATI"]),
    ]],
    B("uk-currys", ["Currys"], ["CURRYS {N4}"], [
        U("computer", "spend", "90.00", "1600.00", "720", "UK-R022", ["Laptop for office", "Monitor and keyboard", "Tablet for site photos", "Desktop PC"], needs_line=True, hooks=["UK-R022"], facts={"asset_kind": "computer"}),
        U("unknown_purchase", "spend", "20.00", "300.00", "NEEDS_REVIEW", "UK-R049", [""], hooks=["UK-R049"]),
    ], category="electronics_it"),
    B("uk-apple", ["Apple"], ["APPLE STORE R{N3}"], [
        U("computer", "spend", "180.00", "2400.00", "720", "UK-R022", ["MacBook Air for design work", "iPad for client demos", "Mac mini"], needs_line=True, hooks=["UK-R022"], facts={"asset_kind": "computer"}),
    ], category="electronics_it"),
    B("uk-ikea", ["IKEA"], ["IKEA LTD SHOP ONLI"], [
        U("furniture", "spend", "60.00", "1300.00", "710", "UK-R022", ["Office desk and chair", "Shelving for studio", "Filing cabinets"], needs_line=True, hooks=["UK-R022"], facts={"asset_kind": "office_equipment"}),
        U("unknown_purchase", "spend", "15.00", "240.00", "NEEDS_REVIEW", "UK-R049", [""], hooks=["UK-R049"]),
    ], category="furniture"),
    B("uk-hobbycraft", ["Hobbycraft"], ["HOBBYCRAFT {N3}"], [U("materials", "spend", "8.00", "160.00", "310", "UK-R055", ["Glaze and clay supplies", "Craft materials for orders", "Packaging for orders"], needs_line=True, routine=True, only={"trades": ["crafts", "retail"]})]),
    # Insurance
    *[B(bid, contacts, narrs, [
        U("business_policy", "spend", "18.00", "260.00", "433", "UK-R039", ["Public liability insurance", "Business insurance premium", "Business contents insurance", "Employers liability cover"], routine=True, needs_line=True, facts={"policy_type": "business"}, amount_mode="fixed"),
    ], fmt="UK-DD", refs=["POL{K7}"]) for bid, contacts, narrs in [
        ("uk-simply-business", ["Simply Business"], ["SIMPLY BUSINESS"]),
        ("uk-hiscox", ["Hiscox"], ["HISCOX UK"]),
        ("uk-zurich", ["Zurich"], ["ZURICH"]),
        ("uk-nfu-mutual", ["NFU Mutual"], ["NFU MUTUAL"]),
        ("uk-allianz", ["Allianz"], ["ALLIANZ INSURANCE"]),
    ]],
    B("uk-axa", ["AXA"], ["AXA INSURANCE"], [
        U("business_policy", "spend", "20.00", "240.00", "433", "UK-R039", ["Business insurance", "Shop contents insurance"], routine=True, needs_line=True, facts={"policy_type": "business"}, amount_mode="fixed"),
        U("employee_medical", "spend", "40.00", "260.00", "483", "UK-R039", ["Staff health cash plan", "Employee private medical"], needs_line=True, facts={"policy_type": "employee_medical"}, only={"employer": True}, amount_mode="fixed"),
    ], fmt="UK-DD", refs=["AXA{K8}"]),
    *[B(bid, contacts, narrs, [
        U("motor_policy", "spend", "45.00", "160.00", "449", "UK-R039", ["Van insurance", "Motor insurance, van", ""], hooks=["UK-R039"], facts={"policy_type": "motor"}, only={"vehicle_methods": ["actual_costs", "taxi_cost_of_sales"]}, amount_mode="fixed"),
    ], fmt="UK-DD", refs=["{K11}"]) for bid, contacts, narrs in [
        ("uk-admiral", ["Admiral"], ["ADMIRAL INSURANCE"]),
        ("uk-direct-line", ["Direct Line"], ["DIRECT LINE INS"]),
        ("uk-swinton", ["Swinton"], ["SWINTON INSURANCE"]),
    ]],
    B("uk-aviva", ["Aviva"], ["AVIVA LIFE", "AVIVA INSURANCE"], [
        U("business_policy", "spend", "20.00", "220.00", "433", "UK-R039", ["Commercial property insurance", "Business insurance premium"], routine=True, needs_line=True, facts={"policy_type": "business"}, amount_mode="fixed"),
        U("private_policy", "spend", "15.00", "90.00", "980", "UK-R039", ["Life cover", "Income protection", "Home insurance"], needs_line=True, hooks=["UK-R039"], facts={"policy_type": "private"}, amount_mode="fixed"),
    ], fmt="UK-DD", refs=["{K10}"]),
    B("uk-lv", ["LV="], ["LV LIFE"], [U("private_policy", "spend", "12.00", "75.00", "980", "UK-R039", ["Life insurance", "Pet insurance"], needs_line=True, hooks=["UK-R039"], facts={"policy_type": "private"}, amount_mode="fixed")], fmt="UK-DD", refs=["{K9}"]),
    # Car purchase
    B("uk-arnold-clark", ["Arnold Clark"], ["ARNOLD CLARK {TOWN}"], [U("vehicle_purchase", "spend", "2500.00", "24000.00", "760", "UK-R023", ["Van purchase", "Deposit on van", "Used car for business"], needs_line=True)], fmt="UK-FPO", refs=["INV{N6}"]),
    # Storage and workspace
    *[B(bid, contacts, narrs, [
        U("space_rent", "spend", lo, hi, "469", "UK-R001", lines, routine=True, facts={"account": "469"}, amount_mode="fixed"),
    ], fmt=fmt, refs=refs) for bid, contacts, narrs, lines, lo, hi, fmt, refs in [
        ("uk-big-yellow-self-storage", ["Big Yellow"], ["BIG YELLOW SELF ST"], ["Storage unit rent", "Storage unit, stock", ""], "60.00", "320.00", "UK-DD", ["BY{K7}"]),
        ("uk-safestore", ["Safestore"], ["SAFESTORE"], ["Storage unit", ""], "55.00", "280.00", "UK-DD", ["SS{K6}"]),
        ("uk-shurgard", ["Shurgard"], ["SHURGARD UK"], ["Storage unit rent"], "60.00", "260.00", "UK-DD", ["{K8}"]),
    ]],
    # Coworking desks only at firms without premises of their own (R5: a firm with a unit has one landlord).
    *[B(bid, contacts, narrs, [
        U("space_rent", "spend", lo, hi, "469", "UK-R001", lines, routine=True, facts={"account": "469"}, only={"premises": False}, amount_mode="fixed"),
    ], fmt=fmt, refs=refs) for bid, contacts, narrs, lines, lo, hi, fmt, refs in [
        ("uk-regus", ["Regus"], ["REGUS MANAGEMENT"], ["Coworking desk", "Meeting room hire", "Office membership"], "40.00", "650.00", "UK-DD", ["INV{N7}", "ACC {K7}"]),
        ("uk-wework", ["WeWork"], ["WEWORK UK"], ["Hot desk membership", "Private office"], "180.00", "900.00", "UK-DEB", [""]),
    ]],
    # Gyms (private)
    *[B(bid, contacts, narrs, [
        U("gym", "spend", "25.00", "110.00", "980", "UK-R042", ["", "Gym membership"], facts={"membership": "gym"}),
    ], fmt="UK-DD", refs=["{N8}"]) for bid, contacts, narrs in [
        ("uk-fitness-first", ["Fitness First"], ["FITNESS FIRST"]),
        ("uk-virgin-active", ["Virgin Active"], ["VIRGIN ACTIVE"]),
    ]],
    B("uk-boots", ["Boots"], ["BOOTS {N4}"], [
        U("private_shop", "spend", "4.00", "60.00", "980", "UK-R002", ["Toiletries", "Prescription", "Personal items"], needs_line=True),
        U("unknown_purchase", "spend", "4.00", "60.00", "NEEDS_REVIEW", "UK-R049", [""]),
    ], category="pharmacy_health"),
    B("uk-taxassist-accountants", ["TaxAssist Accountants"], ["TAXASSIST ACCOUNTA"], [
        U("accountancy", "spend", "60.00", "1200.00", "401", "UK-R040", ["Year end accounts", "VAT return preparation", "Tax computation"], routine=True, facts={"professional": "accountant"}),
        U("accountancy_monthly", "spend", "45.00", "260.00", "401", "UK-R040", ["Bookkeeping {MMM}", "Monthly accountancy fee", "Monthly bookkeeping package"], routine=True, facts={"professional": "accountant"}, amount_mode="fixed", refs=["DD {K6}"]),
        U("personal_return", "spend", "150.00", "450.00", "980", "UK-R040", ["Personal tax return fee", "Self assessment return, owner"], needs_line=True, facts={"professional": "personal_return"}, only={"entity": ["sole_trader", "partnership"]}),
        U("personal_return_director", "spend", "150.00", "450.00", "835", "UK-R040", ["Personal tax return fee, director", "Director self assessment return"], needs_line=True, facts={"professional": "personal_return"}, only={"entity": ["limited_company"]}),
    ], fmt="UK-FPO", refs=["INV {N5}"]),
]

# Processors, marketplaces and banks (bank-side lines)
MERCHANTS += [
    B("uk-stripe", ["Stripe", "Stripe Payments UK"], ["STRIPE PAYMENTS UK STRIPE"], [
        U("payout", "receive", "80.00", "4200.00", "200", "UK-R019", ["Stripe payout", "Card sales payout", ""], facts={"split": "processor_payout", "fee_rate": "0.015", "fee_fixed": "0.20"}, only={"processor": "uk-stripe"}),
    ], fmt="UK-FPI", refs=["STRIPE", "ST-{A10}"]),
    B("uk-sumup", ["SumUp"], ["SUMUP PAYMENTS LTD"], [
        U("payout", "receive", "40.00", "2600.00", "200", "UK-R019", ["SumUp payout", "Card takings", ""], facts={"split": "processor_payout", "fee_rate": "0.0169", "fee_fixed": "0.00"}, only={"processor": "uk-sumup"}),
        U("card_reader", "spend", "19.00", "39.00", "429", "UK-R064", ["Card reader", "Spare card reader"], needs_line=True),
    ], fmt="UK-FPI", refs=["SUMUP {N8}"]),
    B("uk-square", ["Square"], ["SQUARE {A14}"], [
        U("payout", "receive", "50.00", "3200.00", "200", "UK-R019", ["Square payout", ""], facts={"split": "processor_payout", "fee_rate": "0.0175", "fee_fixed": "0.00"}, only={"processor": "uk-square"}),
    ], fmt="UK-FPI", refs=[""]),
    B("uk-zettle", ["Zettle", "PayPal Zettle"], ["ZETTLE PAYOUT"], [
        U("payout", "receive", "50.00", "2400.00", "200", "UK-R019", ["Zettle payout", "Card takings"], facts={"split": "processor_payout", "fee_rate": "0.0175", "fee_fixed": "0.00"}, only={"processor": "uk-zettle"}),
    ], fmt="UK-FPI", refs=["IZ {N8}"]),
    B("uk-paypal", ["PayPal"], ["PAYPAL EUROPE"], [
        U("payout", "receive", "30.00", "1800.00", "200", "UK-R019", ["PayPal transfer to bank", "PayPal sales"], facts={"split": "processor_payout", "fee_rate": "0.029", "fee_fixed": "0.30"}, only={"processor": "uk-paypal"}),
    ], fmt="UK-FPI", refs=["PP{N10}"]),
    B("uk-etsy", ["Etsy"], ["ETSY UK PAYMENTS"], [
        U("payout", "receive", "40.00", "1600.00", "200", "UK-R066", ["Etsy deposit", "Etsy sales", ""], facts={"split": None}, only={"processor": "uk-etsy"}),
    ], fmt="UK-BGC", refs=["ETSY {N8}"]),
    B("uk-gocardless", ["GoCardless"], ["GOCARDLESS"], [
        U("payout", "receive", "60.00", "3000.00", "200", "UK-R019", ["GoCardless payout", "Box subscriptions collected"], facts={"split": "processor_payout", "fee_rate": "0.01", "fee_fixed": "0.20"}, only={"processor": "uk-gocardless"}),
        U("fees", "spend", "4.00", "60.00", "404", "UK-R018", ["GoCardless fees", "Direct debit collection fees"], routine=True, only={"processor": "uk-gocardless"}),
    ], fmt="UK-BGC", refs=["GC-{A8}"]),
    # Amazon seller payouts: a separate merchant id from the Amazon shop (forbidden-merchant rules stay per use family).
    B("uk-amazon", ["Amazon Payments UK", "Amazon Seller Services"], ["AMAZON PAYMENTS UK"], [
        U("payout", "receive", "60.00", "2200.00", "200", "UK-R066", ["Amazon seller payout", "Amazon sales settlement", ""], facts={"split": None}, only={"processor": "uk-amazon-seller"}),
    ], fmt="UK-BGC", refs=["AMZ {N10}"], category="marketplace", name="Amazon Seller Payouts"),
    B("uk-worldpay", ["Worldpay"], ["WORLDPAY {N8}"], [
        U("fees", "spend", "15.00", "120.00", "404", "UK-R018", ["Card processing charges", "Merchant service charge {MMM}"], routine=True),
    ], fmt="UK-DD", refs=["{N8}"]),
]
next(m for m in MERCHANTS if m["name"] == "Amazon Seller Payouts")["merchant_id"] += "-seller"

# R6: every instalment use of one lender draws the same fixed amount (Env keys the plan on firm, lender and group).
LOAN_GROUP = "loan_instalment"

_BANKS = [
    ("uk-barclays", ["Barclays"], "BARCLAYS"),
    ("uk-hsbc", ["HSBC"], "HSBC"),
    ("uk-natwest", ["NatWest"], "NATWEST"),
    ("uk-bank-of-scotland", ["Bank of Scotland"], "BANK OF SCOTLAND"),
    ("uk-starling-bank", ["Starling Bank"], "STARLING"),
    ("uk-monzo", ["Monzo"], "MONZO"),
]
for bid, contacts, short in _BANKS:
    MERCHANTS.append(B(bid, contacts, [short], [
        U("account_fee", "spend", "3.00", "35.00", "404", "UK-R017", ["Account fee", "Monthly account charge", ""], routine=True,
          narratives=["ACCOUNT FEE", "SERVICE CHARGES REF : {N9}", "MONTHLY FEE"], fmt="UK-CHG"),
        U("fx_fee", "spend", "0.40", "9.50", "404", "UK-R017", [""], narratives=["NON-STG TRANS FEE", "NON-GBP PURCH FEE"], fmt="UK-CHG"),
        U("interest_charged", "spend", "1.20", "48.00", "437", "UK-R014", ["Overdraft interest", ""], routine=True, narratives=["INTEREST CHARGED", "OVERDRAFT INTEREST"], fmt="UK-CHG"),
        U("interest_received", "receive", "0.05", "38.00", "270", "UK-R059", ["Interest", ""], routine=True, narratives=["INTEREST", "GROSS INTEREST"], fmt="UK-INT"),
        U("card_repayment", "spend", "120.00", "3200.00", "811", "UK-R046", ["Credit card repayment", "Card payment", ""], hooks=["UK-R046"], narratives=[short + " CARD SERVS", short + " CREDIT CARD"], fmt="UK-DD", refs=["{N6}"]),
        U("loan_drawdown", "receive", "5000.00", "45000.00", "900", "UK-R013", ["Business loan drawdown", "Loan advance"], narratives=[short + " LOANS"], fmt="UK-BGC", refs=["LOAN {K8}"], amount_mode="round"),
        U("loan_instalment", "spend", "180.00", "1400.00", "900", "UK-R016", ["Loan repayment", "Monthly loan instalment"], narratives=[short + " LOANS"], fmt="UK-DD", refs=["LOAN {K8}"], amount_mode="fixed", fixed_group=LOAN_GROUP),
    ], category="bank"))

# Premises landlord merchant by trade (R5). Health and beauty firms rent from a person landlord (firms.py).
LANDLORD_TRADES = {
    "canal-wharf-properties": ["construction", "trades", "manufacturing", "crafts"],
    "meadowgate-business-park": ["catering", "retail", "creative", "services", "events", "professional", "education",
                                 "transport"],
}

# Statutory fee tariffs (R10; sources at the ICO and Companies House entries below).
ICO_FEE_DD = "47.00"  # tier 1, GBP 52 less GBP 5 for direct debit, from 17 February 2025
CS01_FEE = "50.00"  # confirmation statement filed online, from 1 February 2026
CS01_FEE_BEFORE = ("34.00", "2026-02-01")  # the online fee before that date, for history rows

# Invented local merchants, customers and government payees.
MERCHANTS += [
    I("harbour-lane-plumbing-supplies", "Harbour Lane Plumbing Supplies", ["Harbour Lane Plumbing Supplies", "Harbour Lane Plumbing"], ["HARBOUR LANE PLUMB"], [
        U("materials", "spend", "18.00", "900.00", "310", "UK-R055", ["Copper pipe and fittings", "Boiler parts, job {N4}", "Radiator valves", ""], routine=True, only={"trades": CONSTRUCTION}),
    ], refs=["INV {N5}", "ACC {N4}"]),
    I("fernside-timber-merchants", "Fernside Timber Merchants", ["Fernside Timber Merchants", "Fernside Timber"], ["FERNSIDE TIMBER"], [
        U("materials", "spend", "40.00", "1200.00", "310", "UK-R055", ["Oak boards, job {N4}", "Timber for staircase job", "Sheet materials"], routine=True, only={"trades": CONSTRUCTION + ["manufacturing"]}),
    ], refs=["INV {N5}"]),
    I("highmoor-trade-counter", "Highmoor Trade Counter", ["Highmoor Trade Counter"], ["HIGHMOOR TRADE"], [
        U("materials", "spend", "15.00", "480.00", "310", "UK-R055", ["Fixings and sealant", "Consumables, job {N4}"], routine=True, only={"trades": CONSTRUCTION + ["manufacturing"]}),
        U("tools", "spend", "80.00", "1500.00", "764", "UK-R022", ["Welding set", "Bench grinder", "Impact driver kit"], needs_line=True, hooks=["UK-R022"], facts={"asset_kind": "tools"}, only={"trades": CONSTRUCTION + ["manufacturing"]}),
    ], refs=["{N6}"], fmt="UK-DEB"),
    I("northside-electrical", "Northside Electrical Ltd", ["Northside Electrical Ltd", "Northside Electrical"], ["NORTHSIDE ELECTRIC"], [
        U("subcontract", "spend", "250.00", "3200.00", "321", "UK-R055", ["Subcontract electrics, job {N4}", "Rewire subcontract", "Electrical first fix, subcontract"], needs_line=True, facts={"subcontractor": True}, only={"trades": CONSTRUCTION}),
    ], refs=["INV {N4}"]),
    I("stonebridge-scaffolding", "Stonebridge Scaffolding Ltd", ["Stonebridge Scaffolding Ltd"], ["STONEBRIDGE SCAFF"], [
        U("subcontract", "spend", "300.00", "2400.00", "321", "UK-R055", ["Scaffolding erect and strike, job {N4}", "Scaffold subcontract"], needs_line=True, facts={"subcontractor": True}, only={"trades": CONSTRUCTION}),
    ], refs=["SB{N5}"]),
    # CIS contractors that pay the dataset's CIS subcontractor firms (B16; UK-R067, R068, R071). Invented names.
    *[I(slug, name, [name, short_name], [narr], [
        U("cis_receipt", "receive", lo, hi, "200", "UK-R067", [""], facts={"split": "cis_receipt"}, only={"trades": CONSTRUCTION}),
        U("cis_gross_receipt", "receive", lo, hi, "200", "UK-R068", ["Valuation {N2}, plot {N2}", "Stage payment, plot {N2}", "Application {N2}, {TOWN} site", "Final account, plot {N2}"], only={"trades": CONSTRUCTION}),
        U("cis_unclear", "receive", lo, hi, "NEEDS_REVIEW", "UK-R071", ["CIS", "Payment less CIS", "Net of CIS", "CIS deducted", "Valuation {N2} less CIS"], only={"trades": CONSTRUCTION}),
    ], refs=refs, fmt="UK-FPI", category="construction_contractor") for slug, name, short_name, narr, lo, hi, refs in [
        ("pellbrook-developments", "Pellbrook Developments Ltd", "Pellbrook Developments", "PELLBROOK DEVS", "600.00", "5800.00", ["PB{N5}", "REMIT {N6}"]),
        ("ravensgill-construction", "Ravensgill Construction Ltd", "Ravensgill Construction", "RAVENSGILL CONST", "450.00", "4800.00", ["RCL {N5}", "SUBCON {N4}"]),
        ("ashlow-homes", "Ashlow Homes Ltd", "Ashlow Homes", "ASHLOW HOMES LTD", "800.00", "6500.00", ["AH{N6}", "PAYMENT {N5}"]),
    ]],
    I("greystone-plant-hire", "Greystone Plant Hire", ["Greystone Plant Hire"], ["GREYSTONE PLANT"], [
        U("job_hire", "spend", "60.00", "900.00", "310", "UK-R055", ["Digger hire, groundworks job", "Plant hire, job {N4}"], routine=True, needs_line=True, facts={"service": True}, only={"trades": CONSTRUCTION}),
    ], refs=["GPH{N5}"]),
    I("millbrook-joinery", "Millbrook Joinery Ltd", ["Millbrook Joinery Ltd", "Millbrook Joinery"], ["MILLBROOK JOINERY"], [
        U("repair", "spend", "90.00", "900.00", "473", "UK-R024", ["Repair to shop door", "Replace broken window frame", "Fix damaged skirting, office"], needs_line=True, facts={"scope": "repair"}, only={"premises": True}),
        U("large_unknown", "spend", "2200.00", "9800.00", "NEEDS_REVIEW", "UK-R024", ["", "Works per quote", "Stage payment", "Job as agreed", "Invoice per estimate", "Building work, balance"], facts={"scope": "unknown"}, only={"premises": True}),
    ], refs=["INV {N4}"]),
    I("hearthstone-heating", "Hearthstone Heating Ltd", ["Hearthstone Heating Ltd"], ["HEARTHSTONE HEAT"], [
        U("repair", "spend", "70.00", "480.00", "473", "UK-R024", ["Boiler service, premises", "Heating repair, unit {N2}"], needs_line=True, routine=True, facts={"scope": "repair"}, only={"premises": True}),
    ], refs=["HH{N5}"]),
    I("sparkwell-cleaning", "Sparkwell Cleaning Services", ["Sparkwell Cleaning Services", "Sparkwell Cleaning"], ["SPARKWELL CLEANING"], [
        U("cleaning", "spend", "45.00", "380.00", "408", "UK-R001", ["Office cleaning {MMM}", "Shop cleaning contract", ""], routine=True, facts={"account": "408"}, only={"premises": True}),
    ], refs=["INV {N4}"], fmt="UK-SO"),
    I("ashgrove-accountancy", "Ashgrove Accountancy LLP", ["Ashgrove Accountancy LLP", "Ashgrove Accountancy"], ["ASHGROVE ACCOUNTAN"], [
        U("accountancy", "spend", "90.00", "1600.00", "401", "UK-R040", ["Year end accounts", "Tax return work for the business", "VAT return review"], routine=True, facts={"professional": "accountant"}),
        U("accountancy_monthly", "spend", "60.00", "320.00", "401", "UK-R040", ["Payroll bureau {MMM}", "Bookkeeping retainer", "Monthly retainer {MMM}"], routine=True, facts={"professional": "accountant"}, amount_mode="fixed", refs=["AA {K5}"]),
        U("personal_return", "spend", "180.00", "480.00", "980", "UK-R040", ["Owner self assessment return", "Personal tax return fee"], needs_line=True, facts={"professional": "personal_return"}, only={"entity": ["sole_trader"]}),
        U("personal_return_partner", "spend", "180.00", "480.00", "980", "UK-R040", ["Personal tax return, partner", "Partner self assessment return"], needs_line=True, facts={"professional": "personal_return"}, only={"entity": ["partnership"]}),
        U("personal_return_director", "spend", "180.00", "480.00", "835", "UK-R040", ["Self assessment return, director", "Personal tax return for the director"], needs_line=True, facts={"professional": "personal_return"}, only={"entity": ["limited_company"]}),
    ], refs=["AA{N5}"]),
    I("brightfield-advisory", "Brightfield Advisory Ltd", ["Brightfield Advisory Ltd"], ["BRIGHTFIELD ADVISO"], [
        U("advice", "spend", "250.00", "2400.00", "412", "UK-R040", ["Business planning workshop", "HR advice retainer", "Growth strategy sessions"], routine=True, facts={"professional": "adviser"}),
    ], refs=["BA-{N4}"]),
    I("northgate-legal", "Northgate Legal LLP", ["Northgate Legal LLP"], ["NORTHGATE LEGAL"], [
        U("legal", "spend", "180.00", "3200.00", "441", "UK-R040", ["Debt recovery, unpaid invoice", "Trade mark filing", "Review of supplier contract"], routine=True, facts={"professional": "solicitor"}),
    ], refs=["NL{N6}"]),
    # Premises landlords (R5): one per firm. The two landlord merchants split the trades of firms with premises, and
    # trades whose firms rent from a person (firms.py `landlord`) have no landlord merchant; test_gen_uk checks it.
    I("canal-wharf-properties", "Canal Wharf Properties Ltd", ["Canal Wharf Properties Ltd"], ["CANAL WHARF PROPS"], [
        U("rent", "spend", "450.00", "2800.00", "469", "UK-R037", ["Rent, unit {K2}", "Workshop rent {MMM}", "Rent {MMM}"], facts={"account": "469"}, hooks=["UK-R037"], only={"premises": True, "trades": LANDLORD_TRADES["canal-wharf-properties"]}, amount_mode="fixed"),
    ], refs=["RENT {K4}"], fmt="UK-SO"),
    I("meadowgate-business-park", "Meadowgate Business Park Ltd", ["Meadowgate Business Park Ltd", "Meadowgate Business Park"], ["MEADOWGATE BUS PK"], [
        U("rent", "spend", "500.00", "3200.00", "469", "UK-R037", ["Unit rent {MMM}", "Service charge and rent"], facts={"account": "469"}, hooks=["UK-R037"], only={"premises": True, "trades": LANDLORD_TRADES["meadowgate-business-park"]}, amount_mode="fixed"),
    ], refs=["MBP{K4}"], fmt="UK-SO"),
    I("linden-court-lettings", "Linden Court Lettings Ltd", ["Linden Court Lettings Ltd"], ["LINDEN COURT LETS"], [
        U("home_rent", "spend", "650.00", "1450.00", "980", "UK-R036", ["", "Rent, flat"], hooks=["UK-R036"], amount_mode="fixed"),
    ], refs=["FLAT {K2}"], fmt="UK-SO"),
    I("westshire-council", "Westshire Council", ["Westshire Council"], ["WESTSHIRE COUNCIL"], [
        U("business_rates", "spend", "60.00", "640.00", "465", "UK-R038", ["Business rates", ""], facts={"council_marker": "rates"}, refs=["NNDR {N8}", "BUS RATES {N7}"]),
        U("council_tax", "spend", "95.00", "240.00", "980", "UK-R038", [""], facts={"council_marker": "council_tax"}, refs=["CTAX {N8}", "C TAX {N8}"]),
        U("unmarked", "spend", "90.00", "420.00", "NEEDS_REVIEW", "UK-R038", [""], facts={"council_marker": None}, refs=["{N8}", ""]),
    ], fmt="UK-DD"),
    I("eastvale-borough-council", "Eastvale Borough Council", ["Eastvale Borough Council", "Eastvale BC"], ["EASTVALE BOROUGH C"], [
        U("business_rates", "spend", "70.00", "560.00", "465", "UK-R038", ["Business rates {MMM}", ""], facts={"council_marker": "rates"}, refs=["NNDR {N8}"]),
        U("council_tax", "spend", "110.00", "260.00", "980", "UK-R038", [""], facts={"council_marker": "council_tax"}, refs=["CTAX {N8}"]),
        U("unmarked", "spend", "100.00", "380.00", "NEEDS_REVIEW", "UK-R038", [""], facts={"council_marker": None}, refs=["{N9}"]),
        # PCNs are fixed tariffs outside London (GBP 50 or 70, halved if paid within 14 days; re-audit R3).
        U("parking_fine", "spend", "25.00", "70.00", "429", "UK-R021", ["PCN, van parked at job", "Parking penalty, delivery"], needs_line=True, refs=["PCN {A2}{N8}"], only={"vehicle": True}, amount_choices=["25.00", "35.00", "50.00", "70.00"]),
    ], fmt="UK-FPO"),
    # Gifts to charity and party donations are round sums (R11): `round` gives multiples of 100 here.
    I("valley-hospice-trust", "Valley Hospice Trust", ["Valley Hospice Trust"], ["VALLEY HOSPICE"], [
        U("donation", "spend", "100.00", "500.00", "418", "UK-R051", ["Donation", "Charity donation, fun run", ""], routine=True, amount_mode="round"),
        U("sponsorship", "spend", "200.00", "800.00", "400", "UK-R051", ["Sponsorship, logo on event banner", "Programme advert, charity ball"], needs_line=True, facts={"sponsorship": True}, amount_mode="round"),
    ], refs=["DON {N4}"]),
    I("westshire-independents", "Westshire Independents Party", ["Westshire Independents Party"], ["WESTSHIRE INDEPEN"], [
        U("political", "spend", "100.00", "300.00", "418", "UK-R042", ["Party donation", "Political donation"], needs_line=True, facts={"membership": "political"}, amount_mode="round"),
    ], refs=[""]),
    I("guild-of-independent-bakers", "Guild of Independent Bakers", ["Guild of Independent Bakers"], ["GUILD OF IND BAKER"], [
        U("membership", "spend", "45.00", "240.00", "485", "UK-R042", ["Annual membership", "Guild membership {YY}"], routine=True, facts={"membership": "trade_body"}, only={"trades": ["catering"]}),
    ], refs=["MEM {N5}"], fmt="UK-DD"),
    I("joinery-trade-monthly", "Joinery Trade Monthly", ["Joinery Trade Monthly"], ["JOINERY TRADE MTHL"], [
        U("membership", "spend", "6.00", "90.00", "485", "UK-R042", ["Trade journal subscription"], routine=True, facts={"membership": "trade_body"}, only={"trades": ["construction", "manufacturing"]}),
    ], refs=["SUB {N5}"], fmt="UK-DD"),
    I("federation-of-small-traders", "Federation of Small Traders", ["Federation of Small Traders"], ["FED OF SMALL TRADE"], [
        U("membership", "spend", "60.00", "300.00", "485", "UK-R042", ["Membership renewal", "Trade body membership"], routine=True, facts={"membership": "trade_body"}),
    ], refs=["FST{N6}"], fmt="UK-DD"),
    I("brightwater-first-aid", "Brightwater First Aid Training", ["Brightwater First Aid Training"], ["BRIGHTWATER FIRST"], [
        U("training", "spend", "60.00", "450.00", "480", "UK-R052", ["First aid at work course", "Food hygiene level 2 course", "Manual handling training"], routine=True),
    ], refs=["BFA{N4}"]),
    I("harlow-language-school", "Harlow Language School", ["Harlow Language School"], ["HARLOW LANGUAGE"], [
        U("private_course", "spend", "120.00", "600.00", "980", "UK-R052", ["Evening Spanish course, owner", "Pottery hobby class"], needs_line=True, facts={"private": True}),
    ], refs=["HLS{N4}"]),
    I("thornbury-hampers", "Thornbury Hampers Ltd", ["Thornbury Hampers Ltd"], ["THORNBURY HAMPERS"], [
        U("client_gift", "spend", "45.00", "420.00", "424", "UK-R031", ["Christmas hampers for clients", "Thank you hamper, client", "Gift hamper for supplier"], needs_line=True),
    ], fmt="UK-DEB"),
    # Renamed from a name a real wine merchant trades under; the new name was web-checked (2026-10-15).
    I("quillmoor-wines", "Quillmoor Wines", ["Quillmoor Wines"], ["QUILLMOOR WINES"], [
        U("client_gift", "spend", "30.00", "260.00", "424", "UK-R031", ["Wine for client, project completion", "Champagne gift for client"], needs_line=True),
    ], fmt="UK-DEB"),
    I("inkwell-promotions", "Inkwell Promotional Products", ["Inkwell Promotional Products"], ["INKWELL PROMO"], [
        U("branded_gifts", "spend", "60.00", "420.00", "400", "UK-R030", ["Logo pens for customers", "Branded tote bags for open day", "Printed keyrings with logo"], needs_line=True),
    ], refs=["IP{N5}"]),
    I("halden-print-studio", "Halden Print Studio", ["Halden Print Studio"], ["HALDEN PRINT"], [
        U("print_marketing", "spend", "40.00", "480.00", "400", "UK-R056", ["Flyers for open day", "Brochures print run", "Shop window posters"], routine=True, needs_line=True),  # a print shop's name alone does not say marketing (400) or stationery (461)
    ], refs=["HPS{N4}"]),
    I("larkfield-vehicle-leasing", "Larkfield Vehicle Leasing Ltd", ["Larkfield Vehicle Leasing Ltd"], ["LARKFIELD LEASING"], [
        U("lease", "spend", "180.00", "520.00", "457", "UK-R063", ["Van lease rental {MMM}", "Vehicle lease", ""], routine=True, only={"vehicle_methods": ["actual_costs", "taxi_cost_of_sales"]}, amount_mode="fixed"),
    ], refs=["AGR {K7}"], fmt="UK-DD"),
    I("kingsmere-business-finance", "Kingsmere Business Finance Ltd", ["Kingsmere Business Finance Ltd", "Kingsmere Finance"], ["KINGSMERE FINANCE"], [
        U("loan_drawdown", "receive", "3000.00", "40000.00", "900", "UK-R013", ["Loan drawdown", "Business loan advance"], refs=["DRAWDOWN {K8}"], fmt="UK-BGC", amount_mode="round"),
        U("loan_instalment", "spend", "150.00", "1300.00", "900", "UK-R016", ["Loan repayment", "Monthly instalment"], refs=["LOAN {K8}"], fmt="UK-DD", amount_mode="fixed", fixed_group=LOAN_GROUP),
        U("loan_capital", "spend", "500.00", "8000.00", "900", "UK-R015", ["Capital repayment, loan", "Early repayment of loan capital"], needs_line=True, refs=["CAPITAL {K8}"], fmt="UK-FPO"),
        U("loan_interest", "spend", "15.00", "220.00", "437", "UK-R014", ["Loan interest {MMM}", "Interest on business loan"], needs_line=True, refs=["INT {K8}"], fmt="UK-DD"),
    ]),
    I("corvane-workplace-pensions", "Corvane Workplace Pensions", ["Corvane Workplace Pensions"], ["CORVANE PENSIONS"], [
        U("pension", "spend", "40.00", "900.00", "482", "UK-R050", ["Employer pension contributions", "Workplace pension {MMM}", ""], only={"employer": True}),
    ], refs=["EMP{N6}"], fmt="UK-DD"),
    I("ridgeway-personal-pensions", "Ridgeway Personal Pensions", ["Ridgeway Personal Pensions"], ["RIDGEWAY PENSIONS"], [
        U("pension", "spend", "50.00", "800.00", "980", "UK-R050", ["Personal pension", ""], hooks=["UK-R050"]),
    ], refs=["PP{N7}"], fmt="UK-DD"),
    I("northern-catering-equipment", "Northern Catering Equipment Ltd", ["Northern Catering Equipment Ltd"], ["NORTHERN CATERING"], [
        U("tools", "spend", "120.00", "4200.00", "764", "UK-R022", ["Commercial mixer", "Combination oven", "Undercounter fridge", "Coffee grinder"], needs_line=True, hooks=["UK-R022"], facts={"asset_kind": "tools"}, only={"trades": ["catering"]}),
        U("improvement", "spend", "1800.00", "8500.00", "764", "UK-R024", ["Upgrade of extraction canopy", "New walk-in cold room installed"], needs_line=True, facts={"scope": "improvement", "asset_account": "764"}, only={"trades": ["catering"]}),
    ], refs=["NCE{N5}"]),
    I("quayside-garage", "Quayside Garage Services", ["Quayside Garage Services", "Quayside Garage"], ["QUAYSIDE GARAGE"], [
        U("repair", "spend", "45.00", "900.00", "449", "UK-R001", ["MOT and service, van", "Clutch repair, van", "Annual service"], routine=True, facts={"account": "449"}, only={"vehicle_methods": ["actual_costs", "taxi_cost_of_sales"]}),
    ], refs=["QG{N5}"], fmt="UK-DEB"),
    I("lowfield-tyres", "Lowfield Tyres and Exhaust", ["Lowfield Tyres and Exhaust"], ["LOWFIELD TYRES"], [
        U("repair", "spend", "40.00", "420.00", "449", "UK-R001", ["Two tyres, van", "Exhaust repair"], routine=True, facts={"account": "449"}, only={"vehicle_methods": ["actual_costs", "taxi_cost_of_sales"]}),
    ], fmt="UK-DEB"),
    I("quickcut-keys", "Quickcut Keys and Shoe Repairs", ["Quickcut Keys and Shoe Repairs"], ["QUICKCUT KEYS {N3}"], [
        U("keys", "spend", "4.00", "40.00", "429", "UK-R064", ["Spare keys for shop", "Key cutting, unit"], routine=True, needs_line=True),
    ], fmt="UK-DEB"),
    I("safeguard-workwear", "Safeguard Workwear Supplies", ["Safeguard Workwear Supplies"], ["SAFEGUARD WORKWEAR"], [
        # Protective kit for site and workshop trades, chef whites for kitchens only (re-audit R4: not at a roofer).
        U("workwear", "spend", "25.00", "260.00", "429", "UK-R062", ["Safety boots", "Hi-vis and hard hats"], needs_line=True, routine=True, only={"trades": ("construction", "trades", "manufacturing", "transport")}),
        U("workwear_kitchen", "spend", "25.00", "180.00", "429", "UK-R062", ["Chef whites and aprons"], needs_line=True, routine=True, only={"trades": ("catering",)}),
        U("everyday_clothes", "spend", "30.00", "140.00", "980", "UK-R062", ["Jeans and jumper", "Everyday shoes"], needs_line=True, facts={"private": True}),
    ], fmt="UK-DEB"),
    I("riverside-brasserie", "Riverside Brasserie", ["Riverside Brasserie"], ["RIVERSIDE BRASSERI"], _food_uses("25.00", "380.00"), fmt="UK-DEB", category="food_drink"),
    I("copper-pot-kitchen", "The Copper Pot Kitchen", ["The Copper Pot Kitchen", "Copper Pot Kitchen"], ["COPPER POT KITCHEN"], _food_uses("18.00", "260.00"), fmt="UK-DEB", category="food_drink"),
    I("old-granary-tearooms", "The Old Granary Tearooms", ["The Old Granary Tearooms"], ["OLD GRANARY TEAROO"], _food_uses("6.00", "70.00"), fmt="UK-DEB", category="food_drink"),
    I("grand-pavilion-theatre", "Grand Pavilion Theatre", ["Grand Pavilion Theatre"], ["GRAND PAVILION THE"], [
        U("client_tickets", "spend", "60.00", "420.00", "424", "UK-R025", ["Theatre tickets for clients", "Box seats, client evening"], needs_line=True),
    ], fmt="UK-DEB"),
    I("westshire-growth-hub", "Westshire Growth Hub", ["Westshire Growth Hub"], ["WESTSHIRE GROWTH H"], [
        U("grant", "receive", "500.00", "5000.00", "260", "UK-R060", ["Business grant", "Growth grant award", "Energy efficiency grant"], routine=True),
    ], refs=["GRANT {N5}"], fmt="UK-BGC"),
    I("bramblewood-garden-centre", "Bramblewood Garden Centre", ["Bramblewood Garden Centre"], ["BRAMBLEWOOD GARDEN"], [
        U("unknown_purchase", "spend", "12.00", "220.00", "NEEDS_REVIEW", "UK-R049", [""], hooks=["UK-R049"]),
        U("precedent_purchase", "spend", "12.00", "220.00", "310", "UK-R049", [""], hooks=["UK-R049"]),
    ], fmt="UK-DEB", category="retail_general"),
    # Customers (receipts). References as customers type them, a share in lower case (shortcut S-1); the invoice
    # number is the one on the line ({INV} is one value per record, R12).
    *[I(slug, name, [name], [narr], [
        U("customer_receipt", "receive", lo, hi, "200", "UK-R058", ["Invoice {INV}", "Payment for invoice {INV}", ""], routine=True, refs=CUSTOMER_REFS, only={"trades": CUSTOMER_TRADES[slug]}),
        U("customer_refund", "spend", "20.00", "400.00", "200", "UK-R044", ["Refund to customer, {INV}", "Credit note {INV} refunded"], needs_line=True, facts={"account": "200"}, refs=["REFUND {N4}"], only={"trades": CUSTOMER_TRADES[slug]}),
    ], fmt="UK-FPI", category="customer") for slug, name, narr, lo, hi in [
        ("kestrel-print-co", "Kestrel Print Co", "KESTREL PRINT CO", "120.00", "2400.00"),
        ("ashcombe-dental", "Ashcombe Dental Practice Ltd", "ASHCOMBE DENTAL", "150.00", "3800.00"),
        ("fairhaven-cafe", "Fairhaven Cafe Ltd", "FAIRHAVEN CAFE LTD", "60.00", "1200.00"),
        ("moorside-veterinary", "Moorside Veterinary Centre", "MOORSIDE VETERINAR", "90.00", "2600.00"),
        ("elmstead-academy-trust", "Elmstead Primary Academy Trust", "ELMSTEAD ACADEMY", "200.00", "4800.00"),
        ("rookwood-estates", "Rookwood Estates Ltd", "ROOKWOOD ESTATES", "250.00", "6500.00"),
        ("pennant-engineering", "Pennant Engineering Ltd", "PENNANT ENGINEERIN", "300.00", "7200.00"),
        ("bluebell-day-nursery", "Bluebell Day Nursery Ltd", "BLUEBELL NURSERY", "80.00", "1600.00"),
        ("tidewater-marine", "Tidewater Marine Services Ltd", "TIDEWATER MARINE", "250.00", "5400.00"),
        ("lakeview-holiday-lets", "Lakeview Holiday Lets Ltd", "LAKEVIEW HOLIDAY", "120.00", "3100.00"),
    ]],
    # Government payees (kind government)
    I("hmrc-vat", "HMRC VAT", ["HMRC VAT"], ["HMRC VAT"], [
        U("vat_payment", "spend", "180.00", "9800.00", "820", "UK-R008", ["", "VAT return payment"], refs=["{VRN}"], only={"vat": True}),
        U("vat_repayment", "receive", "80.00", "4200.00", "820", "UK-R008", ["", "VAT repayment"], refs=["{VRN}"], only={"vat": True}, fmt="UK-BGC"),
    ], kind="government", category="government"),
    I("hmrc-cumbernauld", "HMRC Cumbernauld", ["HMRC Cumbernauld", "HMRC"], ["HMRC CUMBERNAULD", "HMRC - ACCOUNTS OF"], [
        U("paye", "spend", "150.00", "6200.00", "825", "UK-R009", ["", "PAYE {MMM}"], refs=["{AOREF}", "{AOREF}{YYMM}"], only={"employer": True}),
        U("corporation_tax", "spend", "400.00", "18000.00", "830", "UK-R010", ["", "CT payment", "CT {YY}"], refs=["{CTREF}"], only={"entity": ["limited_company"]}),
        U("self_assessment", "spend", "200.00", "8500.00", "980", "UK-R011", ["", "Tax payment"], refs=["{UTR}K"]),
        U("no_reference", "spend", "200.00", "6000.00", "NEEDS_REVIEW", "UK-R012", [""], refs=[""], narratives=["HMRC CUMBERNAULD"]),
        U("cis_deductions", "spend", "120.00", "2600.00", "827", "UK-R070", ["", "CIS {MMM}", "CIS return {MMM}"], refs=["{AOREF}", "{AOREF}{YYMM}"], only={"trades": CONSTRUCTION}),
    ], kind="government", category="government"),
    I("hmrc-shipley", "HMRC Shipley", ["HMRC Shipley"], ["HMRC SHIPLEY"], [
        U("self_assessment", "spend", "200.00", "8500.00", "980", "UK-R011", ["", "Self assessment"], refs=["{UTR}K"]),
        U("paye", "spend", "150.00", "5200.00", "825", "UK-R009", [""], refs=["{AOREF}"], only={"employer": True}),
        U("no_reference", "spend", "200.00", "5000.00", "NEEDS_REVIEW", "UK-R012", [""], refs=["PAYMENT", ""]),
        U("cis_deductions", "spend", "120.00", "2600.00", "827", "UK-R070", ["", "CIS {MMM}"], refs=["{AOREF}"], only={"trades": CONSTRUCTION}),
    ], kind="government", category="government"),
    I("dvla", "DVLA", ["DVLA"], ["DVLA-{A7}"], [
        U("vehicle_tax", "spend", "15.00", "345.00", "449", "UK-R001", ["Vehicle tax, van", "Road tax"], routine=True, facts={"account": "449"}, only={"vehicle_methods": ["actual_costs", "taxi_cost_of_sales"]}),
    ], kind="government", category="government", fmt="UK-DD"),
    # Statutory fees at the published tariff (R10), checked 2026-10-13. ICO data protection fee, tier 1 (micro
    # organisation): GBP 52 a year from 17 February 2025 (Data Protection (Charges and Information) (Amendment)
    # Regulations 2025; gov.uk "Data protection fee regime: government response"), with the GBP 5 direct debit
    # discount kept, so GBP 47 by direct debit (ico.org.uk/for-organisations/data-protection-fee). Companies House
    # confirmation statement filed online: GBP 50 from 1 February 2026, GBP 34 before (gov.uk/government/
    # publications/companies-house-fees, updated 25 September 2026). Equal bounds put the tariff on every line; the
    # history window starts before 1 February 2026, so history rows dated earlier should carry CS01_FEE_BEFORE.
    I("ico", "Information Commissioner's Office", ["ICO", "Information Commissioner's Office"], ["ICO ZB{N6}"], [
        U("registration", "spend", ICO_FEE_DD, ICO_FEE_DD, "485", "UK-R042", ["Data protection fee", "ICO registration"], routine=True, facts={"membership": "trade_body"}),
    ], kind="government", category="government", fmt="UK-DD"),
    I("companies-house", "Companies House", ["Companies House"], ["COMPANIES HOUSE"], [
        U("confirmation", "spend", CS01_FEE, CS01_FEE, "485", "UK-R042", ["Confirmation statement fee"], routine=True, facts={"membership": "trade_body"}, only={"entity": ["limited_company"]}),
    ], kind="government", category="government", fmt="UK-DEB"),
]

# Small sellers billed through a card processor (shortcut S-1, R4): independent traders who take card payments on a
# SumUp, Square, Zettle or PayPal reader, so their card lines carry the processor prefix. They are ordinary routine
# spending in S0 and S1, so a prefix on a debit is no sign of an attack, and they are the only hosts of card-descriptor
# attacks (attacks.py). Each has one routine spend use with line descriptions; every narrative starts with the
# prefix, and `descriptor` is the short seller part a descriptor keeps within 22 characters. Invented names, checked
# by web search on 2026-10-13 (no UK business of that name found).
SMALL_SELLER_PREFIX = {"uk-b-sumup": "SUMUP *", "uk-b-square": "SQ *", "uk-b-zettle": "iZ *", "uk-b-paypal": "PAYPAL *"}
_SMALL_SELLERS = [
    # slug, name, processor, descriptor (short seller part), card name (long), trades, use, lo, hi, code, rule, lines, facts
    ("tollbeck-print-shop", "Tollbeck Print Shop", "uk-b-square", "TOLLBECK", "TOLLBECK PRINT",
     ["creative", "professional", "transport", "education", "health", "events", "services", "beauty"],
     "printing", "8.00", "140.00", "461", "UK-R057",
     ["Receipt books printed", "Appointment cards printed", "Letterheaded paper"], {"stationery": True}),
    ("copsewood-sawmill", "Copsewood Sawmill", "uk-b-sumup", "COPSEWOOD", "COPSEWOOD SAW",
     ["construction", "manufacturing", "crafts"],
     "materials", "25.00", "420.00", "310", "UK-R055",
     ["Oak boards for job", "Sawn timber, job {N4}", "Offcuts for workshop"], {}),
    ("hollowmere-farm-shop", "Hollowmere Farm Shop", "uk-b-zettle", "HOLLOWMERE", "HOLLOWMERE FARM",
     ["catering"],
     "stock", "12.00", "160.00", "310", "UK-R055",
     ["Eggs and veg for kitchen", "Fresh herbs for menu", "Free range eggs, kitchen"], {}),
    ("tillymoss-packaging", "Tillymoss Packaging Supplies", "uk-b-paypal", "TILLYMOS", "TILLYMOSS PKG",
     ["retail", "crafts", "catering"],
     "packaging", "10.00", "180.00", "310", "UK-R055",
     ["Packaging for orders", "Mailing boxes for orders", "Tissue and ribbon for orders"], {}),
    ("pinmarsh-salon-supplies", "Pinmarsh Salon Supplies", "uk-b-square", "PINMARSH", "PINMARSH SUPPLIES",
     ["beauty"],
     "stock", "15.00", "220.00", "310", "UK-R055",
     ["Hair colour stock", "Colour and developer for salon", "Shampoo for salon use"], {}),
    ("furrowby-grooming-supplies", "Furrowby Grooming Supplies", "uk-b-zettle", "FURROWBY", "FURROWBY GROOMING",
     ["services"],
     "stock", "10.00", "150.00", "310", "UK-R055",
     ["Grooming shampoo stock", "Clipper blades", "Dog conditioner stock"], {}),
    ("selbridge-therapy-supplies", "Selbridge Therapy Supplies", "uk-b-zettle", "SELBRIDGE", "SELBRIDGE THERAPY",
     ["health"],
     "consumables", "10.00", "160.00", "310", "UK-R055",
     ["Couch roll and massage oil", "Kinesiology tape", "Treatment room consumables"], {}),
    ("threadmoor-embroidery", "Threadmoor Embroidery", "uk-b-sumup", "THRDMOOR", "THREADMOOR WEAR",
     ["construction", "trades", "transport", "catering", "manufacturing", "services"],
     "workwear", "25.00", "240.00", "429", "UK-R062",
     ["Logo polo shirts for work", "Embroidered work jackets", "Branded hi-vis vests"], {}),
    ("brindlecombe-tech-repairs", "Brindlecombe Tech Repairs", "uk-b-paypal", "BRINDLE", "BRINDLE REPAIR",
     ["professional", "creative", "education", "events", "health"],
     "equipment_repair", "35.00", "260.00", "473", "UK-R024",
     ["Laptop screen repair", "Replace laptop battery", "Work phone screen repair"], {"scope": "repair"}),
    ("lanternhay-party-hire", "Lanternhay Party Hire", "uk-b-square", "LANTERNHAY", "LANTERNHAY HIRE",
     ["events", "catering"],
     "event_hire", "30.00", "380.00", "310", "UK-R055",
     ["Table linen hire for event", "Glassware hire, client event", "Chair covers hire, wedding job"], {"service": True}),
]
# Sellers whose account turns on the purpose (UK-R062 workwear needs a work context; a farm shop sells kitchen stock or
# groceries): their records always carry the typed line (re-audit R3, D6 small-seller pattern).
_SELLERS_NEEDING_LINE = {"threadmoor-embroidery", "hollowmere-farm-shop", "copsewood-sawmill"}  # "COPSEWOOD SAW": a saw or timber
for slug, name, proc, short, long, trades, use, lo, hi, code, rule, lines, facts in _SMALL_SELLERS:
    prefix = SMALL_SELLER_PREFIX[proc]
    # The card name fits the 22-character descriptor field; prefix plus the short part leaves 6 or more free.
    assert len(prefix + long) <= 22 and len(prefix + short) <= 16, (long, short)
    seller = I(slug, name, [name, prefix + long], [prefix + long, prefix + long + " {TOWN}"], [
        U(use, "spend", lo, hi, code, rule, lines, facts=dict(facts), routine=True, only={"trades": trades},
          needs_line=slug in _SELLERS_NEEDING_LINE),
    ], fmt="UK-DEB", category="small_seller", raw=[prefix + long])
    seller["processor"] = proc
    seller["descriptor"] = prefix + short
    MERCHANTS.append(seller)

# Person payees paid one amount a month (R5 landlord rent, R18 net pay): `Env.amount_for` with these pseudo uses and
# the person's merchant id (`person:<firm>:<token>`) gives one plan per firm and person, so scored items
# (scenarios_uk.person_amount) and history rows draw the same amount, with at most one step.
PERSON_FIXED_UK = {
    "landlord": {"use": "rent", "amount_range": ["450.00", "1500.00"], "amount_mode": "fixed"},
    "employee": {"use": "net_pay", "amount_range": ["600.00", "2400.00"], "amount_mode": "fixed"},
    "director": {"use": "net_pay", "amount_range": ["700.00", "1100.00"], "amount_mode": "fixed"},
}


def _chart_defaults() -> None:
    """Per-chart default codes (F12): owner accounts follow the entity's chart (980 / 970 on the sole trader chart,
    835 on the company chart), and a use restricted to the other entity family has no default on a chart. The rule
    functions decide gold; this only keeps the catalogue from naming a code the chart variant lacks."""
    from .charts import accounts, uk_variant

    owner = {"st": {"835": "980"}, "co": {"980": "835", "970": "835"}}
    ents = {"st": ("sole_trader", "partnership"), "co": ("limited_company",)}
    for m in MERCHANTS:
        for u in m["uses"]:
            for key in ("st", "co"):
                cid = uk_variant(key)["chart_id"]
                code = u["default_code"]
                allowed = u["only"].get("entity")
                if allowed and not set(allowed) & set(ents[key]):
                    code = None
                elif code != "NEEDS_REVIEW" and code not in accounts("UK", key):
                    code = owner[key].get(code)
                u["default_code_per_chart"][cid] = code


_chart_defaults()

UK_TOWNS = ["LEEDS", "YORK", "DERBY", "BATH", "HULL", "STOCKPORT", "NORWICH", "EXETER", "TELFORD", "PRESTON",
            "CARDIFF", "PERTH", "READING", "KENDAL", "LINCOLN", "HEREFORD", "DONCASTER", "TRURO", "STIRLING", "IPSWICH"]


MARKETPLACE_PROCESSORS = {"uk-etsy", "uk-amazon-seller"}


def _p(entity, vat, sic, label, trade, town, *, vehicle="none", phone="business_contract", threshold="500.00",
       threshold_in_history=False, card="none", savings=True, processors=(), premises=False, home_office="none",
       employees=0, subcontractors=0, lender=None, basis=None, gaps=(), landlord_person=False, cis=None):
    return {
        "entity_type": entity,
        "vat_registered": vat,
        "trade": {"sic_2007": sic, "label": label, "tag": trade},
        "town": town,
        "accounting_basis": basis or ("cash" if entity != "limited_company" else "traditional"),
        "policies": {
            "vehicle_method": vehicle,
            "phone": phone,
            "capitalisation_threshold": threshold,
            "threshold_in_history": threshold_in_history,
            "card_account": card,
            "savings_account": savings,
            "processors": list(processors),
            # B5 (F10): card processor and payment platform payouts are booked gross with the fee split out
            # (UK-R019); marketplace payouts stay one net line to sales (UK-R066).
            "processor_booking": "gross_split" if set(processors) - MARKETPLACE_PROCESSORS else None,
            "marketplace_booking": "net_single_line" if set(processors) & MARKETPLACE_PROCESSORS else None,
            "premises": premises,
            "home_office": home_office,
            "directors_loan_account_in_use": entity == "limited_company",
            "lender": lender,
        },
        "employees": employees,
        "subcontractors": subcontractors,
        "landlord_person": landlord_person,
        "policy_gaps": list(gaps),
        # UK CIS status (B16, SCHEMA_v0.2 section 8): firms.py fills the default (not in CIS) when None.
        "cis": dict(cis) if cis else None,
    }


def _cis(contractor=False, subcontractor=False, rate=None):
    return {"contractor": contractor, "subcontractor": subcontractor, "deduction_rate": rate}


# uk-01 has two subcontractors (R7): one with gross payment status, one paid under deduction, so the dev split shows
# both kinds of CIS payment.
FIRMS = {
    "uk-01": ("Harbour Lane Joinery Ltd", "dev", _p("limited_company", True, "43320", "Joinery installation", "construction", "KENDAL", vehicle="actual_costs", card="092", premises=True, employees=2, subcontractors=2, threshold_in_history=True, lender="uk-i-kingsmere-business-finance", cis=_cis(True, True, "20"))),
    "uk-02": ("Copperleaf Bakery", "dev", _p("sole_trader", False, "10710", "Manufacture of bread and fresh pastry", "catering", "HEREFORD", vehicle="simplified_mileage", phone="mixed_use_claimed", premises=True, processors=["uk-sumup"], employees=1)),
    "uk-03": ("Northwind Mobile Mechanics", "dev", _p("sole_trader", True, "45200", "Maintenance and repair of motor vehicles", "trades", "DONCASTER", vehicle="actual_costs", phone="personal_not_claimed", card="811")),
    "uk-04": ("Kestrel Lane Design Studio", "test", _p("partnership", True, "74100", "Specialised design activities", "creative", "BATH", phone="mixed_use_claimed", processors=["uk-stripe"], premises=True, threshold="250.00", threshold_in_history=True)),
    "uk-05": ("Brightwell Electrical Services", "test", _p("sole_trader", True, "43210", "Electrical installation", "construction", "STOCKPORT", vehicle="simplified_mileage", phone="mixed_use_claimed", subcontractors=1, gaps=["vehicle_method"], cis=_cis(True, True, "20"))),
    "uk-06": ("Saltmarsh Coffee House Ltd", "test", _p("limited_company", True, "56102", "Unlicensed restaurants and cafes", "catering", "TRURO", card="811", premises=True, processors=["uk-zettle"], employees=4)),
    "uk-07": ("Fernhill Garden Services", "test", _p("sole_trader", False, "81300", "Landscape service activities", "trades", "LINCOLN", vehicle="actual_costs", phone="personal_not_claimed")),
    "uk-08": ("Riverbend Bookkeeping Partners", "dev", _p("partnership", False, "69201", "Accounting and bookkeeping activities", "professional", "YORK", vehicle="simplified_mileage", phone="personal_not_claimed", home_office="flat_rate")),
    "uk-09": ("Ashby Cross Physiotherapy Ltd", "dev", _p("limited_company", False, "86900", "Other human health activities", "health", "DERBY", card="092", premises=True, processors=["uk-square"], employees=2, landlord_person=True)),
    "uk-10": ("Moorland Taxis", "dev", _p("sole_trader", False, "49320", "Taxi operation", "transport", "PRESTON", vehicle="taxi_cost_of_sales", phone="mixed_use_claimed", processors=["uk-sumup"])),
    "uk-11": ("Tidepool Web Partners", "test", _p("partnership", True, "62012", "Business and domestic software development", "creative", "CARDIFF", phone="business_contract", processors=["uk-stripe"], card="092")),
    "uk-12": ("Larkspur Florists Ltd", "test", _p("limited_company", True, "47760", "Retail sale of flowers and plants", "retail", "NORWICH", vehicle="actual_costs", premises=True, processors=["uk-sumup", "uk-etsy"], employees=2)),
    "uk-13": ("Granite Peak Building Contractors Ltd", "test", _p("limited_company", True, "41202", "Construction of domestic buildings", "construction", "TELFORD", vehicle="actual_costs", card="092", premises=True, employees=3, subcontractors=2, lender="uk-b-natwest", gaps=["card_account"], cis=_cis(contractor=True))),
    "uk-14": ("Bellwether Marketing Consultancy", "test", _p("sole_trader", True, "70229", "Management consultancy activities", "professional", "READING", vehicle="simplified_mileage", phone="mixed_use_claimed", home_office="flat_rate", processors=["uk-stripe"], gaps=["phone"])),
    "uk-15": ("Old Mill Pottery", "dev", _p("sole_trader", False, "23410", "Manufacture of ceramic household articles", "crafts", "IPSWICH", phone="personal_not_claimed", processors=["uk-etsy", "uk-paypal", "uk-amazon-seller"], premises=True)),
    "uk-16": ("Cobalt Street Hair Studio", "test", _p("partnership", False, "96020", "Hairdressing and other beauty treatment", "beauty", "EXETER", phone="mixed_use_claimed", premises=True, processors=["uk-square"], employees=1, landlord_person=True)),
    "uk-17": ("Wrenfield Plumbing and Heating Ltd", "dev", _p("limited_company", True, "43220", "Plumbing, heat and air-conditioning installation", "construction", "HULL", vehicle="actual_costs", card="811", employees=1, subcontractors=1, cis=_cis(True, True, "0"))),
    "uk-18": ("Silverdale Dog Grooming", "test", _p("sole_trader", False, "96090", "Other personal service activities", "services", "PERTH", vehicle="actual_costs", phone="personal_not_claimed", processors=["uk-sumup"], premises=True)),
    "uk-19": ("Hollowbrook Catering Partners", "test", _p("partnership", True, "56210", "Event catering activities", "catering", "STIRLING", vehicle="actual_costs", phone="mixed_use_claimed", processors=["uk-stripe"], employees=2, premises=True, lender="uk-b-hsbc")),
    "uk-20": ("Quillstone Translation Services Ltd", "dev", _p("limited_company", True, "74300", "Translation and interpretation activities", "professional", "CARDIFF", processors=["uk-paypal"], card="092")),
    "uk-21": ("Nettlebed Organic Box Scheme", "test", _p("sole_trader", False, "47910", "Retail sale via mail order houses or via Internet", "retail", "HEREFORD", vehicle="actual_costs", phone="personal_not_claimed", processors=["uk-gocardless", "uk-stripe"], premises=True)),
    "uk-22": ("Ironbridge Fabrication Ltd", "test", _p("limited_company", True, "25110", "Manufacture of metal structures", "manufacturing", "TELFORD", vehicle="actual_costs", threshold="1000.00", threshold_in_history=True, premises=True, employees=3, card="811", lender="uk-i-kingsmere-business-finance")),
    "uk-23": ("Pebblebank Tutoring", "dev", _p("sole_trader", False, "85590", "Other education", "education", "YORK", vehicle="simplified_mileage", phone="mixed_use_claimed", home_office="flat_rate")),
    "uk-24": ("Larchmont Events Ltd", "test", _p("limited_company", True, "82302", "Activities of conference organisers", "events", "LEEDS", card="092", processors=["uk-stripe"], employees=2)),
    # Added in v0.2 for CIS (B16, choice S6). Invented names, checked against a web search on 2026-10-13.
    "uk-25": ("Quernmoor Plastering", "dev", _p("sole_trader", False, "43310", "Plastering", "construction", "DONCASTER", vehicle="actual_costs", phone="mixed_use_claimed", savings=False, cis=_cis(subcontractor=True, rate="30"))),
    "uk-26": ("Swaleford Roofing Partners", "test", _p("partnership", True, "43910", "Roofing activities", "construction", "PRESTON", vehicle="actual_costs", phone="mixed_use_claimed", card="811", cis=_cis(subcontractor=True, rate="20"))),
}
