/**
 * PHÂN CÔNG: Thành viên 4 (TV4) sở hữu và chỉnh sửa file này.
 *
 * Lộ trình công việc của TV4:
 * - Tuần 2: Gửi ảnh từ #image-input lên POST /api/scan, hiển thị ảnh kết quả vào #output-image.
 * - Tuần 3: Hoàn thiện hiển thị Trước/Sau và nút tải ảnh #download-btn.
 * - Tuần 4:
 *   + Vẽ ảnh gốc và tứ giác 4 đỉnh [TL, TR, BR, BL] lên #input-canvas.
 *   + Bắt sự kiện mousedown / mousemove / mouseup (và touch) để kéo từng đỉnh.
 *   + Quy đổi tọa độ từ kích thước hiển thị trên Canvas về kích thước thật của ảnh gốc,
 *     rồi gửi lên POST /api/rewarp khi bấm #apply-corners-btn.
 */

const state = {
  corners: [
    [0, 0],
    [0, 0],
    [0, 0],
    [0, 0],
  ],
  isValid: false,
  scaleX: 1.0,
  scaleY: 1.0,
};

console.log("Web UI stub initialized (TV4).", state);
