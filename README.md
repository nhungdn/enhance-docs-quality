# Hệ thống Quét và Cải thiện Chất lượng Tài liệu (`enhance-docs-quality`)

Báo cáo và mã nguồn Bài tập lớn môn **Xử lý ảnh số (Digital Image Processing)**.

---

## 1. Cấu trúc thư mục & Phân quyền sở hữu file (Chống xung đột Git)

Repo được thiết kế tách biệt hoàn toàn file theo từng thành viên (**TV1, TV2, TV3, TV4**) để cả nhóm code song song và tạo Pull Request vào `main` mà **không bao giờ đụng file của nhau**:

```text
enhance-docs-quality/
├── core/                         # Giao diện xử lý ảnh cốt lõi
│   ├── __init__.py               # [KHÓA GIAO DIỆN] Export chung — KHÔNG AI CẦN SỬA
│   ├── detector.py               # [TV1 SỞ HỮU] detect_corners(), order_corners(), validate_quadrilateral()
│   ├── warp.py                   # [TV1 SỞ HỮU] warp_with_corners(), compute_output_dimensions()
│   ├── enhancer.py               # [TV2 SỞ HỮU] enhance(), remove_shadow_bg(), apply_clahe(), apply_threshold()
│   └── pipeline.py               # [TV4 SỞ HỮU] process_document() kết nối 3 hàm chính + đo thời gian
├── web/                          # Ứng dụng Web (Backend + Frontend)
│   ├── app.py                    # [TV4 SỞ HỮU] Backend API (/api/scan, /api/rewarp)
│   └── static/                   # [TV4 SỞ HỮU] Giao diện người dùng
│       ├── index.html            #   Khung tải ảnh, xem Trước/Sau, Canvas kéo 4 góc
│       ├── style.css             #   Định dạng bố cục 2 cột
│       └── app.js                #   Logic kéo thả 4 đỉnh trên Canvas & gọi API
├── experiments/                  # Thực nghiệm, đánh giá & vùng nháp riêng cho từng thành viên
│   ├── tv1_sandbox.py            # [TV1 SỞ HỮU] Script test riêng cho TV1 (lưu ảnh vào outputs/tv1/)
│   ├── tv2_sandbox.py            # [TV2 SỞ HỮU] Script test riêng cho TV2 (lưu ảnh vào outputs/tv2/)
│   ├── annotate_corners.py       # [TV3] Công cụ click gán nhãn 4 góc chuẩn
│   ├── compare_experiments.py    # [TV3] So sánh cấu hình, OCR, sai số góc, thời gian
│   ├── metrics.py                # [TV3 SỞ HỮU] CER/WER, sai số góc pixel, bg_std phụ
│   └── evaluate.py               # [TV3 SỞ HỮU] Đánh giá OCR, góc, thời gian và fallback thực tế
├── data/                         # Bộ dữ liệu ảnh tài liệu và nhãn (TV3 quản lý)
│   ├── raw/                      # Ảnh chụp thật, giữ nguyên ảnh gốc
│   ├── ground_truth_text/        # Transcript chuẩn riêng từng ảnh (*.txt)
│   ├── metadata.csv              # Điều kiện, đường dẫn transcript, góc chuẩn/manual
│   └── README.md                 # Quy trình thu thập, gán nhãn và đánh giá
├── report_draft.md               # Bản nháp báo cáo định dạng Markdown (tất cả cùng cập nhật theo mục riêng)
├── report_draft.docx             # File mẫu gốc (giữ nguyên không chỉnh sửa)
├── timeline.md                   # Kế hoạch phân công 8 tuần
└── requirements.txt              # Danh sách thư viện Python
```

### Bảng phân quyền File cho từng thành viên

| Thành viên | Phụ trách chuyên môn | Các file ĐƯỢC SỬA | Script chạy thử riêng |
|:---:|---|---|---|
| Nguyễn Thị Ngọc Mai | Phát hiện biên, kiểm tra tứ giác hợp lệ, biến đổi phối cảnh, gợi ý góc fallback | `core/detector.py`<br>`core/warp.py` | `python experiments/tv1_sandbox.py` |
| Khổng Thị Thùy Linh | Chuyển xám, khử bóng đổ hình thái học, khử nhiễu, CLAHE, nhị phân hóa (Otsu & Adaptive) | `core/enhancer.py` | `python experiments/tv2_sandbox.py` |
| Nguyễn Thị Anh Ngọc | Dữ liệu ảnh chụp thật, transcript, đánh giá CER/WER, sai số góc pixel, thời gian và fallback | `experiments/metrics.py`<br>`experiments/evaluate.py`<br>`experiments/compare_experiments.py`<br>`data/*` | `python experiments/compare_experiments.py` |
| Đoàn Thị Hồng Nhung | Web Backend/Frontend, xem Trước/Sau, Canvas kéo 4 góc thủ công, tải ảnh kết quả | `web/app.py`<br>`web/static/*`<br>`core/pipeline.py` | `python -m web.app` |

> **Quy tắc làm việc nhóm tránh xung đột:**
> 1. Mỗi thành viên tạo nhánh riêng theo tên mình (ví dụ: `git checkout -b tv1/corner-detection`, `tv2/enhancement`, `tv3/evaluation`, `tv4/web-ui`).
> 2. **Tuyệt đối không đổi tên hàm hoặc kiểu dữ liệu đầu vào/đầu ra** của 3 hàm giao diện chính (`detect_corners`, `warp_with_corners`, `enhance`) đã chốt trong `core/`.
> 3. Mở file mình phụ trách và tìm từ khóa `TODO (TVx - Tuần y)` để làm theo đúng hướng dẫn từng bước đã ghi sẵn trong code.

---

## 2. Sơ đồ Pipeline

```mermaid
flowchart TD
    A["Ảnh đầu vào (BGR chụp từ điện thoại / máy tính)"] --> B["Tiền xử lý dò biên: Chuyển xám + Lọc Gaussian (5x5)"]
    B --> C["Phát hiện biên Canny + Phép đóng hình thái học"]
    C --> D["Tìm Contour & Xấp xỉ đa giác (approxPolyDP)"]
    D --> E{"Kiểm tra tứ giác hợp lệ?\n(4 đỉnh, lồi, diện tích >= 15%, góc 45°-135°)"}
    E -- "Hợp lệ (is_valid = True)" --> E1{"Lề ngoài đã là giấy trắng?\n(_is_inner_border_on_clean_page)"}
    E1 -- "Đúng (Khung viền trong trang bìa)" --> E2["Giữ nguyên 4 góc toàn trang"]
    E1 -- "Sai (Nền bàn ngoài trang giấy)" --> F["Sắp xếp 4 góc [TL, TR, BR, BL]"]
    E2 --> F
    E -- "Không hợp lệ (is_valid = False)" --> G["Fallback: Gợi ý 4 góc minAreaRect + Người dùng kéo 4 góc trên Web"]
    G --> F
    F --> H["Biến đổi phối cảnh Homography 3x3 (warp_with_corners)"]
    H --> I["Chuyển xám + Ước lượng nền hình thái học khử bóng đổ"]
    I --> J["Làm sắc nét Unsharp Mask + Mặt nạ ngưỡng thích nghi & lọc nhiễu <= 3px"]
    J --> K["Làm trắng nền 255 & Kéo giãn tương phản mềm bảo toàn nét chữ/con dấu"]
    K --> L["Đầu ra: Xem Trước/Sau đặt cạnh nhau trên Web & Tải ảnh (.PNG / .JPG)"]
```

---

## 3. Giao diện 3 hàm cốt lõi (`core/`)

| Hàm | Module | Phụ trách | Chữ ký hàm (Signature) | Đầu vào & Đầu ra |
|---|---|---|---|---|
| `detect_corners` | [core/detector.py](file:///e:/nnnnn/p-xla/enhance-docs-quality/core/detector.py) | TV1 | `detect_corners(image: np.ndarray, config: dict \| None = None) -> dict` | Nhận ảnh BGR/xám; trả về `dict` gồm `corners` `(4, 2)` theo thứ tự `[TL, TR, BR, BL]`, `is_valid` (`bool`), `confidence` (`float`), `fallback_reason`, `debug_info`. |
| `warp_with_corners` | [core/warp.py](file:///e:/nnnnn/p-xla/enhance-docs-quality/core/warp.py) | TV1 | `warp_with_corners(image: np.ndarray, corners: np.ndarray, output_size: tuple[int, int] \| None = None) -> np.ndarray` | Nhận ảnh gốc và mảng `corners` `(4, 2)`; trả về ảnh tài liệu đã cắt nền thừa và duỗi phẳng phối cảnh (`uint8`). |
| `enhance` | [core/enhancer.py](file:///e:/nnnnn/p-xla/enhance-docs-quality/core/enhancer.py) | TV2 | `enhance(image: np.ndarray, remove_shadow: bool = True, denoise: bool = True, use_clahe: bool = True, binarize: bool = True, config: dict \| None = None) -> np.ndarray` | Nhận ảnh tài liệu phẳng; trả về ảnh tài liệu 1 kênh (`uint8`) đã khử bóng, khử nhiễu, tăng tương phản CLAHE và nhị phân hóa sắc nét. |

---

## 4. Hướng dẫn cài đặt & Khởi chạy Ứng dụng Web (TV4)

### 4.1. Cài đặt môi trường
Yêu cầu **Python 3.10+**. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

Để chạy đánh giá OCR của TV3, cài thêm ứng dụng Tesseract OCR cùng dữ liệu ngôn
ngữ tiếng Việt (`vie`) và tiếng Anh (`eng`); hướng dẫn chi tiết ở
[`data/README.md`](./data/README.md).

### 4.2. Khởi chạy Ứng dụng Web
Chạy trực tiếp module `web.app`:

```bash
python -m web.app
```

Hoặc chạy với `uvicorn` (tự động reload khi phát triển):

```bash
uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
```

Sau đó mở trình duyệt tại địa chỉ: **`http://127.0.0.1:8000`**

**Luồng sử dụng trên giao diện Web:**
1. **Kéo thả hoặc chọn ảnh chụp tài liệu** (`.JPG`, `.PNG`) vào vùng tải ảnh trên trang chủ.
2. **Hệ thống tự động xử lý** (hiển thị trạng thái *Loading* trong lúc phát hiện 4 góc, cắt phẳng phối cảnh và làm sạch nền).
3. **Xem Trước / Sau đặt cạnh nhau:** Đối chiếu trực tiếp **Ảnh gốc (Trước)** ở cột trái và **Ảnh kết quả (Sau)** ở cột phải (hỗ trợ kéo chỉnh lại 4 góc ngay trên ảnh gốc khi cần).
4. **Tải ảnh kết quả về máy:** Chọn nút **⬇ Tải về .PNG** hoặc **⬇ Tải về .JPG**.

---

## 5. Các lệnh CLI

```bash
python experiments/tv1_sandbox.py
python experiments/tv2_sandbox.py
```

Transcript chuẩn được lưu riêng theo đường dẫn `reference_text_file` trong
`data/metadata.csv` (ví dụ `doc1` hiện dùng `data/ground_truth_text/doc01.txt`).
Để chấm trước một phần ảnh đã có transcript, dùng `--allow-partial`; script sẽ
báo rõ ảnh nào bị bỏ qua. Xem [`data/README.md`](./data/README.md) để biết cách
đặt tên file và chạy đánh giá. Runner so sánh nhiều cấu hình trên cùng ảnh:

```powershell
python experiments/compare_experiments.py --metadata data/metadata.csv --output outputs/tv3_experiment_results.csv --lang vie+eng --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --repeats 3
```
