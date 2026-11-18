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
import cv2
import numpy as np

from .detector import detect_corners, order_corners
from .warp import warp_with_corners
from .enhancer import enhance


def _is_inner_border_on_clean_page(image: np.ndarray, corners: np.ndarray) -> bool:
    """Kiểm tra xem tứ giác tìm được có phải là khung kẻ trang trí bên trong một trang giấy đã thẳng sẵn hay không.

    Khi người dùng tải lên một trang văn bản/trang bìa đã được căn thẳng sát mép ảnh
    (nền ngoài khung tứ giác là lề giấy trắng đồng nhất), `detect_corners` của TV1 có thể
    bắt nhầm vào khung viền chữ nhật trang trí bên trong trang bìa và cắt mất lề giấy.

    Hàm này kiểm tra vùng lề nằm ngoài tứ giác `corners`:
    - Nếu phần lớn điểm ảnh bên ngoài tứ giác đều có màu trắng sáng đồng nhất
      (tỷ lệ điểm sáng >= 235 đạt trên 88% và độ sáng trung bình > 242),
      đó là lề giấy trắng của trang tài liệu -> không cắt bỏ lề này.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

    pts = np.round(corners).astype(np.int32).reshape((-1, 1, 2))
    quad_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(quad_mask, [pts], 255)

    # Giãn nhẹ mặt nạ tứ giác để loại trừ chính đường viền đen của khung trang trí
    pad = max(6, int(round(min(h, w) * 0.02)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (pad, pad))
    quad_mask = cv2.dilate(quad_mask, kernel, iterations=1)

    outside_pixels = gray[quad_mask == 0]
    # Nếu tứ giác đã chiếm gần trọn ảnh (> 96%) thì không cần can thiệp
    if outside_pixels.size < 0.04 * h * w:
        return False

    bright_ratio = float((outside_pixels >= 225).mean())
    mean_outside = float(outside_pixels.mean())

    # Lề ngoài trắng sáng (hơn 85% điểm ảnh >= 225 và trung bình >= 235) -> đây là lề trang giấy
    return bright_ratio >= 0.85 and mean_outside >= 235.0


def _refine_document_appearance(
    shadow_free_gray: np.ndarray,
    hard_binary: np.ndarray | None = None,
) -> np.ndarray:
    """Làm trắng nền sạch và bảo toàn độ sắc nét mượt mà (anti-aliasing) của nét chữ, con dấu.

    Khắc phục hiện tượng chữ cỡ nhỏ/con dấu bị phình to, dính bết và răng cưa khi dùng
    `medianBlur(3)` + `CLAHE` + `adaptiveThreshold` nhị phân cứng trong `core/enhancer.py`:
    1. Áp dụng Unsharp Masking nhẹ lên ảnh xám đã khử bóng để khôi phục độ sắc nét của ký tự.
    2. Dùng mặt nạ ngưỡng thích nghi kết hợp lọc bỏ các chấm nhiễu cô lập (< 4 pixel) để xác định vùng nền giấy.
    3. Đưa toàn bộ nền giấy về trắng tinh (`255`), đồng thời kéo giãn tương phản mềm cho các điểm ảnh
       thuộc nét chữ để chữ đen đậm rõ nhưng vẫn giữ biên xám chống răng cưa mượt mà.
    """
    h, w = shadow_free_gray.shape[:2]

    # 1. Làm sắc nét nhẹ (Unsharp Mask) giúp chữ sau warp không bị mờ
    gaussian_blur = cv2.GaussianBlur(shadow_free_gray, (0, 0), sigmaX=1.0)
    sharpened = cv2.addWeighted(shadow_free_gray, 1.45, gaussian_blur, -0.45, 0)

    # 2. Tạo mặt nạ tách chữ / nền bằng ngưỡng thích nghi với kích thước cửa sổ tỉ lệ theo ảnh
    block_size = max(25, int(round(min(h, w) / 28)))
    if block_size % 2 == 0:
        block_size += 1

    fg_mask = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        12,
    )

    # Nếu TV2 truyền sang mặt nạ nhị phân Otsu, kết hợp để không bắt nhiễu nền
    if hard_binary is not None and hard_binary.shape == fg_mask.shape:
        fg_mask = cv2.bitwise_and(fg_mask, cv2.bitwise_not(hard_binary))

    # Loại bỏ các hạt nhiễu đen li ti cô lập (diện tích <= 3 pixel) trên nền trắng
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, connectivity=8)
    if num_labels > 1:
        small_areas = stats[:, cv2.CC_STAT_AREA] <= 3
        small_areas[0] = False  # Giữ nhãn nền 0
        remove_mask = small_areas[labels]
        fg_mask[remove_mask] = 0

    # Nới nhẹ mặt nạ 1px bằng phép giãn có trọng số để giữ trọn viền anti-aliasing của nét chữ
    kernel_3x3 = np.ones((3, 3), dtype=np.uint8)
    fg_region = cv2.dilate(fg_mask, kernel_3x3, iterations=1) > 0

    # 3. Kéo giãn mức xám mềm (Soft Contrast Stretch) cho vùng nét chữ, nền ngoài trắng tuyệt đối (255)
    out = np.full((h, w), 255, dtype=np.uint8)
    if np.any(fg_region):
        fg_vals = sharpened[fg_region].astype(np.float32)
        p_low = float(np.percentile(fg_vals, 10))
        p_high = max(p_low + 25.0, float(np.percentile(fg_vals, 96)))

        # Đưa nét chữ về dải đậm rõ [0..245] nhưng vẫn giữ chuyển tiếp mượt ở mép chữ
        scaled = (fg_vals - p_low) / (p_high - p_low)
        scaled = np.clip(scaled, 0.0, 1.0)
        # Gamma > 1.0 ở vùng tối giúp thân chữ đậm chắc như bản in
        scaled = np.power(scaled, 1.25) * 245.0
        out[fg_region] = np.clip(np.round(scaled), 0, 255).astype(np.uint8)

    # Đảm bảo vùng nền خارج nét chữ trắng sạch 255
    out[~fg_region] = 255
    return out


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
            - `soft_binarize`: bool (mặc định `True` để giữ nét chữ mượt không bị bết dính;
              đặt `False` nếu muốn lấy trực tiếp ảnh nhị phân 0/255 thô từ `enhance`).

    Returns:
        Từ điển chứa kết quả từng bước của pipeline:
            - `"detection"`: Kết quả từ `detect_corners` (hoặc thông tin góc thủ công).
            - `"corners_used"`: Mảng `(4, 2)` góc `[TL, TR, BR, BL]` thực tế đã dùng.
            - `"warped_image"`: Ảnh sau khi cắt nền và làm phẳng (`warp_with_corners`).
            - `"enhanced_image"`: Ảnh sau khi tăng cường chất lượng (`enhance`).
            - `"timing_ms"`: Thời gian thực thi từng bước (ms) phục vụ báo cáo Mục 7.4.
    """
    cfg = config or {}
    h, w = image.shape[:2]

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

        # Bảo vệ chống cắt nhầm vào khung kẻ viền bên trong khi ảnh gốc đã là trang giấy trắng phẳng
        if (
            cfg.get("protect_inner_border", True)
            and detection.get("is_valid", False)
            and _is_inner_border_on_clean_page(image, corners_used)
        ):
            detection["inner_frame_corners"] = corners_used.copy()
            corners_used = np.array(
                [
                    [0.0, 0.0],
                    [float(w - 1), 0.0],
                    [float(w - 1), float(h - 1)],
                    [0.0, float(h - 1)],
                ],
                dtype=np.float32,
            )
            detection["corners"] = corners_used
    t1 = time.perf_counter()

    # Nếu 4 góc trùng đúng 4 góc khung ảnh gốc thì giữ nguyên ảnh gốc tránh nội suy làm mờ chữ
    full_page_corners = np.array(
        [[0.0, 0.0], [float(w - 1), 0.0], [float(w - 1), float(h - 1)], [0.0, float(h - 1)]],
        dtype=np.float32,
    )
    if cfg.get("output_size") is None and np.allclose(corners_used, full_page_corners, atol=1.5):
        warped_image = image.copy()
    else:
        warped_image = warp_with_corners(
            image=image,
            corners=corners_used,
            output_size=cfg.get("output_size"),
        )
    t2 = time.perf_counter()

    remove_shadow = cfg.get("remove_shadow", True)
    denoise = cfg.get("denoise", True)
    use_clahe = cfg.get("use_clahe", True)
    binarize = cfg.get("binarize", True)
    enhance_cfg = dict(cfg.get("enhance") or {})

    # Tự động chọn kích thước nhân khử bóng tỉ lệ với độ phân giải ảnh để không làm tối chữ đậm/con dấu
    if "bg_kernel_size" not in enhance_cfg:
        wh_min = min(warped_image.shape[:2])
        auto_ksize = max(31, int(round(wh_min / 18)))
        if auto_ksize % 2 == 0:
            auto_ksize += 1
        enhance_cfg["bg_kernel_size"] = auto_ksize

    if binarize and cfg.get("soft_binarize", True):
        # Lấy ảnh đã khử bóng từ hàm enhance() của TV2 (tắt medianBlur và CLAHE thô để không làm bết chữ)
        shadow_free = enhance(
            image=warped_image,
            remove_shadow=remove_shadow,
            denoise=False,
            use_clahe=False,
            binarize=False,
            config=enhance_cfg,
        )
        hard_bin = None
        if str(enhance_cfg.get("threshold_method", "")).lower() == "otsu":
            hard_bin = enhance(
                image=shadow_free,
                remove_shadow=False,
                denoise=False,
                use_clahe=False,
                binarize=True,
                config=enhance_cfg,
            )
        enhanced_image = _refine_document_appearance(shadow_free, hard_binary=hard_bin)
    else:
        enhanced_image = enhance(
            image=warped_image,
            remove_shadow=remove_shadow,
            denoise=denoise,
            use_clahe=use_clahe,
            binarize=binarize,
            config=enhance_cfg,
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
