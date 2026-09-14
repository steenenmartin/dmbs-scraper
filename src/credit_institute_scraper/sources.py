"""The four feeds: explicit field translations and validation at the boundary."""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, overload

ENDPOINTS = {
    "Jyske": ("https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste",) * 2,
    "Nordea": ("https://ebolig.nordea.dk/wemapp/api/credit/fixedrate/bonds.json",),
    "RealKreditDanmark": (
        "https://rd.dk/api/Rates/GetOpenOffers",
        "https://rd.dk/api/Rates/GetVariableLoans",
    ),
    "TotalKredit": (
        "https://www.totalkredit.dk//api/bondinformation/table?tableId=privat-udbetaling-af-laan-aktuelle-kurser-kunder&domain=totalkredit",
        "https://www.totalkredit.dk//api/bondinformation/table?tableId=privat-udbetaling-af-laan-kontantrenter-raadgivere-og-kunder&domain=totalkredit",
    ),
}


@dataclass(frozen=True)
class Bond:
    institute: str
    years_to_maturity: int
    spot_price: float | None
    offer_price: float | None
    max_interest_only_period: int
    coupon_rate: float
    isin: str


@dataclass(frozen=True)
class Rate:
    institute: str
    fixed_rate_period: int
    max_interest_only_period: int
    spot_rate: float | None


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    product: str | None = None


class SourceError(ValueError):
    """An expected, explicitly validated problem in the provider's input."""


def field(product: Any, name: str, expected: type | None = None) -> Any:
    if not isinstance(product, dict):
        raise SourceError(f"product={product!r}: expected an object")
    if name not in product:
        raise SourceError(f"{name}=<missing>: required field")
    value = product[name]
    if expected is not None and (
        not isinstance(value, expected) or (expected is str and not value.strip())
    ):
        raise SourceError(f"{name}={value!r}: expected {expected.__name__}")
    return value


@overload
def number(value: object, *, integer: Literal[True], field: str = "value") -> int: ...


@overload
def number(value: object, *, integer: Literal[False] = False, field: str = "value") -> float: ...


def number(value: Any, *, integer: bool = False, field: str = "value") -> float | int:
    raw = value
    if isinstance(value, bool):
        raise SourceError(f"{field}={raw!r}: boolean is not a market value")
    try:
        value = float(
            value.replace(",", ".").strip().removesuffix("%") if isinstance(value, str) else value
        )
    except (ValueError, TypeError, OverflowError) as error:
        raise SourceError(f"{field}={raw!r}: expected a number") from error
    if not math.isfinite(value) or (integer and (not value.is_integer() or not 0 <= value < 2**63)):
        raise SourceError(
            f"{field}={raw!r}: expected a finite number"
            + (" of whole years within PostgreSQL bigint range" if integer else "")
        )
    return int(value) if integer else value


def price(value: object) -> float | None:
    try:
        value = number(value)
        return value if value > 0 else None
    except SourceError:
        return None


def bond(
    institute: str,
    term: object,
    spot: object,
    offer: object,
    freedom: object,
    coupon: object,
    isin: object,
) -> Bond:
    term = number(term, integer=True, field="years_to_maturity")
    freedom = number(freedom, integer=True, field="max_interest_only_period")
    if not isinstance(isin, str) or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        raise SourceError(f"isin={isin!r}: invalid ISIN")
    if term == 0 or freedom > term:
        raise SourceError(
            f"years_to_maturity={term!r}, max_interest_only_period={freedom!r}: invalid periods"
        )
    return Bond(
        institute,
        term,
        price(spot),
        price(offer),
        freedom,
        number(coupon, field="coupon_rate"),
        isin,
    )


def rate(institute: str, period: object, freedom: object, value: object) -> Rate:
    period = number(period, integer=True, field="fixed_rate_period")
    freedom = number(freedom, integer=True, field="max_interest_only_period")
    if period == 0:
        raise SourceError("fixed_rate_period=0: expected a positive period")
    try:
        value = number(value, field="spot_rate") or None
    except SourceError:
        value = None
    return Rate(institute, period, freedom, value)


def isin_code(fund: object) -> str:
    if not re.fullmatch(r"\d{1,9}", str(fund)):
        raise SourceError(f"fondCode={fund!r}: expected up to nine digits")
    prefix = "DK" + str(fund).zfill(9)
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in prefix)
    total = sum(
        sum(divmod(int(c) * (2 if i % 2 == 0 else 1), 10)) for i, c in enumerate(reversed(digits))
    )
    return prefix + str(-total % 10)


def jyske(kind: str, p: dict[str, Any]) -> Bond | Rate:
    if kind == "floating":
        return rate("Jyske", field(p, "fastrenteperiode"), 0, p.get("vaegtetTilbudskursProcent"))
    return bond(
        "Jyske",
        field(p, "loebetidAar"),
        p.get("aktuelKurs"),
        p.get("tilbudsKurs"),
        field(p, "maxAntalAfdragsfrieAar"),
        field(p, "kuponrenteProcent"),
        field(p, "isin"),
    )


def nordea(kind: str, p: dict[str, Any]) -> Bond | None:
    term = number(field(p, "loanPeriodMax"), integer=True, field="loanPeriodMax")
    isin = field(p, "isinCode", str)
    if term == 15 and isin in {
        "DK0002056134",
        "DK0002054436",
        "DK0002053545",
        "DK0002051176",
        "DK0002050285",
    }:
        return None
    return bond(
        "Nordea",
        term,
        p.get("rate"),
        None,
        0 if field(p, "repaymentFreedomMax") == "Nej" else p["repaymentFreedomMax"],
        number(field(p, "fundName", str).split()[0].strip("%"), field="fundName"),
        isin,
    )


def realkredit_dk(kind: str, p: dict[str, Any]) -> Bond | Rate | None:
    if kind == "floating":
        match = re.fullmatch(
            r"FlexLoan_F(\d{1,2})_(WithInstallment|WithoutInstallment)",
            field(p, "name", str),
        )
        if match:
            return rate(
                "RealKreditDanmark",
                match[1],
                0 if match[2] == "WithInstallment" else 30,
                p.get("offerrate"),
            )
        return None
    if field(p, "loanTypeCode", str) not in {"01", "16"}:
        return None
    term = number(field(p, "termToMaturityYears"), integer=True, field="termToMaturityYears")
    isin = field(p, "isinCode")
    if isin == "DK0004618733" and term == 0:
        term = 30
    terms = number(field(p, "numberOfTermsWithoutRepayment"), field="numberOfTermsWithoutRepayment")
    quotes = p.get("prices") or []
    spot = (
        quotes[0].get("price")
        if isinstance(quotes, list) and quotes and isinstance(quotes[0], dict)
        else None
    )
    if p.get("offerprice") in (-1, "-1", "-1.0"):
        spot = None
    return bond(
        "RealKreditDanmark",
        term,
        spot,
        p.get("offerprice"),
        (120 if terms == 119 else terms) / 4,
        field(p, "nominelInterestRate"),
        isin,
    )


def totalkredit(kind: str, p: dict[str, Any]) -> Bond | Rate:
    name = field(p, "name", str)
    if kind == "floating":
        match = re.fullmatch(r"F(\d{1,2}) med (?:(afdrag)|op til (\d+) års afdragsfrihed)", name)
        if not match:
            raise SourceError(f"name={name!r}: unrecognized floating product name")
        return rate(
            "TotalKredit",
            match[1],
            0 if match[2] else match[3],
            p.get("innerInterestGrossValue"),
        )
    parts = name.split()
    if not name.endswith("med afdrag") and len(parts) < 6:
        raise SourceError(f"name={name!r}: missing interest-only period")
    return bond(
        "TotalKredit",
        number(field(p, "lifetime", str).split()[0], integer=True, field="lifetime"),
        p.get("spotPriceRatePayment"),
        p.get("priceRate"),
        0 if name.endswith("med afdrag") else number(parts[5], integer=True, field="name"),
        number(parts[0].strip("%"), field="name"),
        isin_code(field(p, "fondCode")),
    )


PARSERS: dict[str, Callable[[str, dict[str, Any]], Bond | Rate | None]] = {
    "Jyske": jyske,
    "Nordea": nordea,
    "RealKreditDanmark": realkredit_dk,
    "TotalKredit": totalkredit,
}


QUOTE_FIELDS = {
    "Jyske": {
        "spot_price": "aktuelKurs",
        "offer_price": "tilbudsKurs",
        "spot_rate": "vaegtetTilbudskursProcent",
    },
    "Nordea": {"spot_price": "rate"},
    "RealKreditDanmark": {
        "spot_price": "prices",
        "offer_price": "offerprice",
        "spot_rate": "offerrate",
    },
    "TotalKredit": {
        "spot_price": "spotPriceRatePayment",
        "offer_price": "priceRate",
        "spot_rate": "innerInterestGrossValue",
    },
}


def parse(institute: str, kind: str, payload: Any) -> tuple[list[Bond | Rate], list[Issue]]:
    """Return products and issues; a malformed sibling never discards good products."""
    parser = PARSERS[institute]
    if kind not in {"fixed", "floating"}:
        raise ValueError(f"Unsupported product kind: {kind}")
    entries, issues = [], []
    try:
        if institute == "Jyske":
            payload = field(
                payload,
                "fastRenteProdukter" if kind == "fixed" else "variabelRenteProdukter",
                list,
            )
        elif institute == "TotalKredit":
            groups = field(payload, "groups", list)
            if not groups:
                raise SourceError("groups=[]: expected a product group")
            payload = field(groups[0], "entries", list)
        if not isinstance(payload, list):
            raise SourceError(f"response={payload!r}: expected a product list")
    except SourceError as error:
        return entries, [Issue(kind + ".response", str(error))]
    for index, product in enumerate(payload):
        identity = None
        try:
            if not isinstance(product, dict):
                raise SourceError(f"product={product!r}: expected an object")
            identity = next(
                (
                    str(product[key])
                    for key in ("isin", "isinCode", "name", "fondCode")
                    if product.get(key) is not None
                ),
                None,
            )
            entry = parser(kind, product)
            if entry is None:
                continue
            entries.append(entry)
            if isinstance(entry, Bond):
                identity = entry.isin
                quote_fields = (
                    ("spot_price",) if institute == "Nordea" else ("spot_price", "offer_price")
                )
            else:
                identity = f"F{entry.fixed_rate_period}/IO{entry.max_interest_only_period}"
                quote_fields = ("spot_rate",)
            for quote in quote_fields:
                if getattr(entry, quote) is None:
                    raw_field = QUOTE_FIELDS[institute][quote]
                    detail = f"{raw_field}={product.get(raw_field)!r}"
                    if institute == "RealKreditDanmark" and quote == "spot_price":
                        detail += f", offerprice={product.get('offerprice')!r}"
                    issues.append(
                        Issue(
                            f"{kind}.{quote}",
                            f"Missing or invalid {quote}: {detail}",
                            identity,
                        )
                    )
        except SourceError as error:
            issues.append(Issue(kind + ".product", f"Product {index}: {error}", identity))
        except Exception as error:
            error.add_note(f"Parsing {institute} {kind}: product={identity!r}, index={index}")
            raise
    if not entries and not issues:
        issues.append(Issue(kind + ".empty", "No supported products in response"))
    return entries, issues
