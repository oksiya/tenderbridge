# Base image
FROM python:3.11-slim AS base
WORKDIR /code

RUN apt-get update && apt-get install -y build-essential python3-dev gcc libffi-dev libssl-dev libpq-dev wget \
 && pip install --upgrade pip \
 && pip config set global.timeout 120 \
 && pip config set global.retries 10

# Dependencies
FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development image
FROM deps AS dev
COPY . .

# Default command (API)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
