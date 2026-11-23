"""
QuoteFlow AI — Professional Procurement Quotation Comparison & Evaluation PDF Report Generator.
Generates an executive-grade, publication-ready PDF document suitable for procurement managers
and evaluation committees using ReportLab.

Includes:
1. Executive Cover Banner & RFQ Baseline Scope
2. Key Performance Indicators (KPI) Summary Dashboard
3. Supplier Comparative Ranking Matrix
4. Detailed Price Comparison & Itemized BOM Pricing Schedule
5. Specification Matching & Parameter Verification Log
6. Commercial Terms Comparison (Delivery, Payment Terms, Warranty)
7. Deterministic Quotation Risk Flags (14-Rule Engine Log)
8. Explainable Supplier Scoring Engine (Configurable Weights & Factor Breakdown)
9. Strategic Award Recommendation & Decision Trade-Off Analysis
10. Mandatory Human Decision-Support Guardrail & Disclaimer
"""
from datetime import date, datetime
from decimal import Decimal
import io
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
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

from comparisons.services import get_or_generate_comprehensive_comparison


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that accumulates page states during document flowable layout,
    then decorates each page with running headers, footers, confidentiality notices,
    and exact 'Page X of Y' total page numbers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()

        page_width, page_height = letter
        margin_x = 36
        top_y = page_height - 32
        bottom_y = 22

        # 1. Header (Pages 2+)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor('#0F172A'))
            self.drawString(margin_x, top_y, "QuoteFlow AI")

            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor('#64748B'))
            self.drawString(margin_x + 60, top_y, "|   Procurement Quotation Evaluation & Comparison Report")

            rfq_ref = getattr(self, '_doc_rfq_number', '')
            if rfq_ref:
                self.drawRightString(page_width - margin_x, top_y, f"RFQ: {rfq_ref}")

            # Top divider rule
            self.setStrokeColor(colors.HexColor('#E2E8F0'))
            self.setLineWidth(0.75)
            self.line(margin_x, top_y - 6, page_width - margin_x, top_y - 6)

        # 2. Bottom Divider Rule (All Pages)
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.75)
        self.line(margin_x, bottom_y + 14, page_width - margin_x, bottom_y + 14)

        # 3. Footer (All Pages)
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor('#94A3B8'))
        self.drawString(margin_x, bottom_y, "CONFIDENTIAL")

        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor('#64748B'))
        self.drawString(margin_x + 68, bottom_y, "— FOR AUTHORIZED PROCUREMENT COMMITTEE EVALUATION ONLY")

        # Guardrail reminder
        center_text = "Decision-Support Guideline — Requires Human Authorization"
        self.drawCentredString(page_width / 2.0, bottom_y, center_text)

        # Page numbering
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor('#0F172A'))
        self.drawRightString(page_width - margin_x, bottom_y, page_str)

        self.restoreState()


class RFQComparisonPDFGenerator:
    """
    Constructs a publication-grade PDF comparison report using ReportLab.
    Handles long tables with repeated headers across page breaks, wrapping cells
    in Paragraphs with strict column widths to avoid layout truncation.
    """

    # Corporate Executive Palette
    NAVY_PRIMARY = colors.HexColor('#0F172A')
    NAVY_SECONDARY = colors.HexColor('#1E293B')
    SLATE_DARK = colors.HexColor('#334155')
    SLATE_MUTED = colors.HexColor('#64748B')
    BORDER_LIGHT = colors.HexColor('#E2E8F0')
    BG_CARD = colors.HexColor('#F8FAFC')
    BG_CARD_ALT = colors.HexColor('#F1F5F9')

    # Status / Accent Colors
    EMERALD_FILL = colors.HexColor('#DCFCE7')
    EMERALD_FONT = colors.HexColor('#166534')
    ROSE_FILL = colors.HexColor('#FFE4E6')
    ROSE_FONT = colors.HexColor('#9F1239')
    AMBER_FILL = colors.HexColor('#FEF3C7')
    AMBER_FONT = colors.HexColor('#92400E')
    INDIGO_FILL = colors.HexColor('#EEF2FF')
    INDIGO_FONT = colors.HexColor('#3730A3')

    PAGE_WIDTH = 540  # Printable width: letter (612) - 2 * 36 margin

    def __init__(
        self,
        rfq,
        comparison_data: Optional[Dict[str, Any]] = None,
        user=None,
        organization=None,
    ):
        self.rfq = rfq
        self.user = user
        self.organization = organization or getattr(rfq, 'organization', None)

        if comparison_data is None:
            self.data = get_or_generate_comprehensive_comparison(
                rfq=self.rfq,
                organization=self.organization,
                user=self.user,
                force_refresh=False,
            )
        else:
            self.data = comparison_data

        self.currency = (
            self.data.get('comparison_currency')
            or getattr(rfq, 'currency', 'USD')
            or 'USD'
        )
        self.styles = self._init_styles()

    def _init_styles(self) -> Dict[str, ParagraphStyle]:
        """Configures typography hierarchy for executive reading."""
        base = getSampleStyleSheet()

        styles = {
            'ReportTitle': ParagraphStyle(
                'ReportTitle',
                parent=base['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=17,
                leading=21,
                textColor=colors.white,
                spaceAfter=4,
            ),
            'ReportSubtitle': ParagraphStyle(
                'ReportSubtitle',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=13,
                textColor=colors.HexColor('#CBD5E1'),
            ),
            'SectionHeader': ParagraphStyle(
                'SectionHeader',
                parent=base['Heading2'],
                fontName='Helvetica-Bold',
                fontSize=11,
                leading=14,
                textColor=self.NAVY_PRIMARY,
                spaceBefore=14,
                spaceAfter=6,
                keepWithNext=True,
            ),
            'SectionSubtext': ParagraphStyle(
                'SectionSubtext',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11,
                textColor=self.SLATE_MUTED,
                spaceAfter=6,
                keepWithNext=True,
            ),
            'CardLabel': ParagraphStyle(
                'CardLabel',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7.5,
                leading=10,
                textColor=self.SLATE_MUTED,
            ),
            'CardValue': ParagraphStyle(
                'CardValue',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=9.5,
                leading=12,
                textColor=self.NAVY_PRIMARY,
            ),
            'TableHead': ParagraphStyle(
                'TableHead',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=0,  # Left
            ),
            'TableHeadCenter': ParagraphStyle(
                'TableHeadCenter',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=1,  # Center
            ),
            'TableHeadRight': ParagraphStyle(
                'TableHeadRight',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=2,  # Right
            ),
            'CellText': ParagraphStyle(
                'CellText',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=7.5,
                leading=9.5,
                textColor=self.NAVY_PRIMARY,
            ),
            'CellTextBold': ParagraphStyle(
                'CellTextBold',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7.5,
                leading=9.5,
                textColor=self.NAVY_PRIMARY,
            ),
            'CellTextCenter': ParagraphStyle(
                'CellTextCenter',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=7.5,
                leading=9.5,
                textColor=self.NAVY_PRIMARY,
                alignment=1,
            ),
            'CellTextRight': ParagraphStyle(
                'CellTextRight',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=7.5,
                leading=9.5,
                textColor=self.NAVY_PRIMARY,
                alignment=2,
            ),
            'CellMuted': ParagraphStyle(
                'CellMuted',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=7,
                leading=9,
                textColor=self.SLATE_MUTED,
            ),
            'KpiNum': ParagraphStyle(
                'KpiNum',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=12,
                leading=14,
                textColor=self.NAVY_PRIMARY,
                alignment=1,
            ),
            'KpiLabel': ParagraphStyle(
                'KpiLabel',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7,
                leading=9,
                textColor=self.SLATE_MUTED,
                alignment=1,
            ),
            'GuardrailTitle': ParagraphStyle(
                'GuardrailTitle',
                parent=base['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8.5,
                leading=11,
                textColor=self.NAVY_PRIMARY,
            ),
            'GuardrailText': ParagraphStyle(
                'GuardrailText',
                parent=base['Normal'],
                fontName='Helvetica-Oblique',
                fontSize=7.5,
                leading=10.5,
                textColor=self.SLATE_DARK,
            ),
            'Narrative': ParagraphStyle(
                'Narrative',
                parent=base['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11.5,
                textColor=self.SLATE_DARK,
            ),
        }
        return styles

    # =========================================================================
    # NUMBER & BADGE FORMATTING HELPERS
    # =========================================================================
    def _fmt_curr(self, val: Any) -> str:
        """Formats numbers into standard currency."""
        if val is None or val == '':
            return '—'
        try:
            num = float(val)
            return f"${num:,.2f}" if self.currency == 'USD' else f"{self.currency} {num:,.2f}"
        except (ValueError, TypeError):
            return str(val)

    def _fmt_pct(self, val: Any) -> str:
        """Formats numbers into percentages."""
        if val is None or val == '':
            return '—'
        try:
            num = float(val)
            return f"{num:+.1f}%" if num != 0 else "0.0%"
        except (ValueError, TypeError):
            return str(val)

    def _fmt_int(self, val: Any) -> str:
        """Formats numbers into integer string."""
        if val is None or val == '':
            return '—'
        try:
            return f"{int(val):,}"
        except (ValueError, TypeError):
            return str(val)

    def _make_badge(self, text: str, bg_color: colors.Color, text_color: colors.Color) -> Table:
        """Creates an inline styled badge/pill inside a mini table."""
        p = Paragraph(
            f"<b>{text}</b>",
            ParagraphStyle(
                'Badge',
                fontName='Helvetica-Bold',
                fontSize=6.5,
                leading=7.5,
                textColor=text_color,
                alignment=1,
            ),
        )
        t = Table([[p]], colWidths=[None])
        t.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
        )
        return t

    # =========================================================================
    # DOCUMENT GENERATION
    # =========================================================================
    def generate_bytes(self) -> io.BytesIO:
        """
        Builds the entire PDF story and writes it into an in-memory BytesIO buffer.
        """
        buffer = io.BytesIO()

        # Document geometry: Letter, 36pt (0.5 inch) side margins, 50pt top/bottom
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=46,
        )

        story: List[Any] = []

        # 1. Executive Title Banner
        self._add_title_banner(story)

        # 2. RFQ Baseline Scope & KPI Highlights
        self._add_rfq_summary_and_kpis(story)

        # 3. Overall Supplier Comparative Ranking Matrix
        self._add_supplier_ranking_matrix(story)

        # 4. Detailed Price Comparison (Financial totals + Itemized BOM schedule)
        self._add_price_comparison_section(story)

        # 5. Technical Specification Matching Matrix
        self._add_specification_comparison_section(story)

        # 6. Commercial Terms (Delivery, Incoterms, Payment, Warranty)
        self._add_commercial_terms_section(story)

        # 7. Deterministic Quotation Risk Flags (14-Rule Log)
        self._add_risk_flags_section(story)

        # 8. Explainable Supplier Scoring Engine & Math Explanation
        self._add_scoring_engine_section(story)

        # 9. Strategic Award Recommendation & Decision Trade-Offs
        self._add_recommendation_and_tradeoffs(story)

        # 10. Mandatory Decision-Support Guardrail Disclaimer
        self._add_decision_guardrail_callout(story)

        # Set RFQ number on custom canvas for header drawing
        NumberedCanvas._doc_rfq_number = getattr(self.rfq, 'rfq_number', '')

        # Build document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    # =========================================================================
    # SECTION BUILDERS
    # =========================================================================
    def _add_title_banner(self, story: List[Any]):
        """Renders executive corporate title banner."""
        rfq_num = getattr(self.rfq, 'rfq_number', 'RFQ')
        rfq_title = getattr(self.rfq, 'title', 'Procurement Quotation Evaluation')
        eval_date = date.today().strftime('%B %d, %Y')
        org_name = getattr(self.organization, 'name', 'Enterprise Sourcing Entity')

        content = [
            Paragraph("QUOTEFLOW AI  —  INTELLIGENT SOURCING & PROCUREMENT AUDIT", self.styles['ReportSubtitle']),
            Spacer(1, 3),
            Paragraph("Procurement Quotation Evaluation & Comparison Report", self.styles['ReportTitle']),
            Spacer(1, 3),
            Paragraph(
                f"<b>RFQ:</b> {rfq_num} &nbsp;|&nbsp; <b>Project:</b> {rfq_title} &nbsp;|&nbsp; "
                f"<b>Date:</b> {eval_date} &nbsp;|&nbsp; <b>Organization:</b> {org_name}",
                self.styles['ReportSubtitle'],
            ),
        ]

        banner_table = Table([[content]], colWidths=[self.PAGE_WIDTH])
        banner_table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.NAVY_PRIMARY),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 14),
                ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ])
        )
        story.append(banner_table)
        story.append(Spacer(1, 10))

    def _add_rfq_summary_and_kpis(self, story: List[Any]):
        """Renders Section 1: RFQ Baseline Metadata and Executive KPI cards."""
        story.append(Paragraph("1. RFQ Scope & Procurement Baseline", self.styles['SectionHeader']))

        rfq_num = getattr(self.rfq, 'rfq_number', 'Not Assigned')
        rfq_title = getattr(self.rfq, 'title', 'General Sourcing')
        req_deliv = str(getattr(self.rfq, 'required_delivery_date', 'Not specified'))
        rfq_status = str(getattr(self.rfq, 'status', 'OPEN')).upper()

        # Calculate target budget
        target_budget = 0.0
        if hasattr(self.rfq, 'items'):
            target_budget = sum(
                float(it.quantity) * float(it.target_unit_price or 0)
                for it in self.rfq.items.all()
            )
        line_count = self.rfq.items.count() if hasattr(self.rfq, 'items') else 0

        # 4-column RFQ Metadata Grid
        meta_data = [
            [
                Paragraph("RFQ Identifier:", self.styles['CardLabel']),
                Paragraph(rfq_num, self.styles['CardValue']),
                Paragraph("Required Delivery Date:", self.styles['CardLabel']),
                Paragraph(req_deliv, self.styles['CardValue']),
            ],
            [
                Paragraph("Project Scope Title:", self.styles['CardLabel']),
                Paragraph(rfq_title, self.styles['CardValue']),
                Paragraph("RFQ Lifecycle Status:", self.styles['CardLabel']),
                Paragraph(rfq_status, self.styles['CardValue']),
            ],
            [
                Paragraph("Procurement Currency:", self.styles['CardLabel']),
                Paragraph(self.currency, self.styles['CardValue']),
                Paragraph("Line Items Count:", self.styles['CardLabel']),
                Paragraph(f"{line_count} BOM Items", self.styles['CardValue']),
            ],
            [
                Paragraph("Baseline Target Budget:", self.styles['CardLabel']),
                Paragraph(self._fmt_curr(target_budget) if target_budget > 0 else 'Unbudgeted', self.styles['CardValue']),
                Paragraph("Buying Organization:", self.styles['CardLabel']),
                Paragraph(getattr(self.organization, 'name', 'Enterprise'), self.styles['CardValue']),
            ],
        ]

        meta_table = Table(meta_data, colWidths=[115, 155, 115, 155])
        meta_table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.BG_CARD),
                ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 8))

        # KPI Dashboard Cards
        price_comp = self.data.get('price_comparison', {})
        lowest_gt = price_comp.get('lowest_grand_total')
        highest_gt = price_comp.get('highest_grand_total')
        savings_amt = price_comp.get('max_savings_amount') or price_comp.get('potential_savings') or 0
        savings_pct = price_comp.get('max_savings_percentage', 0)
        cherry_total = price_comp.get('cherry_pick_total') or 0
        cherry_savings = price_comp.get('cherry_pick_savings') or 0
        quotes_count = price_comp.get('quotations_compared_count', 0)

        kpi_data = [
            [
                [
                    Paragraph("QUOTES EVALUATED", self.styles['KpiLabel']),
                    Paragraph(f"{quotes_count} Verified", self.styles['KpiNum']),
                ],
                [
                    Paragraph("LOWEST QUOTED PRICE", self.styles['KpiLabel']),
                    Paragraph(self._fmt_curr(lowest_gt), self.styles['KpiNum']),
                ],
                [
                    Paragraph("HIGHEST QUOTED PRICE", self.styles['KpiLabel']),
                    Paragraph(self._fmt_curr(highest_gt), self.styles['KpiNum']),
                ],
                [
                    Paragraph("MAX POTENTIAL SAVINGS", self.styles['KpiLabel']),
                    Paragraph(self._fmt_curr(savings_amt), self.styles['KpiNum']),
                ],
                [
                    Paragraph("SPLIT CHERRY-PICK TOTAL", self.styles['KpiLabel']),
                    Paragraph(self._fmt_curr(cherry_total), self.styles['KpiNum']),
                ],
            ]
        ]

        kpi_table = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
        kpi_table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.BG_CARD_ALT),
                ('BOX', (0, 0), (-1, -1), 0.75, self.BORDER_LIGHT),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
        )
        story.append(kpi_table)
        story.append(Spacer(1, 10))

    def _add_supplier_ranking_matrix(self, story: List[Any]):
        """Renders Section 2: Overall Supplier Evaluation & Comparative Ranking Matrix."""
        story.append(Paragraph("2. Overall Supplier Evaluation & Comparative Ranking Matrix", self.styles['SectionHeader']))
        story.append(
            Paragraph(
                "Aggregated multi-factor evaluation combining commercial pricing, technical specification compliance, "
                "delivery lead time, payment terms risk, and warranty coverage.",
                self.styles['SectionSubtext'],
            )
        )

        headers = [
            Paragraph("Rank", self.styles['TableHeadCenter']),
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quote Ref", self.styles['TableHead']),
            Paragraph("Quoted Total", self.styles['TableHeadRight']),
            Paragraph("Variance", self.styles['TableHeadRight']),
            Paragraph("Spec Match", self.styles['TableHeadCenter']),
            Paragraph("Lead Time", self.styles['TableHeadCenter']),
            Paragraph("Risk Profile", self.styles['TableHeadCenter']),
            Paragraph("Score /100", self.styles['TableHeadCenter']),
            Paragraph("Status", self.styles['TableHeadCenter']),
        ]

        table_rows = [headers]
        cards = self.data.get('supplier_comparison', [])

        row_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        for idx, card in enumerate(cards, start=1):
            rank = card.get('rank') or idx
            is_top = (rank == 1)
            supp_name = card.get('supplier_name', 'Unknown')
            q_num = card.get('quotation_number', '—')

            pricing = card.get('pricing', {})
            grand_total = pricing.get('grand_total', 0)
            diff_lowest = pricing.get('price_difference_from_lowest')

            specs = card.get('specifications', {})
            comp_score = specs.get('compliance_score', 0)

            deliv = card.get('delivery', {})
            lead_wks = deliv.get('lead_time_weeks') or 0

            risk_prof = card.get('risk_profile', {})
            risk_level = (risk_prof.get('overall_risk_level') or 'LOW').upper()

            scoring = card.get('scoring', {})
            final_score = scoring.get('final_score', 0)

            rec_status = "Top Ranked" if is_top else ("Lowest Price" if pricing.get('is_lowest_price') else "Eligible")

            # Risk pill
            if risk_level == 'LOW':
                risk_badge = self._make_badge("LOW", self.EMERALD_FILL, self.EMERALD_FONT)
            elif risk_level == 'MEDIUM':
                risk_badge = self._make_badge("MEDIUM", self.AMBER_FILL, self.AMBER_FONT)
            else:
                risk_badge = self._make_badge(risk_level, self.ROSE_FILL, self.ROSE_FONT)

            row = [
                Paragraph(f"<b>#{rank}</b>", self.styles['CellTextCenter']),
                Paragraph(f"<b>{supp_name}</b>" if is_top else supp_name, self.styles['CellTextBold' if is_top else 'CellText']),
                Paragraph(q_num, self.styles['CellMuted']),
                Paragraph(self._fmt_curr(grand_total), self.styles['CellTextRight']),
                Paragraph(self._fmt_curr(diff_lowest) if (diff_lowest is not None and float(diff_lowest) > 0) else 'LOWEST', self.styles['CellTextRight']),
                Paragraph(f"{comp_score:.0f}%", self.styles['CellTextCenter']),
                Paragraph(f"{int(lead_wks or 0)} wks", self.styles['CellTextCenter']),
                risk_badge,
                Paragraph(f"<b>{float(final_score):.1f}</b>", self.styles['CellTextCenter']),
                Paragraph(rec_status, self.styles['CellTextCenter']),
            ]
            table_rows.append(row)

            # Highlight top vendor row in subtle emerald
            if is_top:
                row_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#F0FDF4')))
            elif idx % 2 == 0:
                row_styles.append(('BACKGROUND', (0, idx), (-1, idx), self.BG_CARD))

        col_widths = [28, 110, 68, 62, 52, 45, 42, 45, 45, 43]
        rank_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        rank_table.setStyle(TableStyle(row_styles))
        story.append(rank_table)
        story.append(Spacer(1, 10))

    def _add_price_comparison_section(self, story: List[Any]):
        """Renders Section 3: Detailed Price Comparison & Itemized BOM Pricing Schedule."""
        story.append(Paragraph("3. Detailed Price Comparison & BOM Pricing Schedule", self.styles['SectionHeader']))

        price_comp = self.data.get('price_comparison', {})
        quotations = price_comp.get('quotations', [])

        # Sub-Table 1: Financial Schedule
        story.append(Paragraph("<b>Table 3.1: Supplier Financial Schedule & Cost Breakdown</b>", self.styles['SectionSubtext']))

        fin_headers = [
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quote Ref", self.styles['TableHead']),
            Paragraph("Subtotal", self.styles['TableHeadRight']),
            Paragraph("Taxes", self.styles['TableHeadRight']),
            Paragraph("Shipping", self.styles['TableHeadRight']),
            Paragraph("Discounts", self.styles['TableHeadRight']),
            Paragraph("Grand Total", self.styles['TableHeadRight']),
            Paragraph("Variance vs Low", self.styles['TableHeadRight']),
            Paragraph("Lowest?", self.styles['TableHeadCenter']),
        ]
        fin_rows = [fin_headers]
        fin_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        for idx, q in enumerate(quotations, start=1):
            is_low = q.get('is_lowest_price', False)
            diff_low = q.get('price_difference_from_lowest')

            row = [
                Paragraph(q.get('supplier_name', ''), self.styles['CellTextBold' if is_low else 'CellText']),
                Paragraph(q.get('quotation_number', ''), self.styles['CellMuted']),
                Paragraph(self._fmt_curr(q.get('subtotal')), self.styles['CellTextRight']),
                Paragraph(self._fmt_curr(q.get('tax_amount')), self.styles['CellTextRight']),
                Paragraph(self._fmt_curr(q.get('shipping_amount')), self.styles['CellTextRight']),
                Paragraph(self._fmt_curr(q.get('discount_amount')), self.styles['CellTextRight']),
                Paragraph(f"<b>{self._fmt_curr(q.get('grand_total'))}</b>", self.styles['CellTextRight']),
                Paragraph(self._fmt_curr(diff_low) if (diff_low is not None and float(diff_low) > 0) else 'BASE', self.styles['CellTextRight']),
                Paragraph("YES ★" if is_low else "NO", self.styles['CellTextCenter']),
            ]
            fin_rows.append(row)
            if is_low:
                fin_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#F0FDF4')))
            elif idx % 2 == 0:
                fin_styles.append(('BACKGROUND', (0, idx), (-1, idx), self.BG_CARD))

        fin_table = Table(fin_rows, colWidths=[105, 65, 55, 45, 45, 45, 65, 65, 50], repeatRows=1)
        fin_table.setStyle(TableStyle(fin_styles))
        story.append(fin_table)
        story.append(Spacer(1, 8))

        # Sub-Table 2: Itemized BOM Line Items Pricing Schedule
        story.append(Paragraph("<b>Table 3.2: Itemized BOM Line Items Pricing Schedule</b>", self.styles['SectionSubtext']))

        bom_headers = [
            Paragraph("Item Scope / Part", self.styles['TableHead']),
            Paragraph("RFQ Qty", self.styles['TableHeadCenter']),
            Paragraph("Target", self.styles['TableHeadRight']),
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Unit Price", self.styles['TableHeadRight']),
            Paragraph("Extended Total", self.styles['TableHeadRight']),
            Paragraph("Unit Variance", self.styles['TableHeadRight']),
            Paragraph("Compatibility", self.styles['TableHeadCenter']),
        ]
        bom_rows = [bom_headers]
        bom_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        items_matrix = price_comp.get('items_matrix', [])
        row_idx = 1
        for row_data in items_matrix:
            item_name = row_data.get('item_name', 'Line Item')
            qty = row_data.get('target_quantity') or row_data.get('quantity', 0)
            uom = row_data.get('target_unit') or row_data.get('uom', 'EA')
            target_unit = row_data.get('target_unit_price')
            lowest_unit = row_data.get('lowest_unit_price')

            bids_val = row_data.get('bids')
            if isinstance(bids_val, dict):
                quotes = list(bids_val.values())
            elif isinstance(bids_val, list):
                quotes = bids_val
            else:
                quotes = row_data.get('quotes', [])

            for q_entry in quotes:
                supp_name = q_entry.get('supplier_name', '')
                u_price = float(q_entry.get('normalized_unit_price') or q_entry.get('quoted_unit_price') or q_entry.get('unit_price') or 0)
                ext_price = float(q_entry.get('extended_price_target_qty') or q_entry.get('extended_price_quoted_qty') or q_entry.get('quoted_line_total') or q_entry.get('extended_price') or 0)
                is_low_item = q_entry.get('is_lowest_unit_price') or q_entry.get('is_lowest', False)
                compat_status = q_entry.get('compatibility_status')
                is_compat = (compat_status == 'COMPATIBLE') if compat_status is not None else q_entry.get('is_compatible', True)

                diff_from_low = (u_price - float(lowest_unit)) if (lowest_unit is not None and str(lowest_unit) != '') else 0

                bom_row = [
                    Paragraph(item_name, self.styles['CellTextBold']),
                    Paragraph(f"{self._fmt_int(qty)} {uom}", self.styles['CellTextCenter']),
                    Paragraph(self._fmt_curr(target_unit), self.styles['CellTextRight']),
                    Paragraph(supp_name, self.styles['CellText']),
                    Paragraph(self._fmt_curr(u_price), self.styles['CellTextRight']),
                    Paragraph(self._fmt_curr(ext_price), self.styles['CellTextRight']),
                    Paragraph(self._fmt_curr(diff_from_low) if (diff_from_low is not None and float(diff_from_low) > 0) else 'LOWEST', self.styles['CellTextRight']),
                    Paragraph("COMPLIANT" if is_compat else "VARIANCE", self.styles['CellTextCenter']),
                ]
                bom_rows.append(bom_row)
                if is_low_item:
                    bom_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#F0FDF4')))
                elif row_idx % 2 == 0:
                    bom_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), self.BG_CARD))
                row_idx += 1

        bom_table = Table(bom_rows, colWidths=[110, 48, 48, 100, 58, 62, 54, 60], repeatRows=1)
        bom_table.setStyle(TableStyle(bom_styles))
        story.append(bom_table)
        story.append(Spacer(1, 10))

    def _add_specification_comparison_section(self, story: List[Any]):
        """Renders Section 4: Technical Specification Compliance & Verification."""
        story.append(Paragraph("4. Technical Specification Matching & Compliance Audit", self.styles['SectionHeader']))

        specs_data = self.data.get('specification_matching', {})
        summaries = specs_data.get('supplier_summaries', [])

        # Sub-Table 1: Supplier Compliance Summary
        story.append(Paragraph("<b>Table 4.1: Supplier Technical Verdict Summary</b>", self.styles['SectionSubtext']))

        sum_headers = [
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quote Ref", self.styles['TableHead']),
            Paragraph("Compliance %", self.styles['TableHeadCenter']),
            Paragraph("Technical Verdict", self.styles['TableHeadCenter']),
            Paragraph("Critical Mismatches", self.styles['TableHeadCenter']),
            Paragraph("Compliant Items", self.styles['TableHeadCenter']),
            Paragraph("Non-Compliant Items", self.styles['TableHeadCenter']),
        ]
        sum_rows = [sum_headers]
        sum_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        for idx, s in enumerate(summaries, start=1):
            verdict = s.get('overall_verdict', 'COMPLIANT')
            crit_count = int(s.get('total_critical_mismatches', 0))

            if verdict == 'COMPLIANT':
                v_badge = self._make_badge("COMPLIANT", self.EMERALD_FILL, self.EMERALD_FONT)
            elif verdict == 'PARTIALLY_COMPLIANT':
                v_badge = self._make_badge("PARTIAL", self.AMBER_FILL, self.AMBER_FONT)
            else:
                v_badge = self._make_badge("NON-COMPLIANT", self.ROSE_FILL, self.ROSE_FONT)

            row = [
                Paragraph(s.get('supplier_name', ''), self.styles['CellTextBold']),
                Paragraph(s.get('quotation_number', ''), self.styles['CellMuted']),
                Paragraph(f"{float(s.get('average_score', 0)):.1f}%", self.styles['CellTextCenter']),
                v_badge,
                Paragraph(str(crit_count), self.styles['CellTextCenter']),
                Paragraph(str(s.get('compliant_items_count', 0)), self.styles['CellTextCenter']),
                Paragraph(str(s.get('non_compliant_items_count', 0)), self.styles['CellTextCenter']),
            ]
            sum_rows.append(row)
            if idx % 2 == 0:
                sum_styles.append(('BACKGROUND', (0, idx), (-1, idx), self.BG_CARD))

        sum_table = Table(sum_rows, colWidths=[120, 70, 65, 85, 70, 65, 65], repeatRows=1)
        sum_table.setStyle(TableStyle(sum_styles))
        story.append(sum_table)
        story.append(Spacer(1, 8))

        # Sub-Table 2: Parameter-by-Parameter Matching Table
        story.append(Paragraph("<b>Table 4.2: Parameter-by-Parameter Specification Verification Log</b>", self.styles['SectionSubtext']))

        param_headers = [
            Paragraph("Item Scope", self.styles['TableHead']),
            Paragraph("Parameter", self.styles['TableHead']),
            Paragraph("RFQ Requirement", self.styles['TableHead']),
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quoted Value", self.styles['TableHead']),
            Paragraph("Status", self.styles['TableHeadCenter']),
            Paragraph("Discrepancy / Explanation & Evidence", self.styles['TableHead']),
        ]
        param_rows = [param_headers]
        param_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        spec_items = specs_data.get('items', [])
        p_idx = 1
        for item in spec_items:
            item_name = item.get('item_name') or item.get('rfq_item_name', '')
            evals = item.get('supplier_evaluations') or item.get('supplier_matches', [])

            for s_eval in evals:
                supp_name = s_eval.get('supplier_name', '')
                p_matches = s_eval.get('matches') or s_eval.get('parameter_matches', [])

                for pm in p_matches:
                    param = pm.get('parameter_name') or pm.get('parameter', '')
                    rfq_val = pm.get('requirement_value') or pm.get('rfq_value', '')
                    supp_val = pm.get('supplier_value', '')
                    raw_st = pm.get('status', 'EXACT_MATCH')
                    m_status = str(raw_st).upper()
                    expl = pm.get('explanation', '')
                    evid = pm.get('evidence', '')

                    # Badge
                    if m_status in ('EXACT_MATCH', 'COMPLIANT'):
                        st_badge = self._make_badge("MATCH", self.EMERALD_FILL, self.EMERALD_FONT)
                    elif m_status in ('MISMATCH', 'NON_COMPLIANT'):
                        st_badge = self._make_badge("MISMATCH", self.ROSE_FILL, self.ROSE_FONT)
                    else:
                        st_badge = self._make_badge(m_status, self.AMBER_FILL, self.AMBER_FONT)

                    note_text = expl
                    if evid:
                        note_text += f"<br/><font color='#64748B'>Evidence: {evid}</font>"

                    row = [
                        Paragraph(item_name, self.styles['CellTextBold']),
                        Paragraph(param, self.styles['CellTextBold']),
                        Paragraph(rfq_val, self.styles['CellText']),
                        Paragraph(supp_name, self.styles['CellText']),
                        Paragraph(f"<b>{supp_val}</b>", self.styles['CellText']),
                        st_badge,
                        Paragraph(note_text, self.styles['CellText']),
                    ]
                    param_rows.append(row)
                    if m_status in ('MISMATCH', 'NON_COMPLIANT'):
                        param_styles.append(('BACKGROUND', (0, p_idx), (-1, p_idx), colors.HexColor('#FFF1F2')))
                    elif p_idx % 2 == 0:
                        param_styles.append(('BACKGROUND', (0, p_idx), (-1, p_idx), self.BG_CARD))
                    p_idx += 1

        param_table = Table(param_rows, colWidths=[70, 65, 65, 75, 65, 55, 145], repeatRows=1)
        param_table.setStyle(TableStyle(param_styles))
        story.append(param_table)
        story.append(Spacer(1, 10))

    def _add_commercial_terms_section(self, story: List[Any]):
        """Renders Section 5: Commercial Terms (Delivery, Incoterms, Payment Terms, Warranty)."""
        story.append(Paragraph("5. Commercial Terms, Logistics & Warranty Comparison", self.styles['SectionHeader']))

        headers = [
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quote Ref", self.styles['TableHead']),
            Paragraph("Incoterms", self.styles['TableHeadCenter']),
            Paragraph("Lead Time", self.styles['TableHeadCenter']),
            Paragraph("On-Time Status", self.styles['TableHeadCenter']),
            Paragraph("Payment Terms", self.styles['TableHead']),
            Paragraph("Deposit Risk", self.styles['TableHeadCenter']),
            Paragraph("Warranty Terms & Rating", self.styles['TableHead']),
        ]
        comm_rows = [headers]
        comm_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        cards = self.data.get('supplier_comparison', [])
        for idx, card in enumerate(cards, start=1):
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

            # Deposit risk badge
            if is_advance:
                dep_badge = self._make_badge("DEPOSIT RISK", self.ROSE_FILL, self.ROSE_FONT)
            else:
                dep_badge = self._make_badge("STANDARD", self.EMERALD_FILL, self.EMERALD_FONT)

            # On-time badge
            if on_time == 'On Schedule':
                ot_badge = self._make_badge("ON SCHEDULE", self.EMERALD_FILL, self.EMERALD_FONT)
            else:
                ot_badge = self._make_badge(on_time.upper(), self.ROSE_FILL, self.ROSE_FONT)

            war_text = f"<b>{warranty}</b>"
            if is_no_war:
                war_text += f"<br/><font color='{self.ROSE_FONT.hexval()}'>HIGH RISK (No Warranty)</font>"

            row = [
                Paragraph(supp_name, self.styles['CellTextBold']),
                Paragraph(q_num, self.styles['CellMuted']),
                Paragraph(d_terms, self.styles['CellTextCenter']),
                Paragraph(f"{int(lead_wks or 0)} wks", self.styles['CellTextCenter']),
                ot_badge,
                Paragraph(pay_terms, self.styles['CellText']),
                dep_badge,
                Paragraph(war_text, self.styles['CellText']),
            ]
            comm_rows.append(row)
            if is_advance:
                comm_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#FFF1F2')))
            elif idx % 2 == 0:
                comm_styles.append(('BACKGROUND', (0, idx), (-1, idx), self.BG_CARD))

        comm_table = Table(comm_rows, colWidths=[95, 60, 48, 48, 65, 80, 68, 76], repeatRows=1)
        comm_table.setStyle(TableStyle(comm_styles))
        story.append(comm_table)
        story.append(Spacer(1, 10))

    def _add_risk_flags_section(self, story: List[Any]):
        """Renders Section 6: Deterministic Quotation Risk Flags (14-Rule Log)."""
        story.append(Paragraph("6. Deterministic Quotation Risk Flags (14-Rule Audit Log)", self.styles['SectionHeader']))

        headers = [
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quote Ref", self.styles['TableHead']),
            Paragraph("Severity", self.styles['TableHeadCenter']),
            Paragraph("Flag Title & Type", self.styles['TableHead']),
            Paragraph("Affected Scope", self.styles['TableHead']),
            Paragraph("Audit Evidence & Discrepancy", self.styles['TableHead']),
            Paragraph("Recommended Procurement Action", self.styles['TableHead']),
        ]
        risk_rows = [headers]
        risk_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        risk_reports = self.data.get('risk_flags', [])
        r_idx = 1
        found_any_risk = False

        for rep in risk_reports:
            supp_name = rep.get('supplier_name', '')
            q_num = rep.get('quotation_number', '')
            flags = rep.get('flags', [])

            for f in flags:
                found_any_risk = True
                sev = (f.get('severity') or 'MEDIUM').upper()
                title = f.get('title', '')
                ftype = f.get('type', '')
                field_scope = f.get('affected_field') or 'Commercial/Tech'
                evid = f.get('evidence') or f.get('description', '')
                action = f.get('recommended_action', 'Verify with vendor.')

                if sev in ('CRITICAL', 'HIGH'):
                    sev_badge = self._make_badge(sev, self.ROSE_FILL, self.ROSE_FONT)
                elif sev == 'MEDIUM':
                    sev_badge = self._make_badge("MEDIUM", self.AMBER_FILL, self.AMBER_FONT)
                else:
                    sev_badge = self._make_badge("LOW", self.INDIGO_FILL, self.INDIGO_FONT)

                title_text = f"<b>{title}</b><br/><font color='#64748B'>{ftype}</font>"

                row = [
                    Paragraph(supp_name, self.styles['CellTextBold']),
                    Paragraph(q_num, self.styles['CellMuted']),
                    sev_badge,
                    Paragraph(title_text, self.styles['CellText']),
                    Paragraph(field_scope, self.styles['CellText']),
                    Paragraph(evid, self.styles['CellText']),
                    Paragraph(action, self.styles['CellText']),
                ]
                risk_rows.append(row)
                if sev in ('CRITICAL', 'HIGH'):
                    risk_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#FFF1F2')))
                elif r_idx % 2 == 0:
                    risk_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), self.BG_CARD))
                r_idx += 1

        if not found_any_risk:
            risk_rows.append([
                Paragraph("All Suppliers", self.styles['CellText']),
                Paragraph("—", self.styles['CellMuted']),
                self._make_badge("CLEAR", self.EMERALD_FILL, self.EMERALD_FONT),
                Paragraph("No Critical or Commercial Risk Flags Detected", self.styles['CellTextBold']),
                Paragraph("All line items and terms pass validation rules", self.styles['CellText']),
                Paragraph("No arithmetic or specification discrepancies found", self.styles['CellText']),
                Paragraph("Proceed with standard procurement review", self.styles['CellText']),
            ])

        risk_table = Table(risk_rows, colWidths=[80, 55, 52, 95, 65, 105, 88], repeatRows=1)
        risk_table.setStyle(TableStyle(risk_styles))
        story.append(risk_table)
        story.append(Spacer(1, 10))

    def _add_scoring_engine_section(self, story: List[Any]):
        """Renders Section 7: Explainable Supplier Scoring Engine & Math Explanation."""
        story.append(Paragraph("7. Explainable Supplier Scoring Engine", self.styles['SectionHeader']))

        scoring_data = self.data.get('scoring', {})
        weights = scoring_data.get('weights_applied') or self.data.get('settings', {}).get('weights', {})

        # Weights Table
        story.append(Paragraph("<b>Table 7.1: Active Multi-Factor Evaluation Weighting Scheme</b>", self.styles['SectionSubtext']))
        weight_cols = [
            Paragraph("Factor: Price Total", self.styles['TableHeadCenter']),
            Paragraph("Factor: Spec Compliance", self.styles['TableHeadCenter']),
            Paragraph("Factor: Delivery Lead Time", self.styles['TableHeadCenter']),
            Paragraph("Factor: Payment Credit Terms", self.styles['TableHeadCenter']),
            Paragraph("Factor: Warranty Guarantee", self.styles['TableHeadCenter']),
        ]
        weight_vals = [
            Paragraph(f"<b>{float(weights.get('price', 40)):.0f}%</b>", self.styles['CellTextCenter']),
            Paragraph(f"<b>{float(weights.get('spec_match', 30)):.0f}%</b>", self.styles['CellTextCenter']),
            Paragraph(f"<b>{float(weights.get('delivery', 15)):.0f}%</b>", self.styles['CellTextCenter']),
            Paragraph(f"<b>{float(weights.get('payment_terms', 10)):.0f}%</b>", self.styles['CellTextCenter']),
            Paragraph(f"<b>{float(weights.get('warranty', 5)):.0f}%</b>", self.styles['CellTextCenter']),
        ]
        w_table = Table([weight_cols, weight_vals], colWidths=[108, 108, 108, 108, 108])
        w_table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
                ('BACKGROUND', (0, 1), (-1, 1), self.BG_CARD),
                ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ])
        )
        story.append(w_table)
        story.append(Spacer(1, 8))

        # Factor Breakdown Matrix
        story.append(Paragraph("<b>Table 7.2: Per-Supplier Factor Score Breakdown Matrix</b>", self.styles['SectionSubtext']))
        rankings = scoring_data.get('rankings', [])

        factor_headers = [
            Paragraph("Supplier Name", self.styles['TableHead']),
            Paragraph("Quote Ref", self.styles['TableHead']),
            Paragraph("Price (/100)", self.styles['TableHeadCenter']),
            Paragraph("Spec (/100)", self.styles['TableHeadCenter']),
            Paragraph("Delivery (/100)", self.styles['TableHeadCenter']),
            Paragraph("Payment (/100)", self.styles['TableHeadCenter']),
            Paragraph("Warranty (/100)", self.styles['TableHeadCenter']),
            Paragraph("Final Score", self.styles['TableHeadCenter']),
            Paragraph("Rank", self.styles['TableHeadCenter']),
        ]
        factor_rows = [factor_headers]
        factor_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), self.NAVY_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
        ]

        for idx, r in enumerate(rankings, start=1):
            is_top = (r.get('rank') == 1)
            bdown = r.get('factor_breakdown', {})
            p_score = bdown.get('price', {}).get('factor_score', 0)
            s_score = bdown.get('spec_match', {}).get('factor_score', 0)
            d_score = bdown.get('delivery', {}).get('factor_score', 0)
            pay_score = bdown.get('payment_terms', {}).get('factor_score', 0)
            w_score = bdown.get('warranty', {}).get('factor_score', 0)

            row = [
                Paragraph(r.get('supplier_name', ''), self.styles['CellTextBold' if is_top else 'CellText']),
                Paragraph(r.get('quotation_number', ''), self.styles['CellMuted']),
                Paragraph(f"{float(p_score):.1f}", self.styles['CellTextCenter']),
                Paragraph(f"{float(s_score):.1f}", self.styles['CellTextCenter']),
                Paragraph(f"{float(d_score):.1f}", self.styles['CellTextCenter']),
                Paragraph(f"{float(pay_score):.1f}", self.styles['CellTextCenter']),
                Paragraph(f"{float(w_score):.1f}", self.styles['CellTextCenter']),
                Paragraph(f"<b>{float(r.get('final_score', 0)):.1f}</b>", self.styles['CellTextCenter']),
                Paragraph(f"#{r.get('rank')}", self.styles['CellTextCenter']),
            ]
            factor_rows.append(row)
            if is_top:
                factor_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#F0FDF4')))
            elif idx % 2 == 0:
                factor_styles.append(('BACKGROUND', (0, idx), (-1, idx), self.BG_CARD))

        factor_table = Table(factor_rows, colWidths=[110, 65, 52, 52, 52, 52, 52, 60, 45], repeatRows=1)
        factor_table.setStyle(TableStyle(factor_styles))
        story.append(factor_table)
        story.append(Spacer(1, 8))

        # Transparent Scoring Explanation Box
        math_content = [
            Paragraph("<b>Mathematical Formula & Scoring Methodology:</b>", self.styles['GuardrailTitle']),
            Spacer(1, 2),
            Paragraph(
                "Final Score = &Sigma; (Factor Score<sub>i</sub> &times; Weight<sub>i</sub>). "
                "<b>1. Price Score:</b> Linear interpolation between lowest quoted price (100 pts) and highest quoted price (0 pts). "
                "<b>2. Specification Score:</b> Percentage of technical requirements verified compliant minus penalty deductions for critical mismatches. "
                "<b>3. Delivery Score:</b> 100 points for fulfillment on or before RFQ required date, with linear deductions per week of lead time overrun. "
                "<b>4. Payment Terms Score:</b> Net 30/60 day trade credit receives 100 points; upfront cash advances and high deposit demands receive deterministic risk deductions. "
                "<b>5. Warranty Score:</b> Baseline 24-month manufacturer warranty receives 100 points; shorter or missing warranties receive proportional deductions.",
                self.styles['Narrative'],
            ),
        ]
        math_box = Table([[math_content]], colWidths=[self.PAGE_WIDTH])
        math_box.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.BG_CARD_ALT),
                ('BOX', (0, 0), (-1, -1), 0.5, self.BORDER_LIGHT),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ])
        )
        story.append(math_box)
        story.append(Spacer(1, 10))

    def _add_recommendation_and_tradeoffs(self, story: List[Any]):
        """Renders Section 8: Strategic Award Recommendation Analysis & Decision Trade-Offs."""
        story.append(Paragraph("8. Strategic Award Recommendation & Sourcing Trade-Offs", self.styles['SectionHeader']))

        cards = self.data.get('supplier_comparison', [])
        top_card = next((c for c in cards if c.get('rank') == 1), None)
        low_card = next((c for c in cards if c.get('pricing', {}).get('is_lowest_price')), None)

        top_supp = top_card.get('supplier_name', 'Top Evaluated Vendor') if top_card else 'N/A'
        top_score = top_card.get('scoring', {}).get('final_score', 0) if top_card else 0
        top_total = top_card.get('pricing', {}).get('grand_total', 0) if top_card else 0

        low_supp = low_card.get('supplier_name', 'Lowest Price Vendor') if low_card else 'N/A'
        low_total = low_card.get('pricing', {}).get('grand_total', 0) if low_card else 0

        diff_amt = max(0.0, float(top_total or 0) - float(low_total or 0))

        if top_supp == low_supp:
            rec_text = (
                f"<b>Clear Leading Option:</b> <b>{top_supp}</b> represents both the highest-scoring supplier "
                f"({top_score:.1f}/100) and the lowest overall quoted cost ({self._fmt_curr(top_total)}). "
                f"This quotation provides full technical compliance without commercial risk penalties, offering an optimal "
                f"balance of quality, pricing, and fulfillment reliability."
            )
        else:
            rec_text = (
                f"<b>Multi-Attribute Trade-Off Analysis:</b> <b>{top_supp}</b> achieved the highest overall score "
                f"({top_score:.1f}/100) at a total price of {self._fmt_curr(top_total)}. "
                f"While <b>{low_supp}</b> offers the lowest price ({self._fmt_curr(low_total)}, saving {self._fmt_curr(diff_amt)}), "
                f"the higher-ranking option provides superior technical compliance, more favorable commercial credit terms, "
                f"and reduced delivery risk. The procurement committee should evaluate whether the price differential outweighs "
                f"the technical and commercial risks identified."
            )

        card_content = [
            Paragraph("<b>Procurement Committee Evaluation Brief:</b>", self.styles['CardValue']),
            Spacer(1, 3),
            Paragraph(rec_text, self.styles['Narrative']),
        ]
        card_table = Table([[card_content]], colWidths=[self.PAGE_WIDTH])
        card_table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ])
        )
        story.append(card_table)
        story.append(Spacer(1, 10))

    def _add_decision_guardrail_callout(self, story: List[Any]):
        """Renders Section 9: Mandatory Human Decision-Support Guardrail Disclaimer."""
        callout_content = [
            Paragraph("<b>MANDATORY NOTICE & DECISION-SUPPORT GUARDRAIL:</b>", self.styles['GuardrailTitle']),
            Spacer(1, 3),
            Paragraph(
                "QuoteFlow AI provides transparent mathematical ranking, specification verification, and commercial risk auditing "
                "for authorized procurement evaluation committees. The system <b>does NOT automatically select or purchase from suppliers</b>. "
                "All scoring calculations, risk ratings, and comparison matrices are decision-support guidelines only. "
                "Final award determinations, commercial negotiations, and binding contract commitments require explicit human procurement authorization.",
                self.styles['GuardrailText'],
            ),
        ]

        guardrail_table = Table([[callout_content]], colWidths=[self.PAGE_WIDTH])
        guardrail_table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.INDIGO_FILL),
                ('BOX', (0, 0), (-1, -1), 1, self.INDIGO_FONT),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ])
        )
        story.append(KeepTogether(guardrail_table))
