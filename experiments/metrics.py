"""Module định nghĩa các độ đo đánh giá định lượng (Không dùng OCR).

================================================================================
PHÂN CÔNG: Thành viên 3 (TV3) sở hữu và chỉnh sửa file này.
Các thành viên khác KHÔNG sửa file này để tránh xung đột Git.
================================================================================

Các nhóm độ đo chính:
1. Đánh giá phát hiện góc & biên tài liệu (TV1):
   - `compute_corner_error`: Sai số khoảng cách Euclid trung bình tại 4 đỉnh (theo pixel).
   - `compute_polygon_iou`: Chỉ số Intersection over Union (IoU) giữa tứ giác dự đoán và nhãn chuẩn.
2. Đánh giá chất lượng ảnh sau làm phẳng & tăng cường (TV2):
   - `compute_psnr`: Peak Signal-to-Noise Ratio (dB) so với ảnh tham chiếu chuẩn.
   - `compute_ssim`: Structural Similarity Index so với ảnh tham chiếu chuẩn.
   - `compute_contrast_and_uniformity`: Độ đồng nhất nền sáng và độ tương phản chữ–nền
     (dùng được cho cả ảnh chụp thực tế không có bản scan chuẩn).
"""

from __future__ import annotations

import cv2
import numpy as np


def compute_corner_error(pred_corners: np.ndarray, gt_corners: np.ndarray) -> float:
    """Tính sai số khoảng cách Euclid trung bình (pixel) giữa 4 góc dự đoán và nhãn chuẩn.

    Cả `pred_corners` và `gt_corners` đều có kích thước `(4, 2)` theo thứ tự `[TL, TR, BR, BL]`.
    """
    pred = np.asarray(pred_corners, dtype=np.float32).reshape(4, 2)
    gt = np.asarray(gt_corners, dtype=np.float32).reshape(4, 2)
    return float(np.linalg.norm(pred - gt, axis=1).mean())


def compute_polygon_iou(
    pred_corners: np.ndarray,
    gt_corners: np.ndarray,
    image_shape: tuple[int, int],
) -> float:
    """Tính chỉ số IoU (Intersection over Union) giữa tứ giác dự đoán và tứ giác chuẩn.

    TODO (TV3 - Tuần 2):
    - Tạo 2 mặt nạ nhị phân `mask_pred` và `mask_gt` kích thước `(H, W)` từ `image_shape`.
    - Tô đặc 2 tứ giác bằng `cv2.fillPoly`.
    - Tính `intersection = np.logical_and(mask_pred, mask_gt).sum()`
      và `union = np.logical_or(mask_pred, mask_gt).sum()`.
    - Trả về `intersection / union`.
    """
    h, w = image_shape[:2]
    mask_pred = np.zeros((h, w), dtype=np.uint8)
    mask_gt = np.zeros((h, w), dtype=np.uint8)

    pts_pred = np.round(np.asarray(pred_corners, dtype=np.float32)).astype(np.int32).reshape((-1, 1, 2))
    pts_gt = np.round(np.asarray(gt_corners, dtype=np.float32)).astype(np.int32).reshape((-1, 1, 2))

    cv2.fillPoly(mask_pred, [pts_pred], 1)
    cv2.fillPoly(mask_gt, [pts_gt], 1)

    inter = float(np.logical_and(mask_pred > 0, mask_gt > 0).sum())
    union = float(np.logical_or(mask_pred > 0, mask_gt > 0).sum())
    return inter / union if union > 0 else 0.0


def compute_psnr(pred_img: np.ndarray, ref_img: np.ndarray) -> float:
    r"""Tính PSNR (dB) giữa ảnh đầu ra và ảnh phẳng tham chiếu chuẩn.

    TODO (TV3 - Tuần 2):
    - Đảm bảo 2 ảnh cùng kích thước và cùng số kênh (chuyển về xám nếu cần).
    - Sử dụng `cv2.PSNR(pred_img, ref_img)` hoặc công thức $10 \log_{10}(255^2 / \text{MSE})$.
    """
    if pred_img.shape != ref_img.shape:
        pred_img = cv2.resize(pred_img, (ref_img.shape[1], ref_img.shape[0]))
    return float(cv2.PSNR(pred_img, ref_img))


def compute_ssim(pred_img: np.ndarray, ref_img: np.ndarray) -> float:
    """Tính chỉ số tương đồng cấu trúc SSIM trong khoảng [-1, 1] (cao hơn là tốt hơn).

    TODO (TV3 - Tuần 2):
    - Cài đặt công thức SSIM trên cửa sổ Gaussian cục bộ hoặc toàn ảnh giữa `pred_img` và `ref_img`.
    """
    if pred_img.ndim == 3:
        pred_img = cv2.cvtColor(pred_img, cv2.COLOR_BGR2GRAY)
    if ref_img.ndim == 3:
        ref_img = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    if pred_img.shape != ref_img.shape:
        pred_img = cv2.resize(pred_img, (ref_img.shape[1], ref_img.shape[0]))

    x = pred_img.astype(np.float64)
    y = ref_img.astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    mu_x = cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_y = cv2.GaussianBlur(y, (11, 11), 1.5)
    sigma_x2 = cv2.GaussianBlur(x * x, (11, 11), 1.5) - mu_x * mu_x
    sigma_y2 = cv2.GaussianBlur(y * y, (11, 11), 1.5) - mu_y * mu_y
    sigma_xy = cv2.GaussianBlur(x * y, (11, 11), 1.5) - mu_x * mu_y

    ssim_map = ((2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)) / (
        (mu_x * mu_x + mu_y * mu_y + c1) * (sigma_x2 + sigma_y2 + c2)
    )
    return float(ssim_map.mean())


def compute_contrast_and_uniformity(enhanced_img: np.ndarray) -> dict[str, float]:
    """Đánh giá độ đồng nhất nền giấy và độ tương phản chữ–nền (không cần ảnh tham chiếu).

    TODO (TV3 - Tuần 3):
    - Dùng ngưỡng Otsu tách các điểm ảnh thành 2 lớp: tiền cảnh (chữ tối) và hậu cảnh (nền sáng).
    - Tính độ lệch chuẩn của vùng nền `bg_std` (càng nhỏ chứng tỏ bóng đổ càng được khử sạch).
    - Tính độ chênh lệch trung bình `fg_bg_contrast = mean(bg) - mean(fg)` (càng lớn chữ càng rõ).
    """
    gray = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2GRAY) if enhanced_img.ndim == 3 else enhanced_img
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bg_pixels = gray[mask > 0]
    fg_pixels = gray[mask == 0]

    bg_mean = float(bg_pixels.mean()) if bg_pixels.size > 0 else 255.0
    bg_std = float(bg_pixels.std()) if bg_pixels.size > 0 else 0.0
    fg_mean = float(fg_pixels.mean()) if fg_pixels.size > 0 else 0.0

    return {
        "bg_std": round(bg_std, 2),
        "fg_bg_contrast": round(bg_mean - fg_mean, 2),
    }
