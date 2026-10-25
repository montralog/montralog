FROM python:3.13-slim@sha256:57b29a7c050c4e679e4bea572e14b3965cf4b5839de2da49d55e49ffc4024f39
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MONTRALOG_DB=/data/montralog.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m pip uninstall --yes pip setuptools wheel && \
    python -c "import shutil,sysconfig; from pathlib import Path; shutil.rmtree(Path(sysconfig.get_path('stdlib'))/'ensurepip')" && \
    groupadd --gid 10001 montralog && \
    useradd --uid 10001 --gid 10001 --no-create-home montralog && \
    mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 . .
ENV PYTHONPATH=/app/src
USER 10001:10001
EXPOSE 8080
CMD ["gunicorn","--config","deploy/docker/gunicorn.conf.py","montralog.wsgi:application"]
