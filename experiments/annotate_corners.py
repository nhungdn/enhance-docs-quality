"""Interactively label ground-truth document corners in the original images."""

from __future__ import annotations

import argparse
import csv
import ctypes
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORNER_COLUMNS = ("tl_x", "tl_y", "tr_x", "tr_y", "br_x", "br_y", "bl_x", "bl_y")
CORNER_LABELS = ("TL", "TR", "BR", "BL")


def _read_manifest(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        required = {"image_id", "file_path", *CORNER_COLUMNS}
        missing = required.difference(fieldnames)
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")
        return fieldnames, list(reader)


def _save_manifest(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    try:
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _existing_corners(row: dict[str, str]) -> bool:
    values = [row.get(column, "").strip() for column in CORNER_COLUMNS]
    if any(values) and not all(values):
        raise ValueError(f"{row['image_id']}: ground-truth corners are only partially filled.")
    return all(values)


def _fit_image(image: np.ndarray, max_width: int, max_height: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(max_width / width, max_height / height, 1.0)
    display_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    if display_size == (width, height):
        return image.copy()
    return cv2.resize(image, display_size, interpolation=cv2.INTER_AREA)


def _windows_work_area() -> tuple[int, int] | None:
    if os.name != "nt":
        return None

    class Rect(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = Rect()
    try:
        success = ctypes.windll.user32.SystemParametersInfoW(
            0x0030,
            0,
            ctypes.byref(rect),
            0,
        )
    except AttributeError:
        return None
    if not success:
        return None
    return rect.right - rect.left, rect.bottom - rect.top


def _fit_display_limits(
    max_width: int,
    max_height: int,
    work_area: tuple[int, int] | None,
) -> tuple[int, int]:
    if work_area is None:
        return min(max_width, 1000), min(max_height, 600)
    work_width, work_height = work_area
    return (
        max(320, min(max_width, work_width - 80)),
        max(240, min(max_height, work_height - 170)),
    )


def _is_valid_quad(points: list[tuple[int, int]]) -> bool:
    contour = np.asarray(points, dtype=np.int32).reshape(4, 1, 2)
    return cv2.isContourConvex(contour) and cv2.contourArea(contour) > 0


def _annotate_image(
    image: np.ndarray,
    image_id: str,
    filename: str,
    max_width: int,
    max_height: int,
) -> list[tuple[int, int]] | None:
    original_height, original_width = image.shape[:2]
    display = _fit_image(image, max_width, max_height)
    display_height, display_width = display.shape[:2]
    points: list[tuple[int, int]] = []
    status = ""
    window_name = f"Ground-truth corners - {image_id} - {filename}"
    header_height = 56

    def render() -> np.ndarray:
        canvas = display.copy()
        for index, (x, y) in enumerate(points):
            dx = round(x * display_width / original_width)
            dy = round(y * display_height / original_height)
            cv2.circle(canvas, (dx, dy), 7, (0, 0, 255), -1)
            cv2.putText(
                canvas,
                f"{CORNER_LABELS[index]} ({x},{y})",
                (dx + 10, max(20, dy - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
        if len(points) > 1:
            display_points = np.asarray(
                [
                    (
                        round(x * display_width / original_width),
                        round(y * display_height / original_height),
                    )
                    for x, y in points
                ],
                dtype=np.int32,
            )
            cv2.polylines(canvas, [display_points.reshape(-1, 1, 2)], False, (0, 200, 0), 2)
        if len(points) == 4:
            display_points = np.asarray(
                [
                    (
                        round(x * display_width / original_width),
                        round(y * display_height / original_height),
                    )
                    for x, y in points
                ],
                dtype=np.int32,
            )
            cv2.polylines(canvas, [display_points.reshape(-1, 1, 2)], True, (0, 200, 0), 2)

        header = np.zeros((header_height, canvas.shape[1], 3), dtype=np.uint8)
        instructions = f"{image_id}: click TL, TR, BR, BL | Enter=save U=undo R=reset S=skip Q/Esc=quit"
        cv2.putText(
            header,
            instructions,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        if status:
            cv2.putText(
                header,
                status,
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )
        return np.vstack((header, canvas))

    def on_mouse(event: int, x: int, y: int, _flags: int, _parameter: object) -> None:
        image_y = y - header_height
        if (
            event != cv2.EVENT_LBUTTONDOWN
            or len(points) >= 4
            or image_y < 0
            or image_y >= display_height
        ):
            return
        original_x = min(original_width - 1, round(x * original_width / display_width))
        original_y = min(original_height - 1, round(image_y * original_height / display_height))
        points.append((original_x, original_y))

    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(window_name, 20, 20)
    cv2.setMouseCallback(window_name, on_mouse)
    try:
        while True:
            cv2.imshow(window_name, render())
            key = cv2.waitKey(30) & 0xFF
            if key in (ord("q"), 27):
                return None
            try:
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    return None
            except cv2.error:
                return None
            if key in (ord("s"), ord("S")):
                return []
            if key in (ord("u"), ord("U"), 8, 127):
                if points:
                    points.pop()
                continue
            if key in (ord("r"), ord("R")):
                points.clear()
                status = ""
                continue
            if key in (10, 13):
                if len(points) != 4:
                    status = "Click all four corners before saving."
                elif not _is_valid_quad(points):
                    status = "Corners must form a convex quadrilateral; reset and click again."
                else:
                    return points
    finally:
        cv2.destroyAllWindows()


def annotate_manifest(
    metadata_path: Path,
    limit: int | None = None,
    max_width: int = 1200,
    max_height: int = 850,
) -> tuple[int, int]:
    fieldnames, rows = _read_manifest(metadata_path)
    max_width, max_height = _fit_display_limits(
        max_width,
        max_height,
        _windows_work_area(),
    )
    pending = [(index, row) for index, row in enumerate(rows) if not _existing_corners(row)]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be a positive integer.")
        pending = pending[:limit]

    saved = 0
    skipped = 0
    for position, (row_index, row) in enumerate(pending, start=1):
        image_id = row["image_id"].strip()
        image_path = (PROJECT_ROOT / row["file_path"]).resolve()
        if not image_path.is_relative_to(PROJECT_ROOT):
            raise ValueError(f"{image_id}: image path must stay inside the project root.")
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"{image_id}: could not read image at {image_path}")

        print(f"[{position}/{len(pending)}] {image_id}: {image_path.name}")
        points = _annotate_image(image, image_id, image_path.name, max_width, max_height)
        if points is None:
            break
        if not points:
            skipped += 1
            continue

        for index, (x, y) in enumerate(points):
            row[CORNER_COLUMNS[index * 2]] = str(x)
            row[CORNER_COLUMNS[index * 2 + 1]] = str(y)
        rows[row_index] = row
        _save_manifest(metadata_path, fieldnames, rows)
        saved += 1

    print(f"Saved labels for {saved} image(s); skipped {skipped}.")
    return saved, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Click four ground-truth page corners on each original image."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=PROJECT_ROOT / "data" / "metadata.csv",
        help="Metadata CSV to update.",
    )
    parser.add_argument("--limit", type=int, help="Annotate at most N unlabeled images.")
    parser.add_argument("--max-width", type=int, default=1200)
    parser.add_argument("--max-height", type=int, default=850)
    args = parser.parse_args()
    annotate_manifest(
        args.metadata.resolve(),
        limit=args.limit,
        max_width=args.max_width,
        max_height=args.max_height,
    )


if __name__ == "__main__":
    main()
