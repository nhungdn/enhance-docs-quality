"""Script khởi tạo bộ dữ liệu mẫu Tuần 1 (36 ảnh tài liệu đa điều kiện chụp + metadata).

Mục đích:
- Tạo 36 ảnh đầu tiên (`data/raw/doc_001.jpg` .. `data/raw/doc_036.jpg`) đại diện cho 6 nhóm điều kiện
  thu nhận ảnh thực tế (nền đơn giản, nghiêng phối cảnh mạnh, ánh sáng không đều, bóng đổ,
  nền đồng màu/phức tạp, và hóa đơn/biểu mẫu).
- Lưu kèm `data/metadata.csv` ghi nhận điều kiện chụp và tọa độ 4 góc chuẩn `[TL, TR, BR, BL]`
  để kiểm thử pipeline v0 ngay từ Tuần 1.
"""

from __future__ import annotations

import csv
from pathlib import Path
import cv2
import numpy as np


CONDITIONS = [
    ("normal_simple_bg", "Ánh sáng đều, nền tối tương phản cao, nghiêng nhẹ"),
    ("tilted_perspective", "Góc chụp nghiêng lớn, biến dạng phối cảnh mạnh"),
    ("uneven_lighting", "Ánh sáng không đều, gradient sáng-tối rõ rệt"),
    ("shadow_cast", "Có bóng đổ chéo/bóng điện thoại che một phần trang giấy"),
    ("similar_or_cluttered_bg", "Nền sáng màu gần giống màu giấy hoặc nhiều chi tiết"),
    ("receipt_and_table", "Biểu mẫu/hóa đơn có kẻ bảng và cỡ chữ nhỏ"),
]


def _render_clean_page(idx: int, cond_key: str, page_w: int = 600, page_h: int = 840) -> np.ndarray:
    """Tạo trang tài liệu phẳng có tiêu đề, đoạn văn bản và bảng biểu."""
    page = np.full((page_h, page_w, 3), 248, dtype=np.uint8)

    # Thêm nhiễu hạt giấy rất nhẹ
    rng = np.random.default_rng(1000 + idx)
    paper_grain = rng.integers(-4, 5, size=(page_h, page_w, 1), dtype=np.int16)
    page = np.clip(page.astype(np.int16) + paper_grain, 225, 255).astype(np.uint8)

    # Tiêu đề tài liệu
    cv2.putText(
        page,
        f"DAI HOC BACH KHOA - BAO CAO XLA #{idx:03d}",
        (45, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (25, 25, 25),
        2,
        cv2.LINE_AA,
    )
    cv2.line(page, (45, 82), (page_w - 45, 82), (60, 60, 60), 2)

    cv2.putText(
        page,
        f"Condition: {cond_key} | Sample ID: DOC-{idx:03d}",
        (45, 112),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (50, 50, 50),
        1,
        cv2.LINE_AA,
    )

    lines = [
        "1. Gioi thieu bai toan:",
        "   He thong quet va cai thien chat luong anh tai lieu chup",
        "   bang dien thoai di dong trong dieu kien thuc te.",
        "2. Cac buoc xu ly chinh trong Pipeline v0:",
        "   - Loc Gaussian va do bien Canny de tim contour.",
        "   - Xap xi da giac approxPolyDP tim 4 dinh trang giay.",
        "   - Bien doi phoi canh Homography 3x3 cat bo nen thua.",
        "   - Khu bong do, tang tuong phan CLAHE va nhi phan hoa.",
        "3. Ket qua mong doi:",
        "   - Anh phang, nen trang sach, chu den ro net nhu ban scan.",
    ]

    y = 155
    for line in lines:
        cv2.putText(
            page,
            line,
            (45, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (30, 30, 30),
            1,
            cv2.LINE_AA,
        )
        y += 34

    # Vẽ bảng biểu mẫu ở nửa dưới trang
    table_top = 520
    table_bottom = 740
    cv2.rectangle(page, (45, table_top), (page_w - 45, table_bottom), (40, 40, 40), 2)
    for row_y in range(table_top + 44, table_bottom, 44):
        cv2.line(page, (45, row_y), (page_w - 45, row_y), (80, 80, 80), 1)
    cv2.line(page, (190, table_top), (190, table_bottom), (80, 80, 80), 1)
    cv2.line(page, (390, table_top), (390, table_bottom), (80, 80, 80), 1)

    headers = [("Module", 65), ("Ham chinh", 205), ("Phu trach", 405)]
    for text, x_pos in headers:
        cv2.putText(
            page,
            text,
            (x_pos, table_top + 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )

    rows = [
        ("Corner Detect", "detect_corners()", "TV1"),
        ("Perspective", "warp_with_corners()", "TV1"),
        ("Enhancement", "enhance()", "TV2"),
        ("Evaluation", "evaluate.py", "TV3"),
    ]
    for r_i, (c1, c2, c3) in enumerate(rows, start=1):
        ry = table_top + r_i * 44 + 28
        cv2.putText(page, c1, (55, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (35, 35, 35), 1, cv2.LINE_AA)
        cv2.putText(page, c2, (200, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (35, 35, 35), 1, cv2.LINE_AA)
        cv2.putText(page, c3, (405, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (35, 35, 35), 1, cv2.LINE_AA)

    cv2.putText(
        page,
        f"Trang 1/1 - Ma tai lieu: XLA-W1-{idx:03d}",
        (170, 795),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.44,
        (70, 70, 70),
        1,
        cv2.LINE_AA,
    )
    return page


def generate_dataset(output_dir: Path, num_images: int = 36) -> None:
    """Sinh 36 ảnh mẫu và lưu metadata.csv."""
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    canvas_w, canvas_h = 900, 1200
    page_w, page_h = 600, 840
    src_corners = np.array(
        [[0, 0], [page_w - 1, 0], [page_w - 1, page_h - 1], [0, page_h - 1]],
        dtype=np.float32,
    )

    metadata_rows = []

    for idx in range(1, num_images + 1):
        cond_idx = (idx - 1) // 6
        cond_key, cond_desc = CONDITIONS[cond_idx % len(CONDITIONS)]
        rng = np.random.default_rng(2026 + idx * 17)

        # 1. Tạo nền (background)
        if cond_key == "similar_or_cluttered_bg":
            bg_color = rng.integers(210, 238, size=(1, 1, 3), dtype=np.uint8)
            canvas = np.broadcast_to(bg_color, (canvas_h, canvas_w, 3)).copy()
            # Vẽ các đường vân/chi tiết gây nhiễu trên nền
            for _ in range(12):
                p1 = (int(rng.integers(0, canvas_w)), int(rng.integers(0, canvas_h)))
                p2 = (int(rng.integers(0, canvas_w)), int(rng.integers(0, canvas_h)))
                col = tuple(int(c) for c in rng.integers(150, 215, size=3))
                cv2.line(canvas, p1, p2, col, thickness=int(rng.integers(2, 5)))
        else:
            # Nền bàn gỗ hoặc mặt bàn tối màu
            base_bgr = rng.choice(
                np.array(
                    [
                        [55, 70, 95],
                        [45, 50, 55],
                        [70, 95, 130],
                        [60, 65, 70],
                    ],
                    dtype=np.uint8,
                )
            )
            canvas = np.broadcast_to(base_bgr.reshape(1, 1, 3), (canvas_h, canvas_w, 3)).copy()
            noise = rng.integers(-8, 9, size=(canvas_h, canvas_w, 3), dtype=np.int16)
            canvas = np.clip(canvas.astype(np.int16) + noise, 20, 240).astype(np.uint8)

        # 2. Tạo trang tài liệu gốc và chọn 4 góc đích
        page = _render_clean_page(idx, cond_key, page_w=page_w, page_h=page_h)

        if cond_key == "tilted_perspective":
            jitter = 95
        elif cond_key == "receipt_and_table":
            jitter = 55
        else:
            jitter = 40

        base_dst = np.array(
            [
                [150, 170],
                [750, 170],
                [750, 1020],
                [150, 1020],
            ],
            dtype=np.float32,
        )
        offsets = rng.uniform(-jitter, jitter, size=(4, 2)).astype(np.float32)
        dst_corners = np.clip(
            base_dst + offsets,
            a_min=[40, 40],
            a_max=[canvas_w - 40, canvas_h - 40],
        ).astype(np.float32)

        # 3. Warp trang tài liệu lên nền
        homography = cv2.getPerspectiveTransform(src_corners, dst_corners)
        warped_page = cv2.warpPerspective(page, homography, (canvas_w, canvas_h))
        mask = np.full((page_h, page_w), 255, dtype=np.uint8)
        warped_mask = cv2.warpPerspective(mask, homography, (canvas_w, canvas_h))

        alpha = (warped_mask.astype(np.float32) / 255.0)[..., None]
        composite = (warped_page.astype(np.float32) * alpha + canvas.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)

        # 4. Hiệu ứng ánh sáng không đều hoặc bóng đổ
        if cond_key == "uneven_lighting":
            yy, xx = np.mgrid[0:canvas_h, 0:canvas_w].astype(np.float32)
            illum = 0.52 + 0.55 * (xx / canvas_w * 0.6 + yy / canvas_h * 0.4)
            composite = np.clip(composite.astype(np.float32) * illum[..., None], 0, 255).astype(np.uint8)
        elif cond_key == "shadow_cast":
            shadow_mask = np.ones((canvas_h, canvas_w), dtype=np.float32)
            poly = np.array(
                [
                    [int(canvas_w * 0.25), int(canvas_h * 0.35)],
                    [canvas_w, int(canvas_h * 0.15)],
                    [canvas_w, canvas_h],
                    [int(canvas_w * 0.10), canvas_h],
                ],
                dtype=np.int32,
            )
            cv2.fillPoly(shadow_mask, [poly], 0.55)
            shadow_mask = cv2.GaussianBlur(shadow_mask, (101, 101), 35)
            composite = np.clip(composite.astype(np.float32) * shadow_mask[..., None], 0, 255).astype(np.uint8)

        filename = f"doc_{idx:03d}.jpg"
        filepath = raw_dir / filename
        cv2.imwrite(str(filepath), composite, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        tl, tr, br, bl = dst_corners.round(1).tolist()
        metadata_rows.append(
            {
                "image_id": f"doc_{idx:03d}",
                "file_path": f"data/raw/{filename}",
                "condition_group": cond_key,
                "condition_desc": cond_desc,
                "width": canvas_w,
                "height": canvas_h,
                "tl_x": tl[0],
                "tl_y": tl[1],
                "tr_x": tr[0],
                "tr_y": tr[1],
                "br_x": br[0],
                "br_y": br[1],
                "bl_x": bl[0],
                "bl_y": bl[1],
            }
        )

    csv_path = output_dir / "metadata.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metadata_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metadata_rows)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    generate_dataset(project_root / "data", num_images=36)
    print("Generated 36 images in data/raw/ and saved data/metadata.csv successfully.")
