# Hệ thống quét và cải thiện chất lượng tài liệu

**Báo cáo bài tập lớn môn Xử lý ảnh số (Digital Image Processing)**  
**Giảng viên hướng dẫn:** [Họ tên thầy/cô]  
**Nhóm:** [Số nhóm] | **Lớp:** [Mã lớp] | **Học kỳ:** [HK/Năm học]

---

## Thành viên và phân công đóng góp

| STT | Họ tên | MSSV | Phần phụ trách | % đóng góp |
|:---:|---|---|---|:---:|
| 1 | Nguyễn Thị Ngọc Mai | [MSSV] | Phát hiện biên, kiểm tra tứ giác hợp lệ, hiệu chỉnh phối cảnh, cắt nền & fallback (`detect_corners`, `warp_with_corners`) | 25% |
| 2 | Khổng Thị Thùy Linh | [MSSV] | Tiền xử lý và tăng cường chất lượng ảnh: chuyển xám, loại bóng đổ hình thái học, khử nhiễu, tăng tương phản CLAHE, nhị phân hóa (`enhance`) | 25% |
| 3 | Nguyễn Thị Anh Ngọc | [MSSV] | Xây dựng dữ liệu, gán nhãn 4 góc, thiết kế thí nghiệm, cài đặt các độ đo đánh giá (IoU, sai số góc, PSNR, SSIM, độ đồng nhất nền) | 25% |
| 4 | Đoàn Thị Hồng Nhung | [MSSV] | Ứng dụng Web, giao diện xem Trước/Sau, giao diện Canvas kéo 4 góc thủ công, tải ảnh kết quả, tích hợp pipeline, video demo | 25% |

---

## Tóm tắt

*(Bản nháp sơ bộ Tuần 1 — sẽ cập nhật số liệu thực nghiệm ở Tuần 5–7)*  
Trong thực tế, việc sử dụng camera điện thoại thông minh để chụp lại các văn bản hành chính, hóa đơn, tài liệu học tập hoặc biểu mẫu ngày càng phổ biến nhờ tính tiện lợi. Tuy nhiên, ảnh chụp trực tiếp từ điện thoại thường gặp nhiều suy giảm chất lượng như biến dạng phối cảnh do góc chụp nghiêng, lẫn vùng nền thừa lộn xộn, ánh sáng phân bố không đồng đều, bóng đổ từ tay người chụp hoặc thiết bị, và độ tương phản thấp giữa chữ với nền giấy. Báo cáo này trình bày việc thiết kế và xây dựng **Hệ thống quét và cải thiện chất lượng tài liệu** dựa trên các kỹ thuật xử lý ảnh số cổ điển kết hợp cơ chế tương tác người–máy thông minh. Pipeline đề xuất bao gồm ba giai đoạn xử lý chính: (1) phát hiện biên tài liệu bằng lọc làm mịn Gaussian, dò biên Canny và xấp xỉ đa giác trên contour đi kèm cơ chế kiểm tra tứ giác lồi hợp lệ; (2) hiệu chỉnh phối cảnh bằng phép biến đổi Homography $3 \times 3$ kết hợp cơ chế **fallback cho phép người dùng kéo chỉnh 4 góc thủ công** khi ảnh đầu vào quá phức tạp; (3) tăng cường chất lượng ảnh thông qua ước lượng nền hình thái học để loại bỏ bóng đổ, khử nhiễu, cân bằng biểu đồ mức xám cục bộ (CLAHE) và nhị phân hóa thích nghi (Adaptive Thresholding). Hệ thống được đóng gói thành ứng dụng Web trực quan hỗ trợ so sánh Trước/Sau và được đánh giá định lượng qua tỷ lệ phát hiện góc đúng, chỉ số giao trên hợp (IoU), PSNR/SSIM và độ đồng nhất nền giấy.

---

## 1. Giới thiệu

### 1.1. Phát biểu bài toán

Sự phổ biến của điện thoại thông minh có camera độ phân giải cao đã thay đổi thói quen lưu trữ tài liệu: thay vì sử dụng máy quét phẳng (flatbed scanner) chuyên dụng cồng kềnh, người dùng thường chụp ảnh tài liệu trực tiếp bằng điện thoại. Tuy nhiên, khác với môi trường chiếu sáng chuẩn hóa và mặt phẳng cố định của máy scan, quá trình thu nhận ảnh bằng camera cầm tay trong điều kiện tự nhiên làm phát sinh đồng thời hai nhóm suy giảm lớn: **biến dạng hình học (geometric distortion)** và **suy giảm quang độ (photometric degradation)**.

Bài toán **Quét và cải thiện chất lượng tài liệu (Document Scanning and Quality Enhancement)** được phát biểu chính xác như sau:

- **Đầu vào (Input):** Một ảnh màu kỹ thuật số $I_{\text{in}} \in \{0, 1, \dots, 255\}^{H \times W \times 3}$ (không gian màu BGR/RGB) chụp một trang tài liệu phẳng bằng điện thoại di động. Ảnh đầu vào có thể chứa các yếu tố nhiễu thực tế:
  1. Trang tài liệu nằm ở góc nghiêng bất kỳ so với trục quang học của camera, gây biến dạng phối cảnh (hình chữ nhật biến thành tứ giác lồi bất kỳ).
  2. Bao quanh trang tài liệu là vùng nền thừa (mặt bàn, thảm, vật dụng cá nhân, các tờ giấy khác).
  3. Độ rọi sáng không đồng đều trên bề mặt giấy, có bóng đổ của tay, thân điện thoại hoặc nguồn sáng chéo.
  4. Nhiễu cảm biến trong điều kiện thiếu sáng hoặc mờ nhẹ do rung tay.

- **Đầu ra (Output):** Ảnh tài liệu $I_{\text{out}}$ kích thước $H' \times W'$, trong đó vùng nền ngoài trang giấy đã bị cắt bỏ hoàn toàn, trang tài liệu được duỗi phẳng về góc nhìn trực diện từ trên xuống (top-down/bird's-eye view), bóng đổ bị triệt tiêu, nền giấy trắng sạch đồng nhất, chữ viết/hình in có độ tương phản và độ sắc nét cao tương đương bản quét từ máy scan chuyên dụng.

- **Các thách thức và khó khăn kỹ thuật chính:**
  - *Nền lẫn màu giấy (Low-contrast background):* Khi trang giấy trắng được đặt trên mặt bàn màu trắng, xám nhạt hoặc chồng lên các tờ giấy khác, độ chênh lệch cường độ sáng (gradient) tại ranh giới tờ giấy rất nhỏ, khiến bộ dò biên Canny dễ bị đứt đoạn biên hoặc bắt nhầm biên của vật thể khác.
  - *Bóng đổ cục bộ và chiếu sáng không đều (Shadows and uneven illumination):* Khi chụp tài liệu dưới đèn bàn hoặc ánh sáng tự nhiên bị che khuất bởi tay và điện thoại, trên mặt giấy xuất hiện ranh giới bóng đổ rõ rệt. Các phương pháp phân ngưỡng toàn cục (như ngưỡng cố định hoặc Otsu) sẽ biến toàn bộ vùng bóng đổ thành mảng đen đặc, làm mất hoàn toàn thông tin chữ nằm trong vùng tối.
  - *Nền phức tạp nhiều chi tiết (Cluttered/textured background):* Vân gỗ đậm, gạch lát, bàn phím hoặc các vật dụng xung quanh tạo ra rất nhiều cạnh giả (false edges) và contour nhiễu có cường độ gradient lớn hơn cả cạnh thật của tờ giấy.
  - *Mất góc hoặc che khuất một phần (Occluded corners / truncated borders):* Ngón tay người giữ giấy che mất góc, góc tờ giấy bị quăn/gấp mép hoặc nằm sát rìa khung hình làm đa giác xấp xỉ không còn đủ 4 đỉnh lồi chuẩn.
  - *Bảo toàn các nét chữ mảnh và dấu thanh:* Chữ in cỡ nhỏ, hóa đơn nhiệt phai mực hoặc các dấu thanh mảnh rất dễ bị đứt nét nếu lọc nhiễu quá mạnh hoặc chọn tham số ngưỡng nhị phân không phù hợp.

### 1.2. Ứng dụng thực tế

Một hệ thống quét và tăng cường chất lượng ảnh tài liệu hoạt động ổn định mang lại giá trị ứng dụng rộng rãi trong nhiều lĩnh vực:

1. **Số hóa hồ sơ hành chính, pháp lý và doanh nghiệp:** Hỗ trợ nhân viên văn phòng và người dân chụp hợp đồng, hóa đơn, biểu mẫu, biên lai thu phí để lưu trữ điện tử hoặc nộp trực tuyến trên cổng dịch vụ công mà không cần máy quét chuyên dụng.
2. **Giáo dục và học tập từ xa:** Sinh viên và giảng viên sử dụng để chụp đề thi, bài tập, tài liệu tham khảo, giáo trình và nộp bài qua hệ thống quản lý học tập (LMS) với chất lượng hình ảnh sạch, phẳng và dễ đọc.
3. **In ấn văn phòng (Photocopy kỹ thuật số):** Khi in lại một bức ảnh chụp điện thoại chưa qua xử lý, toàn bộ vùng nền xám tối và bóng đổ của tờ giấy sẽ tiêu tốn lượng lớn mực in và tạo ra bản in lem nhem; việc cắt bỏ nền ngoài và chuẩn hóa nền giấy về màu trắng sạch giúp bản in rõ ràng như bản gốc.
4. **Chuẩn hóa dữ liệu đầu vào cho các hệ thống lưu trữ và phân tích văn bản:** Ảnh tài liệu đã được nắn thẳng phối cảnh (rectified) và khử bóng là bước tiền xử lý bắt buộc trước khi đưa vào các kho lưu trữ số hóa lâu dài.

**Các ứng dụng thương mại tương tự dùng làm đối chứng:**  
Hiện nay trên thị trường có các ứng dụng di động nổi tiếng như **CamScanner**, **Adobe Scan** và **Microsoft Lens**. Trong khuôn khổ đề tài này, nhóm sử dụng kết quả đầu ra của **CamScanner / Adobe Scan** trên cùng bộ ảnh kiểm thử làm mốc đối chứng thực tế (benchmark) để đánh giá ưu điểm, hạn chế của một pipeline xử lý ảnh số cổ điển minh bạch, giải thích được từng bước toán học.

### 1.3. Mục tiêu và phạm vi

#### Mục tiêu của đề tài
- **Về mặt thuật toán:** Thiết kế, cài đặt và làm chủ toàn bộ chuỗi thuật toán xử lý ảnh số cổ điển cho bài toán quét tài liệu, từ bước lọc làm mịn Gaussian, phát hiện biên Canny, tìm contour, xấp xỉ đa giác Ramer–Douglas–Peucker (`approxPolyDP`), biến đổi phối cảnh Homography $3 \times 3$, đến các kỹ thuật ước lượng nền hình thái học khử bóng, cân bằng biểu đồ thích nghi có giới hạn tương phản (CLAHE) và phân ngưỡng thích nghi (Adaptive Mean/Gaussian Thresholding).
- **Về mặt thực nghiệm và đánh giá:** Xây dựng bộ dữ liệu tối thiểu 100 ảnh chụp thực tế đa điều kiện (kèm nhãn tọa độ 4 góc chuẩn và tập ảnh phẳng tham chiếu). Thực hiện các thí nghiệm nghiên cứu cắt bỏ thành phần (ablation study), so sánh các phương pháp phân ngưỡng (Otsu và Adaptive Thresholding), đánh giá hiệu quả của cơ chế fallback và đối sánh định lượng/định tính với ứng dụng thương mại thông qua các chỉ số: tỷ lệ phát hiện góc đúng, sai số góc (pixel), IoU tứ giác, PSNR/SSIM, độ đồng nhất nền và thời gian thực thi.
- **Về mặt sản phẩm phần mềm:** Xây dựng ứng dụng Web hoàn chỉnh cho phép người dùng tải ảnh lên, tự động phát hiện và cắt phẳng tài liệu, trực quan hóa so sánh Trước/Sau (Before/After), kéo chỉnh 4 góc thủ công khi cần thiết và tải ảnh tài liệu sạch về máy.

#### Phạm vi nghiên cứu
- **Đối tượng hỗ trợ tốt:**
  - Tài liệu một trang phẳng (giấy A4, A5, hóa đơn, trang sách phẳng, văn bản hành chính, biểu mẫu có bảng biểu).
  - Ảnh chụp có góc nghiêng phối cảnh vừa và lớn (tới khoảng $45^\circ$), có bóng đổ cục bộ, ánh sáng không đều hoặc nền bàn thông thường.
- **Giới hạn ngoài phạm vi (Out-of-scope):**
  - Tài liệu bị biến dạng phi tuyến nặng như trang sách dày bị cong phồng ở gáy (3D cylindrical/non-rigid dewarping) hoặc giấy bị vò nhàu nát nhiều nếp gấp.
  - Ảnh chụp thiếu sáng cực đoan hoặc bị nhòe chuyển động nặng (severe motion blur) khiến chữ không còn phân biệt được bằng mắt thường.

#### Điểm nhấn và đóng góp thực tiễn của nhóm
1. **Cơ chế kiểm tra tứ giác hợp lệ kết hợp Fallback kéo 4 góc thủ công (Human-in-the-loop Fallback):** Thay vì để pipeline trả về ảnh bị cắt sai hoặc biến dạng méo mó khi thuật toán tự động thất bại trên nền đồng màu/phức tạp, hệ thống tự động kiểm định tính hợp lệ hình học của tứ giác (số đỉnh, tính lồi, tỷ lệ diện tích, góc trong) và chuyển mượt mà sang giao diện tương tác để người dùng kéo 4 đỉnh về đúng góc trang giấy.
2. **Quy trình khử bóng bảo toàn chi tiết chữ:** Kết hợp ước lượng nền bằng phép đóng hình thái học (Morphological Closing) nhân lớn với phép chia chuẩn hóa trước khi áp dụng CLAHE và ngưỡng thích nghi, khắc phục triệt để nhược điểm mất chữ trong vùng bóng râm của ngưỡng toàn cục.

### 1.4. Bố cục báo cáo

Báo cáo được tổ chức thành 10 chương cùng phần Tài liệu tham khảo và Phụ lục như sau:

- **Chương 1 — Giới thiệu:** Phát biểu bài toán quét và cải thiện chất lượng tài liệu, phân tích các thách thức thực tế, nêu ứng dụng, mục tiêu, phạm vi và bố cục báo cáo.
- **Chương 2 — Cơ sở lý thuyết và các kỹ thuật sử dụng:** Trình bày nền tảng toán học, công thức và vai trò của từng kỹ thuật trong pipeline (Lọc Gaussian, Canny, Contour & xấp xỉ đa giác, Homography, chuyển xám & Otsu, Adaptive Thresholding, khử bóng/khử nhiễu/CLAHE, và các độ đo đánh giá).
- **Chương 3 — Dữ liệu:** Mô tả quy trình thu thập, gán nhãn bộ dữ liệu và phân tích thống kê các nhóm điều kiện chụp đầu vào.
- **Chương 4 — Pipeline đề xuất:** Trình bày sơ đồ khối tổng quan của hệ thống, mô tả chi tiết đầu vào/đầu ra, bộ tham số của từng bước và tiêu chí kiểm tra tứ giác hợp lệ + fallback.
- **Chương 5 — Cài đặt hệ thống:** Mô tả công nghệ sử dụng, cấu trúc thư mục mã nguồn, chữ ký 3 hàm cốt lõi trong package `core`, kiến trúc ứng dụng Web và giao diện kéo 4 góc thủ công.
- **Chương 6 — Thiết kế thí nghiệm:** Nêu các câu hỏi nghiên cứu, các cấu hình thực nghiệm (Ablation study, so sánh phương pháp phân ngưỡng, đánh giá fallback, đối sánh với ứng dụng thương mại) và định nghĩa chi tiết các độ đo.
- **Chương 7 — Kết quả và đánh giá:** Trình bày và phân tích các bảng kết quả định lượng, hình ảnh so sánh định tính, hiệu quả của cơ chế fallback và thống kê thời gian xử lý.
- **Chương 8 — Phân tích các trường hợp thất bại:** Đi sâu phân tích nguyên nhân kỹ thuật, tần suất xuất hiện và giải pháp khắc phục cho các ca lỗi điển hình ở từng mô-đun (phát hiện biên và tăng cường chất lượng).
- **Chương 9 — Demo sản phẩm:** Mô tả kịch bản video demo thực tế và hướng dẫn cài đặt, vận hành hệ thống.
- **Chương 10 — Kết luận và hướng phát triển:** Tổng kết những kết quả đạt được so với mục tiêu đề ra, nhìn nhận trung thực các hạn chế và đề xuất hướng cải tiến trong tương lai.

---

## 2. Cơ sở lý thuyết và các kỹ thuật sử dụng

*(Nội dung chi tiết mục 2.1 – 2.8 sẽ được TV1, TV2, TV3 hoàn thiện ở Tuần 2–4 theo đúng phân công)*

### 2.1. Lọc Gaussian (Gaussian filtering) — TV1
- *[Công thức kernel 2D Gaussian, vai trò làm mịn giảm nhiễu tần số cao trước khi tính đạo hàm dò biên, ảnh hưởng của kích thước kernel $k \times k$ và độ lệch chuẩn $\sigma$]*

### 2.2. Phát hiện biên Canny — TV1
- *[Các bước: tính biên độ và hướng gradient Sobel, triệt phi cực đại (non-maximum suppression), ngưỡng kép ($T_{\text{low}}, T_{\text{high}}$) và nối biên theo trễ (hysteresis)]*

### 2.3. Phát hiện contour và xấp xỉ đa giác — TV1
- *[Thuật toán `findContours`, thuật toán Ramer–Douglas–Peucker (`approxPolyDP`) với tham số $\epsilon = \alpha \cdot \text{chu vi}$, tiêu chí chọn contour tờ giấy: diện tích lớn nhất, 4 đỉnh, đa giác lồi]*

### 2.4. Biến đổi phối cảnh (Perspective transformation) — TV1
- *[Ma trận Homography $H \in \mathbb{R}^{3 \times 3}$, cách chuẩn hóa thứ tự 4 góc `[TL, TR, BR, BL]`, công thức tính chiều rộng $W'$ và chiều cao $H'$ của ảnh phẳng đầu ra]*

### 2.5. Chuyển ảnh xám và ảnh nhị phân — TV2
- *[Công thức độ chói chuẩn $Y = 0.299R + 0.587G + 0.114B$; phân ngưỡng toàn cục và thuật toán Otsu cực đại hóa phương sai giữa hai lớp]*

### 2.6. Ngưỡng thích nghi (Adaptive thresholding) — TV2
- *[Phương pháp trung bình cục bộ (Adaptive Mean) và trọng số Gaussian (Adaptive Gaussian), vai trò của kích thước lân cận `blockSize` và hằng số bù `C` dưới điều kiện chiếu sáng không đều]*

### 2.7. Loại bỏ bóng, khử nhiễu và tăng tương phản — TV2
- *[Ước lượng nền chiếu sáng bằng phép đóng hình thái học (Morphological Closing) hoặc lọc làm mờ nhân lớn, phép chia chuẩn hóa khử bóng; lọc trung vị (Median) / lọc song phương (Bilateral); thuật toán CLAHE]*

### 2.8. Các độ đo đánh giá chất lượng — TV3
- *[Định nghĩa và công thức toán học của: Sai số khoảng cách Euclid trung bình tại 4 đỉnh góc, Chỉ số giao trên hợp đa giác (Polygon IoU), PSNR, SSIM, Độ lệch chuẩn nền sáng (`bg_std`) và Độ tương phản chữ–nền (`fg_bg_contrast`)]*

---

## 3. Dữ liệu

### 3.1. Xây dựng hoặc lựa chọn bộ dữ liệu — TV3 (Khởi tạo Đợt 1 — Tuần 1)

Trong Tuần 1, nhóm đã khởi tạo cấu trúc lưu trữ tại thư mục `data/` và thu thập/khởi tạo **đợt 1 gồm 36 ảnh tài liệu** (`data/raw/doc_001.jpg` đến `data/raw/doc_036.jpg`) kèm tệp nhãn `data/metadata.csv` ghi nhận tọa độ 4 góc chuẩn `[TL, TR, BR, BL]` và nhóm điều kiện chụp. Trong Tuần 2, bộ dữ liệu sẽ được mở rộng lên tối thiểu **100 ảnh** kèm ảnh tham chiếu phẳng (ground truth) cho 20–30 ảnh đại diện để đánh giá PSNR/SSIM.

| Nguồn dữ liệu | Số ảnh (Tuần 1) | Mục tiêu (Tuần 2) | Điều kiện thu nhận | Có Ground Truth không |
|---|:---:|:---:|---|---|
| Bộ dữ liệu nhóm xây dựng (`data/raw/`) | 36 ảnh | $\ge 100$ ảnh | Đa dạng: nền đơn giản, nghiêng phối cảnh lớn, ánh sáng không đều, có bóng đổ, nền đồng màu/phức tạp, biểu mẫu/hóa đơn | Có tọa độ 4 góc trong `data/metadata.csv` (bổ sung ảnh phẳng tham chiếu chuẩn ở Tuần 2) |

### 3.2. Phân tích đặc điểm dữ liệu đầu vào — TV3

Bảng phân bố 36 ảnh đầu tiên trong Tuần 1 theo 6 nhóm điều kiện thực tế:

| Nhóm điều kiện (`condition_group`) | Mã ảnh | Số lượng | Đặc điểm kỹ thuật & Thách thức dự kiến |
|---|---|:---:|---|
| 1. `normal_simple_bg` | `doc_001` – `doc_006` | 6 | Ánh sáng đều, nền tối tương phản cao, góc nghiêng nhẹ ($<15^\circ$). Nhóm cơ sở (baseline) dễ phát hiện góc nhất. |
| 2. `tilted_perspective` | `doc_007` – `doc_012` | 6 | Góc chụp nghiêng lớn, biến dạng phối cảnh hình thang mạnh. Kiểm tra khả năng sắp xếp góc và nội suy khi warp. |
| 3. `uneven_lighting` | `doc_013` – `doc_018` | 6 | Ánh sáng phân bố gradient sáng–tối rõ rệt trên mặt giấy. Thách thức đối với ngưỡng toàn cục Otsu. |
| 4. `shadow_cast` | `doc_019` – `doc_024` | 6 | Bóng đổ chéo qua trang tài liệu làm giảm độ tương phản cục bộ và dễ tạo biên giả dọc ranh giới bóng. |
| 5. `similar_or_cluttered_bg` | `doc_025` – `doc_030` | 6 | **Nhóm dự kiến khó nhất cho `detect_corners`:** nền sáng màu gần giống giấy trắng hoặc có nhiều đường vân/chi tiết gây nhiễu contour. |
| 6. `receipt_and_table` | `doc_031` – `doc_036` | 6 | Tài liệu có khung bảng kẻ ô và chữ cỡ nhỏ; dễ bị bắt nhầm khung bảng bên trong thay vì viền tờ giấy ngoài cùng. |

---

## 4. Pipeline đề xuất (Đã tối ưu tích hợp tại `core/pipeline.py`)

### 4.1. Sơ đồ tổng quan

Sơ đồ khối tổng quan của Pipeline sau khi tích hợp các cơ chế bảo vệ lề trang giấy và làm trắng nền bảo toàn nét chữ:

```mermaid
flowchart TD
    A["Ảnh đầu vào (BGR chụp từ điện thoại / máy tính)"] --> B["Bước 1: Tiền xử lý dò biên\n(Chuyển xám + Lọc Gaussian 5x5)"]
    B --> C["Bước 2: Phát hiện biên & Đóng hình thái học\n(Canny Edge Detection + Morphological Closing)"]
    C --> D["Bước 3: Tìm Contour & Xấp xỉ đa giác\n(findContours + approxPolyDP)"]
    D --> E{"Bước 4: Tứ giác hợp lệ?\n(4 đỉnh, lồi, diện tích >= 15%, góc 45°-135°)"}
    E -- "Hợp lệ (is_valid = True)" --> E1{"Lề ngoài đã là giấy trắng?\n(_is_inner_border_on_clean_page)"}
    E1 -- "Đúng (Khung viền trong trang bìa)" --> E2["Giữ nguyên 4 góc toàn trang\n(Bảo toàn lề trắng trang giấy)"]
    E1 -- "Sai (Nền bàn ngoài trang giấy)" --> F["Chuẩn hóa thứ tự 4 góc\n[Top-Left, Top-Right, Bottom-Right, Bottom-Left]"]
    E2 --> F
    E -- "Không hợp lệ (is_valid = False)" --> G["Cơ chế Fallback:\nGợi ý 4 góc (minAreaRect) + Người dùng kéo 4 góc trên Web"]
    G --> F
    F --> H["Bước 5: Biến đổi phối cảnh Homography 3x3\n(warp_with_corners / Bỏ qua nội suy nếu góc trùng khung gốc)"]
    H --> I["Bước 6: Chuyển xám & Khử bóng đổ thích nghi\n(Morphological Closing nhân tỉ lệ theo ảnh + Chia chuẩn hóa)"]
    I --> J["Bước 7: Làm sắc nét Unsharp Mask & Mặt nạ ngưỡng thích nghi\n(Adaptive Gaussian Mask + Lọc nhiễu liên thông <= 3px)"]
    J --> K["Bước 8: Làm trắng nền & Kéo giãn tương phản mềm\n(Nền trắng 255 + Bảo toàn viền chống răng cưa nét chữ/con dấu)"]
    K --> L["Bước 9: Hiển thị Trước/Sau đặt cạnh nhau & Tải ảnh (.PNG / .JPG)"]
```

### 4.2. Mô tả từng bước và bảng tham số của Pipeline

| Bước | Kỹ thuật sử dụng | Hàm phụ trách | Tham số chính | Giá trị cấu hình | Lý do lựa chọn & Cải tiến chất lượng |
|---|---|---|---|---|---|
| **1. Tiền xử lý dò biên** | Chuyển xám, lọc Gaussian (`cv2.GaussianBlur`) | `detect_corners` (TV1) | `gaussian_ksize`, `sigma` | `ksize = (5, 5)`, `sigma = 1.2` | Làm mượt nhiễu hạt giấy và vân chữ nhỏ để tránh sinh cạnh giả khi tính đạo hàm dò biên. |
| **2. Phát hiện biên** | Dò biên Canny (`cv2.Canny`) + phép đóng (`cv2.morphologyEx`) | `detect_corners` (TV1) | `canny_low`, `canny_high`, `morph_ksize` | `canny_low = 50`, `canny_high = 150`, `ksize = (5, 5)` | Tỷ lệ ngưỡng $1:3$ theo khuyến nghị của Canny; phép đóng nối liền các đoạn biên tờ giấy bị đứt quãng. |
| **3. Tìm contour & xấp xỉ đa giác** | `cv2.findContours` (`RETR_LIST`) + `cv2.approxPolyDP` | `detect_corners` (TV1) | `top_k_contours`, `approx_eps_ratio` | `top_k = 5`, `eps = 0.02 * perimeter` | Xét 5 contour có diện tích lớn nhất; hệ số $2\%$ chu vi đủ để làm phẳng viền giấy hơi cong nhẹ về đúng 4 đỉnh. |
| **4. Kiểm tra tứ giác & bảo vệ lề trang** | Kiểm định hình học + kiểm tra độ sáng vùng ngoài tứ giác | `detect_corners` (TV1), `_is_inner_border_on_clean_page` (TV4) | `min_area_ratio`, `angle_range`, `bright_ratio` | `min_area_ratio = 0.15`, góc $[45^\circ, 135^\circ]$, vùng ngoài $\ge 85\%$ sáng $\ge 225$ | Loại bỏ contour nhiễu; đặc biệt **chống cắt nhầm vào khung kẻ trang trí bên trong trang bìa** khi ảnh đầu vào đã là trang giấy trắng thẳng sẵn. |
| **5. Biến đổi phối cảnh** | `cv2.getPerspectiveTransform` + `cv2.warpPerspective` | `warp_with_corners` (TV1), `process_document` (TV4) | `interpolation`, `border_mode` | `INTER_CUBIC`, `BORDER_REPLICATE` | Nội suy bậc ba giữ độ nét ký tự; tự động bỏ qua nội suy nếu 4 góc trùng với khung ảnh gốc ($\text{sai số} < 1.5\text{ px}$). |
| **6. Loại bỏ bóng đổ thích nghi** | Ước lượng nền bằng phép đóng hình thái học nhân elip + chia chuẩn hóa | `enhance` (TV2), `process_document` (TV4) | `bg_kernel_size` | $\max(31, \text{odd}(\min(H, W) / 18))$ | Tự động co giãn kích thước nhân theo độ phân giải ảnh để xóa sạch bóng đổ mà không làm tối chữ tiêu đề lớn hoặc con dấu. |
| **7. Làm sắc nét & Tách mặt nạ chữ–nền** | Unsharp Masking ($\sigma=1.0$) + `adaptiveThreshold` + lọc thành phần liên thông | `_refine_document_appearance` (TV4) | `block_size`, `c_offset`, `min_cc_area` | `block_size` tỉ lệ $\min(H,W)/28$, `c_offset = 12`, xóa hạt $\le 3\text{ px}$ | Khôi phục độ nét ký tự và loại bỏ hoàn toàn các hạt nhiễu nén JPEG li ti trên mặt giấy trắng. |
| **8. Làm trắng nền mềm bảo toàn nét chữ** | Kéo giãn phân vị mức xám kết hợp hiệu chỉnh Gamma trên vùng chữ | `_refine_document_appearance` (TV4) | `p_low`, `p_high`, `gamma` | Phân vị $[10\%, 96\%]$, $\gamma = 1.25$, nền $= 255$ | Đưa nền giấy về trắng tuyệt đối (`255`) nhưng giữ nguyên biên xám chống răng cưa (anti-aliasing), khắc phục triệt để lỗi chữ nhỏ bị phình bết của nhị phân cứng `0/255`. |

### 4.3. Cơ chế kiểm tra tứ giác hợp lệ và fallback — TV1

Một tứ giác ứng viên $Q = \{P_1, P_2, P_3, P_4\}$ tìm được từ bước xấp xỉ contour chỉ được đánh dấu là **hợp lệ (`is_valid = True`)** khi thỏa mãn đồng thời 4 điều kiện hình học:
1. **Đúng 4 đỉnh:** Đa giác sau `approxPolyDP` có đúng 4 đỉnh phân biệt.
2. **Tính lồi (Convexity):** `cv2.isContourConvex(Q) == True`, đảm bảo tứ giác không tự cắt hoặc lõm vào trong.
3. **Tỷ lệ diện tích tối thiểu:** Diện tích tứ giác chiếm ít nhất $15\%$ diện tích toàn khung hình ($\text{Area}(Q) \ge 0.15 \times W \times H$), tránh bắt nhầm nhãn dán, con dấu hoặc ô bảng nhỏ bên trong trang giấy.
4. **Ràng buộc góc trong:** Mọi góc trong tại 4 đỉnh nằm trong khoảng $[45^\circ, 135^\circ]$, tránh các tứ giác suy biến quá dẹt.

**Khi `is_valid == False` (Cơ chế Fallback):**
- Hàm `detect_corners` trả về bộ 4 góc gợi ý ban đầu (lấy từ hình chữ nhật bao nhỏ nhất `cv2.minAreaRect` của contour lớn nhất nếu có, hoặc khung chữ nhật cách đều lề ảnh $8\%$).
- Giao diện Web nhận cờ `is_valid = False` sẽ tự động bật **chế độ kéo 4 góc thủ công** với 4 nút điều khiển tại 4 đỉnh gợi ý, cho phép người dùng kéo thả trực quan và gửi tọa độ đã chỉnh về hàm `warp_with_corners`.

---

## 5. Cài đặt hệ thống

### 5.1. Công nghệ và môi trường

- **Ngôn ngữ lập trình:** Python 3.10+
- **Thư viện xử lý ảnh & tính toán:** OpenCV (`opencv-python`), NumPy (`numpy`), Pillow (`Pillow`)
- **Ứng dụng Web:** FastAPI / Uvicorn (Backend REST API) + HTML5 Canvas / JavaScript (Frontend kéo thả 4 góc tương tác, xem Trước/Sau)

### 5.2. Cấu trúc mã nguồn và giao diện các module (Hoàn thành Tuần 1)

Cấu trúc kho mã nguồn Git được phân tách theo từng thành viên để tránh xung đột khi làm việc nhóm:

```text
enhance-docs-quality/
  core/
    __init__.py          # Export 3 hàm chính: detect_corners, warp_with_corners, enhance
    detector.py          # Phát hiện 4 góc & kiểm tra tứ giác hợp lệ (TV1)
    warp.py              # Biến đổi phối cảnh Homography 3x3 (TV1)
    enhancer.py          # Khử bóng, khử nhiễu, CLAHE, nhị phân hóa (TV2)
    pipeline.py          # Hàm tích hợp end-to-end process_document() (TV4)
  web/
    app.py               # Backend API kết nối với package core (TV4)
    static/              # Frontend HTML/CSS/JS hiển thị Trước/Sau & Canvas kéo góc (TV4)
  experiments/
    tv1_sandbox.py       # Script test riêng của TV1
    tv2_sandbox.py       # Script test riêng của TV2
    metrics.py           # Các hàm tính sai số góc, IoU, PSNR, SSIM, độ đồng nhất nền (TV3)
    evaluate.py          # Script chạy Ablation, so sánh ngưỡng, đánh giá Fallback (TV3)
    seed_week1_dataset.py# Sinh bộ dữ liệu mẫu đợt 1 (TV3)
  data/
    raw/                 # 36 ảnh chụp đầu tiên (doc_001.jpg .. doc_036.jpg)
    metadata.csv         # Nhãn tọa độ 4 góc & phân nhóm điều kiện
    README.md
  report_draft.md        # Bản nháp báo cáo định dạng Markdown
  timeline.md            # Kế hoạch thực hiện 8 tuần
  requirements.txt
  README.md
```

**Chữ ký (Signature) của 3 hàm cốt lõi trong `core/`:**

1. **Phát hiện 4 góc tài liệu — Phụ trách: TV1 (`core/detector.py`)**
   ```python
   def detect_corners(
       image: np.ndarray,
       config: dict[str, Any] | None = None,
   ) -> dict[str, Any]:
       """Trả về dict gồm:
       - 'corners': np.ndarray shape (4, 2), dtype float32 theo thứ tự [TL, TR, BR, BL]
       - 'is_valid': bool (True nếu tứ giác hợp lệ, False nếu cần fallback chỉnh tay)
       - 'confidence': float (0.0 -> 1.0)
       - 'fallback_reason': str | None
       - 'debug_info': dict
       """
   ```

2. **Biến đổi phối cảnh từ 4 góc — Phụ trách: TV1 (`core/warp.py`)**
   ```python
   def warp_with_corners(
       image: np.ndarray,
       corners: np.ndarray,
       output_size: tuple[int, int] | None = None,
   ) -> np.ndarray:
       """Nhận ảnh gốc và mảng corners (4, 2), trả về ảnh tài liệu đã cắt nền và làm phẳng."""
   ```

3. **Tăng cường chất lượng ảnh tài liệu — Phụ trách: TV2 (`core/enhancer.py`)**
   ```python
   def enhance(
       image: np.ndarray,
       remove_shadow: bool = True,
       denoise: bool = True,
       use_clahe: bool = True,
       binarize: bool = True,
       config: dict[str, Any] | None = None,
   ) -> np.ndarray:
       """Trả về ảnh tài liệu đã chuyển xám, khử bóng, khử nhiễu, tăng tương phản CLAHE và nhị phân hóa."""
   ```

### 5.3. Ứng dụng web — TV4

Ứng dụng Web được thiết kế hướng tới **trải nghiệm sản phẩm hoàn chỉnh cho người dùng cuối (End-User Product)** theo kiến trúc **Client–Server tách biệt**, kết nối trực tiếp với luồng tích hợp `process_document()` trong `core/pipeline.py`:

```mermaid
sequenceDiagram
    participant U as Người dùng (Trình duyệt)
    participant FE as Frontend (HTML5 Canvas / app.js)
    participant BE as Backend FastAPI (web/app.py)
    participant CORE as Package Core (pipeline.py)

    U->>FE: 1. Kéo thả hoặc chọn ảnh chụp tài liệu (.JPG / .PNG)
    FE->>U: 2. Hiển thị trạng thái Loading ("Đang xử lý tài liệu...")
    FE->>BE: POST /api/scan (file ảnh)
    BE->>CORE: handle_auto_scan() -> process_document(image, manual_corners=None)
    CORE-->>BE: detection, corners_used, warped_image, enhanced_image, timing_ms
    BE-->>FE: JSON (image_id, corners, is_valid, timing_ms, images Base64 .PNG & .JPG)
    FE->>U: 3. Hiển thị 2 khung Trước (Ảnh gốc) & Sau (Ảnh kết quả) đặt cạnh nhau
    opt Khi is_valid = False hoặc người dùng bấm "Chỉnh 4 góc"
        U->>FE: Kéo 4 đỉnh [TL, TR, BR, BL] trên Ảnh gốc & bấm "Áp dụng 4 góc"
        FE->>BE: POST /api/rewarp (image_id, corners=[[x1,y1]..[x4,y4]])
        BE->>CORE: handle_manual_rewarp() -> process_document(image, manual_corners)
        CORE-->>BE: Ảnh phẳng & tăng cường mới
        BE-->>FE: JSON cập nhật Ảnh kết quả
    end
    U->>FE: 4. Chọn nút Tải về (.PNG hoặc .JPG)
```

1. **Thiết kế Backend REST API (`web/app.py`):**
   - **`POST /api/scan`:** Nhận file ảnh người dùng kéo thả hoặc chọn từ máy, giải mã sang mảng BGR OpenCV, lưu ảnh gốc vào bộ nhớ đệm phiên làm việc `_IMAGE_CACHE` theo `image_id` và gọi `handle_auto_scan()`. Kết quả trả về gồm tọa độ 4 góc `corners`, trạng thái kiểm định `is_valid`, thời gian thực thi `timing_ms` và dữ liệu ảnh kết quả được mã hóa sẵn ở cả hai định dạng `.PNG` (`images.enhanced`) và `.JPG` (`images.enhanced_jpg`).
   - **`POST /api/rewarp`:** Nhận `image_id` cùng tọa độ 4 góc `corners` sau khi người dùng kéo chỉnh trên ảnh gốc, lấy lại ảnh gốc từ bộ nhớ đệm mà không cần tải lại file và gọi `handle_manual_rewarp()` để cập nhật tức thì ảnh kết quả.

2. **Luồng trải nghiệm người dùng 4 bước (`web/static/index.html`, `style.css`, `app.js`):**
   - **Bước 1 — Kéo thả hoặc Chọn ảnh (`#drop-zone`):** Người dùng kéo thả trực tiếp file ảnh chụp tài liệu vào vùng tải ảnh hoặc bấm chọn file từ điện thoại/máy tính.
   - **Bước 2 — Xử lý & Hiển thị trạng thái chờ (`#loading-overlay`):** Trong lúc hệ thống thực thi pipeline dưới Backend, giao diện hiển thị biểu tượng xoay (spinner) kèm thông báo *"Đang xử lý tài liệu, vui lòng đợi..."*.
   - **Bước 3 — Đối chiếu Trước / Sau đặt cạnh nhau (`#workspace`):** Giao diện chia thành 2 khung song song: bên trái là **Ảnh gốc (Trước)** và bên phải là **Ảnh kết quả (Sau)** đã được cắt phẳng phối cảnh, khử bóng đổ và làm rõ nét chữ để người dùng so sánh trực tiếp.
   - **Bước 4 — Tải ảnh kết quả về máy (`.PNG` / `.JPG`):** Cung cấp 2 nút tải về trực tiếp ứng với 2 định dạng phổ biến: **⬇ Tải về .PNG** (bảo toàn chất lượng sắc nét không nén mất mát) và **⬇ Tải về .JPG** (dung lượng gọn nhẹ).

### 5.4. Giao diện kéo 4 góc thủ công — TV4

Để giữ cho giao diện so sánh Trước/Sau luôn sạch sẽ nhưng vẫn xử lý tốt các ca ảnh khó, cơ chế **kéo 4 góc thủ công (Human-in-the-loop Fallback)** được tích hợp ngay trên khung **Ảnh gốc (Trước)** (`<canvas id="input-canvas">`):

1. **Cơ chế kích hoạt thông minh:**
   - **Khi phát hiện tự động hợp lệ (`is_valid == True`):** Khung bên trái hiển thị ảnh gốc nguyên bản để người dùng đối chiếu trực diện với ảnh kết quả bên phải. Nếu muốn tự điều chỉnh lại vùng cắt, người dùng chỉ cần bấm nút **"Chỉnh 4 góc"** ở góc trên của khung ảnh gốc.
   - **Khi phát hiện tự động không đủ tin cậy (`is_valid == False`):** Giao diện tự động hiển thị thanh thông báo `#fallback-banner` và bật sẵn 4 chấm tròn `[TL, TR, BR, BL]` tại vị trí gợi ý trên ảnh gốc để người dùng kéo vào đúng 4 góc trang giấy rồi bấm **"Áp dụng 4 góc"**.

2. **Quy đổi hệ tọa độ giữa Canvas hiển thị và Ảnh gốc:**
   - Do ảnh chụp từ điện thoại thường có độ phân giải lớn $(W_{\text{orig}}, H_{\text{orig}})$ trong khi khung hiển thị trên trình duyệt có kích thước thu gọn $(W_{\text{disp}}, H_{\text{disp}})$, hệ thống duy trì hai hệ số tỷ lệ:
     $$s_x = \frac{W_{\text{orig}}}{W_{\text{disp}}}, \qquad s_y = \frac{H_{\text{orig}}}{H_{\text{disp}}}$$
   - **Khi vẽ từ dữ liệu lên Canvas:** Mỗi đỉnh $(x_{\text{orig}}, y_{\text{orig}})$ được chiếu sang tọa độ điểm ảnh trên Canvas $(x_c, y_c) = \left(\frac{x_{\text{orig}}}{s_x}, \frac{y_{\text{orig}}}{s_y}\right)$.
   - **Khi người dùng kéo thả trên Canvas:** Sự kiện `mousedown` / `touchstart` tính khoảng cách Euclid từ vị trí con trỏ $(p_x, p_y)$ tới cả 4 đỉnh trên Canvas và bắt đỉnh gần nhất nếu khoảng cách $d \le 22\text{ px}$. Khi di chuyển (`mousemove` / `touchmove`), tọa độ mới trên ảnh gốc được tính ngược và kẹp biên an toàn:
     $$x_{\text{orig}} = \text{clip}\!\left(p_x \cdot s_x,\; 0,\; W_{\text{orig}} - 1\right), \qquad y_{\text{orig}} = \text{clip}\!\left(p_y \cdot s_y,\; 0,\; H_{\text{orig}} - 1\right)$$
   - Khi gửi mảng 4 đỉnh về `POST /api/rewarp`, hàm `process_document` tiếp tục gọi `order_corners()` để tự động sắp xếp lại đúng thứ tự chuẩn `[TL, TR, BR, BL]`, đảm bảo ma trận Homography không bị lật hoặc xoắn.

---

## 6. Thiết kế thí nghiệm — TV3

*(Cập nhật chi tiết ở Tuần 4–5)*

### 6.1. Câu hỏi nghiên cứu
1. Từng bước trong pipeline (làm phẳng phối cảnh, loại bóng đổ, CLAHE, ngưỡng thích nghi) đóng góp bao nhiêu phần trăm cải thiện vào chất lượng ảnh đầu ra (PSNR/SSIM, độ đồng nhất nền, độ tương phản chữ–nền)?
2. Phương pháp phân ngưỡng thích nghi (Adaptive Mean / Adaptive Gaussian) vượt trội như thế nào so với ngưỡng toàn cục Otsu trên nhóm ảnh có bóng đổ và ánh sáng không đều?
3. Cơ chế fallback kéo 4 góc thủ công giúp khôi phục được bao nhiêu phần trăm các trường hợp phát hiện biên tự động thất bại?
4. Chất lượng đầu ra của hệ thống so với ứng dụng thương mại (CamScanner / Adobe Scan) đạt mức nào?

### 6.2. Các cấu hình so sánh

| Thí nghiệm | Biến thay đổi | Các cấu hình so sánh | Mục đích |
|---|---|---|---|
| **Ablation Study** | Bỏ/thêm từng bước xử lý | (1) Chỉ chuyển xám + Nhị phân, (2) Warp + Nhị phân, (3) Warp + Khử bóng + Nhị phân, (4) Pipeline đầy đủ (Warp + Khử bóng + Khử nhiễu + CLAHE + Nhị phân) | Đánh giá đóng góp riêng lẻ của từng bước trong pipeline |
| **So sánh phân ngưỡng** | Thuật toán nhị phân hóa | Otsu toàn cục, Adaptive Mean, Adaptive Gaussian | Kiểm chứng hiệu quả xử lý ánh sáng không đều và bóng đổ |
| **Khảo sát tham số** | Tham số chính | `block_size` $\in \{11, 21, 31, 41\}$, ngưỡng Canny | Tìm bộ siêu tham số tối ưu trên tập dữ liệu |
| **So sánh với App** | Hệ thống đối chứng | Hệ thống của nhóm vs. CamScanner / Adobe Scan | Đối sánh thực tế với sản phẩm thương mại |
| **Đánh giá Fallback** | Chế độ xác định góc | Tự động hoàn toàn vs. Tự động + Fallback chỉnh tay | Lượng hóa giá trị của cơ chế tương tác người–máy |

### 6.3. Độ đo đánh giá
- **Độ chính xác phát hiện góc:** Sai số khoảng cách Euclid trung bình tại 4 đỉnh (pixel), chỉ số giao trên hợp (Polygon IoU) và Tỷ lệ phát hiện góc đúng ($\text{IoU} \ge 0.90$).
- **Chất lượng ảnh có tham chiếu:** PSNR (dB) và SSIM trên tập ảnh có bản phẳng chuẩn.
- **Chất lượng ảnh không tham chiếu & Hiệu năng:** Độ lệch chuẩn vùng nền trắng (`bg_std`), độ tương phản chữ–nền (`fg_bg_contrast`) và thời gian xử lý trung bình (ms/ảnh).

---

## 7. Kết quả và đánh giá — TV3 tổng hợp

*(Số liệu thực nghiệm sẽ được điền vào Tuần 4–6)*

### 7.1. Đánh giá định lượng

| Phương pháp / Cấu hình | Phát hiện góc đúng (%) | IoU trung bình | PSNR (dB) / SSIM | Độ lệch chuẩn nền (`bg_std` $\downarrow$) | Thời gian (ms) |
|---|:---:|:---:|:---:|:---:|:---:|
| Ảnh gốc (chỉ chuyển xám + Otsu) | — | — | [...] | [...] | [...] |
| Chỉ biến đổi phối cảnh + Otsu | [...] | [...] | [...] | [...] | [...] |
| Warp + Adaptive Threshold (chưa khử bóng) | [...] | [...] | [...] | [...] | [...] |
| **Pipeline đầy đủ (Đề xuất)** | **[...]** | **[...]** | **[...]** | **[...]** | **[...]** |
| Ứng dụng đối chứng (CamScanner/Adobe Scan) | [...] | [...] | [...] | [...] | [...] |

### 7.2. Đánh giá định tính
- *[Hiển thị 4–6 ví dụ tiêu biểu theo hàng: Ảnh gốc | Kết quả của nhóm | Kết quả ứng dụng đối chứng]*

### 7.3. Hiệu quả của cơ chế fallback
- *[Thống kê tỷ lệ ảnh tự động thất bại và mức cải thiện IoU, PSNR/SSIM sau khi người dùng kéo 4 góc thủ công]*

### 7.4. Thời gian xử lý

Hàm tích hợp `process_document()` trong `core/pipeline.py` sử dụng bộ đếm độ phân giải cao `time.perf_counter()` để đo độc lập thời gian thực thi của từng giai đoạn và trả về trực tiếp trên giao diện Web. Bảng dưới đây thống kê thời gian xử lý thực tế trên bộ 36 ảnh kiểm thử (`data/raw/doc_001.jpg` đến `doc_036.jpg`) sau khi tích hợp đầy đủ cơ chế bảo vệ lề trang giấy và làm trắng nền bảo toàn nét chữ:

| Giai đoạn xử lý | Hàm thực thi | Thời gian trung bình (ms) | Nhỏ nhất – Lớn nhất (ms) | Tỷ trọng (%) | Nhận xét kỹ thuật |
|---|---|:---:|:---:|:---:|---|
| **1. Phát hiện biên, 4 góc & Kiểm tra lề** | `detect_corners` + `_is_inner_border_on_clean_page` | $12.77$ | $5.84 - 35.87$ | $20.90\%$ | Chuẩn hóa chiều cao tạm thời về `proc_height = 800` khi dò biên Canny và kiểm tra phân bố độ sáng vùng ngoài tứ giác. |
| **2. Biến đổi phối cảnh** | `warp_with_corners` | $4.16$ | $2.72 - 9.94$ | $6.81\%$ | Phép nhân ma trận Homography $3 \times 3$ và nội suy bậc ba `INTER_CUBIC` (tự động bỏ qua nội suy khi góc trùng khung gốc). |
| **3. Khử bóng & Tinh chỉnh nét chữ mềm** | `enhance` + `_refine_document_appearance` | $44.18$ | $29.81 - 85.86$ | $72.29\%$ | Gồm phép đóng hình thái học nhân lớn khử bóng, làm sắc nét Unsharp Mask, lọc nhiễu liên thông ($\le 3\text{ px}$) và kéo giãn tương phản mềm bảo toàn chống răng cưa. |
| **Tổng cộng End-to-End** | `process_document` | **$61.11$** | **$43.25 - 125.62$** | **$100\%$** | Tốc độ trung bình đạt $\approx 16.4\text{ ảnh/giây}$ ($\approx 0.06\text{ giây/ảnh}$), đảm bảo phản hồi tức thì cho người dùng trên Web. |

---

## 8. Phân tích các trường hợp thất bại

*(Hoàn thiện ở Tuần 6)*

### 8.1. Thất bại ở phát hiện biên và phối cảnh — TV1
- **Nền lẫn màu giấy:** [...]
- **Giấy bị che góc:** [...]
- **Giấy cong hoặc nhàu:** [...]
- **Nền nhiều chi tiết:** [...]

### 8.2. Thất bại ở tăng cường chất lượng — TV2
- **Bóng đậm:** [...]
- **Ánh sáng không đều:** [...]
- **Chữ mờ hoặc nét mảnh bị mất khi nhị phân:** [...]

### 8.3. Tổng hợp và hướng khắc phục — TV3 tổng hợp

| Trường hợp thất bại | Nguyên nhân kỹ thuật | Tần suất gặp | Giải pháp khắc phục |
|---|---|---|---|
| [...] | [...] | [...] | [...] |

---

## 9. Demo sản phẩm — TV4

- **Link video demo:** *[Cập nhật link Google Drive / YouTube khi nộp bài]*
- **Kịch bản trình diễn thực tế trên Ứng dụng Web (Thời lượng 2–4 phút):**
  1. **Tình huống 1 — Kéo thả ảnh tài liệu tiêu chuẩn & nghiêng phối cảnh lớn (`doc_001.jpg`, `doc_009.jpg`):**
     - Người dùng kéo thả trực tiếp file ảnh chụp tài liệu vào vùng tải ảnh trên trang Web.
     - Giao diện hiển thị trạng thái *"Đang xử lý tài liệu, vui lòng đợi..."* rồi lập tức hiển thị **Ảnh gốc (Trước)** bên trái và **Ảnh kết quả (Sau)** bên phải đặt cạnh nhau để đối chiếu trực quan.
  2. **Tình huống 2 — Xử lý ảnh chụp có bóng đổ nặng (`doc_019.jpg`):**
     - Tải lên ảnh tài liệu có bóng đổ chéo rõ rệt; so sánh trực tiếp khung Trước (có bóng tối che chữ) và khung Sau (nền giấy trắng sạch đồng nhất, chữ rõ nét).
  3. **Tình huống 3 — Chỉnh 4 góc thủ công trên nền đồng màu/phức tạp (`doc_025.jpg`) & Tải ảnh kết quả:**
     - Khi ảnh đầu vào có nền sáng màu trùng màu giấy (`is_valid = False`), ứng dụng tự động hiển thị thông báo hướng dẫn và bật 4 chấm tròn `[TL, TR, BR, BL]` ngay trên khung **Ảnh gốc (Trước)**.
     - Người dùng kéo 4 đỉnh vào đúng 4 góc trang giấy, bấm **"Áp dụng 4 góc"** để nhận bản quét phẳng sạch bên khung phải, sau đó bấm **"⬇ Tải về .PNG"** hoặc **"⬇ Tải về .JPG"** để lưu tài liệu về máy.

---

## 10. Kết luận và hướng phát triển

*(Hoàn thiện ở Tuần 7–8)*
### 10.1. Kết luận
### 10.2. Hạn chế
### 10.3. Hướng phát triển

---

## Tài liệu tham khảo

1. R. C. Gonzalez and R. E. Woods, *Digital Image Processing*, 4th ed. Pearson, 2018.
2. J. Canny, "A Computational Approach to Edge Detection," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. PAMI-8, no. 6, pp. 679–698, Nov. 1986.
3. N. Otsu, "A Threshold Selection Method from Gray-Level Histograms," *IEEE Transactions on Systems, Man, and Cybernetics*, vol. 9, no. 1, pp. 62–66, Jan. 1979.
4. K. Zuiderveld, "Contrast Limited Adaptive Histograph Equalization," in *Graphics Gems IV*, Academic Press, 1994, pp. 474–485.
5. D. H. Douglas and T. K. Peucker, "Algorithms for the reduction of the number of points required to represent a digitized line or its caricature," *Cartographica*, vol. 10, no. 2, pp. 112–122, 1973.
6. Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, "Image quality assessment: from error visibility to structural similarity," *IEEE Transactions on Image Processing*, vol. 13, no. 4, pp. 600–612, Apr. 2004.
7. OpenCV Documentation, "Image Processing (imgproc module)," [Online]. Available: https://docs.opencv.org/

---

## Phụ lục

### Phụ lục A: Bảng đóng góp chi tiết từng thành viên

| Thành viên | Mô-đun mã nguồn sở hữu | Mục báo cáo phụ trách | Các đầu việc đã thực hiện | Tỷ lệ |
|---|---|---|---|:---:|
| **Nguyễn Thị Ngọc Mai (TV1)** | `core/detector.py`<br>`core/warp.py`<br>`experiments/tv1_sandbox.py` | Mục 2.1 – 2.4, 4.3, 8.1 | Cài đặt lọc Gaussian, dò biên Canny + phép đóng hình thái học, xấp xỉ đa giác `approxPolyDP`, kiểm định tứ giác lồi hợp lệ (`validate_quadrilateral`), gợi ý góc fallback (`minAreaRect`) và biến đổi phối cảnh Homography $3 \times 3$. | 25% |
| **Khổng Thị Thùy Linh (TV2)** | `core/enhancer.py`<br>`experiments/tv2_sandbox.py` | Mục 2.5 – 2.7, 8.2 | Cài đặt chuyển đổi đa mức xám, ước lượng nền bằng phép đóng hình thái học nhân elip lớn để chia chuẩn hóa khử bóng đổ (`remove_shadow_bg`), khử nhiễu (`median`/`bilateral`), cân bằng biểu đồ cục bộ CLAHE và nhị phân hóa (`otsu`, `adaptive_mean`, `adaptive_gaussian`). | 25% |
| **Nguyễn Thị Anh Ngọc (TV3)** | `experiments/metrics.py`<br>`experiments/evaluate.py`<br>`data/*` | Mục 2.8, Chương 3, 6, 7.1 – 7.3, 8.3 | Thu thập và gán nhãn tọa độ 4 góc bộ dữ liệu (`metadata.csv`), cài đặt bộ độ đo định lượng (sai số góc Euclid, Polygon IoU, PSNR, SSIM, `bg_std`, `fg_bg_contrast`), thiết kế và vận hành các kịch bản thực nghiệm Ablation Study & đánh giá Fallback. | 25% |
| **Đoàn Thị Hồng Nhung (TV4)** | `core/pipeline.py`<br>`web/app.py`<br>`web/static/*` | Mục 4.1 – 4.2 (cập nhật tích hợp), 5.1 – 5.4, 7.4, Chương 9, Phụ lục D | Tích hợp và tối ưu pipeline end-to-end `process_document()` (bổ sung bảo vệ lề trang giấy `_is_inner_border_on_clean_page` và làm trắng nền bảo toàn nét chữ `_refine_document_appearance`), xây dựng Backend FastAPI (`/api/scan`, `/api/rewarp`), phát triển giao diện Web kéo thả ảnh, xem Trước/Sau đặt cạnh nhau, chỉnh 4 góc thủ công và tải ảnh kết quả (`.PNG` / `.JPG`). | 25% |

### Phụ lục B: Bảng tham số đầy đủ của pipeline

| Nhóm mô-đun | Tên tham số trong `config` | Giá trị mặc định | Kiểu dữ liệu | Ý nghĩa kỹ thuật |
|---|---|:---:|:---:|---|
| **Dò biên & Góc (`detector.py`)** | `proc_height` | `800` | `int` | Chiều cao chuẩn hóa tạm thời khi dò biên để tăng tốc độ xử lý |
| | `gaussian_ksize` | `(5, 5)` | `tuple[int, int]` | Kích thước nhân lọc làm mịn Gaussian |
| | `gaussian_sigma` | `1.2` | `float` | Độ lệch chuẩn $\sigma$ của bộ lọc Gaussian |
| | `canny_low`, `canny_high` | `50`, `150` | `int` | Ngưỡng kép dưới và trên của thuật toán dò biên Canny |
| | `morph_ksize` | `(5, 5)` | `tuple[int, int]` | Kích thước nhân phép đóng hình thái học nối liền biên đứt |
| | `top_k_contours` | `5` | `int` | Số lượng contour có diện tích lớn nhất đưa vào xét duyệt |
| | `approx_eps_ratio` | `0.02` | `float` | Hệ số $\epsilon$ xấp xỉ đa giác theo tỷ lệ chu vi contour |
| | `min_area_ratio` | `0.15` | `float` | Tỷ lệ diện tích tối thiểu của tứ giác tài liệu so với khung hình |
| | `min_angle_deg`, `max_angle_deg` | `45.0`, `135.0` | `float` | Khoảng góc trong hợp lệ tại mỗi đỉnh của tứ giác (độ) |
| **Tăng cường (`enhancer.py`)** | `bg_kernel_size` | $\max(31, \text{odd}(\min(H,W)/18))$ | `int` | Kích thước nhân elip đóng hình thái học ước lượng nền khử bóng (tự động tỉ lệ theo ảnh) |
| | `denoise_method` | `"median"` | `str` | Phương pháp lọc nhiễu (`"median"` hoặc `"bilateral"`) |
| | `denoise_ksize` | `3` | `int` | Kích thước cửa sổ lọc trung vị Median |
| | `clahe_clip_limit` | `2.0` | `float` | Ngưỡng giới hạn khuếch đại tương phản của CLAHE |
| | `clahe_tile_grid` | `(8, 8)` | `tuple[int, int]` | Số ô lưới chia cục bộ trong thuật toán CLAHE |
| | `threshold_method` | `"adaptive_gaussian"` | `str` | Thuật toán nhị phân hóa (`"adaptive_gaussian"`, `"adaptive_mean"`, `"otsu"`) |
| | `block_size` | `21` | `int` | Kích thước vùng lân cận cục bộ (số lẻ $\ge 3$) khi tính ngưỡng thích nghi |
| | `c_offset` | `10` | `float` | Hằng số trừ bù $C$ trong phân ngưỡng thích nghi |
| **Điều phối & Hậu xử lý (`pipeline.py`)** | `protect_inner_border` | `True` | `bool` | Tự động giữ nguyên lề trắng khi phát hiện tứ giác chỉ là khung kẻ trang trí bên trong trang giấy |
| | `soft_binarize` | `True` | `bool` | Làm trắng nền `255` kết hợp Unsharp Mask, lọc hạt nhiễu $\le 3\text{ px}$ và kéo giãn tương phản mềm chống răng cưa |

### Phụ lục C: Thêm ảnh kết quả thực nghiệm
- *(Tổng hợp hình ảnh minh họa từ thư mục `experiments/outputs/`)*

### Phụ lục D: Hướng dẫn cài đặt và chạy hệ thống — TV4

1. **Yêu cầu môi trường:** Python 3.10 trở lên. Khuyến khích sử dụng môi trường ảo (`venv`).
2. **Cài đặt các thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Khởi chạy ứng dụng Web (Giao diện đầy đủ):**
   ```bash
   python -m web.app
   ```
   Hoặc chạy qua Uvicorn với chế độ tự động tải lại khi sửa code:
   ```bash
   uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
   ```
   Sau khi khởi động, mở trình duyệt truy cập địa chỉ **`http://127.0.0.1:8000`**.
4. **Chạy các kịch bản kiểm thử và đánh giá định lượng qua dòng lệnh (CLI):**
   ```bash
   python experiments/tv1_sandbox.py   # Kiểm thử phát hiện 4 góc & làm phẳng (TV1)
   python experiments/tv2_sandbox.py   # Kiểm thử khử bóng, CLAHE & nhị phân hóa (TV2)
   python experiments/evaluate.py      # Chạy đánh giá định lượng trên bộ dữ liệu (TV3)
   ```
