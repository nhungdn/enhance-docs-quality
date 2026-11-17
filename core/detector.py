"""Module phát hiện biên và 4 góc tài liệu.

================================================================================
PHÂN CÔNG: Thành viên 1 (TV1) sở hữu và chỉnh sửa file này.
Các thành viên khác KHÔNG sửa file này để tránh xung đột Git (Merge Conflict).
================================================================================

Lộ trình công việc của TV1 trong file này:
- Tuần 1 (Đã xong): Chốt chữ ký hàm `detect_corners(image, config)` và `order_corners(pts)`.
- Tuần 2:
    + Hoàn thiện `preprocess_for_edges()`: chuyển ảnh xám + lọc Gaussian (`cv2.GaussianBlur`).
    + Hoàn thiện `detect_edges()`: dò biên Canny (`cv2.Canny`) + phép đóng hình thái học.
    + Hoàn thiện `find_document_contour()`: tìm contour lớn nhất và xấp xỉ đa giác (`approxPolyDP`).
- Tuần 3:
    + Hoàn thiện `validate_quadrilateral()`: kiểm tra đủ 4 đỉnh, tính lồi, diện tích >= 15% ảnh,
      góc trong hợp lý [45°, 135°].
    + Hoàn thiện `get_fallback_corners()`: khi không tìm được tứ giác hợp lệ, trả về `is_valid=False`
      kèm 4 góc gợi ý từ `cv2.minAreaRect` để giao diện Web (TV4) bật chế độ kéo góc thủ công.
"""

from __future__ import annotations

from typing import Any
import cv2
import numpy as np


DEFAULT_DETECT_CONFIG: dict[str, Any] = {
    "proc_height": 800,           # Chiều cao chuẩn hóa tạm thời khi dò biên để tăng tốc
    "gaussian_ksize": (5, 5),     # Kích thước nhân lọc Gaussian
    "gaussian_sigma": 1.2,        # Độ lệch chuẩn sigma của Gaussian
    "canny_low": 50,              # Ngưỡng dưới Canny
    "canny_high": 150,            # Ngưỡng trên Canny
    "morph_ksize": (5, 5),        # Nhân phép đóng (Morphological Closing) nối biên đứt
    "top_k_contours": 5,          # Số contour lớn nhất đưa vào xét duyệt
    "approx_eps_ratio": 0.02,     # Hệ số epsilon xấp xỉ đa giác (tỉ lệ theo chu vi)
    "min_area_ratio": 0.15,       # Diện tích tối thiểu của tờ giấy so với khung hình
    "min_angle_deg": 45.0,        # Góc trong nhỏ nhất cho phép (độ)
    "max_angle_deg": 135.0,       # Góc trong lớn nhất cho phép (độ)
}


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Sắp xếp 4 điểm góc theo thứ tự chuẩn: [top-left, top-right, bottom-right, bottom-left].

    Quy ước chuẩn cho toàn nhóm (TV1, TV3, TV4 đều dùng chung thứ tự này):
    - Index 0: Top-Left (TL)     - tổng (x + y) nhỏ nhất
    - Index 1: Top-Right (TR)    - hiệu (y - x) nhỏ nhất
    - Index 2: Bottom-Right (BR) - tổng (x + y) lớn nhất
    - Index 3: Bottom-Left (BL)  - hiệu (y - x) lớn nhất

    Args:
        pts: Mảng NumPy kích thước (4, 2) chứa tọa độ (x, y) của 4 đỉnh.

    Returns:
        Mảng NumPy float32 kích thước (4, 2) theo thứ tự [TL, TR, BR, BL].
    """
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    rect = np.zeros((4, 2), dtype=np.float32)

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def preprocess_for_edges(image: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Bước 1: Chuyển ảnh sang đa mức xám và làm mịn bằng lọc Gaussian.

    TODO (TV1 - Tuần 2):
    - Chuyển `image` từ BGR sang Grayscale (nếu ảnh đang có 3 kênh).
    - Áp dụng `cv2.GaussianBlur` với `cfg["gaussian_ksize"]` và `cfg["gaussian_sigma"]`.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    ksize = cfg.get("gaussian_ksize", (5, 5))
    sigma = cfg.get("gaussian_sigma", 1.2)
    return cv2.GaussianBlur(gray, ksize, sigma)


def detect_edges(blurred: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Bước 2: Phát hiện biên Canny kết hợp phép đóng hình thái học.

    TODO (TV1 - Tuần 2):
    - Gọi `cv2.Canny(blurred, cfg["canny_low"], cfg["canny_high"])`.
    - Áp dụng `cv2.morphologyEx(..., cv2.MORPH_CLOSE, kernel)` để nối các đoạn biên đứt.
    """
    _ = cfg
    return np.zeros_like(blurred, dtype=np.uint8)


def find_document_contour(
    edges: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[np.ndarray | None, list[np.ndarray]]:
    """Bước 3: Tìm các contour lớn nhất và xấp xỉ đa giác bằng `approxPolyDP`.

    TODO (TV1 - Tuần 2):
    - Dùng `cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)`.
    - Sắp xếp contour giảm dần theo diện tích (`cv2.contourArea`), lấy `top_k_contours`.
    - Với mỗi contour, tính chu vi `peri = cv2.arcLength(c, True)` và gọi
      `approx = cv2.approxPolyDP(c, cfg["approx_eps_ratio"] * peri, True)`.
    - Trả về tứ giác ứng viên 4 đỉnh đầu tiên tìm được cùng danh sách top contours.
    """
    _ = (edges, cfg)
    return None, []


def validate_quadrilateral(
    corners: np.ndarray | None,
    image_shape: tuple[int, int],
    cfg: dict[str, Any],
) -> tuple[bool, str | None]:
    """Bước 4: Kiểm tra tứ giác ứng viên có hợp lệ về mặt hình học hay không.

    TODO (TV1 - Tuần 3):
    Kiểm tra 4 tiêu chí:
    1. `corners` không phải None và có đúng 4 đỉnh `(4, 2)`.
    2. Đa giác lồi (`cv2.isContourConvex`).
    3. Diện tích tứ giác >= `cfg["min_area_ratio"] * H * W`.
    4. 4 góc trong tại 4 đỉnh nằm trong khoảng `[min_angle_deg, max_angle_deg]`.

    Returns:
        Tuple `(is_valid, fallback_reason)`:
        - `is_valid`: `True` nếu đạt cả 4 tiêu chí, ngược lại `False`.
        - `fallback_reason`: Chuỗi mô tả lý do lỗi (ví dụ `"area_too_small"`, `"not_4_vertices"`),
          hoặc `None` nếu hợp lệ.
    """
    _ = (corners, image_shape, cfg)
    return False, "stub_v0_not_implemented"


def get_fallback_corners(
    contours: list[np.ndarray],
    image_shape: tuple[int, int],
) -> np.ndarray:
    """Sinh 4 góc gợi ý khi phát hiện tự động thất bại (`is_valid == False`).

    TODO (TV1 - Tuần 3):
    - Nếu danh sách `contours` không rỗng và contour lớn nhất có diện tích đủ lớn,
      dùng `cv2.minAreaRect(contours[0])` và `cv2.boxPoints(...)` để lấy 4 đỉnh gợi ý.
    - Ngược lại, trả về khung chữ nhật mặc định cách đều lề ảnh 8%.
    """
    _ = contours
    h, w = image_shape[:2]
    margin_x = float(w) * 0.08
    margin_y = float(h) * 0.08
    default_pts = np.array(
        [
            [margin_x, margin_y],
            [w - margin_x, margin_y],
            [w - margin_x, h - margin_y],
            [margin_x, h - margin_y],
        ],
        dtype=np.float32,
    )
    return order_corners(default_pts)


def detect_corners(
    image: np.ndarray,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Hàm giao diện chính: Phát hiện 4 góc trang tài liệu trong ảnh chụp (Stub v0).

    CHÚ Ý: Không thay đổi tên hàm và các khóa trả về trong dict để đảm bảo tương thích
    với `core/pipeline.py`, `experiments/evaluate.py` (TV3) và `web/app.py` (TV4).

    Args:
        image: Ảnh đầu vào BGR `(H, W, 3)` hoặc ảnh xám `(H, W)`, dtype `uint8`.
        config: Từ điển tham số ghi đè lên `DEFAULT_DETECT_CONFIG`.

    Returns:
        Từ điển kết quả gồm:
            - `"corners"`: `np.ndarray` shape `(4, 2)`, dtype `float32`, thứ tự `[TL, TR, BR, BL]`.
            - `"is_valid"`: `bool` (`True` nếu phát hiện tự động thành công, `False` nếu cần fallback).
            - `"confidence"`: `float` trong khoảng `[0.0, 1.0]`.
            - `"fallback_reason"`: `str | None` lý do cần chuyển sang kéo góc thủ công.
            - `"debug_info"`: `dict` chứa dữ liệu trung gian phục vụ vẽ hình báo cáo.
    """
    if image is None or image.size == 0:
        raise ValueError("Ảnh đầu vào không hợp lệ (None hoặc rỗng).")

    cfg = {**DEFAULT_DETECT_CONFIG, **(config or {})}
    h, w = image.shape[:2]

    # Luồng khung gọi các hàm con của TV1:
    blurred = preprocess_for_edges(image, cfg)
    edges = detect_edges(blurred, cfg)
    candidate_quad, top_contours = find_document_contour(edges, cfg)
    is_valid, reason = validate_quadrilateral(candidate_quad, (h, w), cfg)

    if is_valid and candidate_quad is not None:
        corners = order_corners(candidate_quad)
        confidence = 1.0
    else:
        corners = get_fallback_corners(top_contours, (h, w))
        confidence = 0.0

    return {
        "corners": corners,
        "is_valid": is_valid,
        "confidence": confidence,
        "fallback_reason": reason,
        "debug_info": {
            "image_shape": (h, w),
            "config_used": cfg,
            "num_top_contours": len(top_contours),
            "status": "stub_v0",
        },
    }
