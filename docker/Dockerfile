# Self-contained Flask download server + optional localhost DLP daemon.
# Local build: ./scripts/docker-build.sh
#   docker build -f docker/Dockerfile -t dlp-laya .
# Skip heavy Laya/torch deps:
#   docker build --build-arg WITH_DLP=0 -f docker/Dockerfile -t dlp-laya .
# CPU torch (default) vs CUDA torch for --gpus:
#   docker build --build-arg WITH_GPU=1 -f docker/Dockerfile -t dlp-laya .

FROM python:3.12-slim

ARG WITH_DLP=1
ARG WITH_GPU=0
# PyTorch CUDA wheel channel (ignored when WITH_GPU=0).
ARG TORCH_CUDA_INDEX=https://download.pytorch.org/whl/cu124

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY requirements-dlp.txt /app/requirements-dlp.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && if [ "$WITH_DLP" = "1" ]; then \
         if [ "$WITH_GPU" = "1" ]; then \
           pip install --no-cache-dir torch --index-url "${TORCH_CUDA_INDEX}"; \
         else \
           pip install --no-cache-dir torch; \
         fi; \
         pip install --no-cache-dir -r /app/requirements-dlp.txt; \
       fi

# Bake Laya Experts weights into the image so runtime needs no HF download.
# Hub cache layout under /opt/laya-cache; LAYA_CACHE_DIR points here.
ENV HF_HOME=/opt/laya-cache \
    HUGGINGFACE_HUB_CACHE=/opt/laya-cache \
    LAYA_CACHE_DIR=/opt/laya-cache
RUN if [ "$WITH_DLP" = "1" ]; then \
      python -c "from huggingface_hub import snapshot_download; snapshot_download('goku-san/laya-experts', cache_dir='/opt/laya-cache'); print('baked goku-san/laya-experts into /opt/laya-cache')"; \
    fi

COPY src/webserver /app/src/webserver
COPY src/dlp_service /app/src/dlp_service
COPY data/files /files
COPY data/manifest.json /app/data/manifest.json
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /certs /var/lib/dlp

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
    DLP_WARMUP_DELAY_SECONDS=0 \
    LAYA_CACHE_DIR=/opt/laya-cache \
    HF_HOME=/opt/laya-cache \
    HUGGINGFACE_HUB_CACHE=/opt/laya-cache

EXPOSE 8443

ENTRYPOINT ["/app/entrypoint.sh"]
