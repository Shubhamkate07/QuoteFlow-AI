"""
Generator script for QuoteFlow AI 10 Realistic Supplier Quotation Benchmark Documents.
Produces publication-grade PDFs, scanned rasterized PDFs, and Excel (.xlsx) workbooks
matching the exact Ground Truth dataset specifications.
"""

import io
import math
import os
from pathlib import Path
import random
from typing import List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from evaluation.dataset.ground_truth import DATASET_GROUND_TRUTH, get_ground_truth_by_case_id

DOCS_DIR = Path(__file__).resolve().parent / "documents"


def ensure_output_dir() -> Path:
    """Ensures documents destination directory exists."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    return DOCS_DIR


# -----------------------------------------------------------------------------
# Reusable ReportLab Helpers
# -----------------------------------------------------------------------------
def get_base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=8,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="MetaLabel",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    ))
    styles.add(ParagraphStyle(
        name="MetaValue",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    ))
    styles.add(ParagraphStyle(
        name="TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    ))
    styles.add(ParagraphStyle(
        name="TableHead",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="TermsText",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    ))
    return styles


def build_header_block(supplier: dict, quote: dict, styles) -> Table:
    """Creates standard two-column supplier & quotation metadata block."""
    left_meta = [
        Paragraph(f"<b>{supplier['supplier_name']}</b>", styles["DocTitle"]),
        Paragraph(f"{supplier['address']}", styles["DocSubtitle"]),
        Paragraph(f"Contact: {supplier['contact_person']} | Tel: {supplier['phone']}", styles["DocSubtitle"]),
        Paragraph(f"Email: {supplier['email']}", styles["DocSubtitle"]),
    ]
    right_meta = [
        Paragraph("<b>QUOTATION / PROPOSAL</b>", styles["SectionHeading"]),
        Paragraph(f"<b>Quote Number:</b> {supplier['quotation_number']}", styles["MetaValue"]),
        Paragraph(f"<b>Date:</b> {quote['quotation_date']}", styles["MetaValue"]),
        Paragraph(f"<b>Valid Until:</b> {quote['validity_date']}", styles["MetaValue"]),
        Paragraph(f"<b>Currency:</b> {quote['currency']}", styles["MetaValue"]),
    ]
    meta_table = Table([[left_meta, right_meta]], colWidths=[310, 230])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    return meta_table


# -----------------------------------------------------------------------------
# 1. Clean PDF Generator (Apex Precision)
# -----------------------------------------------------------------------------
def generate_case_01_clean_pdf(output_path: Path):
    case = get_ground_truth_by_case_id("case_01_clean_pdf")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    # Header
    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=12))

    # Line Items Table
    table_data = [[
        Paragraph("Item #", styles["TableHead"]),
        Paragraph("Description & Technical Specifications", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("UoM", styles["TableHead"]),
        Paragraph("Unit Price", styles["TableHead"]),
        Paragraph("Total (USD)", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        specs_str = " | ".join([f"<b>{s['name']}:</b> {s['value']}" for s in item.get("specifications", [])])
        desc_p = Paragraph(f"<b>{item['description']}</b><br/><font color='#64748B'>{specs_str}</font>", styles["TableCell"])
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            desc_p,
            Paragraph(f"{item['quantity']:.0f}", styles["TableCell"]),
            Paragraph(item["unit"], styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[40, 270, 45, 45, 70, 70])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    # Financial Summary
    q = ext["quotation"]
    summary_data = [
        ["Subtotal:", f"${q['subtotal']:,.2f}"],
        ["Sales Tax (8.25%):", f"${q['tax']:,.2f}"],
        ["Shipping & Freight:", "INCLUDED (FOB)"],
        ["Total Payable (USD):", f"${q['grand_total']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[440, 100])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 10),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#0F172A")),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Commercial Terms Box
    terms = ext["commercial_terms"]
    terms_box = Table([
        [Paragraph("<b>COMMERCIAL TERMS & CONDITIONS</b>", styles["TableCellBold"])],
        [Paragraph(f"• <b>Delivery / Lead Time:</b> {terms['delivery_time']}", styles["TermsText"])],
        [Paragraph(f"• <b>Shipping Terms:</b> {terms['delivery_terms']}", styles["TermsText"])],
        [Paragraph(f"• <b>Payment Terms:</b> {terms['payment_terms']}", styles["TermsText"])],
        [Paragraph(f"• <b>Warranty:</b> {terms['warranty']}", styles["TermsText"])],
        [Paragraph(f"• <b>Special Notes:</b> {terms['notes']}", styles["TermsText"])],
    ], colWidths=[540])
    terms_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(terms_box)
    doc.build(story)


# -----------------------------------------------------------------------------
# 2. Messy PDF Generator (Titan Industrial)
# -----------------------------------------------------------------------------
def generate_case_02_messy_pdf(output_path: Path):
    case = get_ground_truth_by_case_id("case_02_messy_pdf")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    # Irregular Header with disclaimers intermingled
    story.append(Paragraph(f"<b>*** PROPOSAL & COST ESTIMATE ***</b>", styles["DocSubtitle"]))
    story.append(Paragraph(f"<b>{ext['supplier']['supplier_name']}</b>", styles["DocTitle"]))
    story.append(Paragraph(f"Facility: {ext['supplier']['address']} | Tele: {ext['supplier']['phone']} | {ext['supplier']['email']}", styles["TableCell"]))
    story.append(Spacer(1, 6))

    # Inline metadata in irregular paragraph style
    meta_para = Paragraph(
        f"ESTIMATE REF: <b>{ext['supplier']['quotation_number']}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"DATE ISSUED: <b>{ext['quotation']['quotation_date']}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"EXPIRES: <b>{ext['quotation']['validity_date']}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"CURRENCY: <b>{ext['quotation']['currency']}</b>",
        styles["TableCellBold"]
    )
    story.append(meta_para)
    story.append(Spacer(1, 10))

    # Wrapped description table with multi-line cells
    table_data = [[
        Paragraph("<b>Ln</b>", styles["TableCellBold"]),
        Paragraph("<b>Bill of Materials / Custom Fabrications Schedule</b>", styles["TableCellBold"]),
        Paragraph("<b>Qty</b>", styles["TableCellBold"]),
        Paragraph("<b>Rate</b>", styles["TableCellBold"]),
        Paragraph("<b>Ext Total</b>", styles["TableCellBold"]),
    ]]

    for item in ext["line_items"]:
        specs_str = "; ".join([f"{s['name']}={s['value']}" for s in item.get("specifications", [])])
        desc_text = (
            f"<b>{item['description']}</b><br/>"
            f"<font color='#475569'>Tech Specs: {specs_str}. Fabricated strictly under quality supervision. "
            f"Note: mill test reports and paint thickness inspection certificates provided upon delivery.</font>"
        )
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCell"]),
            Paragraph(desc_text, styles["TableCell"]),
            Paragraph(f"{item['quantity']:.0f} {item['unit']}", styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[30, 330, 60, 60, 60])
    items_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    # Messy Totals with Separate Freight & Tax Note
    q = ext["quotation"]
    totals_p = Paragraph(
        f"<div align='right'>"
        f"Estimated Net Fabrication Subtotal: <b>${q['subtotal']:,.2f}</b><br/>"
        f"Special Handling & Heavy Transport Fee: <b>${q['shipping']:,.2f}</b><br/>"
        f"State Applicable Surcharge / Sales Tax (5.0% on $13,200): <b>${q['tax']:,.2f}</b><br/>"
        f"<font size='10'><b>TOTAL QUOTE AMOUNT: ${q['grand_total']:,.2f} USD</b></font>"
        f"</div>",
        styles["TableCell"]
    )
    story.append(totals_p)
    story.append(Spacer(1, 15))

    # Clause with Escalation Clause Warning
    terms = ext["commercial_terms"]
    story.append(Paragraph("<b>TERMS & SPECIAL PROVISIONS:</b>", styles["TableCellBold"]))
    story.append(Paragraph(f"• Lead Time: {terms['delivery_time']} (Shop capacity reserved upon deposit receipt)", styles["TermsText"]))
    story.append(Paragraph(f"• Shipping Terms: {terms['delivery_terms']} (Buyer arranges freight carrier unless requested)", styles["TermsText"]))
    story.append(Paragraph(f"• Payment Terms: {terms['payment_terms']}", styles["TermsText"]))
    story.append(Paragraph(f"• Warranty: {terms['warranty']}", styles["TermsText"]))
    story.append(Paragraph(f"• <b>CRITICAL NOTE:</b> {terms['notes']}", styles["TermsText"]))

    doc.build(story)


# -----------------------------------------------------------------------------
# 3. Excel Quotation Generator (.xlsx) (Nexus Electronic Systems)
# -----------------------------------------------------------------------------
def generate_case_03_excel(output_path: Path):
    case = get_ground_truth_by_case_id("case_03_excel")
    ext = case["expected_extracted_data"]
    wb = openpyxl.Workbook()

    # Sheet 1: Price Quotation
    ws1 = wb.active
    ws1.title = "Price Quotation"
    ws1.views.sheetView[0].showGridLines = True

    # Styling colors
    navy_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    light_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    font_title = Font(name="Calibri", size=16, bold=True, color="0F172A")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_white = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Calibri", size=10, color="1E293B")
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0'),
    )

    # Header block
    ws1["A1"] = ext["supplier"]["supplier_name"]
    ws1["A1"].font = font_title
    ws1["A2"] = f"Address: {ext['supplier']['address']}"
    ws1["A2"].font = font_regular
    ws1["A3"] = f"Contact: {ext['supplier']['contact_person']} | Email: {ext['supplier']['email']} | Tel: {ext['supplier']['phone']}"
    ws1["A3"].font = font_regular

    ws1["E1"] = "OFFICIAL QUOTATION"
    ws1["E1"].font = font_bold
    ws1["E2"] = f"Quotation #: {ext['supplier']['quotation_number']}"
    ws1["E2"].font = font_bold
    ws1["E3"] = f"Date: {ext['quotation']['quotation_date']} | Valid Until: {ext['quotation']['validity_date']}"
    ws1["E3"].font = font_regular

    # Table Headers
    headers = ["Item #", "Product Description", "Quantity", "UoM", "Unit Price (€)", "Line Total (€)"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws1.cell(row=5, column=col_idx, value=h)
        cell.font = font_white
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center" if col_idx in [1, 3, 4] else "left")

    # Line Items
    start_row = 6
    for idx, item in enumerate(ext["line_items"], start_row):
        ws1.cell(row=idx, column=1, value=item["line_number"]).alignment = Alignment(horizontal="center")
        ws1.cell(row=idx, column=2, value=item["description"])
        ws1.cell(row=idx, column=3, value=item["quantity"]).alignment = Alignment(horizontal="right")
        ws1.cell(row=idx, column=4, value=item["unit"]).alignment = Alignment(horizontal="center")
        ws1.cell(row=idx, column=5, value=item["unit_price"]).number_format = '€#,##0.00'
        # Native Excel formula for total: =C{idx}*E{idx}
        ws1.cell(row=idx, column=6, value=f"=C{idx}*E{idx}").number_format = '€#,##0.00'

        for col in range(1, 7):
            ws1.cell(row=idx, column=col).border = border_thin

    last_item_row = start_row + len(ext["line_items"]) - 1

    # Totals using formulas
    subtotal_row = last_item_row + 2
    ws1.cell(row=subtotal_row, column=5, value="Subtotal:").font = font_bold
    ws1.cell(row=subtotal_row, column=6, value=f"=SUM(F{start_row}:F{last_item_row})").number_format = '€#,##0.00'
    ws1.cell(row=subtotal_row, column=6).font = font_bold

    tax_row = subtotal_row + 1
    ws1.cell(row=tax_row, column=5, value="MwSt (19% VAT):").font = font_bold
    ws1.cell(row=tax_row, column=6, value=f"=F{subtotal_row}*0.19").number_format = '€#,##0.00'

    grand_row = tax_row + 1
    ws1.cell(row=grand_row, column=5, value="Total Payable (EUR):").font = font_bold
    ws1.cell(row=grand_row, column=6, value=f"=F{subtotal_row}+F{tax_row}").number_format = '€#,##0.00'
    ws1.cell(row=grand_row, column=6).font = font_bold

    # Commercial terms in spreadsheet footer
    terms_row = grand_row + 3
    ws1.cell(row=terms_row, column=1, value="COMMERCIAL TERMS").font = font_bold
    terms = ext["commercial_terms"]
    ws1.cell(row=terms_row + 1, column=1, value=f"Delivery Time: {terms['delivery_time']}")
    ws1.cell(row=terms_row + 2, column=1, value=f"Incoterms: {terms['delivery_terms']}")
    ws1.cell(row=terms_row + 3, column=1, value=f"Payment Terms: {terms['payment_terms']}")
    ws1.cell(row=terms_row + 4, column=1, value=f"Warranty: {terms['warranty']}")

    # Sheet 2: Technical Specifications
    ws2 = wb.create_sheet(title="Technical Data")
    ws2.views.sheetView[0].showGridLines = True
    ws2["A1"] = "Component Engineering Specifications"
    ws2["A1"].font = font_title
    ws2["A3"] = "Item #"
    ws2["B3"] = "Parameter"
    ws2["C3"] = "Value"
    for c in ["A3", "B3", "C3"]:
        ws2[c].font = font_white
        ws2[c].fill = navy_fill

    t_row = 4
    for item in ext["line_items"]:
        for spec in item.get("specifications", []):
            ws2.cell(row=t_row, column=1, value=item["line_number"])
            ws2.cell(row=t_row, column=2, value=spec["name"])
            ws2.cell(row=t_row, column=3, value=spec["value"])
            t_row += 1

    # Auto-fit column widths
    for ws in [ws1, ws2]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(output_path)


# -----------------------------------------------------------------------------
# 4. Scanned Quotation PDF Generator (Vanguard Fasteners)
# -----------------------------------------------------------------------------
def generate_case_04_scanned_pdf(output_path: Path):
    case = get_ground_truth_by_case_id("case_04_scanned_pdf")
    ext = case["expected_extracted_data"]

    # First, render clean image with Pillow
    img_width, img_height = 1700, 2200
    img = Image.new('L', (img_width, img_height), color=250)
    draw = ImageDraw.Draw(img)

    # Simulated Fax Header
    draw.text((80, 40), "TRANSMIT: 2026-11-08 09:14:22 EST   FROM: VANGUARD FASTENERS   TO: PROCUREMENT DEPT   P. 1/1", fill=70)
    draw.line([(80, 65), (img_width - 80, 65)], fill=100, width=2)

    # Company Header
    draw.text((80, 110), ext["supplier"]["supplier_name"].upper(), fill=20)
    draw.text((80, 150), f"Address: {ext['supplier']['address']}", fill=60)
    draw.text((80, 185), f"Contact: {ext['supplier']['contact_person']} | Tel: {ext['supplier']['phone']} | {ext['supplier']['email']}", fill=60)

    # Quotation Box
    draw.rectangle([(img_width - 550, 100), (img_width - 80, 230)], outline=80, width=2)
    draw.text((img_width - 530, 115), "QUOTATION SHEET", fill=20)
    draw.text((img_width - 530, 145), f"QUOTE NO: {ext['supplier']['quotation_number']}", fill=20)
    draw.text((img_width - 530, 175), f"DATE: {ext['quotation']['quotation_date']}", fill=40)
    draw.text((img_width - 530, 200), f"VALIDITY: {ext['quotation']['validity_date']}", fill=40)

    # Table Header
    y_table = 300
    draw.rectangle([(80, y_table), (img_width - 80, y_table + 45)], fill=60)
    draw.text((95, y_table + 12), "ITEM", fill=255)
    draw.text((220, y_table + 12), "PART DESCRIPTION & STANDARD SPEC", fill=255)
    draw.text((1050, y_table + 12), "QTY", fill=255)
    draw.text((1200, y_table + 12), "UNIT", fill=255)
    draw.text((1350, y_table + 12), "PRICE", fill=255)
    draw.text((1500, y_table + 12), "EXT TOTAL", fill=255)

    y_curr = y_table + 50
    for item in ext["line_items"]:
        specs_str = " | ".join([f"{s['name']}: {s['value']}" for s in item.get("specifications", [])])
        draw.text((100, y_curr), str(item["line_number"]), fill=20)
        draw.text((220, y_curr), item["description"], fill=20)
        draw.text((220, y_curr + 28), specs_str, fill=70)
        draw.text((1050, y_curr), f"{item['quantity']:.0f}", fill=20)
        draw.text((1200, y_curr), item["unit"], fill=20)
        draw.text((1350, y_curr), f"${item['unit_price']:,.2f}", fill=20)
        draw.text((1500, y_curr), f"${item['total']:,.2f}", fill=20)
        draw.line([(80, y_curr + 65), (img_width - 80, y_curr + 65)], fill=200, width=1)
        y_curr += 85

    # Totals
    y_curr += 20
    q = ext["quotation"]
    draw.text((1250, y_curr), "Subtotal:", fill=40)
    draw.text((1500, y_curr), f"${q['subtotal']:,.2f}", fill=20)
    draw.text((1250, y_curr + 35), "Tax (Exempt):", fill=40)
    draw.text((1500, y_curr + 35), "$0.00", fill=20)
    draw.line([(1200, y_curr + 70), (img_width - 80, y_curr + 70)], fill=40, width=2)
    draw.text((1250, y_curr + 80), "TOTAL PAYABLE:", fill=10)
    draw.text((1500, y_curr + 80), f"${q['grand_total']:,.2f}", fill=10)

    # Commercial Terms
    y_terms = y_curr + 180
    terms = ext["commercial_terms"]
    draw.rectangle([(80, y_terms), (img_width - 80, y_terms + 200)], outline=140, width=1)
    draw.text((100, y_terms + 15), "COMMERCIAL TERMS & NOTES:", fill=30)
    draw.text((100, y_terms + 50), f"1. Delivery: {terms['delivery_time']}", fill=60)
    draw.text((100, y_terms + 80), f"2. Terms: {terms['delivery_terms']} | Payment: {terms['payment_terms']}", fill=60)
    draw.text((100, y_terms + 110), f"3. Warranty: {terms['warranty']}", fill=60)
    draw.text((100, y_terms + 140), f"4. Tax Note: {terms['notes']}", fill=60)

    # Simulated handwritten signature
    draw.text((150, y_terms + 260), "Authorized Signature:  D. Kowalski (Quality Dept)", fill=40)

    # Add scanner noise and slight rotation
    img = img.rotate(0.7, resample=Image.Resampling.BILINEAR, fillcolor=255)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

    # Convert to PDF using PIL
    img_rgb = img.convert('RGB')
    img_rgb.save(output_path, "PDF", resolution=150.0)


# -----------------------------------------------------------------------------
# 5. Multi-Item High-Density BOM Generator (OmniTech Industrial)
# -----------------------------------------------------------------------------
def generate_case_05_multi_item_bom(output_path: Path):
    case = get_ground_truth_by_case_id("case_05_multi_item_bom")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    # Header
    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=8))
    story.append(Paragraph("<b>Itemized Machine Subassembly BOM Package</b>", styles["SectionHeading"]))

    table_data = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Component Description & Specification", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("UoM", styles["TableHead"]),
        Paragraph("Unit ($)", styles["TableHead"]),
        Paragraph("Ext Total ($)", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        specs_str = " | ".join([f"{s['name']}: {s['value']}" for s in item.get("specifications", [])])
        desc_p = Paragraph(f"<b>{item['description']}</b><br/><font color='#64748B'>{specs_str}</font>", styles["TableCell"])
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            desc_p,
            Paragraph(f"{item['quantity']:.0f}", styles["TableCell"]),
            Paragraph(item["unit"], styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[35, 280, 40, 45, 70, 70])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Totals
    q = ext["quotation"]
    totals_data = [
        ["Subtotal Line Items (12 Items):", f"${q['subtotal']:,.2f}"],
        ["Freight & Packaging Fee:", f"${q['shipping']:,.2f}"],
        ["Applicable Sales Tax (7.0% on Items):", f"${q['tax']:,.2f}"],
        ["Grand Total Payable (USD):", f"${q['grand_total']:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[420, 120])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 10))

    # Terms
    terms = ext["commercial_terms"]
    terms_p = Paragraph(
        f"<b>Commercial Terms:</b> Delivery: {terms['delivery_time']} | "
        f"Incoterms: {terms['delivery_terms']} | Payment: {terms['payment_terms']} | "
        f"Warranty: {terms['warranty']}<br/>"
        f"<b>Notes:</b> {terms['notes']}",
        styles["TermsText"]
    )
    story.append(terms_p)
    doc.build(story)


# -----------------------------------------------------------------------------
# 6. Compound / Split Tax Generator (Global Tooling)
# -----------------------------------------------------------------------------
def generate_case_06_compound_tax(output_path: Path):
    case = get_ground_truth_by_case_id("case_06_compound_tax")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=12))

    table_data = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Item Description & Tax Classification", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("Rate", styles["TableHead"]),
        Paragraph("Tax Applied", styles["TableHead"]),
        Paragraph("Total (USD)", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        tax_str = f"${item['tax']:,.2f} (8.5%)" if item['tax'] > 0 else "EXEMPT (0%)"
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            Paragraph(f"<b>{item['description']}</b>", styles["TableCell"]),
            Paragraph(f"{item['quantity']:.0f} {item['unit']}", styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(tax_str, styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[35, 260, 65, 60, 60, 60])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    q = ext["quotation"]
    summary_data = [
        ["Total Gross Amount:", f"${q['subtotal']:,.2f}"],
        ["Non-Taxable Labor Portion (Line 1):", "$4,000.00 (Exempt)"],
        ["Taxable Goods Portion (Lines 2 & 3):", "$16,000.00"],
        ["State Sales Tax (8.5% on $16,000):", f"${q['tax']:,.2f}"],
        ["Net Payable Amount (USD):", f"${q['grand_total']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[420, 120])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    terms = ext["commercial_terms"]
    story.append(Paragraph(f"<b>Commercial Conditions:</b> Delivery: {terms['delivery_time']} | Incoterms: {terms['delivery_terms']} | Payment: {terms['payment_terms']} | Warranty: {terms['warranty']}", styles["TermsText"]))
    story.append(Paragraph(f"<b>Statutory Exemption Certificate Note:</b> {terms['notes']}", styles["TermsText"]))
    doc.build(story)


# -----------------------------------------------------------------------------
# 7. Tiered Discounts Generator (Sierra Automation)
# -----------------------------------------------------------------------------
def generate_case_07_tiered_discounts(output_path: Path):
    case = get_ground_truth_by_case_id("case_07_tiered_discounts")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=12))

    table_data = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Description", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("List Price", styles["TableHead"]),
        Paragraph("Discount", styles["TableHead"]),
        Paragraph("Net Total", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        disc_str = f"-${item['discount']:,.2f}" if item['discount'] > 0 else "$0.00"
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            Paragraph(f"<b>{item['description']}</b>", styles["TableCell"]),
            Paragraph(f"{item['quantity']:.0f} {item['unit']}", styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(disc_str, styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[35, 270, 55, 60, 60, 60])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    q = ext["quotation"]
    summary_data = [
        ["Sum of Line Items:", "$9,000.00"],
        ["Order Volume Enterprise Rebate (5%):", f"-${q['discount']:,.2f}"],
        ["Taxable Subtotal:", f"${q['subtotal']:,.2f}"],
        ["State Tax (8.0%):", f"${q['tax']:,.2f}"],
        ["Grand Total Payable (USD):", f"${q['grand_total']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[420, 120])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    terms = ext["commercial_terms"]
    story.append(Paragraph(f"<b>Terms:</b> Delivery: {terms['delivery_time']} | Incoterms: {terms['delivery_terms']} | Payment: {terms['payment_terms']} | Warranty: {terms['warranty']}", styles["TermsText"]))
    story.append(Paragraph(f"<b>Note:</b> {terms['notes']}", styles["TermsText"]))
    doc.build(story)


# -----------------------------------------------------------------------------
# 8. Missing Specifications Generator (Summit Tooling)
# -----------------------------------------------------------------------------
def generate_case_08_missing_specs(output_path: Path):
    case = get_ground_truth_by_case_id("case_08_missing_specs")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=12))

    # Line items deliberately without technical specifications
    table_data = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Part Description", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("UoM", styles["TableHead"]),
        Paragraph("Unit Price", styles["TableHead"]),
        Paragraph("Total (USD)", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            Paragraph(f"<b>{item['description']}</b>", styles["TableCell"]),
            Paragraph(f"{item['quantity']:.0f}", styles["TableCell"]),
            Paragraph(item["unit"], styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[35, 305, 50, 40, 55, 55])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    q = ext["quotation"]
    summary_data = [
        ["Subtotal:", f"${q['subtotal']:,.2f}"],
        ["Tax (8.0%):", f"${q['tax']:,.2f}"],
        ["Grand Total (USD):", f"${q['grand_total']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[420, 120])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    terms = ext["commercial_terms"]
    story.append(Paragraph(f"<b>Terms:</b> Delivery: {terms['delivery_time']} | Incoterms: {terms['delivery_terms']} | Payment: {terms['payment_terms']} | Warranty: {terms['warranty']}", styles["TermsText"]))
    story.append(Paragraph(f"<b>Caveat Note:</b> {terms['notes']}", styles["TermsText"]))
    doc.build(story)


# -----------------------------------------------------------------------------
# 9. Mismatched Totals Generator (Delta Precision)
# -----------------------------------------------------------------------------
def generate_case_09_mismatched_totals(output_path: Path):
    case = get_ground_truth_by_case_id("case_09_mismatched_totals")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=12))

    # Line items: $5,000 + $4,500 = $9,500
    table_data = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Part Description", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("UoM", styles["TableHead"]),
        Paragraph("Unit Price", styles["TableHead"]),
        Paragraph("Total (USD)", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            Paragraph(f"<b>{item['description']}</b>", styles["TableCell"]),
            Paragraph(f"{item['quantity']:.0f}", styles["TableCell"]),
            Paragraph(item["unit"], styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[35, 305, 50, 40, 55, 55])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    # Deliberate arithmetic mismatch: Printed subtotal is $8,500 ($1,000 lower than $9,500!)
    q = ext["quotation"]
    summary_data = [
        ["Subtotal (as printed):", f"${q['subtotal']:,.2f}"],
        ["Tax (as printed):", f"${q['tax']:,.2f}"],
        ["Grand Total (as printed):", f"${q['grand_total']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[420, 120])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    terms = ext["commercial_terms"]
    story.append(Paragraph(f"<b>Terms:</b> Delivery: {terms['delivery_time']} | Incoterms: {terms['delivery_terms']} | Payment: {terms['payment_terms']} | Warranty: {terms['warranty']}", styles["TermsText"]))
    story.append(Paragraph(f"<b>Note:</b> {terms['notes']}", styles["TermsText"]))
    doc.build(story)


# -----------------------------------------------------------------------------
# 10. Risky Commercial Terms Generator (Pacific Heavy Industries)
# -----------------------------------------------------------------------------
def generate_case_10_risky_commercial_terms(output_path: Path):
    case = get_ground_truth_by_case_id("case_10_risky_commercial_terms")
    ext = case["expected_extracted_data"]
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = get_base_styles()
    story = []

    story.append(build_header_block(ext["supplier"], ext["quotation"], styles))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=12))

    table_data = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Equipment Description & Mechanical Specifications", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("UoM", styles["TableHead"]),
        Paragraph("Unit Price", styles["TableHead"]),
        Paragraph("Total (USD)", styles["TableHead"]),
    ]]

    for item in ext["line_items"]:
        specs_str = " | ".join([f"{s['name']}: {s['value']}" for s in item.get("specifications", [])])
        table_data.append([
            Paragraph(str(item["line_number"]), styles["TableCellBold"]),
            Paragraph(f"<b>{item['description']}</b><br/><font color='#64748B'>{specs_str}</font>", styles["TableCell"]),
            Paragraph(f"{item['quantity']:.0f}", styles["TableCell"]),
            Paragraph(item["unit"], styles["TableCell"]),
            Paragraph(f"${item['unit_price']:,.2f}", styles["TableCell"]),
            Paragraph(f"${item['total']:,.2f}", styles["TableCellBold"]),
        ])

    items_table = Table(table_data, colWidths=[35, 305, 50, 40, 55, 55])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    q = ext["quotation"]
    summary_data = [
        ["Subtotal:", f"${q['subtotal']:,.2f}"],
        ["Sales Tax (Exempt / Direct Ship):", "$0.00"],
        ["Total Payable (USD):", f"${q['grand_total']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[420, 120])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Prominent Warning / Terms Box
    terms = ext["commercial_terms"]
    terms_box = Table([
        [Paragraph("<b>CRITICAL COMMERCIAL TERMS & SPECIAL RESTRICTIONS</b>", styles["TableCellBold"])],
        [Paragraph(f"• <b>Payment Requirement:</b> <font color='#DC2626'><b>{terms['payment_terms']}</b></font>", styles["TermsText"])],
        [Paragraph(f"• <b>Lead Time:</b> <font color='#DC2626'><b>{terms['delivery_time']}</b></font>", styles["TermsText"])],
        [Paragraph(f"• <b>Warranty Period:</b> <font color='#DC2626'><b>{terms['warranty']}</b></font>", styles["TermsText"])],
        [Paragraph(f"• <b>Incoterms:</b> {terms['delivery_terms']}", styles["TermsText"])],
        [Paragraph(f"• <b>Validity & Cancellation Notice:</b> {terms['notes']}", styles["TermsText"])],
    ], colWidths=[540])
    terms_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#DC2626")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(terms_box)
    doc.build(story)


# -----------------------------------------------------------------------------
# Main Dataset Generation Orchestrator
# -----------------------------------------------------------------------------
GENERATORS = {
    "case_01_clean_pdf": generate_case_01_clean_pdf,
    "case_02_messy_pdf": generate_case_02_messy_pdf,
    "case_03_excel": generate_case_03_excel,
    "case_04_scanned_pdf": generate_case_04_scanned_pdf,
    "case_05_multi_item_bom": generate_case_05_multi_item_bom,
    "case_06_compound_tax": generate_case_06_compound_tax,
    "case_07_tiered_discounts": generate_case_07_tiered_discounts,
    "case_08_missing_specs": generate_case_08_missing_specs,
    "case_09_mismatched_totals": generate_case_09_mismatched_totals,
    "case_10_risky_commercial_terms": generate_case_10_risky_commercial_terms,
}


def generate_all_benchmark_documents(target_dir: Optional[Path] = None) -> List[Path]:
    """
    Generates all 10 realistic test documents in the designated directory.
    Returns list of generated file paths.
    """
    out_dir = target_dir or ensure_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    for case in DATASET_GROUND_TRUTH:
        case_id = case["case_id"]
        file_name = case["file_name"]
        file_path = out_dir / file_name

        generator_fn = GENERATORS.get(case_id)
        if generator_fn:
            generator_fn(file_path)
            generated_files.append(file_path)

    return generated_files


if __name__ == "__main__":
    files = generate_all_benchmark_documents()
    print(f"Successfully generated {len(files)} realistic test documents in {DOCS_DIR}")
