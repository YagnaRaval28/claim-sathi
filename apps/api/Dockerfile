# ClaimSathi API/worker image. Build context: repository root.
FROM python:3.12-slim-bookworm

# WeasyPrint needs Pango/HarfBuzz. Noto fonts cover Latin, Gujarati and Devanagari for letters.
# Tesseract reads photos and scans inside this container (FR-010): free, and documents never leave it.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
      fonts-noto-core tesseract-ocr tesseract-ocr-guj tesseract-ocr-hin curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv

WORKDIR /app/apps/api
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-install-project

COPY apps/api/ ./
COPY eval/fixtures /app/eval/fixtures
RUN uv sync --frozen

RUN useradd --system --uid 10001 app && chown -R app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "--factory", "claimsathi.main_api:create_app", "--host", "0.0.0.0", "--port", "8000"]
