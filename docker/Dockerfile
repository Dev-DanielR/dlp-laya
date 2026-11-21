# Self-contained Flask download server (HTTPS :443).
# Build from repo root:
#   docker build -f docker/Dockerfile -t dlp-laya-web .

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/webserver /app/src/webserver
COPY data/files /files
COPY data/manifest.json /app/data/manifest.json
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /certs

# TLS paths default in entrypoint.sh (/certs/cert.pem, /certs/key.pem).
# Do not bake TLS_KEY* into image ENV — BuildKit treats *KEY* names as secrets.
ENV PYTHONPATH=/app/src \
    FILES_ROOT=/files \
    MANIFEST_PATH=/app/data/manifest.json \
    ACL_PATH=/app/src/webserver/defaults/acl_paths.yaml \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=8443 \
    AUDIT_LOG_PATH=-

EXPOSE 8443

ENTRYPOINT ["/app/entrypoint.sh"]
