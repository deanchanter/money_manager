"""Merchant Category Code -> category name mapping.

SimpleFIN sends an `mcc` on most transactions. It is assigned by the card
network rather than guessed from text, so it beats keyword matching on
merchants whose names say nothing about what they sell ("John's Fishin Shack").

Values map to the default category names seeded in main.py. Names that do not
exist in a given database are simply ignored.
"""

# Ranges are (low, high, category name), inclusive.
MCC_RANGES: list[tuple[int, int, str]] = [
    (3000, 3299, "Transportation"),   # airlines
    (3300, 3499, "Transportation"),   # car rental
    (3500, 3999, "Entertainment"),    # lodging
    (5300, 5399, "Shopping"),         # wholesale clubs
    (5600, 5699, "Shopping"),         # apparel
    (5700, 5799, "Housing"),          # home furnishing
    (5800, 5899, "Dining"),
    (5900, 5999, "Shopping"),
    (7000, 7299, "Entertainment"),
    (7800, 7999, "Entertainment"),
    (8000, 8099, "Healthcare"),
    (8200, 8299, "Other"),            # education
]

MCC_CODES: dict[int, str] = {
    4111: "Transportation",   # commuter transport
    4121: "Transportation",   # taxis / rideshare
    4131: "Transportation",   # bus lines
    4784: "Transportation",   # tolls
    4900: "Utilities",        # utilities
    4812: "Utilities",        # telecom equipment
    4814: "Utilities",        # telecom services
    4816: "Utilities",        # internet
    4899: "Utilities",        # cable / satellite
    5411: "Groceries",        # grocery stores / supermarkets
    5422: "Groceries",        # meat provisioners
    5441: "Groceries",        # candy / confectionery
    5451: "Groceries",        # dairy
    5462: "Groceries",        # bakeries
    5499: "Groceries",        # misc food stores
    5541: "Transportation",   # service stations
    5542: "Transportation",   # automated fuel dispensers
    5812: "Dining",           # eating places / restaurants
    5813: "Dining",           # bars / taverns
    5814: "Dining",           # fast food
    5912: "Healthcare",       # drug stores / pharmacies
    5921: "Dining",           # package stores (beer/wine/liquor)
    6300: "Insurance",        # insurance sales / premiums
    6011: "Transfer",         # ATM withdrawals
    6012: "Transfer",         # financial institutions
    6540: "Transfer",         # non-financial money transfer
    7011: "Entertainment",    # lodging / hotels
    7832: "Entertainment",    # movie theaters
    8011: "Healthcare",       # doctors
    8021: "Healthcare",       # dentists
    8062: "Healthcare",       # hospitals
    8099: "Healthcare",       # medical services
    8931: "Other",            # accounting / bookkeeping
    9211: "Other",            # court costs
    9399: "Other",            # government services
}


def category_name_for_mcc(mcc: object) -> str | None:
    """Category name for a merchant category code, or None if unmapped."""
    if mcc is None:
        return None
    try:
        code = int(str(mcc).strip())
    except (TypeError, ValueError):
        return None

    if code in MCC_CODES:
        return MCC_CODES[code]
    for low, high, name in MCC_RANGES:
        if low <= code <= high:
            return name
    return None
