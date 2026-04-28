# Build stage: install dependencies into a clean prefix for the runtime image.
FROM python:3.9.19-slim AS builder

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage: minimal image with only app and installed deps.
FROM python:3.9.19-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /install /usr/local
COPY *.py /app/

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health')" || exit 1

CMD ["python", "app.py"]
