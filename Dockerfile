
FROM python:3.12-slim

# Python configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Application directory
WORKDIR /app

# Create non-root application user
RUN groupadd --system app && \
    useradd --system --gid app --create-home app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project configuration
COPY pytest.ini .
COPY alembic.ini .

# Copy application source
COPY db ./db
COPY api ./api
COPY app ./app
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests

# Run as non-root user
USER app

# API port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
