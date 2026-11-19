"""Đánh giá phát hiện góc, OCR và hiệu quả chỉnh góc thủ công (TV3)."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import cv2
import numpy as np
import pytesseract

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import process_document
from experiments.metrics import compute_background_std, compute_cer, compute_corner_error, compute_wer

CORNER_COLUMNS = ("tl_x", "tl_y", "tr_x", "tr_y", "br_x", "br_y", "bl_x", "bl_y")
MANUAL_CORNER_COLUMNS = tuple(f"manual_{column}" for column in CORNER_COLUMNS)


def _read_corners(
    row: dict[str, str],
    columns: tuple[str, ...],
    label: str,
    image_id: str,
) -> np.ndarray | None:
    values = [row.get(column, "").strip() for column in columns]
    if not any(values):
        return None
    if not all(values):
        raise ValueError(f"{image_id}: {label} must contain all 8 coordinates or be empty.")

    corners = np.array([float(value) for value in values], dtype=np.float32).reshape(4, 2)
    if not np.isfinite(corners).all():
        raise ValueError(f"{image_id}: {label} must contain finite coordinates.")
    return corners


def _recognize_and_score(
    image: np.ndarray,
    reference_text: str,
    language: str,
) -> tuple[float, float]:
    recognized_text = pytesseract.image_to_string(image, lang=language, config="--psm 6")
    return compute_cer(reference_text, recognized_text), compute_wer(reference_text, recognized_text)


def run_evaluation(
    metadata_csv: Path,
    limit: int | None = None,
    ocr_language: str = "vie+eng",
    allow_partial: bool = False,
) -> list[dict[str, object]]:
    """Đánh giá tự động và các chỉnh góc thực tế đã ghi trong manifest.

    Góc chuẩn (`tl_x`…`bl_y`) dùng tính sai số góc. Các cột `manual_*` chỉ chứa
    tọa độ thực tế người dùng kéo trên giao diện; không tự thay bằng góc chuẩn.
    Khi `allow_partial=True`, chỉ các dòng có file transcript không rỗng được chấm.
    """
    with metadata_csv.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"image_id", "file_path", "reference_text_file"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{metadata_csv} is missing required columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be a positive integer.")
        rows = rows[:limit]

    results: list[dict[str, object]] = []
    skipped_ids: list[str] = []
    for row in rows:
        image_id = row["image_id"].strip()
        reference_file = row["reference_text_file"].strip()
        if not reference_file:
            if allow_partial:
                skipped_ids.append(image_id)
                continue
            raise ValueError(f"{image_id}: reference_text_file must point to a UTF-8 text file.")

        reference_relative_path = Path(reference_file)
        if reference_relative_path.is_absolute():
            raise ValueError(f"{image_id}: reference_text_file must be relative to the project root.")
        reference_path = (PROJECT_ROOT / reference_relative_path).resolve()
        if not reference_path.is_relative_to(PROJECT_ROOT):
            raise ValueError(f"{image_id}: reference_text_file must stay inside the project root.")
        if not reference_path.is_file():
            if allow_partial:
                skipped_ids.append(image_id)
                continue
            raise FileNotFoundError(f"{image_id}: transcript file not found at {reference_path}")

        reference_text = reference_path.read_text(encoding="utf-8-sig").strip()
        if not reference_text:
            if allow_partial:
                skipped_ids.append(image_id)
                continue
            raise ValueError(f"{image_id}: transcript file is empty: {reference_path}")

        gt_corners = _read_corners(row, CORNER_COLUMNS, "ground-truth corners", image_id)
        manual_corners = _read_corners(row, MANUAL_CORNER_COLUMNS, "manual corners", image_id)
        if manual_corners is not None and gt_corners is None:
            raise ValueError(f"{image_id}: manual corners require ground-truth corner labels.")

        img_path = (PROJECT_ROOT / row["file_path"]).resolve()
        image = cv2.imread(str(img_path))
        if image is None:
            raise FileNotFoundError(f"{image_id}: could not read image at {img_path}")
        height, width = image.shape[:2]
        for label, corners in (
            ("ground-truth corners", gt_corners),
            ("manual corners", manual_corners),
        ):
            if corners is not None and (
                np.any(corners[:, 0] < 0)
                or np.any(corners[:, 0] >= width)
                or np.any(corners[:, 1] < 0)
                or np.any(corners[:, 1] >= height)
            ):
                raise ValueError(
                    f"{image_id}: {label} must be inside the original image bounds "
                    f"(0..{width - 1}, 0..{height - 1})."
                )

        auto_out = process_document(image)
        auto_cer, auto_wer = _recognize_and_score(
            auto_out["enhanced_image"],
            reference_text,
            ocr_language,
        )
        result: dict[str, object] = {
            "image_id": image_id,
            "reference_text_file": reference_file,
            "condition_group": row.get("condition_group", ""),
            "image_width": width,
            "image_height": height,
            "detection_valid": auto_out["detection"]["is_valid"],
            "auto_corner_error_px": None,
            "auto_cer": round(auto_cer, 6),
            "auto_wer": round(auto_wer, 6),
            "auto_bg_std": compute_background_std(auto_out["enhanced_image"]),
            "auto_pipeline_ms": auto_out["timing_ms"]["total_ms"],
            "manual_correction_recorded": manual_corners is not None,
            "manual_corner_error_px": None,
            "manual_cer": None,
            "manual_wer": None,
            "manual_bg_std": None,
            "manual_pipeline_ms": None,
        }

        if gt_corners is not None:
            result["auto_corner_error_px"] = round(
                compute_corner_error(auto_out["corners_used"], gt_corners),
                2,
            )

        if manual_corners is not None and gt_corners is not None:
            manual_out = process_document(image, manual_corners=manual_corners)
            manual_cer, manual_wer = _recognize_and_score(
                manual_out["enhanced_image"],
                reference_text,
                ocr_language,
            )
            result.update(
                {
                    "manual_corner_error_px": round(
                        compute_corner_error(manual_out["corners_used"], gt_corners),
                        2,
                    ),
                    "manual_cer": round(manual_cer, 6),
                    "manual_wer": round(manual_wer, 6),
                    "manual_bg_std": compute_background_std(manual_out["enhanced_image"]),
                    "manual_pipeline_ms": manual_out["timing_ms"]["total_ms"],
                }
            )

        results.append(result)

    if skipped_ids:
        print(
            f"Skipped {len(skipped_ids)} unlabeled image(s) (--allow-partial): "
            + ", ".join(skipped_ids)
        )
    return results


def _write_results_csv(results: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(results[0])
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def _mean_metric(results: list[dict[str, object]], metric: str) -> float | None:
    values = [float(result[metric]) for result in results if result[metric] is not None]
    return float(np.mean(values)) if values else None


def _print_summary(results: list[dict[str, object]]) -> None:
    failure_count = sum(not bool(row["detection_valid"]) for row in results)
    failure_rate = failure_count / len(results) * 100.0
    print(f"Automatic detection failures: {failure_count}/{len(results)} ({failure_rate:.1f}%)")
    print(
        "Automatic pipeline mean: "
        f"CER={_mean_metric(results, 'auto_cer'):.4f}, "
        f"WER={_mean_metric(results, 'auto_wer'):.4f}, "
        f"time={_mean_metric(results, 'auto_pipeline_ms'):.2f} ms"
    )
    corner_error = _mean_metric(results, "auto_corner_error_px")
    if corner_error is not None:
        print(f"Mean automatic corner error: {corner_error:.2f} px")
    bg_std = _mean_metric(results, "auto_bg_std")
    if bg_std is not None:
        print(f"Supplementary mean background std: {bg_std:.2f}")

    failures = [row for row in results if not bool(row["detection_valid"])]
    corrected_failures = [row for row in failures if row["manual_correction_recorded"]]
    if not failures:
        print("No failed detections; no fallback comparison is available.")
        return
    if not corrected_failures:
        print("No actual manual-correction coordinates are recorded for failed detections.")
        return

    improved_corners = sum(
        float(row["manual_corner_error_px"]) < float(row["auto_corner_error_px"])
        for row in corrected_failures
    )
    success_rate = improved_corners / len(corrected_failures) * 100.0
    print(
        f"Manual-correction coverage: {len(corrected_failures)}/{len(failures)} failed detections; "
        f"corner-error improvement success: {improved_corners}/{len(corrected_failures)} "
        f"({success_rate:.1f}%)."
    )
    for metric, label in (
        ("corner_error_px", "corner error (px)"),
        ("cer", "CER"),
        ("wer", "WER"),
        ("pipeline_ms", "pipeline time (ms)"),
    ):
        automatic = _mean_metric(corrected_failures, f"auto_{metric}")
        manual = _mean_metric(corrected_failures, f"manual_{metric}")
        print(f"  {label}: {automatic:.4f} -> {manual:.4f}")
    cer_improved = sum(float(row["manual_cer"]) < float(row["auto_cer"]) for row in corrected_failures)
    wer_improved = sum(float(row["manual_wer"]) < float(row["auto_wer"]) for row in corrected_failures)
    print(
        f"  OCR error decreased in {cer_improved}/{len(corrected_failures)} cases (CER), "
        f"{wer_improved}/{len(corrected_failures)} cases (WER)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate corner error, OCR CER/WER, and pipeline time.")
    parser.add_argument("--metadata", type=Path, default=PROJECT_ROOT / "data" / "metadata.csv")
    parser.add_argument("--output", type=Path, help="Optional path for per-image CSV results.")
    parser.add_argument("--limit", type=int, help="Evaluate only the first N manifest rows.")
    parser.add_argument("--lang", default="vie+eng", help="Installed Tesseract language(s), e.g. vie+eng.")
    parser.add_argument("--tesseract-cmd", help="Optional path to tesseract.exe when it is not on PATH.")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Evaluate only rows with a non-empty existing transcript file and report skipped rows.",
    )
    args = parser.parse_args()

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd
    results = run_evaluation(
        args.metadata,
        limit=args.limit,
        ocr_language=args.lang,
        allow_partial=args.allow_partial,
    )
    if not results:
        print(f"No labeled dataset rows found in {args.metadata}. Add transcript files first.")
        return

    print(f"Evaluated {len(results)} labeled image(s).")
    for item in results:
        print(item)
    _print_summary(results)
    if args.output:
        _write_results_csv(results, args.output)
        print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
