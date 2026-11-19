"""Run repeatable OCR, corner-accuracy, ablation, threshold, and fallback experiments."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

import cv2
import numpy as np
import pytesseract

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import enhance, process_document
from experiments.metrics import (
    compute_background_std,
    compute_cer,
    compute_corner_error,
    compute_wer,
)

CORNER_COLUMNS = ("tl_x", "tl_y", "tr_x", "tr_y", "br_x", "br_y", "bl_x", "bl_y")
MANUAL_CORNER_COLUMNS = tuple(f"manual_{column}" for column in CORNER_COLUMNS)


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    family: str
    use_warp: bool = True
    remove_shadow: bool = True
    denoise: bool = True
    use_clahe: bool = True
    threshold_method: str = "adaptive_gaussian"


CONFIGURATIONS = (
    ExperimentConfig("production_default", "production"),
    ExperimentConfig("full_adaptive_gaussian", "ablation_baseline"),
    ExperimentConfig("no_warp", "ablation", use_warp=False),
    ExperimentConfig("threshold_only", "ablation", remove_shadow=False, denoise=False, use_clahe=False),
    ExperimentConfig("no_shadow", "ablation", remove_shadow=False),
    ExperimentConfig("no_denoise", "ablation", denoise=False),
    ExperimentConfig("no_clahe", "ablation", use_clahe=False),
    ExperimentConfig("threshold_otsu", "threshold", threshold_method="otsu"),
    ExperimentConfig("threshold_adaptive_mean", "threshold", threshold_method="adaptive_mean"),
)

RESULT_FIELDS = (
    "image_id",
    "condition_group",
    "mode",
    "config",
    "image_width",
    "image_height",
    "auto_detection_valid",
    "corner_error_px",
    "ocr_scored",
    "cer",
    "wer",
    "bg_std",
    "pipeline_ms_mean",
    "pipeline_ms_median",
    "detect_ms_mean",
    "warp_ms_mean",
    "enhance_ms_mean",
    "timing_repeats",
    "reference_text_file",
    "output_image",
)


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

    corners = np.asarray([float(value) for value in values], dtype=np.float32).reshape(4, 2)
    if not np.isfinite(corners).all():
        raise ValueError(f"{image_id}: {label} must contain finite coordinates.")
    return corners


def _resolve_image_path(value: str, image_id: str) -> Path:
    relative_path = Path(value)
    if relative_path.is_absolute():
        raise ValueError(f"{image_id}: file_path must be relative to the project root.")
    path = (PROJECT_ROOT / relative_path).resolve()
    if not path.is_relative_to(PROJECT_ROOT):
        raise ValueError(f"{image_id}: file_path must stay inside the project root.")
    return path


def _read_reference(row: dict[str, str], image_id: str) -> tuple[str | None, str]:
    reference_file = row.get("reference_text_file", "").strip()
    if not reference_file:
        return None, ""

    relative_path = Path(reference_file)
    if relative_path.is_absolute():
        raise ValueError(f"{image_id}: reference_text_file must be relative to the project root.")
    path = (PROJECT_ROOT / relative_path).resolve()
    if not path.is_relative_to(PROJECT_ROOT):
        raise ValueError(f"{image_id}: reference_text_file must stay inside the project root.")
    if not path.is_file():
        return None, reference_file

    text = path.read_text(encoding="utf-8-sig").strip()
    return (text or None), reference_file


def _validate_corners(
    corners: np.ndarray | None,
    width: int,
    height: int,
    label: str,
    image_id: str,
) -> None:
    if corners is None:
        return
    if (
        np.any(corners[:, 0] < 0)
        or np.any(corners[:, 0] >= width)
        or np.any(corners[:, 1] < 0)
        or np.any(corners[:, 1] >= height)
    ):
        raise ValueError(
            f"{image_id}: {label} must be inside image bounds "
            f"(0..{width - 1}, 0..{height - 1})."
        )


def _enhance_config(image: np.ndarray, threshold_method: str) -> dict[str, object]:
    kernel_size = max(31, int(round(min(image.shape[:2]) / 18)))
    if kernel_size % 2 == 0:
        kernel_size += 1
    return {
        "bg_kernel_size": kernel_size,
        "threshold_method": threshold_method,
    }


def _score_ocr(image: np.ndarray, reference: str, language: str) -> tuple[float, float]:
    hypothesis = pytesseract.image_to_string(image, lang=language, config="--psm 6")
    return compute_cer(reference, hypothesis), compute_wer(reference, hypothesis)


def _save_output_image(
    image: np.ndarray,
    output_dir: Path | None,
    config: str,
    image_id: str,
) -> str:
    if output_dir is None:
        return ""
    path = output_dir / config / f"{image_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not save experiment output image: {path}")
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved_path)


def _write_results(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        if temp_path is None:
            raise RuntimeError("Could not create temporary experiment results file.")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _make_result(
    *,
    image_id: str,
    condition_group: str,
    mode: str,
    config: str,
    image_shape: tuple[int, ...],
    detection_valid: bool,
    corner_error: float | None,
    reference: str | None,
    reference_file: str,
    output_image: str,
    durations_ms: list[float],
    detect_ms: float | None,
    warp_ms: float | None,
    enhance_ms: float | None,
    enhanced_image: np.ndarray,
    language: str,
) -> dict[str, object]:
    cer: float | None = None
    wer: float | None = None
    if reference is not None:
        cer, wer = _score_ocr(enhanced_image, reference, language)

    height, width = image_shape[:2]
    return {
        "image_id": image_id,
        "condition_group": condition_group,
        "mode": mode,
        "config": config,
        "image_width": width,
        "image_height": height,
        "auto_detection_valid": detection_valid,
        "corner_error_px": round(corner_error, 2) if corner_error is not None else None,
        "ocr_scored": reference is not None,
        "cer": round(cer, 6) if cer is not None else None,
        "wer": round(wer, 6) if wer is not None else None,
        "bg_std": compute_background_std(enhanced_image),
        "pipeline_ms_mean": round(statistics.mean(durations_ms), 2),
        "pipeline_ms_median": round(statistics.median(durations_ms), 2),
        "detect_ms_mean": round(detect_ms, 2) if detect_ms is not None else None,
        "warp_ms_mean": round(warp_ms, 2) if warp_ms is not None else None,
        "enhance_ms_mean": round(enhance_ms, 2) if enhance_ms is not None else None,
        "timing_repeats": len(durations_ms),
        "reference_text_file": reference_file,
        "output_image": output_image,
    }


def _run_image(
    row: dict[str, str],
    repeats: int,
    language: str,
    output_dir: Path | None,
) -> list[dict[str, object]]:
    image_id = row["image_id"].strip()
    if not image_id:
        raise ValueError("Every metadata row must have a non-empty image_id.")

    image_path = _resolve_image_path(row["file_path"].strip(), image_id)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"{image_id}: could not read image at {image_path}")
    height, width = image.shape[:2]

    gt_corners = _read_corners(row, CORNER_COLUMNS, "ground-truth corners", image_id)
    manual_corners = _read_corners(row, MANUAL_CORNER_COLUMNS, "manual corners", image_id)
    if manual_corners is not None and gt_corners is None:
        raise ValueError(f"{image_id}: manual corners require ground-truth corner labels.")
    _validate_corners(gt_corners, width, height, "ground-truth corners", image_id)
    _validate_corners(manual_corners, width, height, "manual corners", image_id)
    reference, reference_file = _read_reference(row, image_id)

    production_runs: list[dict[str, object]] = []
    production_durations: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        result = process_document(image)
        production_durations.append((time.perf_counter() - started) * 1000.0)
        production_runs.append(result)

    production = production_runs[-1]
    detection_valid = bool(production["detection"]["is_valid"])
    auto_corner_error = (
        compute_corner_error(production["corners_used"], gt_corners)
        if gt_corners is not None
        else None
    )
    detect_ms = statistics.mean(float(run["timing_ms"]["detect_ms"]) for run in production_runs)
    warp_ms = statistics.mean(float(run["timing_ms"]["warp_ms"]) for run in production_runs)
    production_enhance_ms = statistics.mean(
        float(run["timing_ms"]["enhance_ms"]) for run in production_runs
    )

    results: list[dict[str, object]] = []
    for config in CONFIGURATIONS:
        if config.family == "production":
            enhanced_image = production["enhanced_image"]
            durations = production_durations
            config_detect_ms = detect_ms
            config_warp_ms = warp_ms
            config_enhance_ms = production_enhance_ms
        else:
            source_image = production["warped_image"] if config.use_warp else image
            enhance_durations: list[float] = []
            enhanced_image = source_image
            enhance_cfg = _enhance_config(source_image, config.threshold_method)
            for _ in range(repeats):
                started = time.perf_counter()
                enhanced_image = enhance(
                    source_image,
                    remove_shadow=config.remove_shadow,
                    denoise=config.denoise,
                    use_clahe=config.use_clahe,
                    binarize=True,
                    config=enhance_cfg,
                )
                enhance_durations.append((time.perf_counter() - started) * 1000.0)

            if config.use_warp:
                durations = [detect_ms + warp_ms + value for value in enhance_durations]
                config_detect_ms = detect_ms
                config_warp_ms = warp_ms
            else:
                durations = enhance_durations
                config_detect_ms = 0.0
                config_warp_ms = 0.0
            config_enhance_ms = statistics.mean(enhance_durations)

        output_image = _save_output_image(enhanced_image, output_dir, config.name, image_id)
        results.append(
            _make_result(
                image_id=image_id,
                condition_group=row.get("condition_group", ""),
                mode="auto",
                config=config.name,
                image_shape=image.shape,
                detection_valid=detection_valid,
                corner_error=auto_corner_error,
                reference=reference,
                reference_file=reference_file,
                output_image=output_image,
                durations_ms=durations,
                detect_ms=config_detect_ms,
                warp_ms=config_warp_ms,
                enhance_ms=config_enhance_ms,
                enhanced_image=enhanced_image,
                language=language,
            )
        )

    if manual_corners is not None:
        manual_runs: list[dict[str, object]] = []
        manual_durations: list[float] = []
        for _ in range(repeats):
            started = time.perf_counter()
            manual_result = process_document(image, manual_corners=manual_corners)
            manual_durations.append((time.perf_counter() - started) * 1000.0)
            manual_runs.append(manual_result)
        manual_result = manual_runs[-1]
        manual_corner_error = (
            compute_corner_error(manual_result["corners_used"], gt_corners)
            if gt_corners is not None
            else None
        )
        manual_enhance_ms = statistics.mean(
            float(run["timing_ms"]["enhance_ms"]) for run in manual_runs
        )
        manual_output = manual_result["enhanced_image"]
        output_image = _save_output_image(manual_output, output_dir, "manual_fallback", image_id)
        results.append(
            _make_result(
                image_id=image_id,
                condition_group=row.get("condition_group", ""),
                mode="manual_fallback",
                config="production_default",
                image_shape=image.shape,
                detection_valid=detection_valid,
                corner_error=manual_corner_error,
                reference=reference,
                reference_file=reference_file,
                output_image=output_image,
                durations_ms=manual_durations,
                detect_ms=None,
                warp_ms=None,
                enhance_ms=manual_enhance_ms,
                enhanced_image=manual_output,
                language=language,
            )
        )

    return results


def _metric_summary(rows: list[dict[str, object]], key: str) -> tuple[float | None, float | None, int]:
    values = [float(row[key]) for row in rows if row[key] is not None]
    if not values:
        return None, None, 0
    return statistics.mean(values), statistics.median(values), len(values)


def _print_summary(rows: list[dict[str, object]]) -> None:
    print("\nSummary by mode/config (mean / median):")
    config_keys = sorted({(str(row["mode"]), str(row["config"])) for row in rows})
    for mode, config in config_keys:
        subset = [row for row in rows if row["mode"] == mode and row["config"] == config]
        failure_rate = (
            sum(not bool(row["auto_detection_valid"]) for row in subset) / len(subset) * 100.0
            if mode == "auto" and subset
            else None
        )
        corner_mean, corner_median, n_corner = _metric_summary(subset, "corner_error_px")
        cer_mean, cer_median, n_ocr = _metric_summary(subset, "cer")
        wer_mean, wer_median, _ = _metric_summary(subset, "wer")
        time_mean, time_median, _ = _metric_summary(subset, "pipeline_ms_mean")
        print(
            f"{mode}/{config}: N={len(subset)}, corner N={n_corner} "
            f"mean/median={corner_mean}/{corner_median}, "
            f"OCR N={n_ocr} CER={cer_mean}/{cer_median} WER={wer_mean}/{wer_median}, "
            f"time ms={time_mean}/{time_median}, "
            f"auto-failure={failure_rate if failure_rate is not None else 'n/a'}"
        )

    print("\nSummary by condition (mode/config/group; mean / median):")
    group_keys = sorted(
        {
            (str(row["mode"]), str(row["config"]), str(row["condition_group"]))
            for row in rows
        }
    )
    for mode, config, group in group_keys:
        subset = [
            row
            for row in rows
            if row["mode"] == mode
            and row["config"] == config
            and str(row["condition_group"]) == group
        ]
        corner_mean, corner_median, n_corner = _metric_summary(subset, "corner_error_px")
        cer_mean, cer_median, n_ocr = _metric_summary(subset, "cer")
        wer_mean, wer_median, _ = _metric_summary(subset, "wer")
        print(
            f"{mode}/{config}/{group or 'unclassified'}: N={len(subset)}, "
            f"corner N={n_corner}={corner_mean}/{corner_median}, "
            f"OCR N={n_ocr} CER={cer_mean}/{cer_median} WER={wer_mean}/{wer_median}"
        )


def run_experiments(
    metadata_path: Path,
    output_path: Path,
    repeats: int = 3,
    limit: int | None = None,
    language: str = "vie+eng",
    save_images: bool = False,
) -> list[dict[str, object]]:
    if repeats < 1:
        raise ValueError("repeats must be a positive integer.")
    if limit is not None and limit < 1:
        raise ValueError("limit must be a positive integer.")

    output_path = output_path.resolve()
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"image_id", "file_path"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{metadata_path} is missing required columns: {', '.join(sorted(missing))}")
        rows = list(reader)
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise ValueError(f"No images found in {metadata_path}.")

    image_output_dir = output_path.parent / f"{output_path.stem}_images" if save_images else None
    results: list[dict[str, object]] = []
    _write_results(output_path, results)
    for index, row in enumerate(rows, start=1):
        image_id = row.get("image_id", "").strip()
        print(f"[{index}/{len(rows)}] Processing {image_id}")
        results.extend(
            _run_image(
                row,
                repeats=repeats,
                language=language,
                output_dir=image_output_dir,
            )
        )
        _write_results(output_path, results)

    print(
        f"\nSaved {len(results)} image/configuration rows to {output_path}. "
        f"Images evaluated: {len(rows)}; OCR-scored rows: "
        f"{sum(bool(row['ocr_scored']) for row in results)}."
    )
    if image_output_dir is not None:
        print(f"Saved processed images under {image_output_dir}.")
    _print_summary(results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare document pipeline configurations using OCR, corner error, and timing."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=PROJECT_ROOT / "data" / "metadata.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "tv3_experiment_results.csv",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Pipeline timing repetitions.")
    parser.add_argument("--limit", type=int, help="Process only the first N metadata rows.")
    parser.add_argument("--lang", default="vie+eng", help="Tesseract language(s), e.g. vie+eng.")
    parser.add_argument("--tesseract-cmd", help="Path to tesseract.exe when it is not on PATH.")
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="Save every configuration output image (may use substantial disk space).",
    )
    args = parser.parse_args()

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd
    run_experiments(
        metadata_path=args.metadata,
        output_path=args.output,
        repeats=args.repeats,
        limit=args.limit,
        language=args.lang,
        save_images=args.save_images,
    )


if __name__ == "__main__":
    main()
