"""Package `core`: Chứa 3 hàm giao diện cốt lõi của hệ thống quét và cải thiện chất lượng tài liệu.

================================================================================
CHÚ Ý: File này cố định giao diện import chung cho toàn dự án.
Các thành viên KHÔNG cần chỉnh sửa file này trong quá trình làm việc.
================================================================================

Các hàm chính:
- `detect_corners`: Phát hiện 4 góc tài liệu và kiểm tra tứ giác hợp lệ (TV1 - `core/detector.py`).
- `warp_with_corners`: Biến đổi phối cảnh làm phẳng tài liệu từ 4 góc (TV1 - `core/warp.py`).
- `enhance`: Khử bóng, khử nhiễu, tăng tương phản CLAHE và nhị phân hóa (TV2 - `core/enhancer.py`).
- `process_document`: Luồng tích hợp Pipeline end-to-end (TV4 - `core/pipeline.py`).
"""

from .detector import detect_corners, order_corners, validate_quadrilateral
from .warp import compute_output_dimensions, warp_with_corners
from .enhancer import enhance
from .pipeline import process_document

__all__ = [
    "detect_corners",
    "order_corners",
    "validate_quadrilateral",
    "compute_output_dimensions",
    "warp_with_corners",
    "enhance",
    "process_document",
]
