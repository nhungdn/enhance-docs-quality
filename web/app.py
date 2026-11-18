"""Ứng dụng Web phục vụ quét và cải thiện chất lượng tài liệu.

================================================================================
PHÂN CÔNG: Thành viên 4 (TV4) sở hữu và chỉnh sửa thư mục `web/`.
Các thành viên khác KHÔNG sửa file trong `web/` để tránh xung đột Git.
================================================================================

Lộ trình công việc của TV4 (Đã hoàn thiện):
- Tuần 2: Dựng Web v0 cho phép người dùng tải ảnh lên (`POST /api/scan`) và nhận về
  ảnh kết quả sau khi chạy `core.process_document`.
- Tuần 3: Xây dựng giao diện so sánh Trước/Sau (Before/After) và nút tải ảnh kết quả (PNG/JPG).
- Tuần 4: Xây dựng giao diện Canvas kéo 4 góc thủ công khi `is_valid == False` (hoặc khi
  người dùng bấm "Chỉnh lại 4 góc"), gửi tọa độ 4 đỉnh về `POST /api/rewarp`.
- Tuần 5-6: Hiển thị thời gian xử lý từng bước, ảnh trung gian (warped vs enhanced), hoàn thiện UI.
"""

from __future__ import annotations

import base64
from collections import OrderedDict
import csv
from email.parser import BytesParser
from email.policy import default as default_email_policy
import json
from pathlib import Path
from typing import Any
import uuid

import cv2
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import numpy as np

from core import process_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = PROJECT_ROOT / "data"
METADATA_CSV = DATA_DIR / "metadata.csv"

# Bộ nhớ đệm lưu tạm các ảnh vừa tải lên để không cần upload lại khi kéo 4 góc
MAX_CACHE_ITEMS = 30
_IMAGE_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()

FALLBACK_REASON_VI: dict[str, str] = {
    "no_contour_found": "Không tìm thấy đường viền (contour) nào trong ảnh.",
    "not_4_vertices": "Đường viền lớn nhất không xấp xỉ được về đúng 4 đỉnh tứ giác.",
    "not_convex": "Tứ giác tìm được bị lõm hoặc tự cắt (không phải đa giác lồi).",
    "area_too_small": "Diện tích vùng tìm được quá nhỏ (< 15% diện tích khung hình).",
    "degenerate_vertex": "Có đỉnh tứ giác bị trùng lặp hoặc suy biến.",
}


def _explain_fallback_reason(reason: str | None) -> str | None:
    """Chuyển mã lý do fallback kỹ thuật sang thông báo tiếng Việt dễ hiểu trên Web."""
    if not reason:
        return None
    if reason in FALLBACK_REASON_VI:
        return FALLBACK_REASON_VI[reason]
    if reason.startswith("bad_angle_"):
        parts = reason.split("_")
        deg = parts[-1] if parts else "?"
        return (
            f"Góc trong của tứ giác bị biến dạng quá mức ({deg}° nằm ngoài khoảng cho phép [45°, 135°])."
        )
    return f"Không thỏa điều kiện tứ giác hợp lệ ({reason})."


def _cache_put(image: np.ndarray, filename: str = "uploaded.jpg") -> str:
    """Lưu ảnh gốc vào bộ nhớ đệm và trả về `image_id`."""
    image_id = uuid.uuid4().hex[:12]
    _IMAGE_CACHE[image_id] = {
        "image": image.copy(),
        "filename": filename,
    }
    while len(_IMAGE_CACHE) > MAX_CACHE_ITEMS:
        _IMAGE_CACHE.popitem(last=False)
    return image_id


def _cache_get(image_id: str) -> dict[str, Any] | None:
    """Lấy ảnh gốc từ bộ nhớ đệm theo `image_id`."""
    item = _IMAGE_CACHE.get(image_id)
    if item is not None:
        _IMAGE_CACHE.move_to_end(image_id)
    return item


def _encode_image_data_url(image: np.ndarray, ext: str = ".png") -> str:
    """Mã hóa ảnh NumPy (`uint8`) sang chuỗi Data URL Base64 để hiển thị trực tiếp trên Web."""
    ext_clean = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    mime = "image/jpeg" if ext_clean in (".jpg", ".jpeg") else "image/png"
    params = [cv2.IMWRITE_JPEG_QUALITY, 92] if mime == "image/jpeg" else []
    ok, buf = cv2.imencode(ext_clean, image, params)
    if not ok:
        raise ValueError("Không thể mã hóa ảnh đầu ra.")
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _decode_image_bytes(raw_bytes: bytes) -> np.ndarray:
    """Giải mã mảng byte từ file upload thành ảnh BGR OpenCV (`np.ndarray`)."""
    if not raw_bytes:
        raise ValueError("Dữ liệu file ảnh rỗng.")
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        raise ValueError("Không thể đọc định dạng file ảnh. Vui lòng chọn ảnh JPG/PNG hợp lệ.")
    return img


def _decode_base64_image(data_url_or_b64: str) -> np.ndarray:
    """Giải mã chuỗi Base64 (hoặc Data URL) thành ảnh BGR OpenCV (`np.ndarray`)."""
    payload = data_url_or_b64.strip()
    if "," in payload and payload.startswith("data:"):
        payload = payload.split(",", 1)[1]
    raw_bytes = base64.b64decode(payload)
    return _decode_image_bytes(raw_bytes)


def _parse_multipart_fallback(content_type: str, body: bytes) -> dict[str, Any]:
    """Phân tích `multipart/form-data` bằng thư viện chuẩn Python (không phụ thuộc `python-multipart`)."""
    raw_headers = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    msg = BytesParser(policy=default_email_policy).parsebytes(raw_headers + body)
    fields: dict[str, Any] = {}
    if not msg.is_multipart():
        return fields

    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if not name:
            continue
        if filename is not None:
            fields[name] = {"filename": filename, "content": payload}
        else:
            fields[name] = payload.decode("utf-8", errors="replace")
    return fields


async def _extract_request_data(request: Request) -> dict[str, Any]:
    """Đọc dữ liệu đầu vào từ cả `application/json` hoặc `multipart/form-data`."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    if "multipart/form-data" in content_type:
        body = await request.body()
        return _parse_multipart_fallback(content_type, body)
    # Thử đọc JSON mặc định
    body = await request.body()
    if body:
        return json.loads(body.decode("utf-8"))
    return {}


def _to_bool(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() not in ("false", "0", "no", "off")


def _draw_corner_overlay(
    image: np.ndarray,
    corners: np.ndarray,
    is_valid: bool,
    source: str = "auto",
) -> np.ndarray:
    """Vẽ khung tứ giác và 4 đỉnh `[TL, TR, BR, BL]` lên ảnh gốc phục vụ trực quan hóa các bước trung gian."""
    vis = image.copy()
    if vis.ndim == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    h, w = vis.shape[:2]
    scale = max(1.0, min(h, w) / 700.0)
    thickness = max(2, int(round(3 * scale)))
    radius = max(6, int(round(9 * scale)))
    font_scale = max(0.55, 0.65 * scale)

    pts = np.round(corners).astype(np.int32).reshape(4, 2)
    poly_pts = pts.reshape((-1, 1, 2))

    # Màu xanh lá cho tự động hợp lệ, màu xanh dương cho chỉnh tay, màu cam/đỏ cho fallback cảnh báo
    if source == "manual_fallback":
        main_color = (235, 99, 37)   # BGR: Xanh dương đậm
    elif is_valid:
        main_color = (85, 197, 34)   # BGR: Xanh lá
    else:
        main_color = (22, 115, 249)  # BGR: Cam cảnh báo

    overlay = vis.copy()
    cv2.fillPoly(overlay, [poly_pts], main_color)
    cv2.addWeighted(overlay, 0.16, vis, 0.84, 0, vis)
    cv2.polylines(vis, [poly_pts], isClosed=True, color=main_color, thickness=thickness, lineType=cv2.LINE_AA)

    labels = ["TL", "TR", "BR", "BL"]
    point_colors = [
        (68, 68, 239),   # TL - Đỏ
        (246, 130, 59),  # TR - Xanh dương
        (85, 197, 34),   # BR - Xanh lá
        (11, 158, 245),  # BL - Vàng cam
    ]

    for idx, (pt, label, pt_color) in enumerate(zip(pts, labels, point_colors)):
        x, y = int(pt[0]), int(pt[1])
        cv2.circle(vis, (x, y), radius + 3, (255, 255, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(vis, (x, y), radius, pt_color, -1, lineType=cv2.LINE_AA)

        text = f"{idx + 1}:{label}"
        tx = min(max(8, x + radius + 6), max(8, w - int(90 * scale)))
        ty = min(max(int(24 * scale), y - radius - 4), h - 10)
        cv2.putText(
            vis,
            text,
            (tx, ty),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            thickness + 2,
            lineType=cv2.LINE_AA,
        )
        cv2.putText(
            vis,
            text,
            (tx, ty),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (15, 23, 42),
            max(1, thickness - 1),
            lineType=cv2.LINE_AA,
        )

    return vis


def handle_auto_scan(
    image: np.ndarray,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Xử lý yêu cầu quét tự động khi người dùng tải ảnh lên.

    Kết nối trực tiếp với `core.process_document(image=image, manual_corners=None, config=config)`.
    """
    return process_document(image=image, manual_corners=None, config=config)


def handle_manual_rewarp(
    image: np.ndarray,
    corners_xy: list[list[float]] | np.ndarray,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Xử lý yêu cầu cắt và làm phẳng lại khi người dùng kéo 4 góc thủ công trên Web.

    Nhận mảng `corners_xy` dạng `[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]` ở hệ tọa độ ảnh gốc
    và gọi `core.process_document(image=image, manual_corners=manual_pts, config=config)`.
    """
    manual_pts = np.asarray(corners_xy, dtype=np.float32).reshape(4, 2)
    return process_document(image=image, manual_corners=manual_pts, config=config)


def _build_api_response(
    image: np.ndarray,
    pipeline_out: dict[str, Any],
    image_id: str,
    filename: str = "document.jpg",
) -> dict[str, Any]:
    """Đóng gói kết quả từ `process_document` thành JSON chuẩn trả về cho Frontend."""
    detection = pipeline_out["detection"]
    corners_used = np.asarray(pipeline_out["corners_used"], dtype=np.float32).reshape(4, 2)
    warped_img = pipeline_out["warped_image"]
    enhanced_img = pipeline_out["enhanced_image"]
    timing_ms = pipeline_out["timing_ms"]

    is_valid = bool(detection.get("is_valid", False))
    source = str(detection.get("source", "auto"))
    fallback_reason = detection.get("fallback_reason")
    confidence = float(detection.get("confidence", 1.0 if is_valid else 0.0))

    overlay_img = _draw_corner_overlay(
        image=image,
        corners=corners_used,
        is_valid=is_valid,
        source=source,
    )

    h, w = image.shape[:2]
    out_h, out_w = enhanced_img.shape[:2]

    return {
        "image_id": image_id,
        "filename": filename,
        "image_shape": [int(h), int(w)],
        "output_shape": [int(out_h), int(out_w)],
        "corners": [[round(float(pt[0]), 2), round(float(pt[1]), 2)] for pt in corners_used],
        "is_valid": is_valid,
        "confidence": round(confidence, 4),
        "source": source,
        "fallback_reason": fallback_reason,
        "fallback_message": _explain_fallback_reason(fallback_reason),
        "timing_ms": timing_ms,
        "images": {
            "original": _encode_image_data_url(image, ext=".jpg"),
            "corner_overlay": _encode_image_data_url(overlay_img, ext=".jpg"),
            "warped": _encode_image_data_url(warped_img, ext=".jpg"),
            "enhanced": _encode_image_data_url(enhanced_img, ext=".png"),
            "enhanced_jpg": _encode_image_data_url(enhanced_img, ext=".jpg"),
        },
    }


def _parse_enhance_config_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Tạo dict `config` truyền vào `process_document` từ dữ liệu yêu cầu."""
    block_size_int = max(3, int(data.get("block_size", 21)))
    if block_size_int % 2 == 0:
        block_size_int += 1

    return {
        "remove_shadow": _to_bool(data.get("remove_shadow"), True),
        "denoise": _to_bool(data.get("denoise"), True),
        "use_clahe": _to_bool(data.get("use_clahe"), True),
        "binarize": _to_bool(data.get("binarize"), True),
        "enhance": {
            "threshold_method": str(data.get("threshold_method", "adaptive_gaussian")).lower(),
            "denoise_method": str(data.get("denoise_method", "median")).lower(),
            "block_size": block_size_int,
            "c_offset": float(data.get("c_offset", 10.0)),
        },
    }


app = FastAPI(
    title="Hệ thống Quét và Cải thiện Chất lượng Tài liệu",
    description="Backend API phục vụ phát hiện 4 góc, biến đổi phối cảnh Homography và tăng cường chất lượng tài liệu.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """Kiểm tra trạng thái hoạt động của dịch vụ Web."""
    return {"status": "ok", "service": "enhance-docs-quality-web"}


@app.get("/api/samples")
def list_sample_images() -> dict[str, Any]:
    """Trả về danh sách ảnh mẫu trong `data/metadata.csv` để người dùng chọn thử nhanh trên Web."""
    samples: list[dict[str, Any]] = []
    if METADATA_CSV.exists():
        with METADATA_CSV.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                file_path = PROJECT_ROOT / row["file_path"]
                if file_path.exists():
                    samples.append(
                        {
                            "image_id": row["image_id"],
                            "file_path": row["file_path"],
                            "filename": file_path.name,
                            "condition_group": row.get("condition_group", "unknown"),
                            "notes": row.get("notes", ""),
                        }
                    )
    return {"count": len(samples), "samples": samples}


@app.post("/api/scan")
async def api_scan(request: Request) -> JSONResponse:
    """Endpoint chính: Nhận ảnh tải lên (multipart hoặc JSON Base64) hoặc tên ảnh mẫu, chạy `handle_auto_scan`."""
    try:
        data = await _extract_request_data(request)
        file_entry = data.get("file")
        image_base64 = data.get("image_base64")
        sample_name = data.get("sample_name")

        if isinstance(file_entry, dict) and file_entry.get("content"):
            image = _decode_image_bytes(file_entry["content"])
            filename = str(file_entry.get("filename") or "uploaded.jpg")
        elif image_base64:
            image = _decode_base64_image(str(image_base64))
            filename = str(data.get("filename") or "uploaded.jpg")
        elif sample_name:
            safe_name = Path(str(sample_name)).name
            sample_path = DATA_DIR / "raw" / safe_name
            if not sample_path.exists():
                raise HTTPException(status_code=404, detail=f"Không tìm thấy ảnh mẫu: {safe_name}")
            image = cv2.imread(str(sample_path), cv2.IMREAD_COLOR)
            if image is None:
                raise HTTPException(status_code=400, detail=f"Không thể đọc ảnh mẫu: {safe_name}")
            filename = safe_name
        else:
            raise HTTPException(
                status_code=400,
                detail="Vui lòng tải lên một file ảnh (`file` / `image_base64`) hoặc chọn một ảnh mẫu (`sample_name`).",
            )

        cfg = _parse_enhance_config_from_dict(data)
        image_id = _cache_put(image, filename=filename)
        pipeline_out = handle_auto_scan(image=image, config=cfg)
        payload = _build_api_response(
            image=image,
            pipeline_out=pipeline_out,
            image_id=image_id,
            filename=filename,
        )
        return JSONResponse(content=payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/rewarp")
async def api_rewarp(request: Request) -> JSONResponse:
    """Endpoint cắt phẳng và tăng cường lại khi người dùng kéo chỉnh 4 góc thủ công trên Canvas."""
    try:
        data = await _extract_request_data(request)
        image_id = data.get("image_id")
        corners = data.get("corners")
        if isinstance(corners, str):
            corners = json.loads(corners)

        if not corners or len(corners) != 4 or any(len(pt) != 2 for pt in corners):
            raise HTTPException(
                status_code=400,
                detail="Tọa độ `corners` phải gồm đúng 4 đỉnh `[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]`.",
            )

        file_entry = data.get("file")
        image_base64 = data.get("image_base64")

        if isinstance(file_entry, dict) and file_entry.get("content"):
            image = _decode_image_bytes(file_entry["content"])
            filename = str(file_entry.get("filename") or "uploaded.jpg")
            image_id = _cache_put(image, filename=filename)
        elif image_base64:
            image = _decode_base64_image(str(image_base64))
            filename = str(data.get("filename") or "uploaded.jpg")
            image_id = _cache_put(image, filename=filename)
        elif image_id:
            cached = _cache_get(str(image_id))
            if cached is None:
                raise HTTPException(
                    status_code=404,
                    detail="Phiên làm việc của ảnh đã hết hạn trên bộ nhớ đệm. Vui lòng bấm Quét lại ảnh.",
                )
            image = cached["image"]
            filename = cached["filename"]
        else:
            raise HTTPException(status_code=400, detail="Thiếu `image_id` hoặc dữ liệu ảnh.")

        cfg = _parse_enhance_config_from_dict(data)
        pipeline_out = handle_manual_rewarp(
            image=image,
            corners_xy=corners,
            config=cfg,
        )
        resp = _build_api_response(
            image=image,
            pipeline_out=pipeline_out,
            image_id=str(image_id),
            filename=filename,
        )
        return JSONResponse(content=resp)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
def serve_index() -> FileResponse:
    """Phục vụ trang giao diện chính `web/static/index.html`."""
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=False)
