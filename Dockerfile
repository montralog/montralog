FROM python:3.13.9-slim@sha256:326df678c20c78d465db501563f3492d17c42a4afe33a1f2bf5406a1d56b0e86
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MONTRALOG_DB=/data/montralog.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    groupadd --gid 10001 montralog && \
    useradd --uid 10001 --gid 10001 --no-create-home montralog && \
    mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 . .
ENV PYTHONPATH=/app/src
USER 10001:10001
EXPOSE 8080
CMD ["gunicorn","--config","deploy/docker/gunicorn.conf.py","montralog.wsgi:application"]
