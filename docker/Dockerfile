# ── Base Image ───────────────────────────────────────
FROM python:3.11-slim

# ── Metadata ─────────────────────────────────────────
LABEL maintainer="your-name"
LABEL project="doc-ai-pipeline"

# ── System Dependencies ───────────────────────────────
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
# ── Working Directory ─────────────────────────────────
WORKDIR /app

# ── Install Python Dependencies ───────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy Project Code ─────────────────────────────────
COPY . .

# ── Expose Streamlit Port ─────────────────────────────
EXPOSE 8501

# ── Default Command ───────────────────────────────────
CMD ["streamlit", "run", "src/ui/app.py", "--server.address=0.0.0.0"]