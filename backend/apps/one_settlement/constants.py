from decimal import Decimal


SHIPPER_CODE = "one"
ALLOWED_COMPANY_CODE = "new"
JONGNO_CITY_NAME = "종로구"

SERVICE_W12 = "W12_DAY"
SERVICE_N3 = "N3_DAY"
SERVICE_W4 = "W4_DAWN"

CATEGORY_SSG = "SSG"
CATEGORY_COMMON = "COMMON"
CATEGORY_TRADERS = "TRADERS"
CATEGORY_YES24 = "YES24"

SERVICE_LABELS = {
    SERVICE_W12: "W1,2_당일",
    SERVICE_N3: "N3_당일",
    SERVICE_W4: "W4_새벽",
}

CATEGORY_LABELS = {
    CATEGORY_SSG: "SSG",
    CATEGORY_COMMON: "공동배송",
    CATEGORY_TRADERS: "트레이더스",
    CATEGORY_YES24: "YES24",
}

STATEMENT_ORDER = [
    (SERVICE_W12, CATEGORY_SSG),
    (SERVICE_W12, CATEGORY_TRADERS),
    (SERVICE_W12, CATEGORY_COMMON),
    (SERVICE_W12, CATEGORY_YES24),
    (SERVICE_N3, CATEGORY_SSG),
    (SERVICE_N3, CATEGORY_YES24),
    (SERVICE_W4, CATEGORY_SSG),
    (SERVICE_W4, CATEGORY_COMMON),
    (SERVICE_W4, CATEGORY_YES24),
]

W12_VOLUME_BRACKETS = [
    (500, Decimal("1650")),
    (800, Decimal("1630")),
    (1100, Decimal("1610")),
    (1400, Decimal("1590")),
    (1700, Decimal("1570")),
    (2000, Decimal("1550")),
    (2300, Decimal("1530")),
    (None, Decimal("1510")),
]

N3_SSG_TABLE = {
    1: Decimal("2570"),
    2: Decimal("2870"),
    3: Decimal("3070"),
    4: Decimal("3560"),
    5: Decimal("4050"),
}

W12_SSG_TABLE = {
    1: Decimal("2370"),
    2: Decimal("2670"),
    3: Decimal("2870"),
    4: Decimal("3360"),
    5: Decimal("3850"),
}

W4_TABLE = {
    1: Decimal("2600"),
    2: Decimal("2800"),
    3: Decimal("3000"),
    4: Decimal("3200"),
    5: Decimal("3400"),
}

YES24_RATES = {
    SERVICE_W12: Decimal("1430"),
    SERVICE_N3: Decimal("1430"),
    SERVICE_W4: Decimal("2475"),
}

JONGNO_BOX_EXTRA = Decimal("200")

