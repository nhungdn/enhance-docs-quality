"""Module tiền xử lý và tăng cường chất lượng ảnh tài liệu.

================================================================================
PHÂN CÔNG: Thành viên 2 (TV2) sở hữu và chỉnh sửa file này.
Các thành viên khác KHÔNG sửa file này để tránh xung đột Git (Merge Conflict).
================================================================================

Lộ trình công việc của TV2 trong file này:
- Tuần 1 (Đã xong): Chốt chữ ký hàm `enhance(image, ...)` và các hàm con.
- Tuần 2:
    + Hoàn thiện `to_grayscale(image)`: chuyển ảnh màu BGR sang đa mức xám.
    + Hoàn thiện `apply_threshold(gray, cfg)`: cài đặt ngưỡng toàn cục Otsu (`"otsu"`)
      và ngưỡng thích nghi (`"adaptive_mean"`, `"adaptive_gaussian"`).
- Tuần 3:
    + Hoàn thiện `remove_shadow_bg(gray, cfg)`: ước lượng nền sáng bằng phép đóng hình thái học
      (Morphological Closing) hoặc làm mờ nhân lớn, sau đó chia chuẩn hóa để khử bóng đổ.
    + Hoàn thiện `denoise_image(gray, cfg)`: lọc trung vị (Median) hoặc lọc song phương (Bilateral).
    + Hoàn thiện `apply_clahe(gray, cfg)`: cân bằng biểu đồ mức xám cục bộ có giới hạn tương phản.
"""

from __future__ import annotations

from typing import Any
import cv2
import numpy as np


DEFAULT_ENHANCE_CONFIG: dict[str, Any] = {
    "bg_kernel_size": 31,                  # Kích thước nhân hình thái học ước lượng nền khử bóng
    "denoise_method": "median",            # Phương pháp khử nhiễu: "median" hoặc "bilateral"
    "denoise_ksize": 3,                    # Kích thước nhân lọc trung vị
    "clahe_clip_limit": 2.0,               # Ngưỡng giới hạn khuếch đại tương phản của CLAHE
    "clahe_tile_grid": (8, 8),             # Kích thước lưới ô cục bộ của CLAHE
    "threshold_method": "adaptive_gaussian",  # "adaptive_gaussian", "adaptive_mean", hoặc "otsu"
    "block_size": 21,                      # Kích thước vùng lân cận cho Adaptive Threshold (số lẻ >= 3)
    "c_offset": 10,                        # Hằng số C trừ đi từ trung bình cục bộ
}


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Bước 1: Chuyển ảnh BGR sang ảnh đa mức xám (Grayscale 1 kênh, uint8).

    TODO (TV2 - Tuần 2):
    - Kiểm tra nếu `image` có 3 kênh thì chuyển sang xám theo công thức độ chói chuẩn
      $Y = 0.299R + 0.587G + 0.114B$ (hoặc `cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)`).
    """
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image.copy()


def remove_shadow_bg(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Bước 2: Ước lượng nền chiếu sáng và loại bỏ bóng đổ.

    TODO (TV2 - Tuần 3):
    - Tạo phần tử cấu trúc hình thái học kích thước lớn `k = cfg["bg_kernel_size"]`.
    - Thực hiện phép đóng (`cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)`) hoặc
      `dilate` + `medianBlur` để xóa chữ và giữ lại mặt nền chứa bóng đổ `bg`.
    - Chia chuẩn hóa: `norm = cv2.divide(gray, bg, scale=255)` để làm phẳng độ sáng nền.
    """
    _ = cfg
    return gray.copy()


def denoise_image(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Bước 3: Khử nhiễu hạt trên ảnh xám trước khi tăng tương phản và nhị phân hóa.

    TODO (TV2 - Tuần 3):
    - Nếu `cfg["denoise_method"] == "median"`: dùng `cv2.medianBlur(gray, cfg["denoise_ksize"])`.
    - Nếu `cfg["denoise_method"] == "bilateral"`: dùng `cv2.bilateralFilter(...)` để giữ sắc biên chữ.
    """
    _ = cfg
    return gray.copy()


def apply_clahe(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Bước 4: Tăng cường độ tương phản cục bộ bằng CLAHE.

    TODO (TV2 - Tuần 3):
    - Khởi tạo `clahe = cv2.createCLAHE(clipLimit=cfg["clahe_clip_limit"], tileGridSize=cfg["clahe_tile_grid"])`.
    - Trả về `clahe.apply(gray)`.
    """
    _ = cfg
    return gray.copy()


def apply_threshold(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Bước 5: Nhị phân hóa ảnh tài liệu để tạo nền giấy trắng sạch và chữ đen rõ nét.

    TODO (TV2 - Tuần 2):
    Hỗ trợ 3 lựa chọn trong `cfg["threshold_method"]` (phục vụ cả sản phẩm và thí nghiệm Tuần 5 của TV3):
    - `"adaptive_gaussian"`: dùng `cv2.adaptiveThreshold(..., cv2.ADAPTIVE_THRESH_GAUSSIAN_C, ...)`
    - `"adaptive_mean"`: dùng `cv2.adaptiveThreshold(..., cv2.ADAPTIVE_THRESH_MEAN_C, ...)`
    - `"otsu"`: dùng `cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)`
    """
    _ = cfg
    return gray.copy()


def enhance(
    image: np.ndarray,
    remove_shadow: bool = True,
    denoise: bool = True,
    use_clahe: bool = True,
    binarize: bool = True,
    config: dict[str, Any] | None = None,
) -> np.ndarray:
    """Hàm giao diện chính: Tăng cường chất lượng ảnh tài liệu sau khi đã nắn phẳng (Stub v0).

    CHÚ Ý: Không thay đổi tên hàm và các tham số cờ (`remove_shadow`, `denoise`, `use_clahe`,
    `binarize`) vì TV3 sẽ bật/tắt các cờ này khi chạy thí nghiệm Ablation Study ở Tuần 5.

    Args:
        image: Ảnh tài liệu phẳng đầu vào (`np.ndarray`, `HxWx3` hoặc `HxW`, dtype `uint8`).
        remove_shadow: Bật/tắt bước ước lượng nền khử bóng đổ (`remove_shadow_bg`).
        denoise: Bật/tắt bước lọc khử nhiễu (`denoise_image`).
        use_clahe: Bật/tắt bước tăng tương phản cục bộ (`apply_clahe`).
        binarize: Bật/tắt bước nhị phân hóa tài liệu (`apply_threshold`).
        config: Từ điển tham số ghi đè lên `DEFAULT_ENHANCE_CONFIG`.

    Returns:
        Ảnh tài liệu đã tăng cường chất lượng (`np.ndarray`, 1 kênh `HxW`, dtype `uint8`).
    """
    if image is None or image.size == 0:
        raise ValueError("Ảnh đầu vào không hợp lệ (None hoặc rỗng).")

    cfg = {**DEFAULT_ENHANCE_CONFIG, **(config or {})}

    out = to_grayscale(image)
    if remove_shadow:
        out = remove_shadow_bg(out, cfg)
    if denoise:
        out = denoise_image(out, cfg)
    if use_clahe:
        out = apply_clahe(out, cfg)
    if binarize:
        out = apply_threshold(out, cfg)

    return out
