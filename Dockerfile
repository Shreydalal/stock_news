# ==========================================
# Stage 1: Build Dependencies
# ==========================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install compiler dependencies if needed (e.g. for psycopg2 build from source)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies to a local folder
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Runtime Production Environment
# ==========================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install postgres client libraries for psycopg2 runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder stage
COPY --from=builder /root/.local /root/.local
COPY --from=builder /build/requirements.txt .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Copy project source code
COPY app/ /app/app/

# Create logs and reports directory
RUN mkdir -p /app/logs /app/reports

# Expose port
EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
