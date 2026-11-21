# Self-contained Flask download server + optional localhost DLP daemon.
# Local build: ./scripts/docker-build.sh
#   docker build -f docker/Dockerfile -t dlp-laya .
# Skip heavy Laya/torch deps:
#   docker build --build-arg WITH_DLP=0 -f docker/Dockerfile -t dlp-laya .

FROM python:3.12-slim

ARG WITH_DLP=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY requirements-dlp.txt /app/requirements-dlp.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && if [ "$WITH_DLP" = "1" ]; then \
         pip install --no-cache-dir -r /app/requirements-dlp.txt; \
       fi

COPY src/webserver /app/src/webserver
COPY src/dlp_service /app/src/dlp_service
COPY data/files /files
COPY data/manifest.json /app/data/manifest.json
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /certs /var/lib/dlp /var/cache/laya

# TLS paths default in entrypoint.sh (/certs/cert.pem, /certs/key.pem).
# Do not bake TLS_KEY* into image ENV — BuildKit treats *KEY* names as secrets.
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    FILES_ROOT=/files \
    MANIFEST_PATH=/app/data/manifest.json \
    ACL_PATH=/app/src/webserver/defaults/acl_paths.yaml \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=8443 \
    AUDIT_LOG_PATH=- \
    CLASSIFY_MODE=stub \
    DLP_PORT=8091 \
    DLP_BIND_HOST=127.0.0.1 \
    DLP_CACHE_PATH=/var/lib/dlp/cache.sqlite3 \
    LAYA_CACHE_DIR=/var/cache/laya

EXPOSE 8443

ENTRYPOINT ["/app/entrypoint.sh"]
