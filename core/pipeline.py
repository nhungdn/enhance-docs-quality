"""Luồng tích hợp Pipeline xử lý ảnh tài liệu từ đầu đến cuối (End-to-End).

================================================================================
PHÂN CÔNG: Thành viên 4 (TV4) phụ trách tích hợp luồng này với ứng dụng Web.
Kết nối 3 hàm giao diện cốt lõi:
`detect_corners` (TV1) -> `warp_with_corners` (TV1) -> `enhance` (TV2)
================================================================================
"""

from __future__ import annotations

import time
from typing import Any
import numpy as np

from .detector import detect_corners, order_corners
from .warp import warp_with_corners
from .enhancer import enhance


def process_document(
    image: np.ndarray,
    manual_corners: np.ndarray | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Chạy toàn bộ pipeline quét và cải thiện chất lượng tài liệu.

    Args:
        image: Ảnh chụp tài liệu đầu vào (`np.ndarray` BGR).
        manual_corners: Tọa độ 4 góc `(4, 2)` do người dùng kéo tay trên giao diện Web
            (chế độ fallback). Nếu `None`, hệ thống gọi `detect_corners(image)` tự động.
        config: Từ điển cấu hình tùy chọn truyền xuống từng bước:
            - `detect`: dict tham số cho `detect_corners`
            - `output_size`: tuple `(width, height)` cho `warp_with_corners`
            - `remove_shadow`, `denoise`, `use_clahe`, `binarize`: bool cho `enhance`
            - `enhance`: dict tham số cho `enhance`

    Returns:
        Từ điển chứa kết quả từng bước của pipeline:
            - `"detection"`: Kết quả từ `detect_corners` (hoặc thông tin góc thủ công).
            - `"corners_used"`: Mảng `(4, 2)` góc `[TL, TR, BR, BL]` thực tế đã dùng.
            - `"warped_image"`: Ảnh sau khi cắt nền và làm phẳng (`warp_with_corners`).
            - `"enhanced_image"`: Ảnh sau khi tăng cường chất lượng (`enhance`).
            - `"timing_ms"`: Thời gian thực thi từng bước (ms) phục vụ báo cáo Mục 7.4.
    """
    cfg = config or {}

    t0 = time.perf_counter()
    if manual_corners is not None:
        corners_used = order_corners(np.asarray(manual_corners, dtype=np.float32))
        detection = {
            "corners": corners_used,
            "is_valid": True,
            "confidence": 1.0,
            "fallback_reason": None,
            "source": "manual_fallback",
        }
    else:
        detection = detect_corners(image, config=cfg.get("detect"))
        detection["source"] = "auto"
        corners_used = detection["corners"]
    t1 = time.perf_counter()

    warped_image = warp_with_corners(
        image=image,
        corners=corners_used,
        output_size=cfg.get("output_size"),
    )
    t2 = time.perf_counter()

    enhanced_image = enhance(
        image=warped_image,
        remove_shadow=cfg.get("remove_shadow", True),
        denoise=cfg.get("denoise", True),
        use_clahe=cfg.get("use_clahe", True),
        binarize=cfg.get("binarize", True),
        config=cfg.get("enhance"),
    )
    t3 = time.perf_counter()

    return {
        "detection": detection,
        "corners_used": corners_used,
        "warped_image": warped_image,
        "enhanced_image": enhanced_image,
        "timing_ms": {
            "detect_ms": round((t1 - t0) * 1000.0, 2),
            "warp_ms": round((t2 - t1) * 1000.0, 2),
            "enhance_ms": round((t3 - t2) * 1000.0, 2),
            "total_ms": round((t3 - t0) * 1000.0, 2),
        },
    }
