"""
Excel Report Generation Service for QuoteFlow AI.

Generates a publication-grade, multi-sheet workbook containing:
- Sheet 1: Summary (RFQ info, metadata, KPIs, scoring weights, overall ranking matrix)
- Sheet 2: Price Comparison (Supplier totals, itemized BOM pricing schedule, taxes, discounts, cherry-pick optimal)
- Sheet 3: Specification Comparison (Technical parameter matching, compliance score, verdict, mismatch explanations, evidence)
- Sheet 4: Commercial Terms (Delivery lead time, Incoterms, on-time status, payment terms, advance payment flags, warranty)
- Sheet 5: Risk Flags (Deterministic 14-rule risk audit log, severity, affected fields, evidence, recommended mitigations)
"""
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from comparisons.services import get_or_generate_comprehensive_comparison


class RFQComparisonExcelGenerator:
    """
    Builds a professional 5-sheet Excel workbook from QuoteFlow AI comparison data.
    """

    # Corporate Executive Palette
    NAVY_TITLE = '0F172A'       # Slate 900
    NAVY_HEADER = '1E293B'      # Slate 800
    SECTION_HEADER = '334155'   # Slate 700
    SLATE_MUTED = '64748B'      # Slate 500
    SLATE_LIGHT = 'F8FAFC'      # Slate 50
    SLATE_BORDER = 'E2E8F0'     # Slate 200
    SLATE_BORDER_DARK = 'CBD5E1'# Slate 300

    # Status & Badge Colors
    EMERALD_FILL = 'DCFCE7'
    EMERALD_FONT = '15803D'
    AMBER_FILL = 'FEF3C7'
    AMBER_FONT = 'B45309'
    ROSE_FILL = 'FEE2E2'
    ROSE_FONT = 'B91C1C'
    INDIGO_FILL = 'EEF2FF'
    INDIGO_FONT = '3730A3'
    PURPLE_FILL = 'F3E8FF'
    PURPLE_FONT = '6B21A8'

    def __init__(
        self,
        rfq,
        comparison_data: Optional[Dict[str, Any]] = None,
        user=None,
        organization=None,
    ):
        self.rfq = rfq
        self.organization = organization or getattr(rfq, 'organization', None)
        self.user = user

        if comparison_data is not None:
            self.data = comparison_data
        else:
            self.data = get_or_generate_comprehensive_comparison(
                rfq=rfq,
                organization=self.organization,
                user=self.user,
            )

        # Compute target budget if attribute not present
        target_budget_val = getattr(self.rfq, 'target_budget', None)
        if target_budget_val is None and hasattr(self.rfq, 'items'):
            try:
                target_budget_val = sum(
                    float(it.quantity) * float(it.target_unit_price or 0)
                    for it in self.rfq.items.all()
                )
            except Exception:
                target_budget_val = 0.0
        self.target_budget = float(target_budget_val or 0.0)
        self.currency = self.data.get('comparison_currency') or getattr(rfq, 'currency', 'USD') or 'USD'
        self.currency_symbol = self._get_currency_symbol(self.currency)
        self.currency_format = f'"{self.currency_symbol}"#,##0.00'
        self.currency_format_int = f'"{self.currency_symbol}"#,##0'
        self.percent_format = '0.0%'
        self.int_format = '#,##0'

        # Standard borders
        self.thin_border = Border(
            left=Side(style='thin', color=self.SLATE_BORDER),
            right=Side(style='thin', color=self.SLATE_BORDER),
            top=Side(style='thin', color=self.SLATE_BORDER),
            bottom=Side(style='thin', color=self.SLATE_BORDER),
        )
        self.header_border = Border(
            left=Side(style='thin', color='334155'),
            right=Side(style='thin', color='334155'),
            top=Side(style='medium', color=self.NAVY_HEADER),
            bottom=Side(style='medium', color=self.NAVY_HEADER),
        )

    def _get_currency_symbol(self, code: str) -> str:
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'INR': '₹',
            'CAD': 'CA$',
            'AUD': 'A$',
            'JPY': '¥',
            'CHF': 'CHF ',
            'CNY': '¥',
        }
        return symbols.get(code.upper(), f'{code} ')

    def generate_workbook(self) -> openpyxl.Workbook:
        """
        Creates and formats the 5 sheets in the workbook.
        """
        wb = openpyxl.Workbook()

        # Sheet 1: Summary
        ws1 = wb.active
        ws1.title = "Summary"
        self._build_summary_sheet(ws1)

        # Sheet 2: Price Comparison
        ws2 = wb.create_sheet(title="Price Comparison")
        self._build_price_sheet(ws2)

        # Sheet 3: Specification Comparison
        ws3 = wb.create_sheet(title="Specification Comparison")
        self._build_spec_sheet(ws3)

        # Sheet 4: Commercial Terms
        ws4 = wb.create_sheet(title="Commercial Terms")
        self._build_commercial_sheet(ws4)

        # Sheet 5: Risk Flags
        ws5 = wb.create_sheet(title="Risk Flags")
        self._build_risk_sheet(ws5)

        return wb

    def generate_bytes(self) -> io.BytesIO:
        """
        Serializes the workbook into an in-memory BytesIO buffer.
        """
        wb = self.generate_workbook()
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    # =========================================================================
    # SHEET 1: SUMMARY
    # =========================================================================
    def _build_summary_sheet(self, ws):
        ws.views.sheetView[0].showGridLines = True

        # Title Block
        ws.merge_cells('A1:N1')
        title_cell = ws['A1']
        title_cell.value = "QuoteFlow AI — Procurement Quotation Comparison & Evaluation Report"
        title_cell.font = Font(name='Calibri', size=16, bold=True, color='FFFFFF')
        title_cell.fill = PatternFill(start_color=self.NAVY_TITLE, end_color=self.NAVY_TITLE, fill_type='solid')
        title_cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 40

        ws.merge_cells('A2:N2')
        sub_cell = ws['A2']
        rfq_num = getattr(self.rfq, 'rfq_number', '') or self.data.get('rfq_number', '')
        rfq_title = getattr(self.rfq, 'title', '') or self.data.get('rfq_title', '')
        gen_at = self.data.get('generated_at', datetime.now().isoformat())
        sub_cell.value = f"RFQ Package: {rfq_num} — {rfq_title}   |   Comparison Date: {gen_at[:10]} {gen_at[11:19]} UTC   |   Baseline Currency: {self.currency}"
        sub_cell.font = Font(name='Calibri', size=10, italic=True, color='E2E8F0')
        sub_cell.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
        sub_cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[2].height = 22

        # 1. RFQ Metadata Card
        curr_row = 4
        self._write_section_header(ws, curr_row, "1. RFQ SCOPE & PROCUREMENT BASELINE", col_span=14)
        curr_row += 1

        meta_rows = [
            ("RFQ Identifier", rfq_num, "Required Delivery Date", str(getattr(self.rfq, 'required_delivery_date', 'Not specified'))),
            ("Project Title", rfq_title, "RFQ Lifecycle Status", str(getattr(self.rfq, 'status', 'under_review')).upper()),
            ("Baseline Target Budget", self.target_budget, "Organization / Entity", str(getattr(self.organization, 'name', 'Enterprise'))),
            ("Procurement Currency", self.currency, "Line Items Defined", len(self.data.get('price_comparison', {}).get('items_matrix', []))),
        ]

        for label1, val1, label2, val2 in meta_rows:
            # Col A-B: Label 1
            ws.cell(row=curr_row, column=1, value=label1).font = Font(name='Calibri', size=10, bold=True, color=self.SLATE_MUTED)
            ws.cell(row=curr_row, column=1).fill = PatternFill(start_color=self.SLATE_LIGHT, end_color=self.SLATE_LIGHT, fill_type='solid')
            c_val1 = ws.cell(row=curr_row, column=2, value=val1)
            c_val1.font = Font(name='Calibri', size=10, bold=(label1 == "Baseline Target Budget"), color='0F172A')
            if label1 == "Baseline Target Budget" and isinstance(val1, (int, float)):
                c_val1.number_format = self.currency_format

            # Col D-E: Label 2
            ws.cell(row=curr_row, column=4, value=label2).font = Font(name='Calibri', size=10, bold=True, color=self.SLATE_MUTED)
            ws.cell(row=curr_row, column=4).fill = PatternFill(start_color=self.SLATE_LIGHT, end_color=self.SLATE_LIGHT, fill_type='solid')
            c_val2 = ws.cell(row=curr_row, column=5, value=val2)
            c_val2.font = Font(name='Calibri', size=10, color='0F172A')

            for col in range(1, 6):
                ws.cell(row=curr_row, column=col).border = self.thin_border
            ws.row_dimensions[curr_row].height = 20
            curr_row += 1

        curr_row += 1

        # 2. Key Financial Benchmarks & KPIs
        self._write_section_header(ws, curr_row, "2. FINANCIAL BENCHMARKS & SOURCING COMPARISON", col_span=14)
        curr_row += 1

        price_comp = self.data.get('price_comparison', {})
        q_summary = self.data.get('quotations_summary', {})
        cards = self.data.get('supplier_comparison', [])

        suppliers_count = len(cards)
        lowest_total = price_comp.get('lowest_grand_total')
        highest_total = price_comp.get('highest_grand_total')
        max_savings = price_comp.get('max_savings_amount', 0)
        savings_pct = price_comp.get('max_savings_percentage', 0)
        cherry_total = price_comp.get('cherry_pick_total', 0)
        cherry_savings = price_comp.get('cherry_pick_savings', 0)

        # KPI row
        kpi_cells = [
            (1, "Suppliers Compared", suppliers_count, self.int_format),
            (3, "Lowest Quoted Bid", lowest_total or 0, self.currency_format),
            (5, "Highest Quoted Bid", highest_total or 0, self.currency_format),
            (7, "Single-Source Savings", max_savings, self.currency_format),
            (9, "Cherry-Pick Optimal", cherry_total or lowest_total or 0, self.currency_format),
            (11, "Multi-Sourcing Bonus", cherry_savings, self.currency_format),
        ]

        # Labels
        for col, label, _, _ in kpi_cells:
            c = ws.cell(row=curr_row, column=col, value=label)
            c.font = Font(name='Calibri', size=9, bold=True, color=self.SLATE_MUTED)
            c.fill = PatternFill(start_color=self.SLATE_LIGHT, end_color=self.SLATE_LIGHT, fill_type='solid')
            c.alignment = Alignment(horizontal='center', vertical='center')
            c.border = self.thin_border
            ws.merge_cells(start_row=curr_row, start_column=col, end_row=curr_row, end_column=col+1)
        ws.row_dimensions[curr_row].height = 18
        curr_row += 1

        # Values
        for col, _, val, num_fmt in kpi_cells:
            c = ws.cell(row=curr_row, column=col, value=val)
            c.font = Font(name='Calibri', size=13, bold=True, color='0F172A')
            c.number_format = num_fmt
            c.alignment = Alignment(horizontal='center', vertical='center')
            c.border = self.thin_border
            ws.merge_cells(start_row=curr_row, start_column=col, end_row=curr_row, end_column=col+1)
        ws.row_dimensions[curr_row].height = 26
        curr_row += 2

        # 3. Active Scoring Weights
        self._write_section_header(ws, curr_row, "3. ACTIVE EXPLAINABLE SCORING WEIGHTS (MUST TOTAL 100%)", col_span=14)
        curr_row += 1

        weights = self.data.get('settings', {}).get('weights', {})
        weight_items = [
            ("Price Competitiveness", weights.get('price', 40)),
            ("Technical Spec Match", weights.get('spec_match', 30)),
            ("Delivery Lead Time", weights.get('delivery', 15)),
            ("Commercial Payment Terms", weights.get('payment_terms', 10)),
            ("Warranty Coverage", weights.get('warranty', 5)),
        ]

        w_col = 1
        for factor_name, weight_val in weight_items:
            ws.cell(row=curr_row, column=w_col, value=factor_name).font = Font(name='Calibri', size=9, bold=True, color=self.SLATE_MUTED)
            ws.cell(row=curr_row, column=w_col).alignment = Alignment(horizontal='center', vertical='center')
            ws.cell(row=curr_row, column=w_col).border = self.thin_border

            c_val = ws.cell(row=curr_row+1, column=w_col, value=float(weight_val) / 100.0)
            c_val.font = Font(name='Calibri', size=11, bold=True, color='0F172A')
            c_val.number_format = self.percent_format
            c_val.alignment = Alignment(horizontal='center', vertical='center')
            c_val.border = self.thin_border
            w_col += 1

        ws.row_dimensions[curr_row].height = 18
        ws.row_dimensions[curr_row+1].height = 22
        curr_row += 3

        # 4. Overall Supplier Comparison Matrix Table
        self._write_section_header(ws, curr_row, "4. OVERALL SUPPLIER EVALUATION & COMPARATIVE RANKINGS", col_span=14)
        curr_row += 1

        headers = [
            "Rank",
            "Supplier Name",
            "Quotation Ref",
            "Quoted Total Price",
            "Variance vs Lowest",
            "% Variance",
            "Spec Compliance",
            "Lead Time (Wks)",
            "On-Time Status",
            "Payment Terms",
            "Warranty Coverage",
            "Risk Profile",
            "Overall Score (/100)",
            "Recommendation Status",
        ]

        for col_idx, h_text in enumerate(headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx in (1, 7, 8, 9, 12, 13) else 'left', vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 28
        curr_row += 1

        # Fill table rows
        target_b = self.target_budget
        for card in cards:
            rank = card.get('rank') or '—'
            supplier = card.get('supplier_name', '')
            q_num = card.get('quotation_number', '')
            pricing = card.get('pricing', {})
            grand_total = pricing.get('grand_total', 0)
            diff_lowest = pricing.get('price_difference_from_lowest', 0)
            pct_lowest = pricing.get('percentage_difference_from_lowest', 0)
            specs = card.get('specifications', {})
            comp_score = specs.get('compliance_score', 0)
            delivery = card.get('delivery', {})
            lead_wks = delivery.get('lead_time_weeks') or 0
            on_time = delivery.get('on_time_status', 'On Schedule')
            comm = card.get('commercial_terms', {})
            pay_terms = comm.get('payment_terms', 'Net 30')
            warranty = comm.get('warranty_information', 'Standard')
            risk_prof = card.get('risk_profile', {})
            risk_level = risk_prof.get('overall_risk_level', 'LOW')
            scoring = card.get('scoring', {})
            final_score = scoring.get('final_score', 0)
            rec = "Top Evaluated Option" if rank == 1 else ("Lowest Quoted Price" if pricing.get('is_lowest_price') else "Consideration Eligible")

            is_top = (rank == 1)
            row_fill = PatternFill(start_color=self.EMERALD_FILL, end_color=self.EMERALD_FILL, fill_type='solid') if is_top else None

            # Col 1: Rank
            c1 = ws.cell(row=curr_row, column=1, value=f"#{rank}" if isinstance(rank, int) else rank)
            c1.alignment = Alignment(horizontal='center', vertical='center')
            c1.font = Font(name='Calibri', size=10, bold=True, color='0F172A')

            # Col 2: Supplier
            c2 = ws.cell(row=curr_row, column=2, value=supplier)
            c2.font = Font(name='Calibri', size=10, bold=is_top, color='0F172A')

            # Col 3: Quote Ref
            c3 = ws.cell(row=curr_row, column=3, value=q_num)
            c3.font = Font(name='Calibri', size=10, color=self.SLATE_MUTED)

            # Col 4: Quoted Grand Total
            c4 = ws.cell(row=curr_row, column=4, value=float(grand_total))
            c4.font = Font(name='Calibri', size=10, bold=True, color='0F172A')
            c4.number_format = self.currency_format

            # Col 5: Diff vs Lowest
            c5 = ws.cell(row=curr_row, column=5, value=float(diff_lowest or 0))
            c5.font = Font(name='Calibri', size=10, color='0F172A')
            c5.number_format = self.currency_format

            # Col 6: % Variance
            c6 = ws.cell(row=curr_row, column=6, value=float(pct_lowest or 0) / 100.0)
            c6.font = Font(name='Calibri', size=10, color='0F172A')
            c6.number_format = self.percent_format

            # Col 7: Spec Compliance
            c7 = ws.cell(row=curr_row, column=7, value=float(comp_score) / 100.0)
            c7.font = Font(name='Calibri', size=10, bold=True, color='0F172A')
            c7.number_format = self.percent_format
            c7.alignment = Alignment(horizontal='center', vertical='center')

            # Col 8: Lead Time Weeks
            c8 = ws.cell(row=curr_row, column=8, value=int(lead_wks or 0))
            c8.font = Font(name='Calibri', size=10, color='0F172A')
            c8.alignment = Alignment(horizontal='center', vertical='center')

            # Col 9: On-Time Status
            c9 = ws.cell(row=curr_row, column=9, value=on_time)
            c9.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT if on_time == 'On Schedule' else self.ROSE_FONT)
            c9.alignment = Alignment(horizontal='center', vertical='center')

            # Col 10: Payment Terms
            c10 = ws.cell(row=curr_row, column=10, value=pay_terms)
            c10.font = Font(name='Calibri', size=10, color='0F172A')

            # Col 11: Warranty
            c11 = ws.cell(row=curr_row, column=11, value=warranty)
            c11.font = Font(name='Calibri', size=10, color='0F172A')

            # Col 12: Risk Profile
            c12 = ws.cell(row=curr_row, column=12, value=risk_level.upper())
            r_font = self.EMERALD_FONT if risk_level.upper() == 'LOW' else (self.AMBER_FONT if risk_level.upper() == 'MEDIUM' else self.ROSE_FONT)
            c12.font = Font(name='Calibri', size=9, bold=True, color=r_font)
            c12.alignment = Alignment(horizontal='center', vertical='center')

            # Col 13: Final Score
            c13 = ws.cell(row=curr_row, column=13, value=float(final_score))
            c13.font = Font(name='Calibri', size=11, bold=True, color='0F172A')
            c13.alignment = Alignment(horizontal='center', vertical='center')

            # Col 14: Recommendation
            c14 = ws.cell(row=curr_row, column=14, value=rec)
            c14.font = Font(name='Calibri', size=10, italic=True, color=self.INDIGO_FONT if is_top else '0F172A')

            for col in range(1, 15):
                cell = ws.cell(row=curr_row, column=col)
                cell.border = self.thin_border
                if row_fill and col in (1, 2, 4, 13, 14):
                    cell.fill = row_fill

            ws.row_dimensions[curr_row].height = 22
            curr_row += 1

        curr_row += 2

        # 5. Ethical & Decision-Support Guardrail Footer
        ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row+1, end_column=14)
        g_cell = ws.cell(row=curr_row, column=1)
        g_cell.value = (
            "NOTICE & DECISION-SUPPORT GUARDRAIL: QuoteFlow AI provides transparent mathematical ranking, specification verification, "
            "and commercial risk auditing for authorized procurement evaluation committees. The system does NOT automatically select or purchase "
            "from suppliers. Final award determinations require explicit human procurement authorization."
        )
        g_cell.font = Font(name='Calibri', size=9, italic=True, color='334155')
        g_cell.fill = PatternFill(start_color=self.INDIGO_FILL, end_color=self.INDIGO_FILL, fill_type='solid')
        g_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True, indent=1)
        ws.row_dimensions[curr_row].height = 20
        ws.row_dimensions[curr_row+1].height = 20

        self._autofit_columns(ws, max_cols=14)

    # =========================================================================
    # SHEET 2: PRICE COMPARISON
    # =========================================================================
    def _build_price_sheet(self, ws):
        ws.views.sheetView[0].showGridLines = True

        # Sheet Title Banner
        ws.merge_cells('A1:L1')
        t_cell = ws['A1']
        t_cell.value = "Detailed Price Comparison & Itemized BOM Sourcing Schedule"
        t_cell.font = Font(name='Calibri', size=15, bold=True, color='FFFFFF')
        t_cell.fill = PatternFill(start_color=self.NAVY_TITLE, end_color=self.NAVY_TITLE, fill_type='solid')
        t_cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 36

        price_comp = self.data.get('price_comparison', {})
        curr_row = 3

        # SECTION 1: Supplier Financial Summary Table
        self._write_section_header(ws, curr_row, "1. SUPPLIER FINANCIAL TOTALS & TAX / FREIGHT BREAKDOWN", col_span=10)
        curr_row += 1

        summary_headers = [
            "Supplier Name",
            "Quotation Ref",
            "Subtotal",
            "Taxes Applicable",
            "Freight & Shipping",
            "Discounts Applied",
            "Grand Total Quoted",
            "Difference vs Lowest",
            "% Variance vs Lowest",
            "Lowest Price Flag",
        ]

        for col_idx, h_text in enumerate(summary_headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx in (10,) else ('right' if col_idx >= 3 else 'left'), vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 26
        curr_row += 1

        quotations = price_comp.get('quotations', [])
        for q in quotations:
            is_lowest = q.get('is_lowest_price', False)
            c_fill = PatternFill(start_color=self.EMERALD_FILL, end_color=self.EMERALD_FILL, fill_type='solid') if is_lowest else None

            ws.cell(row=curr_row, column=1, value=q.get('supplier_name', '')).font = Font(name='Calibri', size=10, bold=is_lowest, color='0F172A')
            ws.cell(row=curr_row, column=2, value=q.get('quotation_number', '')).font = Font(name='Calibri', size=10, color=self.SLATE_MUTED)

            # Subtotal
            c_sub = ws.cell(row=curr_row, column=3, value=float(q.get('subtotal') or 0))
            c_sub.number_format = self.currency_format

            # Taxes
            c_tax = ws.cell(row=curr_row, column=4, value=float(q.get('tax_amount') or 0))
            c_tax.number_format = self.currency_format

            # Shipping
            c_ship = ws.cell(row=curr_row, column=5, value=float(q.get('shipping_amount') or 0))
            c_ship.number_format = self.currency_format

            # Discounts
            c_disc = ws.cell(row=curr_row, column=6, value=float(q.get('discount_amount') or 0))
            c_disc.number_format = self.currency_format

            # Grand Total
            c_gt = ws.cell(row=curr_row, column=7, value=float(q.get('grand_total') or 0))
            c_gt.font = Font(name='Calibri', size=10, bold=True, color='0F172A')
            c_gt.number_format = self.currency_format

            # Diff vs lowest
            c_diff = ws.cell(row=curr_row, column=8, value=float(q.get('price_difference_from_lowest') or 0))
            c_diff.number_format = self.currency_format

            # % Variance
            c_pct = ws.cell(row=curr_row, column=9, value=float(q.get('percentage_difference_from_lowest') or 0) / 100.0)
            c_pct.number_format = self.percent_format

            # Lowest Flag
            c_flag = ws.cell(row=curr_row, column=10, value="YES ★" if is_lowest else "NO")
            c_flag.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT if is_lowest else self.SLATE_MUTED)
            c_flag.alignment = Alignment(horizontal='center', vertical='center')

            for col in range(1, 11):
                cell = ws.cell(row=curr_row, column=col)
                cell.border = self.thin_border
                if c_fill and col in (1, 7, 10):
                    cell.fill = c_fill

            ws.row_dimensions[curr_row].height = 20
            curr_row += 1

        curr_row += 2

        # SECTION 2: Itemized BOM Line Items Schedule
        self._write_section_header(ws, curr_row, "2. ITEMIZED BOM LINE ITEMS PRICING SCHEDULE", col_span=12)
        curr_row += 1

        bom_headers = [
            "Item Name / Part Scope",
            "RFQ Quantity",
            "UOM",
            "Target Unit Price",
            "Supplier Name",
            "Quote Reference",
            "Quoted Unit Price",
            "Quoted Line Total",
            "Unit Price Variance",
            "% Variance vs Lowest",
            "Lowest Item Price?",
            "Item Compatibility",
        ]

        for col_idx, h_text in enumerate(bom_headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx in (2, 3, 11, 12) else ('right' if col_idx in (4, 7, 8, 9, 10) else 'left'), vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 26
        curr_row += 1

        items_matrix = price_comp.get('items_matrix', [])
        for row in items_matrix:
            item_name = row.get('item_name', '')
            qty = row.get('target_quantity') or row.get('quantity', 0)
            uom = row.get('target_unit') or row.get('uom', 'EA')
            target_unit = row.get('target_unit_price')
            lowest_unit = row.get('lowest_unit_price')

            bids_val = row.get('bids')
            if isinstance(bids_val, dict):
                quotes = list(bids_val.values())
            elif isinstance(bids_val, list):
                quotes = bids_val
            else:
                quotes = row.get('quotes', [])

            for q_entry in quotes:
                supp_name = q_entry.get('supplier_name', '')
                q_num = q_entry.get('quote_number') or q_entry.get('quotation_number', '')
                u_price = float(q_entry.get('normalized_unit_price') or q_entry.get('quoted_unit_price') or q_entry.get('unit_price') or 0)
                ext_price = float(q_entry.get('extended_price_target_qty') or q_entry.get('extended_price_quoted_qty') or q_entry.get('quoted_line_total') or q_entry.get('extended_price') or 0)
                is_low_item = q_entry.get('is_lowest_unit_price') or q_entry.get('is_lowest', False)
                compat_status = q_entry.get('compatibility_status')
                is_compat = (compat_status == 'COMPATIBLE') if compat_status is not None else q_entry.get('is_compatible', True)

                diff_from_low = (u_price - float(lowest_unit)) if lowest_unit is not None else 0
                pct_from_low = (diff_from_low / float(lowest_unit)) if (lowest_unit and float(lowest_unit) > 0) else 0

                ws.cell(row=curr_row, column=1, value=item_name).font = Font(name='Calibri', size=10, color='0F172A')

                c_qty = ws.cell(row=curr_row, column=2, value=float(qty))
                c_qty.number_format = self.int_format
                c_qty.alignment = Alignment(horizontal='center', vertical='center')

                c_uom = ws.cell(row=curr_row, column=3, value=uom)
                c_uom.alignment = Alignment(horizontal='center', vertical='center')

                c_target = ws.cell(row=curr_row, column=4, value=float(target_unit) if target_unit is not None else 0)
                c_target.number_format = self.currency_format

                ws.cell(row=curr_row, column=5, value=supp_name).font = Font(name='Calibri', size=10, color='0F172A')
                ws.cell(row=curr_row, column=6, value=q_num).font = Font(name='Calibri', size=10, color=self.SLATE_MUTED)

                c_up = ws.cell(row=curr_row, column=7, value=u_price)
                c_up.font = Font(name='Calibri', size=10, bold=is_low_item, color=self.EMERALD_FONT if is_low_item else '0F172A')
                c_up.number_format = self.currency_format

                c_ext = ws.cell(row=curr_row, column=8, value=ext_price)
                c_ext.font = Font(name='Calibri', size=10, bold=is_low_item, color='0F172A')
                c_ext.number_format = self.currency_format

                c_d = ws.cell(row=curr_row, column=9, value=float(diff_from_low))
                c_d.number_format = self.currency_format

                c_p = ws.cell(row=curr_row, column=10, value=float(pct_from_low))
                c_p.number_format = self.percent_format

                c_low = ws.cell(row=curr_row, column=11, value="YES ★" if is_low_item else "—")
                c_low.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT if is_low_item else self.SLATE_MUTED)
                c_low.alignment = Alignment(horizontal='center', vertical='center')

                c_comp = ws.cell(row=curr_row, column=12, value="COMPLIANT" if is_compat else "VARIANCE")
                c_comp.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT if is_compat else self.AMBER_FONT)
                c_comp.alignment = Alignment(horizontal='center', vertical='center')

                for col in range(1, 13):
                    cell = ws.cell(row=curr_row, column=col)
                    cell.border = self.thin_border
                    if is_low_item and col in (7, 8, 11):
                        cell.fill = PatternFill(start_color=self.EMERALD_FILL, end_color=self.EMERALD_FILL, fill_type='solid')

                ws.row_dimensions[curr_row].height = 20
                curr_row += 1

        self._autofit_columns(ws, max_cols=12)

    # =========================================================================
    # SHEET 3: SPECIFICATION COMPARISON
    # =========================================================================
    def _build_spec_sheet(self, ws):
        ws.views.sheetView[0].showGridLines = True

        # Sheet Title Banner
        ws.merge_cells('A1:H1')
        t_cell = ws['A1']
        t_cell.value = "Technical Specification Compliance & Verification Matrix"
        t_cell.font = Font(name='Calibri', size=15, bold=True, color='FFFFFF')
        t_cell.fill = PatternFill(start_color=self.NAVY_TITLE, end_color=self.NAVY_TITLE, fill_type='solid')
        t_cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 36

        specs_data = self.data.get('specification_matching', {})
        curr_row = 3

        # SECTION 1: Supplier Compliance Summary
        self._write_section_header(ws, curr_row, "1. SUPPLIER SPECIFICATION COMPLIANCE SUMMARY", col_span=8)
        curr_row += 1

        sum_headers = [
            "Supplier Name",
            "Quote Ref",
            "Average Compliance Score",
            "Technical Verdict",
            "Critical Mismatches",
            "Compliant Items",
            "Partially Compliant",
            "Non-Compliant Items",
        ]

        for col_idx, h_text in enumerate(sum_headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx >= 3 else 'left', vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 26
        curr_row += 1

        summaries = specs_data.get('supplier_summaries', [])
        for s in summaries:
            verdict = s.get('overall_verdict', 'COMPLIANT')
            crit_count = s.get('total_critical_mismatches', 0)

            ws.cell(row=curr_row, column=1, value=s.get('supplier_name', '')).font = Font(name='Calibri', size=10, bold=True, color='0F172A')
            ws.cell(row=curr_row, column=2, value=s.get('quotation_number', '')).font = Font(name='Calibri', size=10, color=self.SLATE_MUTED)

            c_score = ws.cell(row=curr_row, column=3, value=float(s.get('average_score', 0)) / 100.0)
            c_score.font = Font(name='Calibri', size=10, bold=True, color='0F172A')
            c_score.number_format = self.percent_format
            c_score.alignment = Alignment(horizontal='center', vertical='center')

            c_v = ws.cell(row=curr_row, column=4, value=verdict)
            c_v.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT if verdict == 'COMPLIANT' else (self.AMBER_FONT if verdict == 'PARTIALLY_COMPLIANT' else self.ROSE_FONT))
            c_v.alignment = Alignment(horizontal='center', vertical='center')

            c_crit = ws.cell(row=curr_row, column=5, value=int(crit_count))
            c_crit.font = Font(name='Calibri', size=10, bold=True, color=self.ROSE_FONT if crit_count > 0 else self.EMERALD_FONT)
            c_crit.alignment = Alignment(horizontal='center', vertical='center')

            c_comp = ws.cell(row=curr_row, column=6, value=int(s.get('compliant_items_count', 0)))
            c_comp.alignment = Alignment(horizontal='center', vertical='center')

            c_part = ws.cell(row=curr_row, column=7, value=int(s.get('partially_compliant_items_count', 0)))
            c_part.alignment = Alignment(horizontal='center', vertical='center')

            c_non = ws.cell(row=curr_row, column=8, value=int(s.get('non_compliant_items_count', 0)))
            c_non.alignment = Alignment(horizontal='center', vertical='center')

            for col in range(1, 9):
                ws.cell(row=curr_row, column=col).border = self.thin_border

            ws.row_dimensions[curr_row].height = 20
            curr_row += 1

        curr_row += 2

        # SECTION 2: Parameter-by-Parameter Matching Table
        self._write_section_header(ws, curr_row, "2. PARAMETER-BY-PARAMETER SPECIFICATION VERIFICATION", col_span=8)
        curr_row += 1

        detail_headers = [
            "RFQ Item Name",
            "Specification Parameter",
            "RFQ Requirement",
            "Supplier Name",
            "Supplier Quoted Value",
            "Match Status",
            "Compliance / Discrepancy Explanation",
            "Audit Evidence Citation",
        ]

        for col_idx, h_text in enumerate(detail_headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx == 6 else 'left', vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 26
        curr_row += 1

        spec_items = specs_data.get('items', [])
        for item in spec_items:
            item_name = item.get('item_name') or item.get('rfq_item_name', '')
            matches = item.get('supplier_evaluations') or item.get('supplier_matches', [])

            for s_match in matches:
                supp_name = s_match.get('supplier_name', '')
                p_matches = s_match.get('matches') or s_match.get('parameter_matches', [])

                for pm in p_matches:
                    param = pm.get('parameter_name') or pm.get('parameter', '')
                    rfq_val = pm.get('requirement_value') or pm.get('rfq_value', '')
                    supp_val = pm.get('supplier_value', '')
                    raw_status = pm.get('status', 'EXACT_MATCH')
                    m_status = str(raw_status).upper()
                    expl = pm.get('explanation', '')
                    evid = pm.get('evidence', '')

                    ws.cell(row=curr_row, column=1, value=item_name).font = Font(name='Calibri', size=10, color='0F172A')
                    ws.cell(row=curr_row, column=2, value=param).font = Font(name='Calibri', size=10, bold=True, color='0F172A')
                    ws.cell(row=curr_row, column=3, value=rfq_val).font = Font(name='Calibri', size=10, color='0F172A')
                    ws.cell(row=curr_row, column=4, value=supp_name).font = Font(name='Calibri', size=10, color='0F172A')
                    ws.cell(row=curr_row, column=5, value=supp_val).font = Font(name='Calibri', size=10, bold=True, color='0F172A')

                    c_st = ws.cell(row=curr_row, column=6, value=m_status)
                    c_st.alignment = Alignment(horizontal='center', vertical='center')

                    # Conditional colors on Match Status
                    if m_status in ('EXACT_MATCH', 'COMPLIANT'):
                        c_st.fill = PatternFill(start_color=self.EMERALD_FILL, end_color=self.EMERALD_FILL, fill_type='solid')
                        c_st.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT)
                    elif m_status in ('MISMATCH', 'NON_COMPLIANT'):
                        c_st.fill = PatternFill(start_color=self.ROSE_FILL, end_color=self.ROSE_FILL, fill_type='solid')
                        c_st.font = Font(name='Calibri', size=9, bold=True, color=self.ROSE_FONT)
                    else:
                        c_st.fill = PatternFill(start_color=self.AMBER_FILL, end_color=self.AMBER_FILL, fill_type='solid')
                        c_st.font = Font(name='Calibri', size=9, bold=True, color=self.AMBER_FONT)

                    ws.cell(row=curr_row, column=7, value=expl).font = Font(name='Calibri', size=9, color='334155')
                    ws.cell(row=curr_row, column=8, value=evid).font = Font(name='Calibri', size=9, italic=True, color=self.SLATE_MUTED)

                    for col in range(1, 9):
                        ws.cell(row=curr_row, column=col).border = self.thin_border

                    ws.row_dimensions[curr_row].height = 20
                    curr_row += 1

        self._autofit_columns(ws, max_cols=8)

    # =========================================================================
    # SHEET 4: COMMERCIAL TERMS
    # =========================================================================
    def _build_commercial_sheet(self, ws):
        ws.views.sheetView[0].showGridLines = True

        # Sheet Title Banner
        ws.merge_cells('A1:J1')
        t_cell = ws['A1']
        t_cell.value = "Commercial Terms, Delivery Schedule & Warranty Comparison"
        t_cell.font = Font(name='Calibri', size=15, bold=True, color='FFFFFF')
        t_cell.fill = PatternFill(start_color=self.NAVY_TITLE, end_color=self.NAVY_TITLE, fill_type='solid')
        t_cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 36

        curr_row = 3
        self._write_section_header(ws, curr_row, "LOGISTICS, PAYMENT CREDIT TERMS & WARRANTY GUARANTEE", col_span=10)
        curr_row += 1

        comm_headers = [
            "Supplier Name",
            "Quote Ref",
            "Delivery Terms (Incoterms)",
            "Quoted Lead Time (Weeks)",
            "RFQ Required Delivery Date",
            "On-Time Fulfillment Status",
            "Commercial Payment Terms",
            "Advance Payment Risk",
            "Warranty Guarantee & Terms",
            "Warranty Risk Rating",
        ]

        for col_idx, h_text in enumerate(comm_headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx in (4, 5, 6, 8, 10) else 'left', vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 26
        curr_row += 1

        req_date = str(getattr(self.rfq, 'required_delivery_date', 'Standard'))
        cards = self.data.get('supplier_comparison', [])
        for card in cards:
            supp_name = card.get('supplier_name', '')
            q_num = card.get('quotation_number', '')
            deliv = card.get('delivery', {})
            d_terms = deliv.get('delivery_terms', 'DAP')
            lead_wks = deliv.get('lead_time_weeks') or 0
            on_time = deliv.get('on_time_status', 'On Schedule')
            comm = card.get('commercial_terms', {})
            pay_terms = comm.get('payment_terms', 'Net 30')
            warranty = comm.get('warranty_information', 'Standard Warranty')

            is_advance = 'advance' in pay_terms.lower() or 'deposit' in pay_terms.lower()
            is_no_war = 'no warranty' in warranty.lower() or 'none' in warranty.lower()

            ws.cell(row=curr_row, column=1, value=supp_name).font = Font(name='Calibri', size=10, bold=True, color='0F172A')
            ws.cell(row=curr_row, column=2, value=q_num).font = Font(name='Calibri', size=10, color=self.SLATE_MUTED)
            ws.cell(row=curr_row, column=3, value=d_terms).font = Font(name='Calibri', size=10, color='0F172A')

            c_wks = ws.cell(row=curr_row, column=4, value=int(lead_wks or 0))
            c_wks.alignment = Alignment(horizontal='center', vertical='center')

            c_req = ws.cell(row=curr_row, column=5, value=req_date)
            c_req.alignment = Alignment(horizontal='center', vertical='center')

            c_ot = ws.cell(row=curr_row, column=6, value=on_time)
            c_ot.alignment = Alignment(horizontal='center', vertical='center')
            c_ot.font = Font(name='Calibri', size=9, bold=True, color=self.EMERALD_FONT if on_time == 'On Schedule' else self.ROSE_FONT)

            ws.cell(row=curr_row, column=7, value=pay_terms).font = Font(name='Calibri', size=10, color='0F172A')

            c_adv = ws.cell(row=curr_row, column=8, value="HIGH RISK (Deposit)" if is_advance else "STANDARD CREDIT")
            c_adv.alignment = Alignment(horizontal='center', vertical='center')
            c_adv.font = Font(name='Calibri', size=9, bold=True, color=self.ROSE_FONT if is_advance else self.EMERALD_FONT)
            if is_advance:
                c_adv.fill = PatternFill(start_color=self.ROSE_FILL, end_color=self.ROSE_FILL, fill_type='solid')

            ws.cell(row=curr_row, column=9, value=warranty).font = Font(name='Calibri', size=10, color='0F172A')

            c_warr_r = ws.cell(row=curr_row, column=10, value="HIGH (No Warranty)" if is_no_war else "VERIFIED")
            c_warr_r.alignment = Alignment(horizontal='center', vertical='center')
            c_warr_r.font = Font(name='Calibri', size=9, bold=True, color=self.ROSE_FONT if is_no_war else self.EMERALD_FONT)

            for col in range(1, 11):
                ws.cell(row=curr_row, column=col).border = self.thin_border

            ws.row_dimensions[curr_row].height = 20
            curr_row += 1

        self._autofit_columns(ws, max_cols=10)

    # =========================================================================
    # SHEET 5: RISK FLAGS
    # =========================================================================
    def _build_risk_sheet(self, ws):
        ws.views.sheetView[0].showGridLines = True

        # Sheet Title Banner
        ws.merge_cells('A1:H1')
        t_cell = ws['A1']
        t_cell.value = "Quotation Commercial & Technical Risk Audit Log"
        t_cell.font = Font(name='Calibri', size=15, bold=True, color='FFFFFF')
        t_cell.fill = PatternFill(start_color=self.NAVY_TITLE, end_color=self.NAVY_TITLE, fill_type='solid')
        t_cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 36

        curr_row = 3
        self._write_section_header(ws, curr_row, "DETERMINISTIC 14-RULE EXCEPTION & RISK AUDIT REPORT", col_span=8)
        curr_row += 1

        risk_headers = [
            "Supplier Name",
            "Quotation Ref",
            "Risk Severity",
            "Flag Title",
            "Rule Exception Type",
            "Affected Parameter / Scope",
            "Audit Evidence & Discrepancy",
            "Recommended Procurement Action",
        ]

        for col_idx, h_text in enumerate(risk_headers, start=1):
            c = ws.cell(row=curr_row, column=col_idx, value=h_text)
            c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
            c.fill = PatternFill(start_color=self.NAVY_HEADER, end_color=self.NAVY_HEADER, fill_type='solid')
            c.alignment = Alignment(horizontal='center' if col_idx == 3 else 'left', vertical='center', wrap_text=True)
            c.border = self.header_border
        ws.row_dimensions[curr_row].height = 26
        curr_row += 1

        risk_reports = self.data.get('risk_flags', [])
        total_flags_count = 0

        for r in risk_reports:
            supp_name = r.get('supplier_name', '')
            q_num = r.get('quotation_number', '')
            flags = r.get('flags', [])

            for f in flags:
                total_flags_count += 1
                sev = f.get('severity', 'MEDIUM').upper()
                title = f.get('title', '')
                f_type = f.get('type', '')
                field = f.get('affected_field', '')
                evid = f.get('evidence', '') or f.get('description', '')
                rec = f.get('recommended_action', 'Verify with supplier')

                ws.cell(row=curr_row, column=1, value=supp_name).font = Font(name='Calibri', size=10, bold=True, color='0F172A')
                ws.cell(row=curr_row, column=2, value=q_num).font = Font(name='Calibri', size=10, color=self.SLATE_MUTED)

                c_sev = ws.cell(row=curr_row, column=3, value=sev)
                c_sev.alignment = Alignment(horizontal='center', vertical='center')

                # Conditional styling on severity
                if sev in ('CRITICAL', 'HIGH'):
                    c_sev.fill = PatternFill(start_color=self.ROSE_FILL, end_color=self.ROSE_FILL, fill_type='solid')
                    c_sev.font = Font(name='Calibri', size=9, bold=True, color=self.ROSE_FONT)
                elif sev == 'MEDIUM':
                    c_sev.fill = PatternFill(start_color=self.AMBER_FILL, end_color=self.AMBER_FILL, fill_type='solid')
                    c_sev.font = Font(name='Calibri', size=9, bold=True, color=self.AMBER_FONT)
                else:
                    c_sev.fill = PatternFill(start_color=self.SLATE_LIGHT, end_color=self.SLATE_LIGHT, fill_type='solid')
                    c_sev.font = Font(name='Calibri', size=9, bold=True, color=self.SLATE_MUTED)

                ws.cell(row=curr_row, column=4, value=title).font = Font(name='Calibri', size=10, bold=True, color='0F172A')
                ws.cell(row=curr_row, column=5, value=f_type).font = Font(name='Calibri', size=9, color=self.SLATE_MUTED)
                ws.cell(row=curr_row, column=6, value=field).font = Font(name='Calibri', size=9, color='334155')
                ws.cell(row=curr_row, column=7, value=evid).font = Font(name='Calibri', size=9, color='334155')

                c_rec = ws.cell(row=curr_row, column=8, value=rec)
                c_rec.font = Font(name='Calibri', size=9, italic=True, color=self.INDIGO_FONT)

                for col in range(1, 9):
                    ws.cell(row=curr_row, column=col).border = self.thin_border

                ws.row_dimensions[curr_row].height = 22
                curr_row += 1

        if total_flags_count == 0:
            ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=8)
            empty_c = ws.cell(row=curr_row, column=1, value="No commercial, technical, or financial risk flags identified across evaluated quotations.")
            empty_c.font = Font(name='Calibri', size=10, italic=True, color=self.EMERALD_FONT)
            empty_c.alignment = Alignment(horizontal='center', vertical='center')
            empty_c.fill = PatternFill(start_color=self.EMERALD_FILL, end_color=self.EMERALD_FILL, fill_type='solid')
            for col in range(1, 9):
                ws.cell(row=curr_row, column=col).border = self.thin_border
            ws.row_dimensions[curr_row].height = 24
            curr_row += 1

        self._autofit_columns(ws, max_cols=8)

    # =========================================================================
    # COMMON UTILITIES
    # =========================================================================
    def _write_section_header(self, ws, row_idx: int, title: str, col_span: int = 10):
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=col_span)
        c = ws.cell(row=row_idx, column=1, value=title)
        c.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
        c.fill = PatternFill(start_color=self.SECTION_HEADER, end_color=self.SECTION_HEADER, fill_type='solid')
        c.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[row_idx].height = 22

    def _autofit_columns(self, ws, max_cols: int, min_width: int = 12, max_width: int = 55):
        """
        Adjust column widths based on cell content, ignoring merged title rows to avoid blowout.
        """
        for col_idx in range(1, max_cols + 1):
            col_letter = get_column_letter(col_idx)
            max_len = 0
            for row in range(3, ws.max_row + 1):
                cell = ws.cell(row=row, column=col_idx)
                # Skip if cell is part of merged range spanning more than 2 columns
                if cell.coordinate in ws.merged_cells:
                    continue
                val = cell.value
                if val is not None:
                    s_val = str(val)
                    if len(s_val) > max_len:
                        max_len = len(s_val)
            ws.column_dimensions[col_letter].width = min(max_width, max(min_width, max_len + 4))
