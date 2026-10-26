FROM python:3.13-alpine@sha256:bf12ecc0bea3f171d55145dd02c78b5eeb09f30ee2ac9cc2b4c9e4e8f5e30741
ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/montralog/montralog" \
      org.opencontainers.image.url="https://github.com/montralog/montralog" \
      org.opencontainers.image.version="0.7.0" \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.description="Montralog monitoring, tracing, logging and tracking"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MONTRALOG_DB=/data/montralog.db MONTRALOG_ENCRYPTION_REQUIRED=true MONTRALOG_SILO_STRICT=true
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m pip uninstall --yes pip setuptools wheel && \
    python -c "import shutil,sysconfig; from pathlib import Path; shutil.rmtree(Path(sysconfig.get_path('stdlib'))/'ensurepip')" && \
    addgroup -g 10001 montralog && \
    adduser -D -H -u 10001 -G montralog montralog && \
    mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 . .
ENV PYTHONPATH=/app/src
USER 10001:10001
EXPOSE 8080
CMD ["gunicorn","--config","deploy/docker/gunicorn.conf.py","montralog.wsgi:application"]
