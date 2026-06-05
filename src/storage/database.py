# src/storage/database.py

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
from pathlib import Path
from loguru import logger

# ──────────────────────────────────────────────
# DATABASE SETUP
# ──────────────────────────────────────────────

DB_PATH = Path("/app/db/pipeline.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine       = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()


# ──────────────────────────────────────────────
# TABLE SCHEMAS
# ──────────────────────────────────────────────

class Document(Base):
    """
    Master table — one row per processed document.
    Stores metadata and the full raw OCR text.
    """
    __tablename__ = "documents"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    file_name        = Column(String(255), nullable=False)
    document_type    = Column(String(50))       # invoice / receipt / form / general
    parsed_at        = Column(DateTime, default=datetime.utcnow)
    total_pages      = Column(Integer, default=1)
    confidence_score = Column(Float, default=0.0)
    raw_text         = Column(Text)

    # Relationships — one document has many fields and line items
    fields     = relationship("ExtractedField", back_populates="document",
                              cascade="all, delete-orphan")
    line_items = relationship("LineItem", back_populates="document",
                              cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document id={self.id} type={self.document_type} file={self.file_name}>"


class ExtractedField(Base):
    """
    Stores each extracted key-value field as a separate row.
    Flexible schema — works for any document type.
    """
    __tablename__ = "extracted_fields"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    field_name  = Column(String(100))    # e.g. "invoice_number", "total_due"
    field_value = Column(Text)           # e.g. "INV-2024-001", "$1,500.00"

    document = relationship("Document", back_populates="fields")

    def __repr__(self):
        return f"<Field {self.field_name}={self.field_value}>"


class LineItem(Base):
    """
    Stores table rows extracted from documents.
    Each row = one product/service line from an invoice or receipt.
    """
    __tablename__ = "line_items"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    description = Column(Text)
    amount      = Column(String(50))
    page_number = Column(Integer, default=1)

    document = relationship("Document", back_populates="line_items")

    def __repr__(self):
        return f"<LineItem {self.description} {self.amount}>"


# ──────────────────────────────────────────────
# CREATE ALL TABLES
# ──────────────────────────────────────────────

def init_db():
    """Creates all tables if they don't already exist."""
    Base.metadata.create_all(engine)
    logger.success(f"Database initialized → {DB_PATH}")