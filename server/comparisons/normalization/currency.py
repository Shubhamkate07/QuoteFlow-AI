"""
Currency Normalization and Explicit Currency Conversion Service.
Enforces strict deterministic processing:
- Normalizes currency codes and symbols (e.g. INR vs USD vs EUR vs GBP).
- Never invents, guesses, or estimates exchange rates.
- Any conversion requires an explicit ExchangeRate with rate_source and rate_date.
"""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Dict, List, Optional, Tuple


class MissingExchangeRateError(ValueError):
    """Raised when currency conversion is requested but no explicit exchange rate is provided."""
    pass


class InvalidCurrencyCodeError(ValueError):
    """Raised when an unknown or invalid currency code is supplied."""
    pass


@dataclass(frozen=True)
class CurrencyMetadata:
    code: str
    symbol: str
    name: str
    decimals: int
    aliases: Tuple[str, ...]


# Major ISO 4217 Currencies with formatting metadata
_CURRENCY_REGISTRY: Dict[str, CurrencyMetadata] = {
    'USD': CurrencyMetadata('USD', '$', 'US Dollar', 2, ('usd', '$', 'us$', 'u.s. dollar', 'dollar', 'bucks')),
    'INR': CurrencyMetadata('INR', '₹', 'Indian Rupee', 2, ('inr', '₹', 'rs', 'rs.', 'rupee', 'rupees', 'inr ₹')),
    'EUR': CurrencyMetadata('EUR', '€', 'Euro', 2, ('eur', '€', 'euro', 'euros')),
    'GBP': CurrencyMetadata('GBP', '£', 'British Pound', 2, ('gbp', '£', 'pound', 'pounds', 'quid', 'sterling')),
    'CAD': CurrencyMetadata('CAD', 'C$', 'Canadian Dollar', 2, ('cad', 'c$', 'canadian dollar')),
    'AUD': CurrencyMetadata('AUD', 'A$', 'Australian Dollar', 2, ('aud', 'a$', 'australian dollar')),
    'JPY': CurrencyMetadata('JPY', '¥', 'Japanese Yen', 0, ('jpy', '¥', 'yen')),
    'CNY': CurrencyMetadata('CNY', '¥', 'Chinese Yuan', 2, ('cny', 'rmb', 'yuan', 'renminbi')),
    'SGD': CurrencyMetadata('SGD', 'S$', 'Singapore Dollar', 2, ('sgd', 's$', 'singapore dollar')),
    'CHF': CurrencyMetadata('CHF', 'CHF', 'Swiss Franc', 2, ('chf', 'swiss franc', 'francs')),
    'AED': CurrencyMetadata('AED', 'AED', 'UAE Dirham', 2, ('aed', 'dirham', 'dh', 'dhs')),
    'SAR': CurrencyMetadata('SAR', 'SAR', 'Saudi Riyal', 2, ('sar', 'riyal', 'riyals')),
}

_SYMBOL_MAP: Dict[str, str] = {}
for code, meta in _CURRENCY_REGISTRY.items():
    _SYMBOL_MAP[code.lower()] = code
    for alias in meta.aliases:
        _SYMBOL_MAP[alias.lower().strip()] = code


def normalize_currency_code(raw_currency: Optional[str]) -> str:
    """
    Normalizes arbitrary currency strings, symbols, or codes to standard 3-letter ISO uppercase code.
    Examples:
        '₹' -> 'INR'
        'Rs.' -> 'INR'
        'INR' -> 'INR'
        'inr ₹' -> 'INR'
        '$' -> 'USD'
        '€' -> 'EUR'
        'GBP' -> 'GBP'
    """
    if not raw_currency:
        return 'USD'

    cleaned = raw_currency.strip().lower()
    cleaned = re.sub(r'[\s\.\,]', '', cleaned)

    if cleaned in _SYMBOL_MAP:
        return _SYMBOL_MAP[cleaned]

    # Check substring matches for prominent symbols and codes
    if '₹' in cleaned or 'inr' in cleaned or 'rs' in cleaned:
        return 'INR'
    if '€' in cleaned or 'eur' in cleaned:
        return 'EUR'
    if '£' in cleaned or 'gbp' in cleaned:
        return 'GBP'
    if '$' in cleaned or 'usd' in cleaned:
        return 'USD'
    if '¥' in cleaned or 'jpy' in cleaned:
        return 'JPY'

    upper_raw = raw_currency.strip().upper()
    if re.match(r'^[A-Z]{3}$', upper_raw):
        return upper_raw

    # Fallback to USD if empty or unrecognized
    return 'USD'


def get_currency_decimals(currency_code: str) -> int:
    """Returns decimal precision for currency (e.g. 0 for JPY, 2 for USD/INR/EUR)."""
    norm = normalize_currency_code(currency_code)
    if norm in _CURRENCY_REGISTRY:
        return _CURRENCY_REGISTRY[norm].decimals
    return 2


@dataclass
class ExchangeRate:
    """
    Explicit, verified exchange rate between two currencies.
    Exchange rates must never be invented.
    """
    source_currency: str
    target_currency: str
    rate: Decimal
    rate_source: str       # e.g. "European Central Bank", "RBI Official Fixing", "Contractual Rate"
    rate_date: date        # Date the rate applies to
    notes: Optional[str] = None

    def __post_init__(self):
        self.source_currency = normalize_currency_code(self.source_currency)
        self.target_currency = normalize_currency_code(self.target_currency)
        if not isinstance(self.rate, Decimal):
            self.rate = Decimal(str(self.rate))
        if self.rate <= Decimal('0.0'):
            raise ValueError(f"Exchange rate must be strictly positive. Got {self.rate}")
        if not self.rate_source or not self.rate_source.strip():
            raise ValueError("Exchange rate source must be explicitly documented. Rates cannot be invented.")
        if not isinstance(self.rate_date, (date, datetime)):
            raise ValueError("Exchange rate date must be explicitly specified.")
        if isinstance(self.rate_date, datetime):
            self.rate_date = self.rate_date.date()


@dataclass
class CurrencyConversionRecord:
    """Audit citation attached to any converted financial figure."""
    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    target_currency: str
    exchange_rate: Decimal
    rate_source: str
    rate_date: date
    is_identity: bool = False


class ExchangeRateTable:
    """
    Deterministic repository of explicit exchange rates.
    Supports direct lookup and mathematically derived inverse rates with full source provenance.
    """
    def __init__(self, rates: Optional[List[ExchangeRate]] = None):
        self._rates: Dict[Tuple[str, str, Optional[date]], ExchangeRate] = {}
        if rates:
            for r in rates:
                self.add_rate(r)

    def add_rate(self, rate: ExchangeRate):
        key = (rate.source_currency, rate.target_currency, rate.rate_date)
        self._rates[key] = rate

    def get_rate(
        self,
        source_currency: str,
        target_currency: str,
        as_of_date: Optional[date] = None,
        allow_inverse: bool = True,
    ) -> Optional[ExchangeRate]:
        src = normalize_currency_code(source_currency)
        tgt = normalize_currency_code(target_currency)

        if src == tgt:
            return ExchangeRate(
                source_currency=src,
                target_currency=tgt,
                rate=Decimal('1.0'),
                rate_source='Identity (Same Currency)',
                rate_date=as_of_date or date.today(),
            )

        # 1. Exact match by date
        if as_of_date:
            key = (src, tgt, as_of_date)
            if key in self._rates:
                return self._rates[key]

        # 2. Match without date constraint (latest or single defined rate)
        candidates = [
            r for (s, t, d), r in self._rates.items()
            if s == src and t == tgt
        ]
        if candidates:
            # Sort by rate_date descending
            candidates.sort(key=lambda r: r.rate_date, reverse=True)
            return candidates[0]

        # 3. Allow inverse rate derivation if configured (e.g. A->B rate R implies B->A is 1/R)
        if allow_inverse:
            inv_candidates = [
                r for (s, t, d), r in self._rates.items()
                if s == tgt and t == src
            ]
            if inv_candidates:
                inv_candidates.sort(key=lambda r: r.rate_date, reverse=True)
                direct = inv_candidates[0]
                derived_rate = (Decimal('1.0') / direct.rate).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
                return ExchangeRate(
                    source_currency=src,
                    target_currency=tgt,
                    rate=derived_rate,
                    rate_source=f"Derived Inverse of ({direct.rate_source})",
                    rate_date=direct.rate_date,
                    notes=f"Derived as 1 / {direct.rate} from direct {tgt}->{src} rate",
                )

        return None


class CurrencyConversionService:
    """
    Dedicated, explicit currency conversion service.
    Guarantees:
    - Never invents an exchange rate.
    - If rate is missing, raises MissingExchangeRateError.
    - Produces a full audit trail record detailing original value, converted value, rate, source, and date.
    """
    def __init__(self, rate_table: Optional[ExchangeRateTable] = None):
        self.rate_table = rate_table or ExchangeRateTable()

    def convert(
        self,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        as_of_date: Optional[date] = None,
    ) -> CurrencyConversionRecord:
        """
        Converts amount from source_currency to target_currency using an explicit rate.
        Raises MissingExchangeRateError if currencies differ and no explicit rate exists.
        """
        src = normalize_currency_code(source_currency)
        tgt = normalize_currency_code(target_currency)

        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        # Identity conversion
        if src == tgt:
            return CurrencyConversionRecord(
                original_amount=amount,
                original_currency=src,
                converted_amount=amount,
                target_currency=tgt,
                exchange_rate=Decimal('1.0'),
                rate_source='Identity (Same Currency)',
                rate_date=as_of_date or date.today(),
                is_identity=True,
            )

        # Lookup rate
        rate_entry = self.rate_table.get_rate(src, tgt, as_of_date=as_of_date)
        if not rate_entry:
            raise MissingExchangeRateError(
                f"Cannot convert {amount} {src} to {tgt}: No explicit exchange rate found. "
                f"Exchange rates must never be invented. Please provide an explicit rate with its source and date."
            )

        decimals = get_currency_decimals(tgt)
        rounding_format = Decimal('1.' + '0' * decimals) if decimals > 0 else Decimal('1')
        converted = (amount * rate_entry.rate).quantize(rounding_format, rounding=ROUND_HALF_UP)

        return CurrencyConversionRecord(
            original_amount=amount,
            original_currency=src,
            converted_amount=converted,
            target_currency=tgt,
            exchange_rate=rate_entry.rate,
            rate_source=rate_entry.rate_source,
            rate_date=rate_entry.rate_date,
            is_identity=False,
        )
