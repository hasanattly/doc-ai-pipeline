# src/ui/pdf_exporter.py

import sys
sys.path.append("/app/src")

from io import BytesIO
from datetime import datetime
from parser.document_parser import ParsedDocument

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, PageBreak
)


# ──────────────────────────────────────────────
# BRAND COLORS
# ──────────────────────────────────────────────

NAVY        = colors.HexColor("#1E1E3C")
ACCENT_BLUE = colors.HexColor("#5050B4")
LIGHT_BLUE  = colors.HexColor("#EEEEF8")
MID_GREY    = colors.HexColor("#787878")
LIGHT_GREY  = colors.HexColor("#F5F5F5")
WHITE       = colors.white
BLACK       = colors.HexColor("#282828")
GREEN       = colors.HexColor("#2E7D32")
ORANGE      = colors.HexColor("#E65100")
RED         = colors.HexColor("#C62828")


# ──────────────────────────────────────────────
# STYLES
# ──────────────────────────────────────────────

def _build_styles():
    """Builds and returns all custom paragraph styles."""
    base = getSampleStyleSheet()

    styles = {
        "report_title": ParagraphStyle(
            "report_title",
            fontName    = "Helvetica-Bold",
            fontSize    = 20,
            textColor   = NAVY,
            alignment   = TA_CENTER,
            spaceAfter  = 4,
        ),
        "report_subtitle": ParagraphStyle(
            "report_subtitle",
            fontName    = "Helvetica",
            fontSize    = 9,
            textColor   = MID_GREY,
            alignment   = TA_CENTER,
            spaceAfter  = 2,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName    = "Helvetica-Bold",
            fontSize    = 12,
            textColor   = ACCENT_BLUE,
            spaceBefore = 14,
            spaceAfter  = 4,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName    = "Helvetica-Bold",
            fontSize    = 9,
            textColor   = WHITE,
            alignment   = TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName    = "Helvetica",
            fontSize    = 9,
            textColor   = BLACK,
            leading     = 13,
            wordWrap    = "CJK",
        ),
        "table_cell_bold": ParagraphStyle(
            "table_cell_bold",
            fontName    = "Helvetica-Bold",
            fontSize    = 9,
            textColor   = BLACK,
            leading     = 13,
        ),
        "raw_text": ParagraphStyle(
            "raw_text",
            fontName    = "Courier",
            fontSize    = 8,
            textColor   = BLACK,
            leading     = 12,
            spaceAfter  = 2,
            wordWrap    = "CJK",
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName    = "Helvetica",
            fontSize    = 7,
            textColor   = MID_GREY,
            alignment   = TA_CENTER,
        ),
        "confidence_high": ParagraphStyle(
            "confidence_high",
            fontName  = "Helvetica-Bold",
            fontSize  = 9,
            textColor = GREEN,
        ),
        "confidence_mid": ParagraphStyle(
            "confidence_mid",
            fontName  = "Helvetica-Bold",
            fontSize  = 9,
            textColor = ORANGE,
        ),
        "confidence_low": ParagraphStyle(
            "confidence_low",
            fontName  = "Helvetica-Bold",
            fontSize  = 9,
            textColor = RED,
        ),
    }
    return styles


# ──────────────────────────────────────────────
# TABLE STYLE HELPERS
# ──────────────────────────────────────────────

def _metadata_table_style():
    return TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("TOPPADDING",    (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        # Data rows
        ("BACKGROUND",    (0, 1), (-1, 1), LIGHT_BLUE),
        ("BACKGROUND",    (0, 2), (-1, 2), WHITE),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TOPPADDING",    (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCDD")),
        ("BOX",           (0, 0), (-1, -1), 1.0, ACCENT_BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, WHITE]),
    ])


def _data_table_style():
    return TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), ACCENT_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("TOPPADDING",    (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        # Data rows
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TOPPADDING",    (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        # Alternating rows
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, WHITE]),
        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCDD")),
        ("BOX",           (0, 0), (-1, -1), 1.0, ACCENT_BLUE),
    ])


def _empty_table_style():
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), LIGHT_GREY),
        ("TEXTCOLOR",   (0, 0), (-1, -1), MID_GREY),
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica-Oblique"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("BOX",         (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCDD")),
    ])


# ──────────────────────────────────────────────
# FOOTER RENDERER
# ──────────────────────────────────────────────

def _make_footer(canvas, doc):
    """Draws page number and timestamp on every page."""
    canvas.saveState()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    footer_text = f"Document AI Pipeline  ·  {timestamp}  ·  Page {doc.page}"
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GREY)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, footer_text)

    # Footer line
    canvas.setStrokeColor(colors.HexColor("#CCCCDD"))
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 16 * mm, A4[0] - 20 * mm, 16 * mm)
    canvas.restoreState()


# ──────────────────────────────────────────────
# PDF EXPORTER
# ──────────────────────────────────────────────

class PDFExporter:
    """
    Generates a professional PDF report from a ParsedDocument
    using ReportLab's Platypus layout engine.

    Layout:
        Header → Metadata Table → Fields Table →
        Line Items Table → Raw OCR Text
    """

    PAGE_W   = A4[0]
    PAGE_H   = A4[1]
    MARGIN   = 20 * mm
    COL_W    = A4[0] - 2 * (20 * mm)   # Usable content width

    def __init__(self):
        self.styles = _build_styles()

    # ──────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ──────────────────────────────────────────────

    def generate(self, parsed: ParsedDocument) -> bytes:
        """
        Builds and returns the complete PDF as bytes.

        Args:
            parsed: ParsedDocument from DocumentParser.parse()

        Returns:
            PDF file content as bytes for st.download_button
        """
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize     = A4,
            leftMargin   = self.MARGIN,
            rightMargin  = self.MARGIN,
            topMargin    = self.MARGIN,
            bottomMargin = 22 * mm,   # Space for footer
            title        = "Document AI Extraction Report",
            author       = "Document AI Pipeline",
        )

        story = []
        story += self._build_header()
        story += self._build_metadata(parsed)
        story += self._build_fields(parsed)
        story += self._build_line_items(parsed)
        story += self._build_raw_text(parsed)

        doc.build(story, onFirstPage=_make_footer, onLaterPages=_make_footer)
        return buffer.getvalue()

    # ──────────────────────────────────────────────
    # SECTION BUILDERS
    # ──────────────────────────────────────────────

    def _build_header(self) -> list:
        """Centered title, subtitle, and horizontal divider."""
        return [
            Spacer(1, 4 * mm),
            Paragraph("DOCUMENT AI EXTRACTION REPORT", self.styles["report_title"]),
            Paragraph("Powered by EasyOCR · OpenCV · ReportLab", self.styles["report_subtitle"]),
            Spacer(1, 3 * mm),
            HRFlowable(
                width       = "100%",
                thickness   = 2,
                color       = ACCENT_BLUE,
                spaceAfter  = 6,
            ),
        ]

    def _build_metadata(self, parsed: ParsedDocument) -> list:
        """2-column metadata grid showing key document properties."""
        s = self.styles

        # Confidence color coding
        conf_val = parsed.confidence_score
        if conf_val >= 0.80:
            conf_style = s["confidence_high"]
            conf_label = f"{conf_val:.2%}  ✓ High"
        elif conf_val >= 0.55:
            conf_style = s["confidence_mid"]
            conf_label = f"{conf_val:.2%}  ⚠ Medium"
        else:
            conf_style = s["confidence_low"]
            conf_label = f"{conf_val:.2%}  ✗ Low"

        half = self.COL_W / 2

        data = [
            # Header row
            [
                Paragraph("PROPERTY",       s["table_header"]),
                Paragraph("VALUE",          s["table_header"]),
                Paragraph("PROPERTY",       s["table_header"]),
                Paragraph("VALUE",          s["table_header"]),
            ],
            # Row 1
            [
                Paragraph("File Name",      s["table_cell_bold"]),
                Paragraph(parsed.file_name[:40], s["table_cell"]),
                Paragraph("Document Type",  s["table_cell_bold"]),
                Paragraph(parsed.document_type.capitalize(), s["table_cell"]),
            ],
            # Row 2
            [
                Paragraph("OCR Confidence", s["table_cell_bold"]),
                Paragraph(conf_label,       conf_style),
                Paragraph("Total Pages",    s["table_cell_bold"]),
                Paragraph(str(parsed.total_pages), s["table_cell"]),
            ],
            # Row 3
            [
                Paragraph("Parsed At",      s["table_cell_bold"]),
                Paragraph(parsed.parsed_at[:19].replace("T", "  "), s["table_cell"]),
                Paragraph("Fields Found",   s["table_cell_bold"]),
                Paragraph(str(len(parsed.fields)), s["table_cell"]),
            ],
        ]

        col_widths = [half * 0.35, half * 0.65, half * 0.35, half * 0.65]

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(_metadata_table_style())

        return [
            Paragraph("Document Overview", self.styles["section_header"]),
            HRFlowable(width="100%", thickness=0.5, color=ACCENT_BLUE, spaceAfter=6),
            table,
        ]

    def _build_fields(self, parsed: ParsedDocument) -> list:
        """Extracted key-value fields rendered as a proper table."""
        s = self.styles
        elements = [
            Spacer(1, 4 * mm),
            Paragraph("Extracted Fields", s["section_header"]),
            HRFlowable(width="100%", thickness=0.5, color=ACCENT_BLUE, spaceAfter=6),
        ]

        if not parsed.fields:
            empty = Table(
                [["  No structured fields were extracted from this document."]],
                colWidths=[self.COL_W]
            )
            empty.setStyle(_empty_table_style())
            elements.append(empty)
            return elements

        col_w = [self.COL_W * 0.30, self.COL_W * 0.70]

        data = [[
            Paragraph("FIELD",  s["table_header"]),
            Paragraph("VALUE",  s["table_header"]),
        ]]

        for key, value in parsed.fields.items():
            label = key.replace("_", " ").title()
            val   = str(value)
            data.append([
                Paragraph(label, s["table_cell_bold"]),
                Paragraph(val,   s["table_cell"]),      # Auto-wraps long values
            ])

        table = Table(data, colWidths=col_w, repeatRows=1)
        table.setStyle(_data_table_style())
        elements.append(table)
        return elements

    def _build_line_items(self, parsed: ParsedDocument) -> list:
        """Line items rendered as a description + amount table."""
        s = self.styles
        elements = [
            Spacer(1, 4 * mm),
            Paragraph("Line Items", s["section_header"]),
            HRFlowable(width="100%", thickness=0.5, color=ACCENT_BLUE, spaceAfter=6),
        ]

        if not parsed.line_items:
            empty = Table(
                [["  No line items were detected in this document."]],
                colWidths=[self.COL_W]
            )
            empty.setStyle(_empty_table_style())
            elements.append(empty)
            return elements

        col_w = [self.COL_W * 0.55, self.COL_W * 0.25, self.COL_W * 0.20]

        data = [[
            Paragraph("DESCRIPTION", s["table_header"]),
            Paragraph("AMOUNT",      s["table_header"]),
            Paragraph("PAGE",        s["table_header"]),
        ]]

        for item in parsed.line_items:
            data.append([
                Paragraph(str(item.get("description", "")), s["table_cell"]),
                Paragraph(str(item.get("amount", "")),      s["table_cell"]),
                Paragraph(str(item.get("page", "")),        s["table_cell"]),
            ])

        table = Table(data, colWidths=col_w, repeatRows=1)
        table.setStyle(_data_table_style())
        elements.append(table)
        return elements

    def _build_raw_text(self, parsed: ParsedDocument) -> list:
        """Raw OCR text rendered line by line in monospace font."""
        s = self.styles
        elements = [
            Spacer(1, 4 * mm),
            Paragraph("Raw OCR Text", s["section_header"]),
            HRFlowable(width="100%", thickness=0.5, color=ACCENT_BLUE, spaceAfter=6),
        ]

        if not parsed.raw_text.strip():
            elements.append(Paragraph("No raw text available.", s["table_cell"]))
            return elements

        # Render each line as a separate Paragraph
        # This ensures proper wrapping and no overflow
        lines = parsed.raw_text.split("\n")
        for line in lines:
            text = line.strip() if line.strip() else " "
            # Escape XML special characters for ReportLab
            text = (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            elements.append(Paragraph(text, s["raw_text"]))

        return elements