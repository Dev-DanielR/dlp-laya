"""Laya Experts PII redactor + injectable protocol for tests."""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field
from typing import Protocol

from dlp_service.rules import LABELS, NOT_PII, build_states, candidates
from dlp_service.state import Span

JOIN_GAP = re.compile(r"[ \t\-/.]*")


@dataclass
class Entity:
    start: int
    end: int
    text: str
    label: str
    score: float


@dataclass
class Detection:
    text: str
    entities: list[Entity] = field(default_factory=list)
    candidates: int = 0


class PiiDetector(Protocol):
    def detect(
        self, text: str, *, threshold: float = 0.5, region: str = "US"
    ) -> Detection: ...


class RulesOnlyDetector:
    """Test/dev detector: treat strong PE/contact families as PII without Laya."""

    _STRONG = {
        "EMAIL",
        "PE_DNI",
        "PE_RUC",
        "PE_CCI",
        "PE_PHONE",
        "PHONE",
        "PHONE_RUN",
        "CARD",
        "SSN_DASH",
    }
    _FAMILY_LABEL = {
        "EMAIL": "email address",
        "PE_DNI": "id card number",
        "PE_RUC": "tax number",
        "PE_CCI": "id card number",
        "PE_PHONE": "phone number",
        "PHONE": "phone number",
        "PHONE_RUN": "phone number",
        "CARD": "credit card number",
        "SSN_DASH": "social security number",
    }

    def detect(
        self, text: str, *, threshold: float = 0.5, region: str = "US"
    ) -> Detection:
        del threshold, region
        kept: list[Entity] = []
        for cand in candidates(text):
            hit = next((f for f in cand.families if f in self._STRONG), None)
            if not hit:
                continue
            label = self._FAMILY_LABEL.get(hit, "id card number")
            kept.append(
                Entity(cand.start, cand.end, cand.text, label, 1.0)
            )
        chosen = _dedupe_entities(text, kept)
        return Detection(text, chosen, len(candidates(text)))


class LayaPiiRedactor:
    """goku-san/laya-experts PII flavour (choice over rule candidates).

    Weights load lazily on first detect / ensure_loaded so /healthz can bind
    before HuggingFace downloads finish.
    """

    def __init__(
        self,
        *,
        model: str = "goku-san/laya-experts",
        subfolder: str = "pii",
        device: str | None = None,
        batch_size: int = 16,
        cache_dir: str | None = None,
    ) -> None:
        if cache_dir:
            os.environ.setdefault("HF_HOME", cache_dir)
            os.environ.setdefault("HUGGINGFACE_HUB_CACHE", cache_dir)
        self._model = model
        self._subfolder = subfolder
        self._device = device
        self.batch_size = batch_size
        self.model_id = f"{model}:{subfolder}"
        self.agent = None
        self._load_lock = threading.Lock()
        self._loading = False
        self._load_error: str | None = None
        self.question = {
            "type": "choice",
            "instructions": (
                "A candidate span of text was pulled out of a document, and is shown with the "
                "text either side of it. Which kind of personal data is the span itself, or is "
                "it not personal data at all? Judge the span, not the surrounding text."
            ),
            "criteria": LABELS,
        }

    @property
    def ready(self) -> bool:
        return self.agent is not None

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def ensure_loaded(self) -> None:
        if self.agent is not None:
            return
        with self._load_lock:
            if self.agent is not None:
                return
            self._loading = True
            self._load_error = None
            try:
                import laya

                self.agent = laya.Agent(
                    self._model, subfolder=self._subfolder, device=self._device
                )
            except Exception as exc:  # noqa: BLE001
                self._load_error = str(exc)
                raise
            finally:
                self._loading = False

    def detect(
        self, text: str, *, threshold: float = 0.5, region: str = "US"
    ) -> Detection:
        self.ensure_loaded()
        rows = build_states(text, region=region)
        if not rows:
            return Detection(text, [], 0)
        probs = self._score([st for _, st in rows])
        kept: list[tuple[float, bool, int, Entity]] = []
        for (cand, _), pr in zip(rows, probs, strict=True):
            pii = 1.0 - pr.get(NOT_PII, 1.0)
            if pii < threshold:
                continue
            label = max((k for k in pr if k != NOT_PII), key=pr.get)
            multi_word = all(f == "CAPS_RUN" for f in cand.families)
            ent = Entity(cand.start, cand.end, cand.text, label, pii)
            kept.append((-round(pr[label], 1), multi_word, cand.start - cand.end, ent))
        ordered = [k[3] for k in sorted(kept, key=lambda x: x[:3])]
        chosen = _dedupe_entities(text, ordered)
        return Detection(text, chosen, len(rows))

    def _score(self, states: list[dict]) -> list[dict[str, float]]:
        import numpy as np
        import torch
        from laya.common import QTYPES, build_sequence, collate_items, temp_bucket

        ag = self.agent
        if ag is None:
            raise RuntimeError("Laya agent not loaded")
        max_len = ag.cfg.get("max_len", 512)
        head_max_len = ag.cfg.get("head_max_len", 192)
        q = ag._to_internal(self.question)
        qt = QTYPES["choice"]
        t = ag.temperature_by_options.get(
            temp_bucket(qt, len(LABELS)), ag.temperature[qt]
        )
        out: list[dict[str, float]] = []
        with torch.no_grad():
            for i in range(0, len(states), self.batch_size):
                items = []
                for st in states[i : i + self.batch_size]:
                    seq, markers = build_sequence(
                        ag.tok, st, q, max_len, head_max_len
                    )
                    items.append({"ids": seq, "markers": markers, "qtype": qt})
                b = collate_items([items], ag.tok.pad_token_id)
                with torch.autocast(
                    device_type=ag.device.type,
                    dtype=ag.dtype,
                    enabled=ag.device.type == "cuda",
                ):
                    logits, _ = ag.model(
                        *(
                            b[k].to(ag.device)
                            for k in (
                                "input_ids",
                                "attention_mask",
                                "marker_pos",
                                "marker_mask",
                                "qtype",
                            )
                        )
                    )
                z = logits.float().cpu().numpy()[:, : len(LABELS)] / t
                p = np.exp(z - z.max(axis=1, keepdims=True))
                p /= p.sum(axis=1, keepdims=True)
                out.extend(dict(zip(LABELS, map(float, row))) for row in p)
        return out


def entities_to_spans(entities: list[Entity]) -> list[Span]:
    return [
        Span(type=e.label, text=e.text, start=e.start, end=e.end) for e in entities
    ]


def _dedupe_entities(text: str, ordered: list[Entity]) -> list[Entity]:
    chosen: list[Entity] = []
    for ent in ordered:
        if all(ent.end <= c.start or ent.start >= c.end for c in chosen):
            chosen.append(ent)
    chosen.sort(key=lambda x: x.start)
    merged: list[Entity] = []
    for ent in chosen:
        prev = merged[-1] if merged else None
        if (
            prev
            and prev.label == ent.label
            and JOIN_GAP.fullmatch(text[prev.end : ent.start])
        ):
            merged[-1] = Entity(
                prev.start,
                ent.end,
                text[prev.start : ent.end],
                ent.label,
                min(prev.score, ent.score),
            )
        else:
            merged.append(ent)
    return merged
