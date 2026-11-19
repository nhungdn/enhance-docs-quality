"""Độ đo hình học và OCR cho đánh giá hệ thống tài liệu (TV3)."""

from __future__ import annotations

import unicodedata

import cv2
import numpy as np


def compute_corner_error(pred_corners: np.ndarray, gt_corners: np.ndarray) -> float:
    """Tính sai số khoảng cách Euclid trung bình giữa 4 cặp góc (pixel)."""
    pred = np.asarray(pred_corners, dtype=np.float32).reshape(4, 2)
    gt = np.asarray(gt_corners, dtype=np.float32).reshape(4, 2)
    return float(np.linalg.norm(pred - gt, axis=1).mean())


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("OCR reference and hypothesis must be strings.")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def _edit_distance(reference: str | list[str], hypothesis: str | list[str]) -> int:
    """Tính Levenshtein distance với bộ nhớ O(min(n, m))."""
    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference

    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_item in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def _validate_reference(reference: str) -> str:
    normalized = _normalize_text(reference)
    if not normalized:
        raise ValueError("Reference transcription must not be empty.")
    return normalized


def compute_cer(reference: str, hypothesis: str) -> float:
    """Tính Character Error Rate (CER); thấp hơn là tốt hơn.

    Văn bản được chuẩn hóa Unicode NFKC, không phân biệt hoa/thường và gộp
    khoảng trắng liên tiếp. CER = khoảng cách chỉnh sửa ký tự / số ký tự chuẩn.
    """
    ref = _validate_reference(reference)
    hyp = _normalize_text(hypothesis)
    return _edit_distance(ref, hyp) / len(ref)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Tính Word Error Rate (WER) theo các đơn vị tách bằng khoảng trắng.

    Văn bản dùng cùng chuẩn hóa Unicode NFKC, không phân biệt hoa/thường và
    gộp khoảng trắng. Với tiếng Việt, WER được tính trên đơn vị cách trắng.
    """
    ref = _validate_reference(reference).split()
    hyp = _normalize_text(hypothesis).split()
    return _edit_distance(ref, hyp) / len(ref)


def compute_background_std(enhanced_img: np.ndarray) -> float:
    """Ước lượng độ lệch chuẩn nền giấy bằng ngưỡng Otsu (chỉ số phụ)."""
    gray = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2GRAY) if enhanced_img.ndim == 3 else enhanced_img
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bg_pixels = gray[mask > 0]
    return round(float(bg_pixels.std()) if bg_pixels.size > 0 else 0.0, 2)
