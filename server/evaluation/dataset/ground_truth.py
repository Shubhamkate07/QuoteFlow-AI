"""
Ground-Truth Benchmark Dataset for QuoteFlow AI.
Specifically aligned to Requisition RFQ-2026-001:
"Custom Industrial Shaft Manufacturing – 100 Units"
- Material: EN8 medium carbon steel
- Diameter: 40 mm
- Length: 500 mm
- Tolerance: ±0.05 mm
- Process: CNC turning and machining
- Finish: Machined finish
- Documentation: Material certificate and dimensional inspection report
- Quantity: 100 PCS
- Required Delivery: Dec 15, 2026
- Currency: USD
- Target Budget: $1,000.00 ($10.00 / unit)
"""

from typing import Any, Dict, List

STANDARD_BENCHMARK_RFQ = {
    "rfq_number": "RFQ-2026-001",
    "title": "Custom Industrial Shaft Manufacturing – 100 Units",
    "target_delivery_weeks": 3,
    "payment_terms_benchmark": "Net 30",
    "warranty_benchmark_months": 12,
    "validity_benchmark_days": 30,
    "currency": "USD",
}

DATASET_GROUND_TRUTH: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Case 1: Clean PDF Quotation (Apex Precision) - Benchmark Ideal Bid
    # -------------------------------------------------------------------------
    {
        "case_id": "case_01_clean_pdf",
        "file_name": "01_clean_quotation_apex.pdf",
        "title": "Apex Precision Clean Machining PDF Quotation",
        "document_format": "PDF",
        "edge_case_type": "CLEAN_PDF",
        "edge_case_description": (
            "Well-structured vector PDF with clear metadata, 8% sales tax, and 100% "
            "compliance with EN8 material, 40x500mm dimensions, and inspection reports."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Apex Precision Components Inc.",
                "contact_person": "Sarah Jenkins",
                "email": "sales@apexprecision.com",
                "phone": "+1 (555) 019-2831",
                "address": "1420 Industrial Pkwy, Elk Grove Village, IL 60007",
                "quotation_number": "APX-2026-0881",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 950.00,
                "tax": 76.00,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 1026.00,
            },
            "commercial_terms": {
                "delivery_time": "2 weeks ARO (Delivery by Dec 08, 2026)",
                "delivery_terms": "FOB Destination",
                "payment_terms": "Net 30 days",
                "warranty": "12 months manufacturer warranty",
                "notes": "Full lot of 100 units. Material certificate and dimensional inspection report included.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Custom Industrial Shaft – EN8 Steel (40mm Dia x 500mm Length)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 9.50,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 950.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Finished Diameter", "value": "40 mm"},
                        {"name": "Overall Length", "value": "500 mm"},
                        {"name": "Dimensional Tolerance", "value": "±0.05 mm"},
                        {"name": "Manufacturing Process", "value": "CNC Turning & Machining"},
                        {"name": "Surface Finish", "value": "Machined Finish"},
                        {"name": "Documentation", "value": "Material Certificate & Dimensional Inspection Report Included"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 950.00,
            "calculated_tax_total": 76.00,
            "calculated_grand_total": 1026.00,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [],
    },

    # -------------------------------------------------------------------------
    # Case 2: Messy PDF Quotation (Titan Heavy) - Multi-Column Layout
    # -------------------------------------------------------------------------
    {
        "case_id": "case_02_messy_pdf",
        "file_name": "02_messy_quotation_titan.pdf",
        "title": "Titan Heavy Multi-Column Wrapped PDF Quotation",
        "document_format": "PDF",
        "edge_case_type": "MESSY_LAYOUT",
        "edge_case_description": (
            "Multi-column irregular layout with wrapped tables, setup charges, "
            "and disclaimers in sidebars."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Titan Heavy Industries LLC",
                "contact_person": "Marcus Vance",
                "email": "quotes@titanheavy.com",
                "phone": "+1 (555) 438-9900",
                "address": "4500 Steelworks Blvd, Gary, IN 46402",
                "quotation_number": "TITAN-EST-9902",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-25",
                "currency": "USD",
                "subtotal": 1200.00,
                "tax": 96.00,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 1296.00,
            },
            "commercial_terms": {
                "delivery_time": "3-4 weeks (Estimated Dec 18, 2026)",
                "delivery_terms": "FOB Chicago Plant",
                "payment_terms": "Net 45 days",
                "warranty": "12 months standard industrial warranty",
                "notes": "Prices subject to raw billet steel surcharge. Tooling setup fee included as separate line item.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Heavy-Duty Industrial Shaft EN8 Steel (40mm x 500mm)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 11.20,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 1120.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Diameter", "value": "40 mm"},
                        {"name": "Length", "value": "500 mm"},
                        {"name": "Tolerance", "value": "±0.05 mm"},
                        {"name": "Process", "value": "CNC Lathe Turning"},
                    ],
                },
                {
                    "line_number": 2,
                    "description": "CNC Turning Setup & Programming Fee",
                    "quantity": 1.0,
                    "unit": "LOT",
                    "unit_price": 80.00,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 80.00,
                    "specifications": [
                        {"name": "Service", "value": "Initial CAM Program & CMM Fixture Setup"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 1200.00,
            "calculated_tax_total": 96.00,
            "calculated_grand_total": 1296.00,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [
            {
                "flag_type": "DELIVERY_LEAD_TIME_RISK",
                "severity": "LOW",
                "explanation": "Delivery timeframe (3-4 weeks) slightly exceeds Dec 15 target.",
            }
        ],
    },

    # -------------------------------------------------------------------------
    # Case 3: Excel Quotation (Nexus Systems) - EUR Currency & European Comma
    # -------------------------------------------------------------------------
    {
        "case_id": "case_03_excel",
        "file_name": "03_excel_quotation_nexus.xlsx",
        "title": "Nexus Systems European Excel (.xlsx) Quotation",
        "document_format": "XLSX",
        "edge_case_type": "EXCEL_WORKBOOK",
        "edge_case_description": (
            "Native Excel workbook with dynamic product formulas, European decimal commas (8,50), "
            "19% German VAT, and foreign EUR currency."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Nexus Industrial Systems GmbH",
                "contact_person": "Klaus Schneider",
                "email": "angebote@nexus-sys.de",
                "phone": "+49 89 2345 6789",
                "address": "Industriestrasse 42, 80339 Munich, Germany",
                "quotation_number": "NEX-EU-2026-742",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "EUR",
                "subtotal": 850.00,
                "tax": 161.50,
                "discount": 0.00,
                "shipping": 45.00,
                "grand_total": 1056.50,
            },
            "commercial_terms": {
                "delivery_time": "2-3 weeks (Delivery by Dec 12, 2026)",
                "delivery_terms": "DAP Customer Facility",
                "payment_terms": "Net 30 days",
                "warranty": "24 months EU manufacturer warranty",
                "notes": "Materialprüfzeugnis EN 10204 3.1 & Messprotokoll beigelegt. Luftfracht inklusive.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Industrielle Antriebswelle EN8 Stahl (Ø40mm x 500mm CNC gedreht)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 8.50,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 850.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Stahl (080M40 / C45)"},
                        {"name": "Durchmesser", "value": "40 mm"},
                        {"name": "Laenge", "value": "500 mm"},
                        {"name": "Toleranz", "value": "±0.05 mm"},
                        {"name": "Verfahren", "value": "CNC Drehen & Feinbearbeitung"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 850.00,
            "calculated_tax_total": 161.50,
            "calculated_grand_total": 1056.50,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [
            {
                "flag_type": "CURRENCY_MISMATCH_RISK",
                "severity": "LOW",
                "explanation": "Billed in EUR currency; foreign exchange conversion applied to RFQ USD benchmark.",
            }
        ],
    },

    # -------------------------------------------------------------------------
    # Case 4: Scanned Quotation (Vanguard Machine Works) - Grayscale Scan
    # -------------------------------------------------------------------------
    {
        "case_id": "case_04_scanned_pdf",
        "file_name": "04_scanned_quotation_vanguard.pdf",
        "title": "Vanguard Scanned Fax / Paper Quotation",
        "document_format": "PDF",
        "edge_case_type": "SCANNED_OCR",
        "edge_case_description": (
            "150 DPI skewed grayscale raster scan with background scanner texture, "
            "evaluating OCR preprocessing and binarization."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Vanguard Machine Works",
                "contact_person": "Dave Reynolds",
                "email": "dave@vanguardmachining.com",
                "phone": "+1 (555) 782-9011",
                "address": "704 Foundry Road, Cleveland, OH 44113",
                "quotation_number": "VMW-SCAN-2026-44",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-30",
                "currency": "USD",
                "subtotal": 1050.00,
                "tax": 52.50,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 1102.50,
            },
            "commercial_terms": {
                "delivery_time": "2-3 weeks (Delivery by Dec 12, 2026)",
                "delivery_terms": "FOB Vanguard Works",
                "payment_terms": "Net 30",
                "warranty": "12 months standard warranty",
                "notes": "Mill test report and dimensional check sheet provided upon shipment.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Machine Shaft EN8 Steel Turning 40mm x 500mm",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 10.50,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 1050.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Diameter", "value": "40 mm"},
                        {"name": "Length", "value": "500 mm"},
                        {"name": "Tolerance", "value": "+/- 0.05 mm"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 1050.00,
            "calculated_tax_total": 52.50,
            "calculated_grand_total": 1102.50,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [],
    },

    # -------------------------------------------------------------------------
    # Case 5: Multi-Item Package (OmniTech) - Shafts + End Caps + Crating
    # -------------------------------------------------------------------------
    {
        "case_id": "case_05_multi_item_bom",
        "file_name": "05_multi_item_bom_omnitech.pdf",
        "title": "OmniTech Multi-Item Shaft Packaging Quotation",
        "document_format": "PDF",
        "edge_case_type": "MULTI_ITEM_BOM",
        "edge_case_description": (
            "Multi-row quotation distinguishing primary manufactured shafts from "
            "protective end caps and export wood crating."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "OmniTech Engineering Solutions",
                "contact_person": "Elena Rostova",
                "email": "e.rostova@omnitech-eng.com",
                "phone": "+1 (555) 670-3321",
                "address": "200 Enterprise Dr, Charlotte, NC 28202",
                "quotation_number": "OMNI-BOM-2026-512",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 1120.00,
                "tax": 89.60,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 1209.60,
            },
            "commercial_terms": {
                "delivery_time": "2 weeks ARO (Delivery by Dec 07, 2026)",
                "delivery_terms": "DDP Client Facility",
                "payment_terms": "Net 30 days",
                "warranty": "12 months full warranty",
                "notes": "Full lot packaging. Material certificate and CMM inspection report enclosed.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Custom Industrial Shaft – EN8 Steel (40mm x 500mm)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 9.80,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 980.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Steel"},
                        {"name": "Diameter", "value": "40 mm"},
                        {"name": "Length", "value": "500 mm"},
                        {"name": "Tolerance", "value": "±0.05 mm"},
                    ],
                },
                {
                    "line_number": 2,
                    "description": "Protective Polymer Thread End-Caps & VCI Anti-Corrosion Wrap",
                    "quantity": 100.0,
                    "unit": "SET",
                    "unit_price": 0.80,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 80.00,
                    "specifications": [
                        {"name": "Type", "value": "Heavy Polymer Protective Caps"},
                    ],
                },
                {
                    "line_number": 3,
                    "description": "Reinforced Heavy Duty Wooden Crating for Ocean/Air Freight",
                    "quantity": 1.0,
                    "unit": "LOT",
                    "unit_price": 60.00,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 60.00,
                    "specifications": [
                        {"name": "Standard", "value": "ISPM-15 Heat Treated Export Crating"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 1120.00,
            "calculated_tax_total": 89.60,
            "calculated_grand_total": 1209.60,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [],
    },

    # -------------------------------------------------------------------------
    # Case 6: Compound Tax Quotation (Global Machining) - Split Taxable vs Exempt
    # -------------------------------------------------------------------------
    {
        "case_id": "case_06_compound_tax",
        "file_name": "06_compound_tax_global.pdf",
        "title": "Global Machining Split-Rate Tax Quotation",
        "document_format": "PDF",
        "edge_case_type": "COMPOUND_TAX",
        "edge_case_description": (
            "Hardware material ($800) taxable @ 8.25%, with engineering CAM setup and "
            "CMM inspection ($200) treated as tax-exempt manufacturing labor."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Global Machining Partners",
                "contact_person": "Rajesh Patel",
                "email": "r.patel@globalmachining.com",
                "phone": "+1 (555) 890-4123",
                "address": "500 Precision Way, Houston, TX 77002",
                "quotation_number": "GMP-TAX-2026-06",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 1000.00,
                "tax": 66.00,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 1066.00,
            },
            "commercial_terms": {
                "delivery_time": "3 weeks ARO (Delivery by Dec 14, 2026)",
                "delivery_terms": "FOB Plant",
                "payment_terms": "Net 30 days",
                "warranty": "12 months manufacturer warranty",
                "notes": "Engineering programming and inspection services are exempt from local sales tax under statutory manufacturing exemptions.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Custom Industrial Shaft 40mm x 500mm EN8 Material & Lathe Turning",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 8.00,
                    "discount": 0.00,
                    "tax": 66.00,
                    "total": 800.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Dimensions", "value": "40mm x 500mm"},
                        {"name": "Tolerance", "value": "±0.05 mm"},
                        {"name": "Tax Status", "value": "Taxable 8.25%"},
                    ],
                },
                {
                    "line_number": 2,
                    "description": "CAD/CAM Setup, CNC Toolpath Programming & CMM Inspection Service",
                    "quantity": 1.0,
                    "unit": "LOT",
                    "unit_price": 200.00,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 200.00,
                    "specifications": [
                        {"name": "Tax Status", "value": "Exempt / Non-Taxable Service Labor"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 1000.00,
            "calculated_tax_total": 66.00,
            "calculated_grand_total": 1066.00,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [],
    },

    # -------------------------------------------------------------------------
    # Case 7: Tiered Discounts (Sierra Precision) - 15% Volume Rebate
    # -------------------------------------------------------------------------
    {
        "case_id": "case_07_tiered_discounts",
        "file_name": "07_tiered_discounts_sierra.pdf",
        "title": "Sierra Precision Volume Discount Quotation",
        "document_format": "PDF",
        "edge_case_type": "TIERED_DISCOUNTS",
        "edge_case_description": (
            "List price $12.00 x 100 = $1,200 with an explicit 15% order volume rebate "
            "(-$180.00), testing negative discount parsing."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Sierra Precision Fab",
                "contact_person": "Chloe Bennett",
                "email": "bids@sierrafab.com",
                "phone": "+1 (555) 341-8890",
                "address": "1200 Technology Drive, Reno, NV 89521",
                "quotation_number": "SPF-DISC-2026-71",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 1020.00,
                "tax": 81.60,
                "discount": 180.00,
                "shipping": 0.00,
                "grand_total": 1101.60,
            },
            "commercial_terms": {
                "delivery_time": "2-3 weeks (Delivery by Dec 10, 2026)",
                "delivery_terms": "FOB Sierra Fab",
                "payment_terms": "Net 30 days",
                "warranty": "12 months warranty",
                "notes": "Includes 15% volume discount for 100+ unit order volume. Material test report included.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Industrial Shaft EN8 Turned and Machined (40x500mm)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 12.00,
                    "discount": 180.00,
                    "tax": 0.00,
                    "total": 1020.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Diameter", "value": "40 mm"},
                        {"name": "Length", "value": "500 mm"},
                        {"name": "Tolerance", "value": "±0.05 mm"},
                        {"name": "Discount Applied", "value": "15% Order Volume Discount"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 1020.00,
            "calculated_tax_total": 81.60,
            "calculated_grand_total": 1101.60,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [],
    },

    # -------------------------------------------------------------------------
    # Case 8: Missing Specs / Material Substitution (Summit Machine Works)
    # -------------------------------------------------------------------------
    {
        "case_id": "case_08_missing_specs",
        "file_name": "08_missing_specs_summit.pdf",
        "title": "Summit Machine Commercial Grade Substitution Quotation",
        "document_format": "PDF",
        "edge_case_type": "MISSING_SPECIFICATIONS",
        "edge_case_description": (
            "Supplier quotes commercial Mild Steel (MS) instead of EN8, omits precision "
            "tolerance (quotes ±0.25mm), and excludes required inspection certificates."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Summit Machine Works",
                "contact_person": "Gary Cooper",
                "email": "sales@summitmachine.net",
                "phone": "+1 (555) 234-7711",
                "address": "890 Industrial Ridge, Denver, CO 80216",
                "quotation_number": "SUMMIT-SPEC-2026-88",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 820.00,
                "tax": 65.60,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 885.60,
            },
            "commercial_terms": {
                "delivery_time": "1-2 weeks (Fast Delivery Dec 04, 2026)",
                "delivery_terms": "FOB Summit",
                "payment_terms": "Net 30 days",
                "warranty": "6 months limited warranty",
                "notes": "Commercial grade mild steel quoted for immediate delivery from bar stock. Visual check only.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Standard Industrial Shaft – Commercial Grade Mild Steel (MS)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 8.20,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 820.00,
                    "specifications": [
                        {"name": "Material", "value": "Mild Steel (Commercial Grade MS)"},
                        {"name": "Finished Diameter", "value": "40 mm"},
                        {"name": "Overall Length", "value": "500 mm"},
                        {"name": "Dimensional Tolerance", "value": "Commercial Standard (+/- 0.25 mm)"},
                        {"name": "Inspection", "value": "Visual check only (No material test cert included)"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 820.00,
            "calculated_tax_total": 65.60,
            "calculated_grand_total": 885.60,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [],
        "expected_spec_matching": {
            "overall_verdict": "SPEC_VARIANCE",
            "compliance_score": 60.0,
            "mismatch_count": 2,
            "missing_count": 1,
        },
        "expected_risk_flags": [
            {
                "flag_type": "TECHNICAL_SPECIFICATION_RISK",
                "severity": "HIGH",
                "explanation": "Supplier proposed Mild Steel (MS) instead of specified EN8 steel, and wider ±0.25mm tolerance.",
            }
        ],
    },

    # -------------------------------------------------------------------------
    # Case 9: Math Inconsistency Discrepancy (Delta Industrial)
    # -------------------------------------------------------------------------
    {
        "case_id": "case_09_mismatched_totals",
        "file_name": "09_mismatched_totals_delta.pdf",
        "title": "Delta Industrial Discrepant Invoice Total Quotation",
        "document_format": "PDF",
        "edge_case_type": "MATH_MISMATCH",
        "edge_case_description": (
            "Line items sum to $1,000.00. Tax is $80.00. Correct total is $1,080.00. "
            "However, printed invoice states $1,180.00 ($100 arithmetic discrepancy)."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Delta Industrial Manufacturing Co.",
                "contact_person": "Robert Chen",
                "email": "bids@deltamfg.com",
                "phone": "+1 (555) 772-1144",
                "address": "8800 Michigan Ave, Detroit, MI 48210",
                "quotation_number": "DELTA-ERR-2026-99",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 900.00,  # Erroneous printed subtotal (Sum is 1000.00)
                "tax": 80.00,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 980.00,  # Erroneous grand total
            },
            "commercial_terms": {
                "delivery_time": "3 weeks ARO (Delivery by Dec 14, 2026)",
                "delivery_terms": "FOB Detroit",
                "payment_terms": "Net 30 days",
                "warranty": "12 months manufacturer warranty",
                "notes": "Prices subject to final line audit.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "CNC Machined Industrial Shaft EN8 Steel (40mm Dia x 500mm Length)",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 10.00,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 1000.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Finished Diameter", "value": "40 mm"},
                        {"name": "Overall Length", "value": "500 mm"},
                        {"name": "Tolerance", "value": "±0.05 mm"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 1000.00,
            "calculated_tax_total": 80.00,
            "calculated_grand_total": 1080.00,
            "is_math_consistent": False,
            "subtotal_variance": -100.00,
            "grand_total_variance": -100.00,
        },
        "expected_validation_flags": [
            {
                "flag_type": "SUBTOTAL_INCONSISTENCY",
                "severity": "ERROR",
                "field": "quotation.subtotal",
                "expected_value": 1000.00,
                "actual_value": 900.00,
                "explanation": "Stated subtotal $900.00 does not match calculated sum of line items $1,000.00 (variance: -$100.00).",
            },
        ],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [
            {
                "flag_type": "MATH_INCONSISTENCY_RISK",
                "severity": "CRITICAL",
                "explanation": "Document contains a $100 arithmetic discrepancy between line items and invoice total.",
            }
        ],
    },

    # -------------------------------------------------------------------------
    # Case 10: Risky Commercial Terms (Pacific Rim Machining)
    # -------------------------------------------------------------------------
    {
        "case_id": "case_10_risky_commercial_terms",
        "file_name": "10_risky_terms_pacific.pdf",
        "title": "Pacific Rim High-Risk Commercial Terms Quotation",
        "document_format": "PDF",
        "edge_case_type": "RISKY_COMMERCIAL_TERMS",
        "edge_case_description": (
            "Lowest unit price ($7.50), but imposes 100% advance wire transfer, 20-week lead time "
            "(April 2027, missing Dec 15 deadline), and truncated 15-day warranty."
        ),
        "expected_extracted_data": {
            "supplier": {
                "supplier_name": "Pacific Rim Machining Corp.",
                "contact_person": "Victor Vance",
                "email": "v.vance@pacific-heavy.com",
                "phone": "+1 (206) 555-8910",
                "address": "1100 Harbor Island Way, Seattle, WA 98134",
                "quotation_number": "PACIFIC-TERMS-2026-77",
            },
            "quotation": {
                "quotation_date": "2026-11-23",
                "validity_date": "2026-11-28",
                "currency": "USD",
                "subtotal": 750.00,
                "tax": 0.00,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 750.00,
            },
            "commercial_terms": {
                "delivery_time": "20 weeks ARO (Delivery in April 2027)",
                "delivery_terms": "EXW Seattle Factory (Buyer pays shipping)",
                "payment_terms": "100% Advance Wire Transfer required prior to production",
                "warranty": "15 days limited warranty from dispatch",
                "notes": "Price firm for 5 days only due to alloy futures volatility. Non-refundable deposit.",
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Precision Turned Machine Shaft EN8 Steel 40x500mm",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 7.50,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 750.00,
                    "specifications": [
                        {"name": "Material", "value": "EN8 Medium Carbon Steel"},
                        {"name": "Diameter", "value": "40 mm"},
                        {"name": "Length", "value": "500 mm"},
                        {"name": "Tolerance", "value": "±0.05 mm"},
                    ],
                },
            ],
        },
        "expected_calculations": {
            "calculated_items_subtotal": 750.00,
            "calculated_tax_total": 0.00,
            "calculated_grand_total": 750.00,
            "is_math_consistent": True,
            "subtotal_variance": 0.00,
            "grand_total_variance": 0.00,
        },
        "expected_validation_flags": [
            {
                "flag_type": "DATE_OUT_OF_RANGE",
                "severity": "WARNING",
                "field": "quotation.validity_date",
                "explanation": "Validity window of 5 days is unusually restrictive for procurement.",
            }
        ],
        "expected_spec_matching": {
            "overall_verdict": "EXACT_MATCH",
            "compliance_score": 100.0,
            "mismatch_count": 0,
            "missing_count": 0,
        },
        "expected_risk_flags": [
            {
                "flag_type": "PAYMENT_TERMS_RISK",
                "severity": "CRITICAL",
                "explanation": "Supplier demands 100% advance wire payment before manufacturing.",
            },
            {
                "flag_type": "DELIVERY_LEAD_TIME_RISK",
                "severity": "HIGH",
                "explanation": "Delivery lead time of 20 weeks significantly misses the Dec 15, 2026 deadline.",
            },
            {
                "flag_type": "WARRANTY_RISK",
                "severity": "HIGH",
                "explanation": "15-day warranty is significantly below the standard 12-month commercial benchmark.",
            },
            {
                "flag_type": "SHORT_VALIDITY_RISK",
                "severity": "MEDIUM",
                "explanation": "Price validity expires in 5 calendar days.",
            },
        ],
    },
]


def get_ground_truth_by_case_id(case_id: str) -> Dict[str, Any]:
    """Retrieve a specific ground truth case by its case_id."""
    for case in DATASET_GROUND_TRUTH:
        if case["case_id"] == case_id:
            return case
    raise KeyError(f"Case '{case_id}' not found in benchmark ground truth dataset.")
