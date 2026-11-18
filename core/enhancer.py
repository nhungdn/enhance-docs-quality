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
    "bg_kernel_size": 31,
    "denoise_method": "median",          # "median" hoặc "bilateral"
    "denoise_ksize": 3,
    "bilateral_d": 9,
    "bilateral_sigma_color": 50,
    "bilateral_sigma_space": 50,
    "clahe_clip_limit": 2.0,
    "clahe_tile_grid": (8, 8),
    "threshold_method": "adaptive_gaussian",
    "block_size": 21,
    "c_offset": 10,
}

def _validate_gray(gray: np.ndarray) -> np.ndarray:
    """Kiểm tra ảnh xám đầu vào và chuẩn hóa về uint8."""
    if gray is None or not isinstance(gray, np.ndarray) or gray.size == 0:
        raise ValueError("Ảnh đầu vào không hợp lệ (None hoặc rỗng).")
    if gray.ndim != 2:
        raise ValueError("Hàm này yêu cầu ảnh xám một kênh (HxW).")
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    return gray


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Chuyển ảnh BGR 3 kênh sang ảnh đa mức xám 1 kênh uint8."""
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Ảnh đầu vào không hợp lệ (None hoặc rỗng).")

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    if image.ndim == 2:
        return image.copy()

    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    raise ValueError("Ảnh phải có dạng HxW (xám) hoặc HxWx3 (BGR).")




def remove_shadow_bg(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """
    Ước lượng nền sáng bằng Morphological Closing rồi chia chuẩn hóa.

    Closing giúp lấp các vùng tối nhỏ (ví dụ nét chữ) để ước lượng nền
    chiếu sáng. Kernel cần đủ lớn so với độ dày nét chữ và kích thước ảnh.
    """
    gray = _validate_gray(gray)
    cfg = cfg or {}

    ksize = int(cfg.get("bg_kernel_size", DEFAULT_ENHANCE_CONFIG["bg_kernel_size"]))
    ksize = max(3, ksize)
    if ksize % 2 == 0:
        ksize += 1

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (ksize, ksize)
    )
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    # Tránh chia cho 0 tại các điểm nền rất tối.
    background = np.maximum(background, 1)
    corrected = cv2.divide(gray, background, scale=255)

    # Giữ dải mức xám đầy đủ sau chuẩn hóa.
    corrected = cv2.normalize(
        corrected, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX
    )
    return corrected.astype(np.uint8)


def denoise_image(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Khử nhiễu bằng Median hoặc Bilateral theo cấu hình."""
    gray = _validate_gray(gray)
    cfg = cfg or {}

    method = str(cfg.get("denoise_method", "median")).lower()

    if method == "median":
        ksize = int(cfg.get("denoise_ksize", 3))
        ksize = max(3, ksize)
        if ksize % 2 == 0:
            ksize += 1
        return cv2.medianBlur(gray, ksize)

    if method == "bilateral":
        d = int(cfg.get("bilateral_d", 9))
        sigma_color = float(cfg.get("bilateral_sigma_color", 50))
        sigma_space = float(cfg.get("bilateral_sigma_space", 50))
        return cv2.bilateralFilter(
            gray, d, sigma_color, sigma_space
        )

    raise ValueError(
        "denoise_method không hợp lệ. Chọn 'median' hoặc 'bilateral'."
    )


def apply_clahe(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Tăng cường tương phản cục bộ bằng CLAHE."""
    gray = _validate_gray(gray)
    cfg = cfg or {}

    clip_limit = float(
        cfg.get("clahe_clip_limit", DEFAULT_ENHANCE_CONFIG["clahe_clip_limit"])
    )
    tile_grid = tuple(
        cfg.get("clahe_tile_grid", DEFAULT_ENHANCE_CONFIG["clahe_tile_grid"])
    )

    if clip_limit <= 0:
        raise ValueError("clahe_clip_limit phải lớn hơn 0.")
    if len(tile_grid) != 2 or int(tile_grid[0]) <= 0 or int(tile_grid[1]) <= 0:
        raise ValueError("clahe_tile_grid phải gồm 2 số nguyên dương.")

    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=(int(tile_grid[0]), int(tile_grid[1])),
    )
    return clahe.apply(gray)


def apply_threshold(gray: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """
    Nhị phân hóa ảnh, tạo chữ tối trên nền sáng.

    Hỗ trợ:
    - "otsu"
    - "adaptive_mean"
    - "adaptive_gaussian"
    """
    gray = _validate_gray(gray)
    cfg = cfg or {}

    method = str(cfg.get("threshold_method", "adaptive_gaussian")).lower()

    if method == "otsu":
        _, binary = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        return binary

    if method in ("adaptive_mean", "adaptive_gaussian"):
        block_size = int(cfg.get("block_size", 21))
        if block_size < 3:
            raise ValueError("block_size phải lớn hơn hoặc bằng 3.")
        if block_size % 2 == 0:
            raise ValueError("block_size phải là số lẻ.")

        c_offset = float(cfg.get("c_offset", 10))
        adaptive_method = (
            cv2.ADAPTIVE_THRESH_MEAN_C
            if method == "adaptive_mean"
            else cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        )

        return cv2.adaptiveThreshold(
            gray,
            255,
            adaptive_method,
            cv2.THRESH_BINARY,
            block_size,
            c_offset,
        )

    raise ValueError(
        "threshold_method không hợp lệ. Chọn 'otsu', "
        "'adaptive_mean' hoặc 'adaptive_gaussian'."
    )


def enhance(
    image: np.ndarray,
    remove_shadow: bool = True,
    denoise: bool = True,
    use_clahe: bool = True,
    binarize: bool = True,
    config: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    Hàm giao diện chính: tăng cường chất lượng ảnh tài liệu đã nắn phẳng.

    Giữ nguyên tên hàm và tham số cờ để TV3 có thể bật/tắt từng bước
    trong Ablation Study.

    Args:
        image: Ảnh BGR (HxWx3) hoặc ảnh xám (HxW), uint8.
        remove_shadow: Bật/tắt bước loại bỏ bóng.
        denoise: Bật/tắt bước khử nhiễu.
        use_clahe: Bật/tắt bước tăng tương phản CLAHE.
        binarize: Bật/tắt bước nhị phân hóa.
        config: Các tham số ghi đè DEFAULT_ENHANCE_CONFIG.

    Returns:
        Ảnh xám hoặc nhị phân một kênh HxW, dtype uint8.
    """
    gray = to_grayscale(image)
    cfg = {**DEFAULT_ENHANCE_CONFIG, **(config or {})}

    out = gray

    if remove_shadow:
        out = remove_shadow_bg(out, cfg)

    if denoise:
        out = denoise_image(out, cfg)

    if use_clahe:
        out = apply_clahe(out, cfg)

    if binarize:
        out = apply_threshold(out, cfg)

    return out
