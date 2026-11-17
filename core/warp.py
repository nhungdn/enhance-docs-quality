"""Module biến đổi phối cảnh và làm phẳng tài liệu.

================================================================================
PHÂN CÔNG: Thành viên 1 (TV1) sở hữu và chỉnh sửa file này.
Các thành viên khác KHÔNG sửa file này để tránh xung đột Git (Merge Conflict).
================================================================================

Lộ trình công việc của TV1 trong file này:
- Tuần 1 (Đã xong): Chốt chữ ký hàm `warp_with_corners(image, corners, output_size)`.
- Tuần 3:
    + Hoàn thiện `compute_output_dimensions(ordered_corners)`: tính chiều rộng `max_width`
      và chiều cao `max_height` thực tế từ độ dài 4 cạnh của tứ giác.
    + Hoàn thiện `warp_with_corners()`: tính ma trận Homography 3x3 bằng
      `cv2.getPerspectiveTransform(src, dst)` và thực hiện `cv2.warpPerspective(...)`.
"""

from __future__ import annotations

import cv2
import numpy as np
from .detector import order_corners


def compute_output_dimensions(ordered_corners: np.ndarray) -> tuple[int, int]:
    """Tính kích thước `(width, height)` của ảnh phẳng đầu ra từ 4 góc `[TL, TR, BR, BL]`.

    TODO (TV1 - Tuần 3):
    - Tính `width_top = ||TR - TL||_2`, `width_bottom = ||BR - BL||_2`
      -> `max_width = max(int(width_top), int(width_bottom))`
    - Tính `height_left = ||BL - TL||_2`, `height_right = ||BR - TR||_2`
      -> `max_height = max(int(height_left), int(height_right))`
    - Đảm bảo `max_width >= 10` và `max_height >= 10`.
    """
    tl, tr, br, bl = ordered_corners
    width_top = float(np.linalg.norm(tr - tl))
    width_bottom = float(np.linalg.norm(br - bl))
    max_width = max(10, int(round(max(width_top, width_bottom))))

    height_left = float(np.linalg.norm(bl - tl))
    height_right = float(np.linalg.norm(br - tr))
    max_height = max(10, int(round(max(height_left, height_right))))

    return max_width, max_height


def warp_with_corners(
    image: np.ndarray,
    corners: np.ndarray,
    output_size: tuple[int, int] | None = None,
) -> np.ndarray:
    """Hàm giao diện chính: Biến đổi phối cảnh ảnh tài liệu dựa trên tọa độ 4 góc (Stub v0).

    CHÚ Ý: Không thay đổi tên hàm và kiểu trả về để đảm bảo tương thích với
    `core/pipeline.py`, `experiments/evaluate.py` (TV3) và `web/app.py` (TV4).

    Args:
        image: Ảnh gốc dạng `np.ndarray` (`HxWx3` hoặc `HxW`, dtype `uint8`).
        corners: Mảng `np.ndarray` kích thước `(4, 2)` chứa tọa độ 4 đỉnh
            (tự động từ `detect_corners` hoặc do người dùng kéo trên giao diện Web).
        output_size: Kích thước đầu ra `(width, height)` tùy chọn. Nếu `None`,
            sử dụng `compute_output_dimensions(ordered_corners)`.

    Returns:
        Ảnh tài liệu đã được cắt bỏ nền thừa và duỗi phẳng phối cảnh (`np.ndarray`, `uint8`).
    """
    if image is None or image.size == 0:
        raise ValueError("Ảnh đầu vào không hợp lệ (None hoặc rỗng).")

    pts = order_corners(np.asarray(corners, dtype=np.float32))
    out_w, out_h = output_size if output_size is not None else compute_output_dimensions(pts)

    # TODO (TV1 - Tuần 3): Thay thế đoạn cắt bounding box tạm thời dưới đây bằng
    # biến đổi phối cảnh chuẩn:
    #   dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
    #   M = cv2.getPerspectiveTransform(pts, dst)
    #   warped = cv2.warpPerspective(image, M, (out_w, out_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    h, w = image.shape[:2]
    x_min = max(0, int(np.floor(pts[:, 0].min())))
    x_max = min(w, int(np.ceil(pts[:, 0].max())))
    y_min = max(0, int(np.floor(pts[:, 1].min())))
    y_max = min(h, int(np.ceil(pts[:, 1].max())))

    if x_max <= x_min or y_max <= y_min:
        cropped = image.copy()
    else:
        cropped = image[y_min:y_max, x_min:x_max].copy()

    return cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
