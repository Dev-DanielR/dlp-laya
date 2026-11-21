"""Run the localhost DLP daemon: python -m dlp_service"""

from __future__ import annotations

import logging
import os
import sys
import threading

from dlp_service.api import create_app
from dlp_service.batch import recover_missing
from dlp_service.batch_state import BatchState
from dlp_service.classify import Classifier
from dlp_service.config import DlpSettings
from dlp_service.laya_pii import LayaPiiRedactor, RulesOnlyDetector
from dlp_service.store import ClassifyStore
from dlp_service.watcher import DebouncedWatcher

log = logging.getLogger("dlp_service")


def _build_detector(settings: DlpSettings):
    mode = os.environ.get("DLP_DETECTOR", "laya").strip().lower()
    if mode in {"rules", "rules_only", "fake"}:
        log.warning(
            "DLP_DETECTOR=%s — using rules-only detector (no Laya weights)", mode
        )
        return RulesOnlyDetector(), "rules-only"
    cache = str(settings.laya_cache_dir) if settings.laya_cache_dir else None
    redactor = LayaPiiRedactor(
        model=settings.laya_model,
        subfolder=settings.laya_subfolder,
        device=settings.laya_device,
        cache_dir=cache,
    )
    return redactor, getattr(
        redactor, "model_id", f"{settings.laya_model}:{settings.laya_subfolder}"
    )


def _warmup_then_batch(
    detector,
    classifier: Classifier,
    settings: DlpSettings,
    batch_state: BatchState,
    watcher: DebouncedWatcher,
) -> None:
    # Quiet window before torch contend for RAM/CPU. Default 0 when weights are baked;
    # set DLP_WARMUP_DELAY_SECONDS=20 if Sign-in still races a cold HF download.
    delay = float(os.environ.get("DLP_WARMUP_DELAY_SECONDS", "0"))
    if delay > 0:
        log.info("Warmup delay %.0fs (login can proceed first)", delay)
        threading.Event().wait(delay)
    watcher.pause()
    try:
        if hasattr(detector, "ensure_loaded"):
            log.info("Loading Laya weights in background…")
            try:
                detector.ensure_loaded()
                log.info("Laya model ready (%s)", getattr(detector, "model_id", "?"))
            except Exception:  # noqa: BLE001
                log.exception(
                    "Laya model failed to load — classify will error until fixed"
                )
                return
        if settings.batch_on_start:
            recover_missing(classifier, background=False, batch_state=batch_state)
    finally:
        # Live tree edits after the corpus warmup; static lab image rarely needs this.
        watcher.resume()


def main(argv: list[str] | None = None) -> int:
    del argv
    logging.basicConfig(
        level=os.environ.get("DLP_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = DlpSettings.from_env()
    if settings.bind_host not in {"127.0.0.1", "localhost", "::1"}:
        logging.error(
            "Refusing to bind DLP on %s — loopback only (set DLP_BIND_HOST=127.0.0.1)",
            settings.bind_host,
        )
        return 2

    if not settings.files_root.is_dir():
        logging.error("FILES_ROOT does not exist: %s", settings.files_root)
        return 2

    store = ClassifyStore(settings.cache_path)
    detector, laya_version = _build_detector(settings)
    classifier = Classifier(
        files_root=settings.files_root,
        store=store,
        detector=detector,
        lock_seconds=settings.lock_seconds,
        threshold=settings.laya_threshold,
        region=settings.laya_region,
        laya_version=laya_version,
    )

    batch_state = BatchState()

    watcher = DebouncedWatcher(
        files_root=settings.files_root,
        classifier=classifier,
        debounce_seconds=settings.debounce_seconds,
    )
    # Starts paused; resumed after warmup/batch so invalidate cannot race recovery.
    watcher.start()

    # Load model + batch after /healthz can bind (lazy Laya).
    threading.Thread(
        target=_warmup_then_batch,
        args=(detector, classifier, settings, batch_state, watcher),
        name="dlp-warmup",
        daemon=True,
    ).start()

    app = create_app(classifier, batch_state=batch_state, detector=detector)
    logging.info(
        "DLP listening on http://%s:%s (files=%s)",
        settings.bind_host,
        settings.bind_port,
        settings.files_root,
    )
    # threaded=True so /classify can return locked while another request works.
    app.run(
        host=settings.bind_host,
        port=settings.bind_port,
        threaded=True,
        use_reloader=False,
    )
    watcher.stop()
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
