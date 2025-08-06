# ================================
# Dockerfile ajustado para Streamlit + OCR + ChromaDB
# ================================

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    netcat-openbsd \
    ca-certificates \
    curl \
    gnupg \
    xvfb \
    xauth \
    x11-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip uninstall -y numpy || true \
 && pip install numpy==1.24.4 \
 && pip install chromadb==0.4.22 \
 && pip install -r requirements.txt

# Patch de compatibilidade do ChromaDB
RUN python -c "import os; p='/usr/local/lib/python3.11/site-packages/chromadb/api/types.py'; t=open(p).read(); open(p, 'w').write(t.replace('np.float_', 'np.float64'))" || echo "⚠️ Patch não necessário"

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/interface.py", "--server.port=8501", "--server.address=0.0.0.0"]
