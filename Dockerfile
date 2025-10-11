# Base image
FROM python:3.11-slim AS base
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential python3-dev gcc libffi-dev libssl-dev libpq-dev wget \
 && pip install --upgrade pip \
 && pip config set global.timeout 120 \
 && pip config set global.retries 10

# Install Python dependencies (cached if requirements.txt doesn't change)
FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development image
FROM deps AS dev
# Copy code (volume mount will override during dev)
COPY . .

# CMD is overridden by docker-compose to enable --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
