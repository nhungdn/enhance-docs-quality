"""Ứng dụng Web phục vụ quét và cải thiện chất lượng tài liệu.

================================================================================
PHÂN CÔNG: Thành viên 4 (TV4) sở hữu và chỉnh sửa thư mục `web/`.
Các thành viên khác KHÔNG sửa file trong `web/` để tránh xung đột Git.
================================================================================

Lộ trình công việc của TV4:
- Tuần 2: Dựng Web v0 cho phép người dùng tải ảnh lên (`POST /api/scan`) và nhận về
  ảnh kết quả sau khi chạy `core.process_document`.
- Tuần 3: Xây dựng giao diện so sánh Trước/Sau (Before/After) và nút tải ảnh kết quả (PNG/JPG).
- Tuần 4: Xây dựng giao diện Canvas kéo 4 góc thủ công khi `is_valid == False` (hoặc khi
  người dùng bấm "Chỉnh lại 4 góc"), gửi tọa độ 4 đỉnh về `POST /api/rewarp`.
- Tuần 5-6: Hiển thị thời gian xử lý từng bước, ảnh trung gian (warped vs enhanced), hoàn thiện UI.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from core import process_document


def handle_auto_scan(image: np.ndarray) -> dict[str, Any]:
    """Xử lý yêu cầu quét tự động khi người dùng tải ảnh lên.

    TODO (TV4 - Tuần 2):
    - Kết nối hàm này với endpoint `POST /api/scan` trong FastAPI/Flask.
    - Mã hóa `warped_image` và `enhanced_image` sang Base64 hoặc URL tĩnh để trả về JSON cho Frontend.
    """
    return process_document(image=image, manual_corners=None)


def handle_manual_rewarp(image: np.ndarray, corners_xy: list[list[float]]) -> dict[str, Any]:
    """Xử lý yêu cầu cắt và làm phẳng lại khi người dùng kéo 4 góc thủ công trên Web.

    TODO (TV4 - Tuần 4):
    - Kết nối hàm này với endpoint `POST /api/rewarp`.
    - Nhận mảng `corners_xy` dạng `[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]` ở hệ tọa độ ảnh gốc.
    - Gọi `process_document(image=image, manual_corners=np.array(corners_xy, dtype=np.float32))`.
    """
    manual_pts = np.asarray(corners_xy, dtype=np.float32).reshape(4, 2)
    return process_document(image=image, manual_corners=manual_pts)
