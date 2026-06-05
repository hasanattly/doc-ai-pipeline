# 🧾 Document AI Pipeline

An end-to-end Document AI and OCR Data Pipeline that extracts structured data
from scanned PDFs and images using computer vision and machine learning.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)
![EasyOCR](https://img.shields.io/badge/OCR-EasyOCR-green)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📌 Project Overview

This pipeline accepts scanned documents (PDFs or images) and automatically:

1. **Preprocesses** the image using OpenCV (grayscale, denoise, deskew)
2. **Extracts text** using EasyOCR with confidence scoring
3. **Parses structure** — detects document type and extracts key fields
4. **Stores results** in a SQLite database via SQLAlchemy ORM
5. **Presents results** via a Streamlit UI with export options

---

## 🏗️ Architecture
Input (PDF/Image)

│
▼
┌─────────────────┐
│ ImageProcessor  │  OpenCV — grayscale, denoise, deskew, quality detection
└────────┬────────┘

│
▼
┌─────────────────┐
│   OCREngine     │  EasyOCR — text blocks, bounding boxes, confidence scores
└────────┬────────┘
│
▼
┌─────────────────┐
│ DocumentParser  │  Regex + keyword — type detection, field extraction
└────────┬────────┘

│
▼
┌─────────────────┐
│ StorageManager  │  SQLAlchemy ORM → SQLite (documents, fields, line_items)
└────────┬────────┘
│
▼
┌─────────────────┐
│  Streamlit UI   │  Upload, process, visualize, export (JSON/CSV/TXT/PDF)
└─────────────────┘
---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| OCR Engine | EasyOCR 1.7 | Text extraction with confidence scoring |
| Image Processing | OpenCV 4.9 | Preprocessing, deskewing, quality detection |
| PDF Handling | PyMuPDF (fitz) | PDF → image conversion at 300 DPI |
| Data Parsing | Python Regex | Field extraction, document classification |
| Storage | SQLite + SQLAlchemy | Structured data persistence |
| UI | Streamlit | Interactive web interface |
| PDF Export | ReportLab | Professional report generation |
| Containerization | Docker + Compose | Reproducible environment |
| Logging | Loguru | Production-grade observability |

---

## 📁 Project Structure
doc-ai-pipeline/
│
├── docker/
│   └── Dockerfile              # Python 3.11-slim + system deps
├── src/
│   ├── preprocessor/
│   │   └── image_processor.py  # OpenCV preprocessing pipeline
│   ├── ocr/
│   │   └── ocr_engine.py       # EasyOCR wrapper with structured output
│   ├── parser/
│   │   └── document_parser.py  # Type detection + field extraction
│   ├── storage/
│   │   ├── database.py         # SQLAlchemy ORM models
│   │   └── storage_manager.py  # DB read/write operations
│   └── ui/
│       ├── app.py              # Streamlit frontend
│       └── pdf_exporter.py     # ReportLab PDF generator
├── data/
│   ├── input/                  # Place input PDFs/images here
│   └── output/                 # JSON/CSV outputs saved here
├── db/                         # SQLite database
├── docker-compose.yml
├── requirements.txt
└── README.md

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- 6GB RAM allocated to Docker

### Run the Pipeline

```bash
# Clone the repository
git clone https://github.com/hasanattly/doc-ai-pipeline.git
cd doc-ai-pipeline

# Build and start
docker-compose build
docker-compose up -d

# Open the UI
# Visit http://localhost:8501
```

### First Run Note
EasyOCR downloads model weights (~100MB) on first startup.
This takes 2-3 minutes. Subsequent starts are instant.

---

## 📊 Supported Document Types

| Type | Fields Extracted |
|---|---|
| Invoice | Invoice number, date, bill-to, line items, total |
| Receipt | Items, amounts, tax, total |
| Letter | Sender, salutation, date, recipient |
| General | Dates, amounts, emails, phone numbers |

---

## 📤 Export Formats

- **JSON** — Full structured extraction with metadata
- **CSV** — Line items or key-value fields
- **TXT** — Plain text report
- **PDF** — Professional formatted report via ReportLab

---

## 🗄️ Database Schema

```sql
documents        -- Master document record
extracted_fields -- Key-value pairs per document
line_items       -- Table rows with amounts
```

---

## 🧠 Key Engineering Decisions

- **Adaptive preprocessing** — quality score determines pipeline intensity
- **Dataclass-based DTOs** — clean data flow between modules
- **ORM over raw SQL** — SQLAlchemy enables easy DB migration
- **Docker volumes** — live code sync without rebuilds
- **@st.cache_resource** — EasyOCR model loads once, not per request

---

## 📄 License

MIT License — free to use and modify.

---

Built as a portfolio project targeting AI/ML and Data Engineering roles.
