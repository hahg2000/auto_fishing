from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class OCRBox:
    points: tuple[tuple[int, int], ...]
    score: float

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        xs = [point[0] for point in self.points]
        ys = [point[1] for point in self.points]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass(frozen=True)
class OCRText:
    text: str
    score: float
    box: OCRBox | None = None


@dataclass(frozen=True)
class _RapidOCRPayload:
    boxes: list[OCRBox]
    texts: list[str]
    scores: list[float]


class RapidOCREngine:
    """Thin RapidOCR wrapper that keeps the project-side API stable."""

    def __init__(
        self,
        *,
        det_model_path: str | None = None,
        cls_model_path: str | None = None,
        rec_model_path: str | None = None,
        rec_keys_path: str | None = None,
        use_cls: bool = False,
        **_: Any,
    ) -> None:
        from rapidocr import EngineType, RapidOCR

        params: dict[str, Any] = {
            "Global.use_cls": use_cls,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
        }

        if det_model_path:
            params["Det.model_path"] = det_model_path
        if cls_model_path:
            params["Cls.model_path"] = cls_model_path
        if rec_model_path:
            params["Rec.model_path"] = rec_model_path
        if rec_keys_path:
            params["Rec.rec_keys_path"] = rec_keys_path

        self._engine = RapidOCR(params=params)
        self._use_cls = use_cls

    def detect(self, image: np.ndarray) -> list[OCRBox]:
        payload = self._run(image, use_det=True, use_cls=False, use_rec=False)
        return payload.boxes

    def recognize(self, image: np.ndarray) -> OCRText | None:
        if image.size == 0:
            return None

        payload = self._run(image, use_det=False, use_cls=self._use_cls, use_rec=True)
        if not payload.texts:
            return None

        text = payload.texts[0].strip()
        if not text:
            return None

        score = payload.scores[0] if payload.scores else 0.0
        return OCRText(text=text, score=score)

    def detect_and_recognize(self, image: np.ndarray) -> list[OCRText]:
        if image.size == 0:
            return []

        payload = self._run(image, use_det=True, use_cls=self._use_cls, use_rec=True)
        recognized: list[OCRText] = []

        for index, text in enumerate(payload.texts):
            clean_text = text.strip()
            if not clean_text:
                continue
            score = payload.scores[index] if index < len(payload.scores) else 0.0
            box = payload.boxes[index] if index < len(payload.boxes) else None
            recognized.append(OCRText(text=clean_text, score=score, box=box))

        return recognized

    def recognize_region(
        self,
        image: np.ndarray,
        *,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> list[OCRText]:
        roi = image[top:bottom, left:right]
        return self.detect_and_recognize(roi)

    def _run(
        self,
        image: np.ndarray,
        *,
        use_det: bool,
        use_cls: bool,
        use_rec: bool,
    ) -> _RapidOCRPayload:
        result = self._engine(image, use_det=use_det, use_cls=use_cls, use_rec=use_rec)
        return self._extract_payload(result)

    def _extract_payload(self, result: Any) -> _RapidOCRPayload:
        payload = result[0] if isinstance(result, tuple) else result
        if payload is None:
            return _RapidOCRPayload(boxes=[], texts=[], scores=[])

        boxes = self._extract_boxes(payload)
        texts = self._extract_texts(payload)
        scores = self._extract_scores(payload)
        return _RapidOCRPayload(boxes=boxes, texts=texts, scores=scores)

    def _extract_boxes(self, payload: Any) -> list[OCRBox]:
        raw_boxes = self._extract_value(payload, "boxes", "dt_boxes", default=[])
        raw_scores = self._extract_value(payload, "scores", default=[])
        boxes: list[OCRBox] = []
        for index, raw_box in enumerate(self._as_list(raw_boxes)):
            if raw_box is None:
                continue
            points = tuple(self._normalize_point(point) for point in raw_box)
            if not points:
                continue
            score = float(raw_scores[index]) if index < len(raw_scores) else 0.0
            boxes.append(OCRBox(points=points, score=score))
        return boxes

    def _extract_texts(self, payload: Any) -> list[str]:
        raw_texts = self._extract_value(payload, "txts", "texts", default=[])
        return [str(text) for text in self._as_list(raw_texts)]

    def _extract_scores(self, payload: Any) -> list[float]:
        raw_scores = self._extract_value(payload, "scores", default=[])
        return [float(score) for score in self._as_list(raw_scores)]

    def _extract_value(self, payload: Any, *keys: str, default: Any) -> Any:
        if isinstance(payload, dict):
            for key in keys:
                if key in payload:
                    return payload[key]
            return default

        for key in keys:
            if hasattr(payload, key):
                return getattr(payload, key)

        return default

    def _normalize_point(self, point: Iterable[Any]) -> tuple[int, int]:
        x, y = point
        return (int(round(float(x))), int(round(float(y))))

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]
