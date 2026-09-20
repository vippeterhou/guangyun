FROM python:3.13-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV GUANGYUN_DB=/app/data/processed/guangyun.sqlite

WORKDIR /app
COPY --from=builder /install /usr/local
COPY data/processed/guangyun.sqlite ./data/processed/guangyun.sqlite
COPY data/sources.json DATA_LICENSE.md THIRD_PARTY_NOTICES.md ./
COPY LICENSES ./LICENSES

EXPOSE 8000
CMD ["uvicorn", "guangyun.main:app", "--host", "0.0.0.0", "--port", "8000"]
