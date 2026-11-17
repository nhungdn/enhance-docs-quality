"""Module biến đổi phối cảnh và làm phẳng tài liệu."""

from __future__ import annotations

import cv2
import numpy as np
from .detector import order_corners


def compute_output_dimensions(ordered_corners: np.ndarray) -> tuple[int, int]:
    """Tính kích thước `(width, height)` của ảnh phẳng đầu ra từ 4 góc `[TL, TR, BR, BL]`.

    Chiều rộng và chiều cao lần lượt lấy cạnh dài hơn trong mỗi cặp đối diện,
    với kích thước tối thiểu là 10 pixel.
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
    """Hàm giao diện chính: Biến đổi phối cảnh ảnh tài liệu dựa trên tọa độ 4 góc.

    CHÚ Ý: Không thay đổi tên hàm và kiểu trả về để đảm bảo tương thích với
    `core/pipeline.py`, `experiments/evaluate.py` (TV3) và `web/app.py` (TV4).

    Thuật toán:
    1. Sắp xếp 4 góc về thứ tự chuẩn [TL, TR, BR, BL].
    2. Tính kích thước đầu ra (nếu output_size=None, tính từ 4 cạnh tứ giác).
    3. Dựng ma trận Homography 3×3 bằng `cv2.getPerspectiveTransform`.
    4. Áp dụng biến đổi phối cảnh với `cv2.warpPerspective`.

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

    # --- Bước 1: Sắp xếp góc về thứ tự chuẩn ---
    pts = order_corners(np.asarray(corners, dtype=np.float32))

    # --- Bước 2: Xác định kích thước đầu ra ---
    out_w, out_h = output_size if output_size is not None else compute_output_dimensions(pts)

    # --- Bước 3: Dựng Homography 3×3 ---
    dst = np.array(
        [
            [0,         0        ],
            [out_w - 1, 0        ],
            [out_w - 1, out_h - 1],
            [0,         out_h - 1],
        ],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(pts, dst)

    # --- Bước 4: Biến đổi phối cảnh ---
    warped = cv2.warpPerspective(
        image, M, (out_w, out_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return warped
