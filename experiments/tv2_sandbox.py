"""Script kiểm thử riêng dành cho Thành viên 2 (TV2).

================================================================================
PHÂN CÔNG: Thành viên 2 (TV2) toàn quyền sử dụng file này để:
- Chạy thử `enhance` trên các ảnh mẫu (đặc biệt là 10 ca có bóng đổ `doc_019`..`doc_024`).
- Xuất ảnh so sánh Trước/Sau khi khử bóng, CLAHE, và so sánh Otsu vs Adaptive Thresholding
  để đưa vào المục 2.5–2.7 và 8.2 của báo cáo.
- Lưu kết quả tạm vào `experiments/outputs/tv2/` (đã được `.gitignore` bỏ qua).
================================================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.enhancer import enhance


if __name__ == "__main__":
    out_dir = PROJECT_ROOT / "experiments" / "outputs" / "tv2"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Thử nghiệm trên một ảnh thuộc nhóm có bóng đổ (doc_019.jpg)
    sample_path = PROJECT_ROOT / "data" / "raw" / "doc_019.jpg"
    img = cv2.imread(str(sample_path))
    if img is not None:
        enhanced = enhance(img, remove_shadow=True, denoise=True, use_clahe=True, binarize=True)
        cv2.imwrite(str(out_dir / "doc_019_enhanced.jpg"), enhanced)
        print("TV2 sandbox test OK. Saved output to:", out_dir)
