"""Local PaddleOCR wrapper (CPU, no external OCR API).

Returns a plain, serialisable list of text boxes. Nothing here is specific to
tables; table logic lives in `tablekit`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TextItem:
    id: int
    text: str
    score: float
    bbox: list[int]            # [x_min, y_min, x_max, y_max] in source-image pixels
    poly: list[list[int]]      # 4-point polygon from the detector

    @property
    def x_min(self) -> int: return self.bbox[0]
    @property
    def y_min(self) -> int: return self.bbox[1]
    @property
    def x_max(self) -> int: return self.bbox[2]
    @property
    def y_max(self) -> int: return self.bbox[3]
    @property
    def xc(self) -> float: return (self.bbox[0] + self.bbox[2]) / 2
    @property
    def yc(self) -> float: return (self.bbox[1] + self.bbox[3]) / 2
    @property
    def height(self) -> int: return self.bbox[3] - self.bbox[1]


@dataclass
class OCRResult:
    image_path: str
    image_size: list[int]                  # [width, height]
    items: list[TextItem]
    engine_settings: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)   # untouched PaddleOCR output

    def to_json(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "image_size": self.image_size,
            "engine_settings": self.engine_settings,
            "items": [asdict(i) for i in self.items],
            "paddleocr_raw": self.raw,
        }

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")


def _to_builtin(obj: Any) -> Any:
    """Convert numpy containers inside PaddleOCR output to JSON-safe types."""
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(obj, dict):
        return {k: _to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_builtin(v) for v in obj]
    return obj


class OCREngine:
    """Thin wrapper around PaddleOCR 3.x `PaddleOCR.predict`."""

    def __init__(self, lang: str = "en", device: str = "cpu", enable_mkldnn: bool = False,
                 text_det_model: str | None = None, text_rec_model: str | None = None,
                 text_rec_score_thresh: float = 0.0, **extra: Any):
        from paddleocr import PaddleOCR

        self.settings: dict[str, Any] = {
            "lang": lang,
            "device": device,
            # Document orientation/unwarp/textline-orientation are off: the scan is
            # upright and flat, and these extra models only add runtime and risk.
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            # oneDNN is off: PaddlePaddle 3.3.x on Windows CPU raises
            # "ConvertPirAttribute2RuntimeAttribute not support" with it enabled.
            "enable_mkldnn": enable_mkldnn,
            "text_rec_score_thresh": text_rec_score_thresh,
            **extra,
        }
        if text_det_model:
            self.settings["text_detection_model_name"] = text_det_model
        if text_rec_model:
            self.settings["text_recognition_model_name"] = text_rec_model
        self._ocr = PaddleOCR(**self.settings)

    def run(self, image_path: str | Path) -> OCRResult:
        import cv2

        image_path = str(image_path)
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(image_path)
        h, w = img.shape[:2]

        page = self._ocr.predict(image_path)[0]
        res = _to_builtin(page.json["res"])
        items = [
            TextItem(id=i, text=t, score=round(float(s), 4),
                     bbox=[int(v) for v in b], poly=[[int(x), int(y)] for x, y in p])
            for i, (t, s, b, p) in enumerate(zip(res["rec_texts"], res["rec_scores"],
                                                 res["rec_boxes"], res["rec_polys"]))
        ]
        # Model names actually loaded, as reported by PaddleX.
        try:
            pipe = self._ocr.paddlex_pipeline._pipeline  # type: ignore[attr-defined]
            models = {"text_det_model": pipe.text_det_model.model_name,
                      "text_rec_model": pipe.text_rec_model.model_name}
        except Exception:
            models = {}
        settings = {**self.settings, **models,
                    "text_det_params": res.get("text_det_params"),
                    "model_settings": res.get("model_settings")}
        return OCRResult(image_path=image_path, image_size=[w, h], items=items,
                         engine_settings=settings, raw=res)
