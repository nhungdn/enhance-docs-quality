"""Script chạy đánh giá thực nghiệm toàn hệ thống (Ablation, Ngưỡng, Fallback).

================================================================================
PHÂN CÔNG: Thành viên 3 (TV3) sở hữu và chỉnh sửa file này.
Các thành viên khác KHÔNG sửa file này để tránh xung đột Git.
================================================================================

Lộ trình công việc của TV3 trong file này:
- Tuần 2: Đọc `data/metadata.csv`, chạy thử hàm đánh giá góc (`IoU`, `corner_error`) và `PSNR`/`SSIM`.
- Tuần 3: Thống kê số lượng ảnh theo từng nhóm điều kiện (`condition_group`).
- Tuần 4: Chạy đánh giá Baseline lần 1 trên toàn bộ tập dữ liệu.
- Tuần 5:
    + Chạy thí nghiệm Ablation Study (bật/tắt `remove_shadow`, `denoise`, `use_clahe`, `binarize`).
    + Chạy thí nghiệm so sánh phương pháp nhị phân hóa (`otsu` vs `adaptive_mean` vs `adaptive_gaussian`).
- Tuần 6: Đánh giá riêng các ca `is_valid == False` khi dùng góc tự động so với khi dùng góc chuẩn (mô phỏng kéo tay).
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import process_document
from experiments.metrics import (
    compute_contrast_and_uniformity,
    compute_corner_error,
    compute_polygon_iou,
)


def run_baseline_evaluation(metadata_csv: Path, limit: int | None = None) -> list[dict]:
    """Chạy đánh giá pipeline trên các ảnh trong `data/metadata.csv`.

    TODO (TV3 - Tuần 4 & 5):
    - Mở rộng hàm này để lưu kết quả ra bảng CSV và in bảng Markdown phục vụ Chương 7 của báo cáo.
    """
    results: list[dict] = []
    with metadata_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if limit is not None:
        rows = rows[:limit]

    for row in rows:
        img_path = PROJECT_ROOT / row["file_path"]
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        gt_corners = np.array(
            [
                [float(row["tl_x"]), float(row["tl_y"])],
                [float(row["tr_x"]), float(row["tr_y"])],
                [float(row["br_x"]), float(row["br_y"])],
                [float(row["bl_x"]), float(row["bl_y"])],
            ],
            dtype=np.float32,
        )

        out = process_document(img)
        pred_corners = out["corners_used"]
        err_px = compute_corner_error(pred_corners, gt_corners)
        iou = compute_polygon_iou(pred_corners, gt_corners, img.shape[:2])
        quality = compute_contrast_and_uniformity(out["enhanced_image"])

        results.append(
            {
                "image_id": row["image_id"],
                "condition_group": row["condition_group"],
                "is_valid": out["detection"]["is_valid"],
                "corner_error_px": round(err_px, 2),
                "polygon_iou": round(iou, 4),
                "bg_std": quality["bg_std"],
                "fg_bg_contrast": quality["fg_bg_contrast"],
                "total_ms": out["timing_ms"]["total_ms"],
            }
        )

    return results


if __name__ == "__main__":
    csv_path = PROJECT_ROOT / "data" / "metadata.csv"
    sample_res = run_baseline_evaluation(csv_path, limit=5)
    print(f"Evaluated {len(sample_res)} sample images successfully:")
    for item in sample_res:
        print(" ", item)
