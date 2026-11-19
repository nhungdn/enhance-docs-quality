# Bộ dữ liệu ảnh chụp tài liệu

TV3 quản lý ảnh chụp thật và nhãn phục vụ đánh giá; không thay đổi thuật toán
hoặc giao diện website. Ảnh gốc được giữ trong `data/raw/`, metadata ở
`metadata.csv`, còn transcript chuẩn được lưu thành từng file riêng trong
`ground_truth_text/`.

## Tình trạng hiện tại

- Có 111 ảnh đã đặt tên theo nhóm; `metadata.csv` giữ `image_id` ổn định
  (`doc1`–`doc111`) và trỏ tới tên file ảnh mới.
- Có 25 transcript không rỗng trong 111 ảnh; 86 ảnh chưa có transcript.
- Đã gán nhóm sơ bộ cho cả 111 ảnh theo yêu cầu đặt tên. Cần kiểm tra nhãn từ
  ảnh thật; riêng nhóm `blurred` cần xác nhận có đồng thời nghiêng để tính vào
  quota `tilted_blur` hay không.
- Có 86 ảnh đã gán đủ 4 góc chuẩn; 25 ảnh chưa gán góc. Chưa có ảnh nào có tọa
  độ kéo thủ công; model thiết bị và ghi nhận quyền sử dụng chưa được điền đầy đủ.

Khung báo cáo yêu cầu 120 ảnh theo nhóm: 20 `normal`, 15
`tilted_perspective`, 15 `shadow_cast`, 15 `low_light`, 15 `tilted_blur`, 15
`cluttered_background`, 15 `wrinkled_page` và 10 `occluded_corner`. Hiện có
111/120 ảnh về tổng số; cần ít nhất 9 ảnh nữa. Phân bố hiện tại:
15 `normal`, 15 `shadow_cast`, 15 `tilted_perspective`, 15 `low_light`,
10 `blurred`, 11 `cluttered_background`, 10 `occluded_corner`,
10 `wrinkled_page` và 10 `handwritten_text`. Nhóm viết tay là nhóm bổ sung ngoài
quota gốc; quota gốc yêu cầu 15 `tilted_blur`, nên cần xác nhận điều kiện của
10 ảnh `blurred` và bổ sung các nhóm còn thiếu theo thực tế.

## Việc TV3 cần hoàn thành

- [ ] Kiểm tra nhóm và mô tả điều kiện đã gán cho 111 ảnh theo nội dung ảnh.
- [ ] Ghi thiết bị chụp và ghi chú quyền sử dụng/ẩn danh.
- [x] Tạo transcript riêng cho 25 ảnh đã chép và kiểm tra.
- [ ] Tạo và kiểm tra transcript `.txt` cho các ảnh còn lại; hiện 25 ảnh có
      transcript để chạy đánh giá OCR thử.
- [ ] Gán góc chuẩn cho 25 ảnh còn thiếu; ghi góc kéo thật cho các ca fallback
      được đưa vào so sánh.
- [ ] Bổ sung ít nhất 9 ảnh và kiểm tra quota từng nhóm trong khung báo cáo.
- [ ] Chạy đánh giá, lưu bảng số liệu; phân tích ca OCR/góc thất bại và cập nhật
      Chương 6–8.
- [ ] Chạy `experiments/compare_experiments.py` trên toàn bộ ảnh sau khi kiểm tra
      thử; phân tích CER/WER theo cấu hình và nhóm điều kiện.

## Quy trình thu thập và gán nhãn

1. Giữ nguyên ảnh đầu vào trong `data/raw/`; không nắn thẳng hoặc tăng cường ảnh
   trước khi đưa vào bộ dữ liệu.
2. Dùng các nhóm `normal`, `tilted_perspective`, `shadow_cast`, `low_light`,
   `blurred`, `cluttered_background`, `wrinkled_page`, `occluded_corner` và
   `handwritten_text`; mô tả điều kiện thực tế trong `condition_desc`.
3. Ghi model thiết bị vào `capture_device` và tình trạng quyền sử dụng/ẩn danh
   vào `permission_note`. Chỉ đưa vào kho chia sẻ dữ liệu nhóm có quyền sử dụng;
   che thông tin cá nhân nhạy cảm trước khi commit hoặc gửi báo cáo.
4. Tạo một file UTF-8 trong `data/ground_truth_text/` cho mỗi ảnh được chép
   chuẩn; lấy đường dẫn từ cột `reference_text_file` trong manifest thay vì tự
   suy ra tên file từ `image_id` (ví dụ `doc1` hiện trỏ tới `doc01.txt`). Chép
   và kiểm tra nguyên văn phần nhìn thấy; không dùng kết quả OCR của hệ thống
   làm ground truth, không suy đoán nội dung bị che.
5. Để đánh giá sai số góc, gán đủ 8 tọa độ ground truth `tl_x`…`bl_y` trên ảnh
   gốc theo thứ tự `[TL, TR, BR, BL]`. Tọa độ là pixel ảnh gốc; có thể để trống
   cả 8 cột nếu chưa gán nhãn. Có thể chạy công cụ click tương tác:

   ```powershell
   python experiments/annotate_corners.py
   ```

   Click lần lượt TL, TR, BR, BL trên ranh ngoài của tờ giấy. Nhấn Enter để lưu
   nhãn ảnh hiện tại ngay vào manifest; U hoàn tác điểm cuối, R xóa các điểm đã
   chọn, S bỏ qua ảnh và Q/Esc thoát. Ảnh đã có đủ 4 góc sẽ tự được bỏ qua khi
   chạy lại. Nếu góc bị che khuất/không xác định chắc chắn, bỏ qua thay vì đoán.
   Để thử trên tối đa hai ảnh chưa gán nhãn trước:

   ```powershell
   python experiments/annotate_corners.py --limit 2
   ```
6. Để đánh giá fallback thực tế, sau khi người dùng kéo góc và áp dụng trên web,
   ghi 8 tọa độ trong trường `corners` của phản hồi `/api/rewarp` vào các cột
   `manual_*`. Không chép tọa độ ground truth sang các cột này.

## Manifest `metadata.csv`

Mỗi dòng tương ứng một ảnh:

| Cột | Ý nghĩa |
|---|---|
| `image_id`, `file_path` | Mã ảnh và đường dẫn tương đối từ thư mục gốc repo |
| `condition_group`, `condition_desc` | Nhóm và mô tả điều kiện chụp |
| `capture_device`, `permission_note` | Model thiết bị và ghi chú quyền sử dụng/ẩn danh |
| `reference_text_file` | Đường dẫn tương đối đến file transcript UTF-8 |
| `tl_x`…`bl_y` | Tọa độ 4 góc chuẩn trên ảnh gốc |
| `manual_tl_x`…`manual_bl_y` | Tọa độ sau thao tác kéo góc thực tế trên web |

File transcript chứa nội dung thuần, không cần dấu ngoặc kép CSV. Nếu ảnh chưa
được chép, file `.txt` tương ứng chưa tồn tại.

## Đánh giá

Cài các thư viện Python bằng `pip install -r requirements.txt` và cài Tesseract
OCR với ngôn ngữ `vie` và `eng`. Để chấm các ảnh đã có transcript, dùng:

```powershell
python experiments/evaluate.py --metadata data/metadata.csv --output outputs/tv3_evaluation.csv --lang vie+eng --allow-partial
```

`--allow-partial` chỉ chấm các dòng có file transcript tồn tại và không rỗng;
script sẽ in mã các ảnh bị bỏ qua. Không dùng tùy chọn này khi muốn bảo đảm mọi
ảnh trong manifest đều được đánh giá.

Nếu `tesseract.exe` không nằm trong `PATH`, truyền đường dẫn đã cài:

```powershell
python experiments/evaluate.py --metadata data/metadata.csv --output outputs/tv3_evaluation.csv --lang vie+eng --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --allow-partial
```

Để so sánh nhiều cấu hình trên cùng ảnh, trước tiên chạy thử hai ảnh với một
lần lặp:

```powershell
python experiments/compare_experiments.py --metadata data/metadata.csv --output outputs/tv3_experiment_results.csv --lang vie+eng --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --repeats 1 --limit 2
```

Sau khi kiểm tra CSV, chạy toàn bộ manifest (3 lần lặp thời gian mặc định):

```powershell
python experiments/compare_experiments.py --metadata data/metadata.csv --output outputs/tv3_experiment_results.csv --lang vie+eng --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --repeats 3
```

Runner ghi một dòng cho mỗi ảnh/cấu hình vào cùng CSV, lưu kết quả sau mỗi ảnh
để vẫn giữ phần đã chạy nếu bị gián đoạn. Chín cấu hình gồm pipeline mặc định,
baseline Adaptive Gaussian, ablation bỏ từng bước (warp, khử bóng, khử nhiễu,
CLAHE), chỉ phân ngưỡng, và so sánh Otsu/Adaptive Mean/Adaptive Gaussian.
`production_default` chạy pipeline tích hợp; các cấu hình ablation/ngưỡng gọi
trực tiếp `enhance()` trên cùng ảnh đã warp (riêng `no_warp` dùng ảnh gốc), giữ
các bước còn lại cố định. Vì vậy, xem pipeline mặc định như mốc sản phẩm; so
sánh đóng góp từng bước dựa trên nhóm ablation.

Mọi ảnh đều được xử lý để đo trạng thái detector và thời gian; sai số góc chỉ
tính cho ảnh có đủ 8 nhãn chuẩn (hiện 86 ảnh). OCR chỉ tính cho ảnh có transcript
không rỗng (hiện 25 ảnh), mỗi ảnh/cấu hình chạy OCR một lần; thời gian OCR không
nằm trong thời gian pipeline. Bảng tổng hợp là trung bình/trung vị macro trên
các ảnh có nhãn tương ứng, có phân nhóm theo điều kiện. `--save-images` ghi ảnh
đầu ra của từng cấu hình vào thư mục cạnh CSV, có thể cần nhiều dung lượng.
Các cột `manual_*` chỉ tạo thêm hàng `manual_fallback` khi có tọa độ kéo thật;
hiện chưa có hàng fallback thủ công nào.

Bộ độ đo chính gồm sai số góc trung bình theo pixel, CER, WER và thời gian
pipeline. Thời gian pipeline không tính thời gian người dùng kéo góc hoặc thời
gian OCR bên ngoài pipeline. Tỉ lệ ảnh tự động thất bại được tính từ trạng thái
`is_valid=False`. Tỉ lệ fallback thành công chỉ được tính trên ảnh lỗi tự động
có tọa độ manual thật; thành công hình học nghĩa là sai số góc sau kéo nhỏ hơn
sai số tự động. `bg_std` là chỉ số phụ; IoU, PSNR, SSIM và độ tương phản chữ–nền
không thuộc bộ độ đo đã chốt.
