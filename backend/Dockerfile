FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system luna && adduser --system --ingroup luna --home /app luna && mkdir -p /app/data /app/backups && chown -R luna:luna /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=luna:luna app ./app

USER luna

VOLUME ["/app/data", "/app/backups"]

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
