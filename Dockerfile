# ── Build stage ────────────────────────────────────────
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Dependências ──────────────────────────────────────
COPY pyproject.toml ./
RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir uvicorn[standard]

# ── Código-fonte ──────────────────────────────────────
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
