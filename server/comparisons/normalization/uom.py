"""
Unit of Measure (UOM) Registry, Canonicalization, and Conversion Engine.
Handles deterministic normalization between discrete count units (e.g. pieces vs units vs dozens),
mass/weight (e.g. grams vs kilograms vs tonnes), length (e.g. mm, m, feet, inches),
volume, and service time units.
"""
import re
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, Optional, Tuple, NamedTuple


class UOMCategory(str, Enum):
    COUNT = 'COUNT'          # Discrete units (PCS, Units, Dozen, Pairs, etc.)
    WEIGHT = 'WEIGHT'        # Mass (G, KG, MT, LBS, OZ)
    LENGTH = 'LENGTH'        # Distance (MM, CM, M, KM, IN, FT, YD)
    VOLUME = 'VOLUME'        # Liquid / Space (ML, L, GAL, M3)
    AREA = 'AREA'            # Surface (SQM, SQFT)
    TIME = 'TIME'            # Service / duration (HR, DAY, WEEK, MONTH)
    PACKAGE = 'PACKAGE'      # Packaging containers (BOX, PACK, CTN, SET, LOT)
    CUSTOM = 'CUSTOM'        # Unrecognized or specialized commercial units


class UOMDefinition(NamedTuple):
    code: str
    category: UOMCategory
    base_unit: str
    factor_to_base: Decimal   # 1 source unit = X base units
    aliases: Tuple[str, ...]
    description: str


# Canonical Base Units per Category:
# COUNT -> PCS
# WEIGHT -> KG
# LENGTH -> M
# VOLUME -> L
# AREA -> SQM
# TIME -> HR

_UOM_REGISTRY: Dict[str, UOMDefinition] = {
    # ---------------- COUNT (Discrete items) ----------------
    'PCS': UOMDefinition(
        code='PCS',
        category=UOMCategory.COUNT,
        base_unit='PCS',
        factor_to_base=Decimal('1.0'),
        aliases=('pc', 'pcs', 'piece', 'pieces', 'each', 'ea', 'unit', 'units', 'nos', 'no', 'item', 'items', 'pce', 'nbr'),
        description='Individual piece or unit',
    ),
    'DOZEN': UOMDefinition(
        code='DOZEN',
        category=UOMCategory.COUNT,
        base_unit='PCS',
        factor_to_base=Decimal('12.0'),
        aliases=('dz', 'doz', 'dozen', 'dozens'),
        description='Dozen (12 pieces)',
    ),
    'PAIR': UOMDefinition(
        code='PAIR',
        category=UOMCategory.COUNT,
        base_unit='PCS',
        factor_to_base=Decimal('2.0'),
        aliases=('pr', 'pair', 'pairs'),
        description='Pair (2 pieces)',
    ),
    'GROSS': UOMDefinition(
        code='GROSS',
        category=UOMCategory.COUNT,
        base_unit='PCS',
        factor_to_base=Decimal('144.0'),
        aliases=('gr', 'gross'),
        description='Gross (144 pieces)',
    ),

    # ---------------- WEIGHT / MASS (Base: KG) ----------------
    'KG': UOMDefinition(
        code='KG',
        category=UOMCategory.WEIGHT,
        base_unit='KG',
        factor_to_base=Decimal('1.0'),
        aliases=('kg', 'kgs', 'kilo', 'kilogram', 'kilograms'),
        description='Kilogram',
    ),
    'G': UOMDefinition(
        code='G',
        category=UOMCategory.WEIGHT,
        base_unit='KG',
        factor_to_base=Decimal('0.001'),
        aliases=('g', 'gm', 'gms', 'gram', 'grams'),
        description='Gram',
    ),
    'MG': UOMDefinition(
        code='MG',
        category=UOMCategory.WEIGHT,
        base_unit='KG',
        factor_to_base=Decimal('0.000001'),
        aliases=('mg', 'mgs', 'milligram', 'milligrams'),
        description='Milligram',
    ),
    'MT': UOMDefinition(
        code='MT',
        category=UOMCategory.WEIGHT,
        base_unit='KG',
        factor_to_base=Decimal('1000.0'),
        aliases=('mt', 'ton', 'tons', 'tonne', 'tonnes', 'metric ton', 'metric tons'),
        description='Metric Tonne (1,000 kg)',
    ),
    'LB': UOMDefinition(
        code='LB',
        category=UOMCategory.WEIGHT,
        base_unit='KG',
        factor_to_base=Decimal('0.45359237'),
        aliases=('lb', 'lbs', 'pound', 'pounds'),
        description='Pound (Avoirdupois)',
    ),
    'OZ': UOMDefinition(
        code='OZ',
        category=UOMCategory.WEIGHT,
        base_unit='KG',
        factor_to_base=Decimal('0.028349523125'),
        aliases=('oz', 'ounce', 'ounces'),
        description='Ounce',
    ),

    # ---------------- LENGTH / DISTANCE (Base: M) ----------------
    'M': UOMDefinition(
        code='M',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('1.0'),
        aliases=('m', 'meter', 'meters', 'metre', 'metres', 'mtr', 'mtrs'),
        description='Meter',
    ),
    'MM': UOMDefinition(
        code='MM',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('0.001'),
        aliases=('mm', 'millimeter', 'millimeters', 'millimetre', 'millimetres'),
        description='Millimeter',
    ),
    'CM': UOMDefinition(
        code='CM',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('0.01'),
        aliases=('cm', 'centimeter', 'centimeters', 'centimetre', 'centimetres'),
        description='Centimeter',
    ),
    'KM': UOMDefinition(
        code='KM',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('1000.0'),
        aliases=('km', 'kilometer', 'kilometers', 'kilometre', 'kilometres'),
        description='Kilometer',
    ),
    'IN': UOMDefinition(
        code='IN',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('0.0254'),
        aliases=('in', 'inch', 'inches', '"'),
        description='Inch',
    ),
    'FT': UOMDefinition(
        code='FT',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('0.3048'),
        aliases=('ft', 'foot', 'feet', "'"),
        description='Foot',
    ),
    'YD': UOMDefinition(
        code='YD',
        category=UOMCategory.LENGTH,
        base_unit='M',
        factor_to_base=Decimal('0.9144'),
        aliases=('yd', 'yds', 'yard', 'yards'),
        description='Yard',
    ),

    # ---------------- VOLUME / LIQUID (Base: L) ----------------
    'L': UOMDefinition(
        code='L',
        category=UOMCategory.VOLUME,
        base_unit='L',
        factor_to_base=Decimal('1.0'),
        aliases=('l', 'ltr', 'ltrs', 'liter', 'liters', 'litre', 'litres'),
        description='Liter',
    ),
    'ML': UOMDefinition(
        code='ML',
        category=UOMCategory.VOLUME,
        base_unit='L',
        factor_to_base=Decimal('0.001'),
        aliases=('ml', 'mls', 'milliliter', 'milliliters', 'millilitre', 'millilitres'),
        description='Milliliter',
    ),
    'GAL': UOMDefinition(
        code='GAL',
        category=UOMCategory.VOLUME,
        base_unit='L',
        factor_to_base=Decimal('3.785411784'),
        aliases=('gal', 'gals', 'gallon', 'gallons', 'us gal'),
        description='US Gallon',
    ),

    # ---------------- AREA (Base: SQM) ----------------
    'SQM': UOMDefinition(
        code='SQM',
        category=UOMCategory.AREA,
        base_unit='SQM',
        factor_to_base=Decimal('1.0'),
        aliases=('sqm', 'sq m', 'm2', 'm^2', 'square meter', 'square meters', 'square metre'),
        description='Square Meter',
    ),
    'SQFT': UOMDefinition(
        code='SQFT',
        category=UOMCategory.AREA,
        base_unit='SQM',
        factor_to_base=Decimal('0.09290304'),
        aliases=('sqft', 'sq ft', 'ft2', 'ft^2', 'square foot', 'square feet'),
        description='Square Foot',
    ),

    # ---------------- TIME / SERVICE (Base: HR) ----------------
    'HR': UOMDefinition(
        code='HR',
        category=UOMCategory.TIME,
        base_unit='HR',
        factor_to_base=Decimal('1.0'),
        aliases=('hr', 'hrs', 'hour', 'hours'),
        description='Hour',
    ),
    'DAY': UOMDefinition(
        code='DAY',
        category=UOMCategory.TIME,
        base_unit='HR',
        factor_to_base=Decimal('8.0'),  # Standard 8-hr engineering workday
        aliases=('day', 'days', 'man-day', 'manday', 'man days'),
        description='Work Day (8 hours)',
    ),

    # ---------------- PACKAGING / SETS (Non-convertible without pack size) ----------------
    'SET': UOMDefinition(
        code='SET',
        category=UOMCategory.PACKAGE,
        base_unit='SET',
        factor_to_base=Decimal('1.0'),
        aliases=('set', 'sets', 'kit', 'kits', 'assembly'),
        description='Set or Assembly Kit',
    ),
    'LOT': UOMDefinition(
        code='LOT',
        category=UOMCategory.PACKAGE,
        base_unit='LOT',
        factor_to_base=Decimal('1.0'),
        aliases=('lot', 'lots', 'lump sum', 'ls', 'job', 'package'),
        description='Lump Sum / Lot',
    ),
    'BOX': UOMDefinition(
        code='BOX',
        category=UOMCategory.PACKAGE,
        base_unit='BOX',
        factor_to_base=Decimal('1.0'),
        aliases=('box', 'boxes', 'pack', 'packs', 'pkt', 'ctn', 'carton', 'cartons', 'case', 'cases'),
        description='Packaging Box or Carton',
    ),
}

# Inverted alias lookup table for O(1) resolution
_ALIAS_LOOKUP: Dict[str, str] = {}
for code, uom_def in _UOM_REGISTRY.items():
    _ALIAS_LOOKUP[code.lower()] = code
    for alias in uom_def.aliases:
        _ALIAS_LOOKUP[alias.lower().strip()] = code


def normalize_uom_string(raw: Optional[str]) -> str:
    """Cleans a raw UOM string, stripping dots, extra spaces, and trailing symbols."""
    if not raw:
        return 'PCS'
    cleaned = re.sub(r'[\.\,\/]', '', raw.strip().lower())
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned


def canonicalize_uom(raw_unit: Optional[str]) -> Tuple[str, UOMCategory]:
    """
    Returns the canonical uppercase code and UOM category.
    Handles 'pieces' vs 'units' vs 'ea' -> all resolve to ('PCS', UOMCategory.COUNT).
    """
    if not raw_unit:
        return 'PCS', UOMCategory.COUNT

    cleaned = normalize_uom_string(raw_unit)

    # 1. Exact match in alias lookup
    if cleaned in _ALIAS_LOOKUP:
        code = _ALIAS_LOOKUP[cleaned]
        return code, _UOM_REGISTRY[code].category

    # 2. Check uppercase literal
    upper_raw = raw_unit.strip().upper()
    if upper_raw in _UOM_REGISTRY:
        return upper_raw, _UOM_REGISTRY[upper_raw].category

    # 3. Check regex match for plural variations or "box of N"
    box_match = re.search(r'box\s*(?:of)?\s*(\d+)', cleaned)
    if box_match:
        return 'BOX', UOMCategory.PACKAGE

    # 4. Fallback to clean uppercase string as CUSTOM category
    return upper_raw if upper_raw else 'PCS', UOMCategory.CUSTOM


def can_convert_uom(source_unit: str, target_unit: str) -> bool:
    """
    Returns True if source and target UOMs belong to the exact same convertible category
    and share the same dimensional base unit.
    """
    source_code, source_cat = canonicalize_uom(source_unit)
    target_code, target_cat = canonicalize_uom(target_unit)

    if source_code == target_code:
        return True

    # Both must be registered and in the same category (excluding custom/package which require explicit ratios)
    if source_code not in _UOM_REGISTRY or target_code not in _UOM_REGISTRY:
        return False

    source_def = _UOM_REGISTRY[source_code]
    target_def = _UOM_REGISTRY[target_code]

    if source_def.category == UOMCategory.PACKAGE or target_def.category == UOMCategory.PACKAGE:
        return False

    return source_def.category == target_def.category and source_def.base_unit == target_def.base_unit


def get_uom_conversion_factor(source_unit: str, target_unit: str) -> Optional[Decimal]:
    """
    Returns conversion factor F such that:
        target_quantity = source_quantity * F
        normalized_unit_price = source_unit_price / F

    Example:
        source = 'G', target = 'KG'
        1 G = 0.001 KG. Factor is Decimal('0.001').
        1000 G * 0.001 = 1 KG.
        Price $0.05/G / 0.001 = $50.00/KG.
        Total remains identical: 1000 * 0.05 == 1 * 50.00 == $50.00.
    """
    source_code, _ = canonicalize_uom(source_unit)
    target_code, _ = canonicalize_uom(target_unit)

    if source_code == target_code:
        return Decimal('1.0')

    if not can_convert_uom(source_code, target_code):
        return None

    source_def = _UOM_REGISTRY[source_code]
    target_def = _UOM_REGISTRY[target_code]

    # source_quantity in base = source_quantity * source_def.factor_to_base
    # target_quantity = (source_quantity in base) / target_def.factor_to_base
    factor = source_def.factor_to_base / target_def.factor_to_base
    return factor


def convert_quantity_and_price(
    source_quantity: Decimal,
    source_unit_price: Decimal,
    source_unit: str,
    target_unit: Optional[str] = None,
) -> Tuple[Decimal, Decimal, str, Decimal, bool]:
    """
    Deterministically normalizes quantity and unit price.
    If target_unit is omitted, converts to the category's canonical base unit (e.g. G -> KG, DOZEN -> PCS).

    Returns:
        (normalized_quantity, normalized_unit_price, normalized_unit, conversion_factor, is_converted)

    Invariant:
        normalized_quantity * normalized_unit_price == source_quantity * source_unit_price
        (within rounding precision).
    """
    src_code, src_cat = canonicalize_uom(source_unit)

    if target_unit is None:
        # Default to canonical base unit of the category
        if src_code in _UOM_REGISTRY:
            tgt_code = _UOM_REGISTRY[src_code].base_unit
        else:
            tgt_code = src_code
    else:
        tgt_code, _ = canonicalize_uom(target_unit)

    factor = get_uom_conversion_factor(src_code, tgt_code)

    if factor is None or factor == Decimal('1.0'):
        # No conversion possible or needed; use canonical code
        return (
            source_quantity,
            source_unit_price,
            src_code,
            Decimal('1.0'),
            src_code == tgt_code
        )

    # Apply factor:
    # Q_norm = Q_src * factor
    # P_norm = P_src / factor
    normalized_quantity = (source_quantity * factor).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    normalized_unit_price = (source_unit_price / factor).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    return (
        normalized_quantity,
        normalized_unit_price,
        tgt_code,
        factor,
        True
    )
