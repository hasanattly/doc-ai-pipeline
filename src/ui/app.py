# src/ui/app.py

import streamlit as st
import sys
import json
import pandas as pd
from pathlib import Path
import tempfile

sys.path.append("/app/src")

from preprocessor.image_processor import ImageProcessor
from ocr.ocr_engine import OCREngine
from parser.document_parser import DocumentParser
from storage.storage_manager import StorageManager
from ui.pdf_exporter import PDFExporter

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title = "Document AI Pipeline",
    page_icon  = "🧾",
    layout     = "wide"
)

# ──────────────────────────────────────────────
# INIT PIPELINE (cached — loads only once)
# ──────────────────────────────────────────────

@st.cache_resource
def load_pipeline():
    processor = ImageProcessor(dpi=300)
    engine    = OCREngine(languages=["en"], gpu=False)
    parser    = DocumentParser()
    storage   = StorageManager()
    return processor, engine, parser, storage

processor, engine, parser, storage = load_pipeline()

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/document.png", width=80)
    st.title("Document AI")
    st.caption("OCR + Data Pipeline")
    st.divider()
    page = st.radio(
        "Navigate",
        ["📤 Upload & Process", "📂 Document History"]
    )
    st.divider()
    st.markdown("**Pipeline Modules**")
    st.caption("🔍 OpenCV Preprocessor")
    st.caption("🤖 EasyOCR Engine")
    st.caption("🧠 Document Parser")
    st.caption("💾 SQLite Storage")
    st.divider()
    st.caption("Built with EasyOCR · OpenCV · SQLite · Streamlit")

# ──────────────────────────────────────────────
# PAGE 1 — UPLOAD & PROCESS
# ──────────────────────────────────────────────

if page == "📤 Upload & Process":

    st.title("📤 Upload Document")
    st.write("Upload a scanned PDF or image to extract and structure its data.")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif"]
    )

    if uploaded_file:
        st.divider()

        # ── Save uploaded file to temp location ──
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        # ── Layout: preview left, pipeline right ──
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("📄 Uploaded File")
            if suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]:
                st.image(tmp_path, use_column_width=True)
            else:
                st.info(f"📄 PDF uploaded: **{uploaded_file.name}**")
                st.caption(f"Size: {uploaded_file.size / 1024:.1f} KB")

        with col2:
            st.subheader("⚙️ Pipeline Execution")

            with st.status("Running pipeline...", expanded=True) as status:

                # ── Step 1: Preprocess ──
                st.write("🔍 **Step 1** — Preprocessing image...")
                images = processor.process(tmp_path)
                st.write(f"✅ {len(images)} page(s) preprocessed")

                # ── Step 2: OCR ──
                st.write("🤖 **Step 2** — Running EasyOCR...")
                ocr_result = engine.extract(images, file_name=uploaded_file.name)
                avg_conf   = ocr_result.pages[0].avg_confidence
                total_blocks = ocr_result.pages[0].total_blocks
                st.write(
                    f"✅ OCR complete — "
                    f"**{total_blocks}** blocks detected | "
                    f"confidence: **{avg_conf:.2%}**"
                )

                # ── Step 3: Parse ──
                st.write("🧠 **Step 3** — Parsing document structure...")
                parsed = parser.parse(ocr_result)
                st.write(
                    f"✅ Detected: **{parsed.document_type.upper()}** | "
                    f"**{len(parsed.fields)}** fields | "
                    f"**{len(parsed.line_items)}** line items"
                )

                # ── Step 4: Save ──
                st.write("💾 **Step 4** — Saving to SQLite database...")
                doc_id = storage.save(parsed)
                st.write(f"✅ Saved successfully — Document ID: **{doc_id}**")

                status.update(
                    label  = "✅ Pipeline complete!",
                    state  = "complete",
                    expanded = False
                )

        # ── Confidence Meter ──
        st.divider()
        conf_color = (
            "green"  if avg_conf >= 0.80 else
            "orange" if avg_conf >= 0.55 else
            "red"
        )
        st.markdown(f"**OCR Confidence Score:** :{conf_color}[{avg_conf:.2%}]")
        st.progress(avg_conf)

        # ── Results Tabs ──
        st.divider()
        st.subheader("📊 Extracted Results")

        tab1, tab2, tab3 = st.tabs(["🏷️ Fields", "📋 Line Items", "📝 Raw Text"])

        with tab1:
            if parsed.fields:
                fields_df = pd.DataFrame(
                    [(k.replace("_", " ").title(), str(v))
                     for k, v in parsed.fields.items()],
                    columns=["Field", "Value"]
                )
                st.dataframe(fields_df, use_container_width=True, hide_index=True)
            else:
                st.info(
                    "No structured fields extracted. "
                    "This is expected for general documents without "
                    "invoices, dates, or amounts."
                )

        with tab2:
            if parsed.line_items:
                items_df = pd.DataFrame(parsed.line_items)
                st.dataframe(items_df, use_container_width=True, hide_index=True)
            else:
                st.info(
                    "No line items detected. "
                    "Line items are extracted from invoices and receipts "
                    "containing monetary amounts."
                )

        with tab3:
            st.text_area(
                "Full OCR Text (line-by-line)",
                parsed.raw_text,
                height=300
            )

        # ── Download Section ──
        st.divider()
        st.subheader("⬇️ Download Results")
        st.caption("Export your extracted data in any format.")

        # ── Generate all export formats ──
        json_path = parser.save_json(parsed)
        csv_path  = parser.save_csv(parsed)

        txt_content = f"""DOCUMENT AI PIPELINE — EXPORT
{'='*50}
File          : {parsed.file_name}
Document Type : {parsed.document_type}
Parsed At     : {parsed.parsed_at}
Confidence    : {parsed.confidence_score:.2%}
Pages         : {parsed.total_pages}

EXTRACTED FIELDS
{'='*50}
{chr(10).join(f"{k:20s}: {v}" for k, v in parsed.fields.items()) or "None detected"}

LINE ITEMS
{'='*50}
{chr(10).join(f"{i['description']:40s} {i['amount']}" for i in parsed.line_items) or "None detected"}

RAW OCR TEXT
{'='*50}
{parsed.raw_text}
"""

        pdf_bytes = PDFExporter().generate(parsed)

        # ── 4 Download Buttons ──
        col3, col4, col5, col6 = st.columns(4)

        with col3:
            with open(json_path) as f:
                st.download_button(
                    label              = "📥 JSON",
                    data               = f.read(),
                    file_name          = json_path.name,
                    mime               = "application/json",
                    use_container_width= True
                )
            st.caption("Structured data")

        with col4:
            with open(csv_path) as f:
                st.download_button(
                    label              = "📥 CSV",
                    data               = f.read(),
                    file_name          = csv_path.name,
                    mime               = "text/csv",
                    use_container_width= True
                )
            st.caption("Spreadsheet format")

        with col5:
            st.download_button(
                label              = "📥 TXT Report",
                data               = txt_content,
                file_name          = f"{Path(parsed.file_name).stem}_report.txt",
                mime               = "text/plain",
                use_container_width= True
            )
            st.caption("Plain text export")

        with col6:
            st.download_button(
                label              = "📥 PDF Report",
                data               = bytes(pdf_bytes),
                file_name          = f"{Path(parsed.file_name).stem}_report.pdf",
                mime               = "application/pdf",
                use_container_width= True
            )
            st.caption("Professional report")

# ──────────────────────────────────────────────
# PAGE 2 — DOCUMENT HISTORY
# ──────────────────────────────────────────────

elif page == "📂 Document History":

    st.title("📂 Document History")
    st.write("All documents processed and stored in the database.")

    docs = storage.get_all_documents()

    if not docs:
        st.info(
            "No documents processed yet. "
            "Go to **Upload & Process** to get started."
        )

    else:
        # ── Summary Metrics ──
        total     = len(docs)
        avg_conf  = sum(d["confidence_score"] for d in docs) / total
        doc_types = len(set(d["document_type"] for d in docs))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Documents", total)
        col2.metric("Avg Confidence",  f"{avg_conf:.2%}")
        col3.metric("Document Types",  doc_types)
        col4.metric("Total Pages",     sum(d["total_pages"] for d in docs))

        st.divider()

        # ── Filter by document type ──
        all_types  = ["All"] + sorted(set(d["document_type"] for d in docs))
        filter_type = st.selectbox("Filter by document type", all_types)

        filtered = (
            docs if filter_type == "All"
            else [d for d in docs if d["document_type"] == filter_type]
        )

        # ── Documents Table ──
        df = pd.DataFrame(filtered)
        df["confidence_score"] = df["confidence_score"].apply(lambda x: f"{x:.2%}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Document Detail Viewer ──
        st.divider()
        st.subheader("🔍 View Document Detail")

        doc_ids     = [d["id"] for d in filtered]
        selected_id = st.selectbox("Select Document ID", doc_ids)

        if selected_id:
            detail = storage.get_document_by_id(selected_id)

            # Metadata row
            m1, m2, m3 = st.columns(3)
            m1.metric("Document Type",  detail["document_type"].capitalize())
            m2.metric("Confidence",     f"{detail['confidence_score']:.2%}")
            m3.metric("Parsed At",      detail["parsed_at"][:10])

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.write("**🏷️ Extracted Fields**")
                if detail["fields"]:
                    st.dataframe(
                        pd.DataFrame(
                            [(k.replace("_"," ").title(), str(v))
                             for k, v in detail["fields"].items()],
                            columns=["Field", "Value"]
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No fields extracted.")

            with col2:
                st.write("**📋 Line Items**")
                if detail["line_items"]:
                    st.dataframe(
                        pd.DataFrame(detail["line_items"]),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No line items detected.")

            st.divider()
            st.write("**📝 Raw OCR Text**")
            st.text_area(
                "",
                detail["raw_text"],
                height=250,
                key="history_raw_text"
            )