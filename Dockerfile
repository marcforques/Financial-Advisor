FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8001

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY backend/requirements-prod.txt ./requirements-prod.txt
RUN pip install --upgrade pip && pip install -r requirements-prod.txt

COPY backend/ .
RUN mkdir -p /app/data && chown -R app:app /app

USER app
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8001') + '/salud', timeout=4)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
