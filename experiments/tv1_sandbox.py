"""Script kiểm thử riêng dành cho Thành viên 1 (TV1).

================================================================================
PHÂN CÔNG: Thành viên 1 (TV1) toàn quyền sử dụng file này để:
- Chạy thử `detect_corners` và `warp_with_corners` trên 20 ảnh mẫu ở Tuần 2 & Tuần 3.
- Vẽ hình minh họa 4 đỉnh phát hiện được lên ảnh để đưa vào المục 2.1–2.4 và 8.1 của báo cáo.
- Lưu kết quả tạm vào `experiments/outputs/tv1/` (đã được `.gitignore` bỏ qua, không sợ rác Git).
================================================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.detector import detect_corners
from core.warp import warp_with_corners


def draw_detected_corners(image: np.ndarray, corners: np.ndarray, is_valid: bool) -> np.ndarray:
    """Vẽ tứ giác 4 góc [TL, TR, BR, BL] lên bản sao của ảnh để kiểm tra trực quan."""
    vis = image.copy()
    pts = np.round(corners).astype(np.int32)
    color = (0, 200, 0) if is_valid else (0, 140, 255)
    cv2.polylines(vis, [pts.reshape((-1, 1, 2))], isClosed=True, color=color, thickness=3)

    labels = ["TL", "TR", "BR", "BL"]
    for (x, y), label in zip(pts, labels):
        cv2.circle(vis, (int(x), int(y)), 8, (0, 0, 255), -1)
        cv2.putText(vis, label, (int(x) + 10, int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    return vis


if __name__ == "__main__":
    out_dir = PROJECT_ROOT / "experiments" / "outputs" / "tv1"
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_path = PROJECT_ROOT / "data" / "raw" / "doc_001.jpg"
    img = cv2.imread(str(sample_path))
    if img is not None:
        det = detect_corners(img)
        vis = draw_detected_corners(img, det["corners"], det["is_valid"])
        warped = warp_with_corners(img, det["corners"])
        cv2.imwrite(str(out_dir / "doc_001_corners.jpg"), vis)
        cv2.imwrite(str(out_dir / "doc_001_warped.jpg"), warped)
        print("TV1 sandbox test OK. Saved outputs to:", out_dir)
