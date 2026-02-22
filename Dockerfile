FROM python:3.11-slim

WORKDIR /app

# System dependencies for vision pipeline and document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

COPY src/ src/
COPY data/ data/

EXPOSE 8000

CMD ["python", "-m", "src.agents.crew"]
