"""Loopback-only classify HTTP API."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request

from dlp_service.batch import walk_files
from dlp_service.batch_state import BatchState
from dlp_service.classify import Classifier, to_rel
from dlp_service.progress import build_progress, build_statuses, filter_prefix

log = logging.getLogger("dlp_service.api")


def create_app(
    classifier: Classifier,
    *,
    batch_state: BatchState | None = None,
    detector: object | None = None,
) -> Flask:
    app = Flask("dlp_service")
    app.config["CLASSIFIER"] = classifier
    app.config["BATCH_STATE"] = batch_state or BatchState()
    app.config["DETECTOR"] = detector if detector is not None else classifier.detector

    @app.get("/healthz")
    def healthz():
        det = app.config.get("DETECTOR")
        model_ready = True
        model_loading = False
        if det is not None and hasattr(det, "ensure_loaded"):
            model_ready = bool(getattr(det, "ready", False))
            model_loading = bool(getattr(det, "loading", False)) or not model_ready
        return jsonify(
            {
                "status": "ok",
                "service": "dlp",
                "model_ready": model_ready,
                "model_loading": model_loading,
            }
        ), 200

    @app.get("/classify")
    def classify():
        path = request.args.get("path")
        content_hash = request.args.get("hash")
        if not path and not content_hash:
            return jsonify({"error": "path or hash required"}), 400
        rec = classifier.classify(path=path, content_hash=content_hash)
        code = 200
        if rec.status == "missing":
            code = 404
        return jsonify(rec.to_api()), code

    @app.get("/progress")
    def progress():
        payload = build_progress(
            files_root=classifier.files_root,
            store=classifier.store,
            batch=app.config["BATCH_STATE"],
            detector=app.config.get("DETECTOR"),
        )
        return jsonify(payload), 200

    @app.get("/statuses")
    def statuses():
        """Read-only path phases. Prefer paths=; else prefix= for one folder level."""
        paths_raw = request.args.get("paths", "").strip()
        prefix = request.args.get("prefix", "").strip()
        if paths_raw:
            paths: list[str] = []
            for part in paths_raw.split(","):
                rel = to_rel(part, classifier.files_root) or part.strip().lstrip("/")
                if rel:
                    paths.append(rel)
        else:
            all_rels = walk_files(classifier.files_root)
            pref = to_rel(prefix, classifier.files_root) if prefix else prefix
            pref = (pref or "").strip("/")
            paths = filter_prefix(all_rels, pref)
        items = build_statuses(store=classifier.store, paths=paths)
        return jsonify({"items": items}), 200

    return app
