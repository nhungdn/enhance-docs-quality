"""Script kiểm thử riêng dành cho Thành viên 1."""

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

    available_paths = sorted((PROJECT_ROOT / "data" / "raw").glob("doc_*.jpg"))
    if not available_paths:
        raise FileNotFoundError("Không tìm thấy ảnh mẫu trong data/raw.")
    sample_count = min(20, len(available_paths))
    sample_indices = np.linspace(
        0, len(available_paths) - 1, sample_count, dtype=int
    )
    sample_paths = [available_paths[index] for index in sample_indices]

    valid_count = 0
    for sample_path in sample_paths:
        img = cv2.imread(str(sample_path))
        if img is None:
            raise ValueError(f"Không đọc được ảnh mẫu: {sample_path}")

        det = detect_corners(img)
        valid_count += int(det["is_valid"])
        vis = draw_detected_corners(img, det["corners"], det["is_valid"])
        warped = warp_with_corners(img, det["corners"])
        stem = sample_path.stem
        if not cv2.imwrite(str(out_dir / f"{stem}_corners.jpg"), vis):
            raise OSError(f"Không lưu được ảnh minh họa: {stem}")
        if not cv2.imwrite(str(out_dir / f"{stem}_warped.jpg"), warped):
            raise OSError(f"Không lưu được ảnh warp: {stem}")
        print(
            f"{stem}: is_valid={det['is_valid']}, "
            f"reason={det['fallback_reason']}, "
            f"corners={det['corners'].round(1).tolist()}"
        )

    print(
        f"Checked {len(sample_paths)} images; "
        f"{valid_count} detected automatically. Outputs: {out_dir}"
    )
