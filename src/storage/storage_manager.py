# src/storage/storage_manager.py

from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
import sys
sys.path.append("/app/src")

from storage.database import (
    SessionLocal, init_db,
    Document, ExtractedField, LineItem
)
from parser.document_parser import ParsedDocument


class StorageManager:
    """
    Handles all database read/write operations.
    Translates ParsedDocument objects into database rows.
    """

    def __init__(self):
        init_db()
        logger.info("StorageManager ready")

    # ──────────────────────────────────────────────
    # WRITE
    # ──────────────────────────────────────────────

    def save(self, parsed: ParsedDocument) -> int:
        """
        Saves a fully parsed document to the database.
        Inserts into documents, extracted_fields, and line_items tables.

        Returns:
            document_id: The ID of the inserted document row
        """
        session: Session = SessionLocal()

        try:
            # ── Insert master document row ──
            doc = Document(
                file_name        = parsed.file_name,
                document_type    = parsed.document_type,
                parsed_at        = datetime.fromisoformat(parsed.parsed_at),
                total_pages      = parsed.total_pages,
                confidence_score = parsed.confidence_score,
                raw_text         = parsed.raw_text,
            )
            session.add(doc)
            session.flush()  # Get doc.id before committing

            # ── Insert extracted fields ──
            for field_name, field_value in parsed.fields.items():
                # Convert lists to comma-separated strings for storage
                if isinstance(field_value, list):
                    field_value = ", ".join(str(v) for v in field_value)

                ef = ExtractedField(
                    document_id = doc.id,
                    field_name  = str(field_name),
                    field_value = str(field_value),
                )
                session.add(ef)

            # ── Insert line items ──
            for item in parsed.line_items:
                li = LineItem(
                    document_id = doc.id,
                    description = item.get("description", ""),
                    amount      = item.get("amount", ""),
                    page_number = item.get("page", 1),
                )
                session.add(li)

            session.commit()
            doc_id = doc.id
            logger.success(
                f"Saved to DB → Document ID={doc_id} | "
                f"{len(parsed.fields)} fields | "
                f"{len(parsed.line_items)} line items"
            )
            return doc_id

        except Exception as e:
            session.rollback()
            logger.error(f"Database save failed: {e}")
            raise
        finally:
            session.close()

    # ──────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────

    def get_all_documents(self) -> list:
        """Returns summary of all documents in the database."""
        session = SessionLocal()
        try:
            docs = session.query(Document).all()
            results = []
            for doc in docs:
                results.append({
                    "id":               doc.id,
                    "file_name":        doc.file_name,
                    "document_type":    doc.document_type,
                    "parsed_at":        str(doc.parsed_at),
                    "confidence_score": doc.confidence_score,
                    "total_pages":      doc.total_pages,
                })
            return results
        finally:
            session.close()

    def get_document_by_id(self, doc_id: int) -> dict:
        """Returns full document details including fields and line items."""
        session = SessionLocal()
        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                return {}
            return {
                "id":               doc.id,
                "file_name":        doc.file_name,
                "document_type":    doc.document_type,
                "parsed_at":        str(doc.parsed_at),
                "confidence_score": doc.confidence_score,
                "raw_text":         doc.raw_text,
                "fields":           {f.field_name: f.field_value for f in doc.fields},
                "line_items":       [
                    {"description": li.description, "amount": li.amount}
                    for li in doc.line_items
                ],
            }
        finally:
            session.close()

    def get_documents_by_type(self, doc_type: str) -> list:
        """Returns all documents of a specific type."""
        session = SessionLocal()
        try:
            docs = session.query(Document).filter(
                Document.document_type == doc_type
            ).all()
            return [{"id": d.id, "file_name": d.file_name} for d in docs]
        finally:
            session.close()