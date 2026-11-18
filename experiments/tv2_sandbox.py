
"""
Script kiểm thử riêng dành cho Thành viên 2 (TV2).

Chức năng:
1. Kiểm thử trên 6 ảnh doc_019 đến doc_024 (nhóm ảnh có bóng đổ).
2. Lưu ảnh grayscale.
3. So sánh trước/sau khi khử bóng đổ.
4. So sánh trước/sau CLAHE.
5. So sánh Otsu, Adaptive Mean và Adaptive Gaussian.
6. Lưu ảnh kết quả của pipeline enhance() hoàn chỉnh.
7. Tạo ảnh tổng hợp để phục vụ báo cáo mục 2.5–2.7 và 8.2.

Cách chạy:
    python3 experiments/tv2_sandbox.py

Chạy một ảnh:
    python3 experiments/tv2_sandbox.py --images doc_019

Kết quả:
    experiments/outputs/tv2/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.enhancer import (
    DEFAULT_ENHANCE_CONFIG,
    to_grayscale,
    remove_shadow_bg,
    denoise_image,
    apply_clahe,
    apply_threshold,
    enhance,
)


RAW_DIR = PROJECT_ROOT / "data" / "raw"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "outputs"
    / "tv2"
)

DEFAULT_IMAGES = [
    "doc_019",
    "doc_020",
    "doc_021",
    "doc_022",
    "doc_023",
    "doc_024",
]


# ============================================================
# 2. UTILITY FUNCTIONS
# ============================================================

def save_image(path: Path, image: np.ndarray) -> None:
    """
    Lưu ảnh vào đường dẫn chỉ định.
    Tự động tạo thư mục nếu chưa tồn tại.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    if image is None or image.size == 0:
        print(f"[WARNING] Empty image: {path.name}")
        return

    success = cv2.imwrite(str(path), image)

    if success:
        print(f"[SAVED] {path.name}")
    else:
        print(f"[ERROR] Cannot save: {path}")


def create_config(**overrides) -> dict:
    """
    Tạo bản config riêng để thử nghiệm.
    Không thay đổi DEFAULT_ENHANCE_CONFIG.
    """

    config = dict(DEFAULT_ENHANCE_CONFIG)
    config.update(overrides)

    return config


def resize_for_comparison(
    image: np.ndarray,
    max_width: int = 600
) -> np.ndarray:
    """
    Resize ảnh để tạo ảnh so sánh.
    Giữ nguyên tỷ lệ khung hình.
    """

    height, width = image.shape[:2]

    if width <= max_width:
        return image.copy()

    scale = max_width / width

    new_width = int(width * scale)
    new_height = int(height * scale)

    return cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA
    )


def create_comparison(
    images: list,
    output_path: Path,
    max_width: int = 600
) -> None:
    """
    Ghép nhiều ảnh thành một ảnh so sánh ngang.

    images:
        [
            ("Original", image1),
            ("Enhanced", image2)
        ]
    """

    panels = []

    for title, image in images:

        if image is None:
            continue

        # Chuyển về grayscale để hiển thị thống nhất
        if len(image.shape) == 3:
            display = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY
            )
        else:
            display = image.copy()

        display = resize_for_comparison(
            display,
            max_width
        )

        # Chuyển grayscale thành BGR
        display = cv2.cvtColor(
            display,
            cv2.COLOR_GRAY2BGR
        )

        height, width = display.shape[:2]

        # Tạo vùng tiêu đề
        header = np.full(
            (40, width, 3),
            245,
            dtype=np.uint8
        )

        cv2.putText(
            header,
            title,
            (10, 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            2,
            cv2.LINE_AA
        )

        panel = np.vstack([
            header,
            display
        ])

        panels.append(panel)

    if not panels:
        return

    # Đồng bộ chiều cao các panel
    max_height = max(
        panel.shape[0]
        for panel in panels
    )

    normalized_panels = []

    for panel in panels:

        if panel.shape[0] < max_height:

            padding = np.full(
                (
                    max_height - panel.shape[0],
                    panel.shape[1],
                    3
                ),
                255,
                dtype=np.uint8
            )

            panel = np.vstack([
                panel,
                padding
            ])

        normalized_panels.append(panel)

    comparison = np.hstack(normalized_panels)

    save_image(output_path, comparison)


# ============================================================
# 3. PROCESS ONE IMAGE
# ============================================================

def process_image(image_name: str) -> bool:

    print("\n" + "=" * 60)
    print(f"PROCESSING: {image_name}")
    print("=" * 60)

    image_path = RAW_DIR / f"{image_name}.jpg"

    image_output_dir = OUTPUT_DIR / image_name

    image_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load original image
    # --------------------------------------------------------

    original = cv2.imread(
        str(image_path),
        cv2.IMREAD_COLOR
    )

    if original is None:

        print(f"[ERROR] Cannot read image: {image_path}")

        return False

    print("[OK] Original image loaded")

    save_image(
        image_output_dir / "00_original.jpg",
        original
    )

    # --------------------------------------------------------
    # STEP 1: Grayscale
    # --------------------------------------------------------

    print("\n[STEP 1] Grayscale conversion")

    gray = to_grayscale(original)

    save_image(
        image_output_dir / "01_grayscale.jpg",
        gray
    )

    # --------------------------------------------------------
    # STEP 2: Shadow removal
    # --------------------------------------------------------

    print("\n[STEP 2] Shadow removal")

    shadow_config = create_config()

    shadow_removed = remove_shadow_bg(
        gray,
        shadow_config
    )

    save_image(
        image_output_dir / "02_shadow_removed.jpg",
        shadow_removed
    )

    create_comparison(
        [
            ("Before Shadow Removal", gray),
            ("After Shadow Removal", shadow_removed),
        ],
        image_output_dir / "compare_shadow_removal.jpg"
    )

    # --------------------------------------------------------
    # STEP 3: Denoising
    # --------------------------------------------------------

    print("\n[STEP 3] Denoising")

    denoised = denoise_image(
        shadow_removed,
        create_config()
    )

    save_image(
        image_output_dir / "03_denoised.jpg",
        denoised
    )

    # --------------------------------------------------------
    # STEP 4: CLAHE
    # --------------------------------------------------------

    print("\n[STEP 4] CLAHE")

    clahe_result = apply_clahe(
        denoised,
        create_config()
    )

    save_image(
        image_output_dir / "04_clahe.jpg",
        clahe_result
    )

    create_comparison(
        [
            ("Before CLAHE", denoised),
            ("After CLAHE", clahe_result),
        ],
        image_output_dir / "compare_clahe.jpg"
    )

    # --------------------------------------------------------
    # STEP 5: Thresholding comparison
    # --------------------------------------------------------

    print("\n[STEP 5] Thresholding comparison")

    # Otsu Thresholding
    otsu_result = apply_threshold(
        clahe_result,
        create_config(
            threshold_method="otsu"
        )
    )

    save_image(
        image_output_dir / "05_otsu.jpg",
        otsu_result
    )

    # Adaptive Mean Thresholding
    adaptive_mean_result = apply_threshold(
        clahe_result,
        create_config(
            threshold_method="adaptive_mean"
        )
    )

    save_image(
        image_output_dir / "06_adaptive_mean.jpg",
        adaptive_mean_result
    )

    # Adaptive Gaussian Thresholding
    adaptive_gaussian_result = apply_threshold(
        clahe_result,
        create_config(
            threshold_method="adaptive_gaussian"
        )
    )

    save_image(
        image_output_dir / "07_adaptive_gaussian.jpg",
        adaptive_gaussian_result
    )

    # So sánh 3 phương pháp
    create_comparison(
        [
            ("Otsu", otsu_result),
            ("Adaptive Mean", adaptive_mean_result),
            ("Adaptive Gaussian", adaptive_gaussian_result),
        ],
        image_output_dir / "compare_threshold_methods.jpg"
    )

    # --------------------------------------------------------
    # STEP 6: Full enhancement pipeline
    # --------------------------------------------------------

    print("\n[STEP 6] Full enhancement pipeline")

    full_result = enhance(
        original,
        remove_shadow=True,
        denoise=True,
        use_clahe=True,
        binarize=True
    )

    save_image(
        image_output_dir / "08_full_enhanced.jpg",
        full_result
    )

    # --------------------------------------------------------
    # STEP 7: Pipeline overview
    # --------------------------------------------------------

    print("\n[STEP 7] Creating pipeline overview")

    create_comparison(
        [
            ("Grayscale", gray),
            ("Shadow Removed", shadow_removed),
            ("Denoised", denoised),
            ("CLAHE", clahe_result),
            ("Final Output", full_result),
        ],
        image_output_dir / "pipeline_overview.jpg",
        max_width=450
    )

    print(f"\n[COMPLETED] {image_name}")

    return True


# ============================================================
# 4. MAIN
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description="TV2 Document Enhancement Sandbox"
    )

    parser.add_argument(
        "--images",
        nargs="+",
        default=DEFAULT_IMAGES,
        help="Image names to process"
    )

    return parser.parse_args()


def main():

    args = parse_arguments()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 60)
    print("TV2 - DOCUMENT IMAGE ENHANCEMENT TEST")
    print("=" * 60)

    print("Input directory :", RAW_DIR)
    print("Output directory:", OUTPUT_DIR)

    successful = []
    failed = []

    for image_name in args.images:

        # Chấp nhận cả doc_019 và doc_019.jpg
        image_name = Path(image_name).stem

        try:

            result = process_image(image_name)

            if result:
                successful.append(image_name)
            else:
                failed.append(image_name)

        except Exception as error:

            print(
                f"[ERROR] Failed processing {image_name}: {error}"
            )

            failed.append(image_name)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("TV2 TEST SUMMARY")
    print("=" * 60)

    print(
        f"Successful: {len(successful)}/{len(args.images)}"
    )

    if successful:
        print("Successful images:", ", ".join(successful))

    if failed:
        print("Failed images:", ", ".join(failed))

    print("\nOutput directory:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
