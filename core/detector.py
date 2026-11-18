"""Module phát hiện biên và 4 góc tài liệu."""

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

    Ảnh BGR được chuyển sang grayscale; ảnh xám được giữ nguyên trước khi lọc.
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

    Thuật toán:
    1. Dò biên bằng Canny với ngưỡng thấp/cao từ config.
    2. Áp dụng phép đóng hình thái học (Morphological Closing) để nối các đoạn biên
       bị đứt gãy, giúp contour tài liệu liên tục hơn.

    Args:
        blurred: Ảnh xám đã làm mịn Gaussian, dtype uint8.
        cfg: Từ điển tham số (canny_low, canny_high, morph_ksize).

    Returns:
        Ảnh biên nhị phân (uint8), cùng kích thước với `blurred`.
    """
    # --- Bước 2a: Phát hiện biên Canny ---
    edges = cv2.Canny(
        blurred,
        cfg.get("canny_low", 50),
        cfg.get("canny_high", 150),
    )

    # --- Bước 2b: Phép đóng hình thái học để nối đoạn biên đứt ---
    morph_ksize = cfg.get("morph_ksize", (5, 5))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, morph_ksize)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    return closed


def find_document_contour(
    edges: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[np.ndarray | None, list[np.ndarray]]:
    """Bước 3: Tìm các contour lớn nhất và xấp xỉ đa giác bằng `approxPolyDP`.

    Thuật toán:
    1. Tìm tất cả contour từ ảnh biên.
    2. Sắp xếp contour theo diện tích giảm dần, lấy top-k ứng viên.
    3. Xấp xỉ các contour thành tứ giác và kiểm tra tính hợp lệ hình học.
    4. Trả về ứng viên hợp lệ đầu tiên; nếu không có ứng viên hợp lệ, trả về
       tứ giác đầu tiên để cung cấp lý do fallback cụ thể.

    Args:
        edges: Ảnh biên nhị phân (uint8) từ `detect_edges`.
        cfg: Từ điển tham số (top_k_contours, approx_eps_ratio).

    Returns:
        Tuple gồm:
        - `candidate_quad`: ndarray shape (4, 2) nếu tìm được tứ giác, hoặc None.
        - `top_contours`: Danh sách top-k contour lớn nhất (dùng cho fallback).
    """
    # --- Bước 3a: Tìm tất cả contour ---
    contours, _ = cv2.findContours(
        edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None, []

    # --- Bước 3b: Sắp xếp theo diện tích, lấy top-k ---
    top_k = cfg.get("top_k_contours", 5)
    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
    top_contours = sorted_contours[:top_k]

    # --- Bước 3c: Ưu tiên tứ giác hợp lệ thay vì dừng ở tứ giác đầu tiên ---
    eps_ratio = cfg.get("approx_eps_ratio", 0.02)
    first_quad = None
    for contour in top_contours:
        peri = cv2.arcLength(contour, True)
        if peri < 1.0:
            continue
        approx = cv2.approxPolyDP(contour, eps_ratio * peri, True)
        if len(approx) == 4:
            candidate_quad = approx.reshape(4, 2).astype(np.float32)
            if first_quad is None:
                first_quad = candidate_quad
            is_valid, _ = validate_quadrilateral(
                candidate_quad, edges.shape[:2], cfg
            )
            if is_valid:
                return candidate_quad, top_contours

    return first_quad, top_contours


def validate_quadrilateral(
    corners: np.ndarray | None,
    image_shape: tuple[int, int],
    cfg: dict[str, Any],
) -> tuple[bool, str | None]:
    """Bước 4: Kiểm tra tứ giác ứng viên có hợp lệ về mặt hình học hay không.

    Kiểm tra 4 tiêu chí lần lượt:
    1. `corners` không phải None và có đúng 4 đỉnh hình dạng (4, 2).
    2. Đa giác lồi (`cv2.isContourConvex`).
    3. Diện tích tứ giác >= `cfg["min_area_ratio"] * H * W`.
    4. Mỗi góc trong tại 4 đỉnh nằm trong khoảng [min_angle_deg, max_angle_deg].

    Args:
        corners: Mảng ndarray (4, 2) các đỉnh ứng viên, hoặc None.
        image_shape: Tuple (H, W) kích thước ảnh gốc.
        cfg: Từ điển tham số (min_area_ratio, min_angle_deg, max_angle_deg).

    Returns:
        Tuple `(is_valid, fallback_reason)`:
        - `is_valid`: True nếu đạt cả 4 tiêu chí.
        - `fallback_reason`: Chuỗi mô tả lý do lỗi, hoặc None nếu hợp lệ.
    """
    # --- Tiêu chí 1: Kiểm tra corners không None và đúng 4 đỉnh ---
    if corners is None:
        return False, "no_contour_found"
    pts = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
    if pts.shape[0] != 4:
        return False, "not_4_vertices"

    # --- Tiêu chí 2: Kiểm tra tính lồi ---
    pts_int = pts.reshape(-1, 1, 2).astype(np.int32)
    if not cv2.isContourConvex(pts_int):
        return False, "not_convex"

    # --- Tiêu chí 3: Kiểm tra diện tích ---
    h, w = image_shape[:2]
    min_area_ratio = cfg.get("min_area_ratio", 0.15)
    area = float(cv2.contourArea(pts_int))
    if area < min_area_ratio * h * w:
        return False, "area_too_small"

    # --- Tiêu chí 4: Kiểm tra góc trong tại mỗi đỉnh ---
    min_ang = cfg.get("min_angle_deg", 45.0)
    max_ang = cfg.get("max_angle_deg", 135.0)
    n = 4
    for i in range(n):
        # Vector từ đỉnh i đến đỉnh trước và sau
        prev_pt = pts[(i - 1) % n]
        curr_pt = pts[i]
        next_pt = pts[(i + 1) % n]
        v1 = prev_pt - curr_pt
        v2 = next_pt - curr_pt
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return False, "degenerate_vertex"
        cos_angle = float(np.dot(v1, v2) / (norm1 * norm2))
        # Kẹp [-1, 1] tránh lỗi float
        cos_angle = max(-1.0, min(1.0, cos_angle))
        angle_deg = float(np.degrees(np.arccos(cos_angle)))
        if not (min_ang <= angle_deg <= max_ang):
            return False, f"bad_angle_{i}_deg_{angle_deg:.1f}"

    return True, None


def get_fallback_corners(
    contours: list[np.ndarray],
    image_shape: tuple[int, int],
    min_area_ratio: float = 0.15,
) -> np.ndarray:
    """Sinh 4 góc gợi ý khi phát hiện tự động thất bại (`is_valid == False`).

    Chiến lược:
    - Nếu danh sách `contours` không rỗng và contour lớn nhất đủ lớn để có thể là trang,
      dùng `cv2.minAreaRect` + `cv2.boxPoints` để lấy 4 đỉnh hộp bao nhỏ nhất.
    - Ngược lại, trả về khung chữ nhật mặc định cách đều lề ảnh 8% để người dùng
      có thể kéo góc từ vị trí hợp lý.

    Args:
        contours: Danh sách top-k contour từ `find_document_contour`.
        image_shape: Tuple (H, W) kích thước ảnh gốc.
        min_area_ratio: Tỉ lệ diện tích tối thiểu của trang so với ảnh.

    Returns:
        Mảng float32 shape (4, 2) theo thứ tự [TL, TR, BR, BL].
    """
    h, w = image_shape[:2]

    if contours:
        largest = contours[0]
        area = cv2.contourArea(largest)
        if area >= min_area_ratio * h * w:
            rect = cv2.minAreaRect(largest)
            box_pts = cv2.boxPoints(rect)             # shape (4, 2), float32
            box_pts = np.asarray(box_pts, dtype=np.float32)
            return order_corners(box_pts)

    # --- Fallback mặc định: khung cách lề 8% ---
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
    """Phát hiện 4 góc trang tài liệu trong ảnh chụp.

    CHÚ Ý: Không thay đổi tên hàm và các khóa trả về trong dict để đảm bảo tương thích
    với `core/pipeline.py`, `experiments/evaluate.py` (TV3) và `web/app.py` (TV4).
    Ảnh cao hơn `proc_height` được thu nhỏ khi dò biên; tọa độ trả về luôn theo ảnh gốc.

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

    proc_height = cfg.get("proc_height")
    if proc_height is not None and int(proc_height) < 1:
        raise ValueError("config['proc_height'] phải lớn hơn 0 hoặc là None.")

    processing_image = image
    if proc_height is not None and h > int(proc_height):
        proc_width = max(1, int(round(w * int(proc_height) / h)))
        processing_image = cv2.resize(
            image,
            (proc_width, int(proc_height)),
            interpolation=cv2.INTER_AREA,
        )

    # Luồng khung gọi các hàm con của TV1 trên ảnh đã thu nhỏ nếu cần.
    proc_h, proc_w = processing_image.shape[:2]
    blurred = preprocess_for_edges(processing_image, cfg)
    edges = detect_edges(blurred, cfg)
    candidate_quad, top_contours = find_document_contour(edges, cfg)
    is_valid, reason = validate_quadrilateral(candidate_quad, (proc_h, proc_w), cfg)

    if is_valid and candidate_quad is not None:
        corners = order_corners(candidate_quad)
        confidence = 1.0
    else:
        corners = get_fallback_corners(
            top_contours,
            (proc_h, proc_w),
            min_area_ratio=cfg.get("min_area_ratio", 0.15),
        )
        confidence = 0.0

    corners[:, 0] *= w / proc_w
    corners[:, 1] *= h / proc_h

    return {
        "corners": corners,
        "is_valid": is_valid,
        "confidence": confidence,
        "fallback_reason": reason,
        "debug_info": {
            "image_shape": (h, w),
            "processing_shape": (proc_h, proc_w),
            "config_used": cfg,
            "num_top_contours": len(top_contours),
            "status": "tv1_complete",
        },
    }
