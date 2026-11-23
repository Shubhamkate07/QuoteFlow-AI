"""
Canonicalization and Normalization Engine for Technical Specification Keys and Values.
Maps arbitrary industry vendor phrasing to standard engineering keys, units, and magnitudes.
"""
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Canonical mapping table for common procurement parameters
CANONICAL_KEY_SYNONYMS: Dict[str, str] = {
    # Output and switching
    'output': 'output',
    'output_type': 'output',
    'switching_output': 'output',
    'output_signal': 'output',
    'signal_output': 'output',
    'switching_element_function': 'output_function',
    'output_function': 'output_function',
    'contact_type': 'output_function',
    'contact_configuration': 'output_function',
    'switching_function': 'output_function',
    'contact': 'output_function',
    'contacts': 'output_function',

    # Voltage & Electrical
    'voltage': 'voltage',
    'operating_voltage': 'voltage',
    'supply_voltage': 'voltage',
    'input_voltage': 'voltage',
    'rated_voltage': 'voltage',
    'v_in': 'voltage',
    'power_supply': 'voltage',
    'current': 'current',
    'load_current': 'current',
    'operating_current': 'current',
    'rated_current': 'current',
    'power': 'power',
    'power_consumption': 'power',
    'wattage': 'power',

    # Sensing & Detection
    'sensing_distance': 'sensing_distance',
    'sensing_range': 'sensing_distance',
    'sn': 'sensing_distance',
    'detection_range': 'sensing_distance',
    'detection_distance': 'sensing_distance',
    'operating_distance': 'sensing_distance',
    'range': 'sensing_distance',
    'measuring_range': 'sensing_distance',

    # Connections & Interface
    'connection': 'connection',
    'connection_type': 'connection',
    'connector': 'connection',
    'termination': 'connection',
    'interface': 'connection',
    'plug_type': 'connection',
    'electrical_connection': 'connection',

    # Enclosure & Protection
    'ip_rating': 'ip_rating',
    'ingress_protection': 'ip_rating',
    'protection_class': 'ip_rating',
    'degree_of_protection': 'ip_rating',
    'enclosure_rating': 'ip_rating',

    # Physical / Mechanical
    'mounting': 'mounting',
    'mounting_type': 'mounting',
    'installation_type': 'mounting',
    'flush_non_flush': 'mounting',
    'housing_size': 'housing_size',
    'thread': 'housing_size',
    'diameter': 'housing_size',
    'finished_diameter': 'housing_size',
    'outer_diameter': 'housing_size',
    'outside_diameter': 'housing_size',
    'shaft_diameter': 'housing_size',
    'od': 'housing_size',
    'length': 'length',
    'overall_length': 'length',
    'total_length': 'length',
    'shaft_length': 'length',
    'oal': 'length',
    'size': 'housing_size',
    'dimensions': 'dimensions',
    'body_size': 'housing_size',

    # Material
    'material': 'material',
    'housing_material': 'material',
    'body_material': 'material',
    'case_material': 'material',

    # Manufacturing process
    'process': 'process',
    'manufacturing_process': 'process',
    'machining_process': 'process',
    'fabrication_process': 'process',

    # Inspection & Quality Certification
    'inspection': 'inspection',
    'documentation': 'inspection',
    'inspection_report': 'inspection',
    'dimensional_inspection': 'inspection',
    'quality_inspection': 'inspection',
    'test_certificate': 'inspection',
    'material_certificate': 'inspection',
    'reports': 'inspection',

    # Batch quantity
    'quantity': 'quantity',
    'qty': 'quantity',
    'count': 'quantity',
    'batch_size': 'quantity',
    'order_quantity': 'quantity',

    # Environmental / Operational
    'operating_temperature': 'operating_temperature',
    'ambient_temperature': 'operating_temperature',
    'temperature_range': 'operating_temperature',
    'temp_range': 'operating_temperature',
    'switching_frequency': 'switching_frequency',
    'frequency': 'switching_frequency',
    'operating_frequency': 'switching_frequency',
    'response_time': 'response_time',
    'accuracy': 'accuracy',
    'tolerance': 'accuracy',
    'dimensional_tolerance': 'accuracy',
    'diameter_tolerance': 'accuracy',
    'length_tolerance': 'accuracy',
    'machining_tolerance': 'accuracy',
    'pressure': 'pressure',
    'operating_pressure': 'pressure',
}


def canonicalize_parameter_key(raw_key: str) -> str:
    """
    Standardizes a technical parameter name into a canonical slug.
    Examples:
        - "Operating Voltage" -> "voltage"
        - "Sensing distance (Sn)" -> "sensing_distance"
        - "Output type" -> "output"
        - "Connection / Interface" -> "connection"
    """
    if not raw_key:
        return 'unspecified_parameter'

    clean = raw_key.lower().strip()
    # Remove parentheses and brackets
    clean = re.sub(r'[\(\)\[\]\{\}]', ' ', clean)
    slug = re.sub(r'[^a-z0-9]+', '_', clean).strip('_')

    # Direct synonym match
    if slug in CANONICAL_KEY_SYNONYMS:
        return CANONICAL_KEY_SYNONYMS[slug]

    # Partial / substring match for well-known roots
    if 'sensing_distance' in slug or 'sensing_range' in slug or slug == 'sn':
        return 'sensing_distance'
    if 'voltage' in slug or slug == 'v_in':
        return 'voltage'
    if 'output' in slug and 'function' not in slug:
        return 'output'
    if 'contact' in slug:
        return 'output_function'
    if 'connector' in slug or 'connection' in slug or 'termination' in slug:
        return 'connection'
    if 'ip_rating' in slug or 'ingress_protection' in slug or 'protection_class' in slug:
        return 'ip_rating'
    if 'temperature' in slug:
        return 'operating_temperature'
    if 'frequency' in slug:
        return 'switching_frequency'
    if 'material' in slug:
        return 'material'
    if 'diameter' in slug:
        return 'housing_size'
    if 'length' in slug and 'wave' not in slug:
        return 'length'
    if 'tolerance' in slug:
        return 'accuracy'
    if 'process' in slug:
        return 'process'

    return slug


# Alias for concise import
canonicalize_key = canonicalize_parameter_key


def clean_spec_value(val: Any) -> str:
    """Removes outer formatting, quotes, and excessive whitespace from a spec value."""
    if val is None:
        return ''
    s = str(val).strip()
    return re.sub(r'\s+', ' ', s)


def parse_distance_dimension(val_str: str) -> Optional[Tuple[Decimal, str]]:
    """
    Extracts magnitude and standardizes unit to 'mm' for distance / dimension specs.
    Examples:
        - "8mm" -> (Decimal('8.0'), 'mm')
        - "8 mm" -> (Decimal('8.0'), 'mm')
        - "0.8cm" -> (Decimal('8.0'), 'mm')
        - "25 mm" -> (Decimal('25.0'), 'mm')
    """
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?', val_str.lower())
    if not match:
        return None

    try:
        num = Decimal(match.group(1))
    except InvalidOperation:
        return None

    unit = (match.group(2) or 'mm').strip()

    if unit in ('mm', 'millimeter', 'millimeters'):
        return (num, 'mm')
    elif unit in ('cm', 'centimeter', 'centimeters'):
        return (num * Decimal('10.0'), 'mm')
    elif unit in ('m', 'meter', 'meters'):
        return (num * Decimal('1000.0'), 'mm')
    elif unit in ('in', 'inch', 'inches', '"'):
        return (num * Decimal('25.4'), 'mm')

    return (num, unit)


def normalize_voltage(val_str: str) -> Optional[str]:
    """
    Standardizes DC / AC voltage declarations.
    Examples:
        - "24V DC", "24 VDC", "24V-DC", "24 v dc", "24 volts dc" -> "24V DC"
        - "230V AC", "230 VAC", "230V-AC", "230 volts ac" -> "230V AC"
        - "10-30V DC", "10...30 VDC" -> "10-30V DC"
    """
    clean = val_str.upper().replace(' ', '').replace('VOLTS', 'V').replace('VOLT', 'V')

    # Wide range check
    range_match = re.search(r'([0-9]+)[\.\-]+([0-9]+)V?(DC|AC)?', clean)
    if range_match:
        current_type = range_match.group(3) or ('DC' if 'DC' in clean else 'AC' if 'AC' in clean else '')
        type_str = f" {current_type}" if current_type else ""
        return f"{range_match.group(1)}-{range_match.group(2)}V{type_str}".strip()

    # Fixed voltage check
    single_match = re.search(r'([0-9]+)V?(DC|AC)?', clean)
    if single_match:
        current_type = single_match.group(2) or ('DC' if 'DC' in clean else 'AC' if 'AC' in clean else '')
        type_str = f" {current_type}" if current_type else ""
        return f"{single_match.group(1)}V{type_str}".strip()

    return None


def parse_ip_rating(val_str: str) -> Optional[Tuple[int, int]]:
    """
    Parses IP Ingress Protection rating (e.g. 'IP67' -> (6, 7)).
    First digit: Solids / Dust protection (0-6).
    Second digit: Water / Liquid ingress protection (0-9).
    """
    match = re.search(r'ip\s*([0-6])\s*([0-9][kK]?)', val_str.lower())
    if not match:
        return None
    try:
        solids = int(match.group(1))
        liquids_raw = match.group(2).lower()
        liquids = 9 if '9' in liquids_raw or 'k' in liquids_raw else int(liquids_raw)
        return (solids, liquids)
    except ValueError:
        return None


def extract_connection_tokens(val_str: str) -> Set[str]:
    """
    Extracts core connection tokens (e.g. 'M12', 'M8', '4-pin', 'Cable', 'pigtail').
    """
    tokens = set()
    s = val_str.upper()

    if 'M12' in s:
        tokens.add('M12')
    elif 'M8' in s:
        tokens.add('M8')
    elif 'M5' in s:
        tokens.add('M5')
    elif 'M18' in s:
        tokens.add('M18')
    elif 'M30' in s:
        tokens.add('M30')

    if 'CABLE' in s or 'PRE-WIRED' in s or 'FLYING LEADS' in s:
        tokens.add('CABLE')

    if '4-PIN' in s or '4 PIN' in s or '4P' in s or '4 POLE' in s:
        tokens.add('4-PIN')
    elif '3-PIN' in s or '3 PIN' in s or '3P' in s or '3 POLE' in s:
        tokens.add('3-PIN')
    elif '5-PIN' in s or '5 PIN' in s or '5P' in s or '5 POLE' in s:
        tokens.add('5-PIN')

    return tokens
