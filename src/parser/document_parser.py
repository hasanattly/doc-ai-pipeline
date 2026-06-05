# src/parser/document_parser.py

import re
import json
import csv
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from loguru import logger
import sys
sys.path.append("/app/src")
from ocr.ocr_engine import DocumentResult


# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

@dataclass
class ParsedDocument:
    """
    Final structured output of the entire pipeline.
    This is what gets saved to JSON, CSV, and the database.
    """
    file_name:        str
    document_type:    str
    parsed_at:        str
    fields:           dict = field(default_factory=dict)
    line_items:       list = field(default_factory=list)
    raw_text:         str  = ""
    total_pages:      int  = 1
    confidence_score: float = 0.0


# ──────────────────────────────────────────────
# DOCUMENT PARSER
# ──────────────────────────────────────────────

class DocumentParser:
    """
    Parses a DocumentResult (from OCREngine) into structured data.
    Automatically detects document type and extracts relevant fields.
    Outputs JSON and CSV files to /app/data/output/
    """

    OUTPUT_DIR = Path("/app/data/output")

    # ── Regex Patterns ────────────────────────────────
    PATTERNS = {
        # Dates: 12/01/2024, 2024-01-12
        "date": r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})\b",

        # Currency amounts: $1,500.00
        "amount": r"\$\s?[\d,]+(?:\.\d{2})?",

        # Invoice numbers
        "invoice_number": r"(?:Invoice\s*#\s*|INV-)([A-Z0-9\-]+)",

        # Email addresses
        "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b",

        # Phone numbers
        "phone": r"\b(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b",

        # Percentages
        "percentage": r"\b\d+(?:\.\d+)?%",
    }

    # ── Document Type Keywords ─────────────────────────
    DOC_TYPE_KEYWORDS = {
        "invoice": ["invoice", "inv-", "bill to", "payment due", "subtotal"],
        "receipt": ["receipt", "thank you", "change", "cash", "card payment"],
        "form":    ["form", "signature", "please fill", "checkbox", "applicant"],
        "letter":  ["dear", "yours faithfully", "yours sincerely", "regards",
                    "sincerely", "to whom it may concern"],
    }

    def __init__(self):
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("DocumentParser initialized")

    # ──────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ──────────────────────────────────────────────

    def parse(self, document: DocumentResult) -> ParsedDocument:
        """
        Main method. Accepts a DocumentResult from OCREngine.
        Returns a fully structured ParsedDocument.
        """
        logger.info(f"Parsing document: {document.file_name}")

        full_text = document.full_text
        doc_type  = self._detect_document_type(full_text)
        fields    = self._extract_fields(full_text, doc_type)
        avg_conf  = self._get_avg_confidence(document)

        parsed = ParsedDocument(
            file_name        = document.file_name,
            document_type    = doc_type,
            parsed_at        = datetime.utcnow().isoformat(),
            fields           = fields,
            line_items       = self._extract_line_items(document),
            raw_text         = full_text,
            total_pages      = document.total_pages,
            confidence_score = avg_conf,
        )

        logger.success(
            f"Parsed as '{doc_type}' — "
            f"{len(fields)} fields | "
            f"{len(parsed.line_items)} line items"
        )
        return parsed

    # ──────────────────────────────────────────────
    # DOCUMENT TYPE DETECTION
    # ──────────────────────────────────────────────

    def _detect_document_type(self, text: str) -> str:
        """
        Detects document type by scoring keyword matches.
        Returns the type with the highest keyword hit count.
        Defaults to 'general' if no strong match found.
        """
        text_lower = text.lower()
        scores = {doc_type: 0 for doc_type in self.DOC_TYPE_KEYWORDS}

        for doc_type, keywords in self.DOC_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[doc_type] += 1

        best_type  = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score == 0:
            logger.info("Document type: general (no strong keyword match)")
            return "general"

        logger.info(f"Document type detected: '{best_type}' (score={best_score})")
        return best_type

    # ──────────────────────────────────────────────
    # FIELD EXTRACTION
    # ──────────────────────────────────────────────

    def _extract_fields(self, text: str, doc_type: str) -> dict:
        """
        Extracts structured key-value fields from raw text.
        Runs universal patterns + document-type-specific rules.
        """
        fields = {}

        # ── Universal fields (all document types) ──
        dates = re.findall(self.PATTERNS["date"], text)
        if dates:
            fields["dates"] = list(set(dates))

        amounts = re.findall(self.PATTERNS["amount"], text)
        if amounts:
            fields["amounts"]    = list(set(amounts))
            fields["max_amount"] = max(
                amounts,
                key=lambda x: float(x.replace("$", "").replace(",", ""))
            )

        emails = re.findall(self.PATTERNS["email"], text)
        if emails:
            fields["emails"] = list(set(emails))

        phones = re.findall(self.PATTERNS["phone"], text)
        if phones:
            fields["phones"] = list(set(phones))

        # ── Invoice-specific fields ──
        if doc_type == "invoice":
            inv_match = re.search(
                self.PATTERNS["invoice_number"], text, re.IGNORECASE
            )
            if inv_match:
                fields["invoice_number"] = inv_match.group(1).strip()

            total_match = re.search(
                r"(?:total\s*due|total)[:\s]+(\$[\d,]+(?:\.\d{2})?)",
                text, re.IGNORECASE
            )
            if total_match:
                fields["total_due"] = total_match.group(1)

            bill_match = re.search(
                r"bill\s*to[:\s]+([A-Za-z\s]+)",
                text, re.IGNORECASE
            )
            if bill_match:
                fields["bill_to"] = bill_match.group(1).strip()

        # ── Receipt-specific fields ──
        elif doc_type == "receipt":
            tax_match = re.search(
                r"tax[:\s]+(\$[\d,]+(?:\.\d{2})?)",
                text, re.IGNORECASE
            )
            if tax_match:
                fields["tax"] = tax_match.group(1)

        # ── Letter-specific fields ──
        elif doc_type == "letter":

            # Sender name from sign-off
            signoff_match = re.search(
                r"(?:yours\s+(?:faithfully|sincerely)|regards)"
                r"[,\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                text, re.IGNORECASE
            )
            if signoff_match:
                fields["sender_name"] = signoff_match.group(1).strip()

            # Dear X salutation
            dear_match = re.search(
                r"Dear\s+([A-Za-z\s\/]+)[;,:]",
                text
            )
            if dear_match:
                fields["salutation"] = dear_match.group(1).strip()

            # Written date: Tuesday 20th October 2020
            written_date = re.search(
                r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
                r"\s+\d{1,2}(?:st|nd|rd|th)?\s+"
                r"(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{4}",
                text, re.IGNORECASE
            )
            if written_date:
                fields["document_date"] = written_date.group(0).strip()

            # Postcode-like patterns
            postcode_matches = re.findall(r"[A-Z]{2,}\s?[A-Z]{2,}\d+", text)
            if postcode_matches:
                fields["postcodes_found"] = list(set(postcode_matches))

            # Recipient organization (line after "The Manager" or "To:")
            recipient_match = re.search(
                r"(?:The Manager|To:?)\s+([A-Za-z\s\']+(?:Eatery|Ltd|Inc|Co|"
                r"Company|Restaurant|Hotel|School|Hospital)?)",
                text
            )
            if recipient_match:
                fields["recipient_org"] = recipient_match.group(1).strip()

        # ── General document fields ──
        else:
            # Still try to extract sender and date for unknown doc types
            signoff_match = re.search(
                r"(?:yours\s+(?:faithfully|sincerely)|regards)"
                r"[,\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                text, re.IGNORECASE
            )
            if signoff_match:
                fields["sender_name"] = signoff_match.group(1).strip()

            written_date = re.search(
                r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
                r"\s+\d{1,2}(?:st|nd|rd|th)?\s+"
                r"(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{4}",
                text, re.IGNORECASE
            )
            if written_date:
                fields["document_date"] = written_date.group(0).strip()

        return fields

    # ──────────────────────────────────────────────
    # LINE ITEM EXTRACTION
    # ──────────────────────────────────────────────

    def _extract_line_items(self, document: DocumentResult) -> list:
        """
        Extracts table-like line items by detecting rows that contain
        both a description and a monetary amount on the same line.
        """
        line_items = []

        for page in document.pages:
            rows = {}
            for block in page.blocks:
                row_key = block.y_min // 20
                if row_key not in rows:
                    rows[row_key] = []
                rows[row_key].append(block)

            for row_key in sorted(rows.keys()):
                row_blocks = sorted(rows[row_key], key=lambda b: b.x_min)
                row_text   = " ".join([b.text for b in row_blocks])

                amounts = re.findall(self.PATTERNS["amount"], row_text)
                if amounts and len(row_text.strip()) > len(amounts[0]):
                    description = re.sub(
                        self.PATTERNS["amount"], "", row_text
                    ).strip()
                    if description:
                        line_items.append({
                            "description": description,
                            "amount":      amounts[-1],
                            "page":        page.page_number,
                        })

        return line_items

    # ──────────────────────────────────────────────
    # HELPER
    # ──────────────────────────────────────────────

    def _get_avg_confidence(self, document: DocumentResult) -> float:
        """Calculates average OCR confidence across all pages."""
        scores = [p.avg_confidence for p in document.pages if p.avg_confidence > 0]
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    # ──────────────────────────────────────────────
    # OUTPUT — JSON & CSV
    # ──────────────────────────────────────────────

    def save_json(self, parsed: ParsedDocument) -> Path:
        """Saves ParsedDocument to a JSON file in /app/data/output/"""
        stem     = Path(parsed.file_name).stem
        out_path = self.OUTPUT_DIR / f"{stem}_parsed.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(asdict(parsed), f, indent=2, ensure_ascii=False)

        logger.success(f"JSON saved → {out_path}")
        return out_path

    def save_csv(self, parsed: ParsedDocument) -> Path:
        """
        Saves line items to CSV.
        Falls back to key-value fields if no line items found.
        """
        stem     = Path(parsed.file_name).stem
        out_path = self.OUTPUT_DIR / f"{stem}_parsed.csv"

        if parsed.line_items:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["description", "amount", "page"]
                )
                writer.writeheader()
                writer.writerows(parsed.line_items)
        else:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["field", "value"])
                for key, value in parsed.fields.items():
                    writer.writerow([key, value])

        logger.success(f"CSV saved → {out_path}")
        return out_path