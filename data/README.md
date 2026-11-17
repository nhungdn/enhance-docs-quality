# Bộ dữ liệu kiểm thử — Tuần 1 (Khởi động)

Thư mục `data/` lưu trữ dữ liệu ảnh tài liệu và nhãn phục vụ phát triển và đánh giá hệ thống (TV3 phụ trách).

## Cấu trúc thư mục

```text
data/
├── raw/            # 36 ảnh tài liệu đầu tiên (doc_001.jpg .. doc_036.jpg)
├── metadata.csv    # Bảng thông tin điều kiện chụp và nhãn tọa độ 4 góc [TL, TR, BR, BL]
└── README.md       # Mô tả bộ dữ liệu
```

## Phân bố 36 ảnh đợt 1 (Tuần 1)

| Nhóm điều kiện (`condition_group`) | Mã ảnh | Số lượng | Mô tả |
|---|---|---:|---|
| `normal_simple_bg` | `doc_001` – `doc_006` | 6 | Ánh sáng đều, nền tối tương phản cao, nghiêng nhẹ |
| `tilted_perspective` | `doc_007` – `doc_012` | 6 | Góc chụp nghiêng lớn, biến dạng phối cảnh mạnh |
| `uneven_lighting` | `doc_013` – `doc_018` | 6 | Ánh sáng không đều, gradient sáng–tối rõ rệt |
| `shadow_cast` | `doc_019` – `doc_024` | 6 | Có bóng đổ chéo/bóng điện thoại che một phần trang giấy |
| `similar_or_cluttered_bg` | `doc_025` – `doc_030` | 6 | Nền sáng màu gần giống màu giấy hoặc nhiều chi tiết |
| `receipt_and_table` | `doc_031` – `doc_036` | 6 | Biểu mẫu/hóa đơn có kẻ bảng và cỡ chữ nhỏ |
| **Tổng cộng (Đợt 1 - Tuần 1)** | `doc_001` – `doc_036` | **36** | Đạt chỉ tiêu 30–50 ảnh đầu tiên của Tuần 1 |
