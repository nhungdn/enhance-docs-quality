/**
 * PHÂN CÔNG: Thành viên 4 (TV4) sở hữu và chỉnh sửa file này.
 *
 * Luồng trải nghiệm người dùng cuối:
 * 1. Người dùng kéo thả hoặc chọn ảnh chụp tài liệu (#drop-zone / #image-input).
 * 2. Hiển thị trạng thái Loading (#loading-overlay) trong lúc gửi ảnh lên POST /api/scan.
 * 3. Hiển thị 2 khung đặt cạnh nhau (#workspace):
 *    - Trái: Ảnh gốc (Trước) — hỗ trợ bật/tắt kéo chỉnh 4 góc [TL, TR, BR, BL] khi cần.
 *    - Phải: Ảnh kết quả (Sau).
 * 4. Người dùng bấm nút Tải về hỗ trợ 2 định dạng .PNG (#download-btn) và .JPG (#download-jpg-btn).
 */

const CORNER_LABELS = ["TL", "TR", "BR", "BL"];
const CORNER_COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#f59e0b"];

const state = {
  imageId: null,
  filename: "tai_lieu_da_quet",
  originalImageObj: null,
  imageWidth: 0,
  imageHeight: 0,
  corners: [
    [0, 0],
    [0, 0],
    [0, 0],
    [0, 0],
  ],
  isValid: true,
  showCornerHandles: false,
  scaleX: 1.0,
  scaleY: 1.0,
  draggingIdx: -1,
  hoverIdx: -1,
  currentFile: null,
};

// DOM Elements
const dropZone = document.getElementById("drop-zone");
const imageInput = document.getElementById("image-input");
const fileNameDisplay = document.getElementById("file-name-display");
const scanBtn = document.getElementById("scan-btn");

const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");

const fallbackBanner = document.getElementById("fallback-banner");
const fallbackReasonText = document.getElementById("fallback-reason-text");
const applyCornersBtn = document.getElementById("apply-corners-btn");

const workspace = document.getElementById("workspace");
const canvasContainer = document.getElementById("canvas-container");
const inputCanvas = document.getElementById("input-canvas");
const canvasHint = document.getElementById("canvas-hint");
const ctx = inputCanvas.getContext("2d");

const toggleCornersBtn = document.getElementById("toggle-corners-btn");
const rewarpBtn = document.getElementById("rewarp-btn");

const outputImage = document.getElementById("output-image");
const timeBadge = document.getElementById("time-badge");
const downloadPngBtn = document.getElementById("download-btn");
const downloadJpgBtn = document.getElementById("download-jpg-btn");

/**
 * Bật/tắt khung thông báo Loading
 */
function setLoading(isLoading, message = "Đang xử lý tài liệu, vui lòng đợi...") {
  loadingText.textContent = message;
  loadingOverlay.hidden = !isLoading;
}

/**
 * Xử lý file ảnh khi người dùng chọn hoặc kéo thả vào
 */
function handleSelectedFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    alert("Vui lòng chọn một file ảnh hợp lệ (.JPG, .PNG)!");
    return;
  }
  state.currentFile = file;
  fileNameDisplay.textContent = `Đã chọn: ${file.name}`;
  scanBtn.hidden = false;
  runAutoScan(file);
}

/**
 * Gửi ảnh lên POST /api/scan để tự động cắt phẳng và làm sạch
 */
async function runAutoScan(file) {
  const targetFile = file || state.currentFile;
  if (!targetFile) return;

  const formData = new FormData();
  formData.append("file", targetFile);

  try {
    setLoading(true, "Đang xử lý tài liệu, vui lòng đợi...");
    fallbackBanner.hidden = true;

    const res = await fetch("/api/scan", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Không thể xử lý ảnh này.");
    }

    await applyScanResult(data);
  } catch (err) {
    alert(err.message);
  } finally {
    setLoading(false);
  }
}

/**
 * Gửi tọa độ 4 góc đã kéo chỉnh về POST /api/rewarp
 */
async function runManualRewarp() {
  if (!state.imageId) return;

  try {
    setLoading(true, "Đang cắt phẳng lại theo 4 góc đã chọn...");
    rewarpBtn.disabled = true;
    applyCornersBtn.disabled = true;

    const res = await fetch("/api/rewarp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_id: state.imageId,
        corners: state.corners,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Không thể cập nhật 4 góc.");
    }

    await applyScanResult(data);
    // Sau khi áp dụng xong, ẩn khung kéo góc để người dùng so sánh Trước/Sau rõ ràng
    setCornerEditMode(false);
  } catch (err) {
    alert(err.message);
  } finally {
    setLoading(false);
    rewarpBtn.disabled = false;
    applyCornersBtn.disabled = false;
  }
}

/**
 * Hiển thị kết quả Trước / Sau và cập nhật nút tải về (.PNG / .JPG)
 */
async function applyScanResult(data) {
  state.imageId = data.image_id;
  state.filename = (data.filename || "tai_lieu").replace(/\.[^/.]+$/, "");
  state.imageHeight = data.image_shape[0];
  state.imageWidth = data.image_shape[1];
  state.corners = data.corners.map((pt) => [Number(pt[0]), Number(pt[1])]);
  state.isValid = Boolean(data.is_valid);

  await loadOriginalImage(data.images.original);

  workspace.hidden = false;

  // Nếu tự động phát hiện thất bại (is_valid = false), tự động bật chế độ kéo 4 góc
  if (!state.isValid && data.source === "auto") {
    fallbackBanner.hidden = false;
    if (data.fallback_message) {
      fallbackReasonText.innerHTML =
        `${data.fallback_message} Bạn hãy kéo 4 chấm tròn trên <strong>Ảnh gốc</strong> vào đúng 4 góc tài liệu rồi bấm <strong>Áp dụng 4 góc</strong>.`;
    }
    setCornerEditMode(true);
  } else {
    fallbackBanner.hidden = true;
    setCornerEditMode(false);
  }

  // Hiển thị ảnh kết quả bên phải
  outputImage.src = data.images.enhanced;

  // Thời gian xử lý nhỏ gọn
  if (data.timing_ms && data.timing_ms.total_ms) {
    timeBadge.textContent = `Hoàn tất trong ${(data.timing_ms.total_ms / 1000).toFixed(2)}s`;
  }

  // Cập nhật 2 nút tải về (.PNG và .JPG)
  downloadPngBtn.href = data.images.enhanced;
  downloadPngBtn.download = `${state.filename}_cleaned.png`;

  downloadJpgBtn.href = data.images.enhanced_jpg || data.images.enhanced;
  downloadJpgBtn.download = `${state.filename}_cleaned.jpg`;
}

/**
 * Bật hoặc tắt chế độ hiển thị 4 nút kéo góc trên Ảnh gốc (Trước)
 */
function setCornerEditMode(enabled) {
  state.showCornerHandles = Boolean(enabled);
  toggleCornersBtn.textContent = state.showCornerHandles ? "Ẩn khung 4 góc" : "Chỉnh 4 góc";
  rewarpBtn.hidden = !state.showCornerHandles;
  canvasHint.hidden = !state.showCornerHandles;
  inputCanvas.style.cursor = state.showCornerHandles ? "crosshair" : "default";
  resizeAndRenderCanvas();
}

function loadOriginalImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      state.originalImageObj = img;
      resolve();
    };
    img.onerror = reject;
    img.src = dataUrl;
  });
}

/**
 * Căn chỉnh kích thước Canvas khớp với khung Trước và vẽ ảnh gốc
 */
function resizeAndRenderCanvas() {
  if (!state.originalImageObj) return;

  const containerWidth = Math.max(280, canvasContainer.clientWidth - 16);
  const maxDisplayHeight = 560;

  const imgW = state.imageWidth || state.originalImageObj.naturalWidth;
  const imgH = state.imageHeight || state.originalImageObj.naturalHeight;

  const ratio = Math.min(containerWidth / imgW, maxDisplayHeight / imgH, 1.0);
  const dispW = Math.round(imgW * ratio);
  const dispH = Math.round(imgH * ratio);

  inputCanvas.width = dispW;
  inputCanvas.height = dispH;

  state.scaleX = imgW / dispW;
  state.scaleY = imgH / dispH;

  renderCanvas();
}

/**
 * Vẽ ảnh gốc (và vẽ thêm khung 4 góc nếu đang ở chế độ chỉnh góc)
 */
function renderCanvas() {
  if (!state.originalImageObj) return;

  const w = inputCanvas.width;
  const h = inputCanvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(state.originalImageObj, 0, 0, w, h);

  if (!state.showCornerHandles) return;

  const canvasPts = state.corners.map(([x, y]) => [
    x / state.scaleX,
    y / state.scaleY,
  ]);

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(canvasPts[0][0], canvasPts[0][1]);
  for (let i = 1; i < 4; i++) {
    ctx.lineTo(canvasPts[i][0], canvasPts[i][1]);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(37, 99, 235, 0.16)";
  ctx.fill();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = "#3b82f6";
  ctx.stroke();
  ctx.restore();

  for (let i = 0; i < 4; i++) {
    const [cx, cy] = canvasPts[i];
    const isActive = i === state.draggingIdx || i === state.hoverIdx;
    const radius = isActive ? 12 : 9;

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius + 2.5, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fillStyle = CORNER_COLORS[i];
    ctx.fill();

    ctx.font = "bold 10px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#ffffff";
    ctx.fillText(CORNER_LABELS[i], cx, cy);
    ctx.restore();
  }
}

function getCanvasPointerPos(evt) {
  const rect = inputCanvas.getBoundingClientRect();
  const clientX = evt.touches ? evt.touches[0].clientX : evt.clientX;
  const clientY = evt.touches ? evt.touches[0].clientY : evt.clientY;

  return {
    x: Math.max(0, Math.min(inputCanvas.width, (clientX - rect.left) * (inputCanvas.width / rect.width))),
    y: Math.max(0, Math.min(inputCanvas.height, (clientY - rect.top) * (inputCanvas.height / rect.height))),
  };
}

function findNearestCornerIndex(pos, hitRadius = 20) {
  let bestIdx = -1;
  let bestDist = hitRadius;
  for (let i = 0; i < 4; i++) {
    const cx = state.corners[i][0] / state.scaleX;
    const cy = state.corners[i][1] / state.scaleY;
    const dist = Math.hypot(pos.x - cx, pos.y - cy);
    if (dist <= bestDist) {
      bestDist = dist;
      bestIdx = i;
    }
  }
  return bestIdx;
}

function onPointerDown(evt) {
  if (!state.originalImageObj || !state.showCornerHandles) return;
  const pos = getCanvasPointerPos(evt);
  const idx = findNearestCornerIndex(pos, 22);
  if (idx !== -1) {
    evt.preventDefault();
    state.draggingIdx = idx;
    inputCanvas.style.cursor = "grabbing";
    renderCanvas();
  }
}

function onPointerMove(evt) {
  if (!state.originalImageObj || !state.showCornerHandles) return;
  const pos = getCanvasPointerPos(evt);

  if (state.draggingIdx !== -1) {
    evt.preventDefault();
    const origX = Math.max(0, Math.min(state.imageWidth - 1, pos.x * state.scaleX));
    const origY = Math.max(0, Math.min(state.imageHeight - 1, pos.y * state.scaleY));
    state.corners[state.draggingIdx] = [
      Math.round(origX * 10) / 10,
      Math.round(origY * 10) / 10,
    ];
    renderCanvas();
    return;
  }

  const hoverIdx = findNearestCornerIndex(pos, 18);
  if (hoverIdx !== state.hoverIdx) {
    state.hoverIdx = hoverIdx;
    inputCanvas.style.cursor = hoverIdx !== -1 ? "grab" : "crosshair";
    renderCanvas();
  }
}

function onPointerUp() {
  if (state.draggingIdx !== -1) {
    state.draggingIdx = -1;
    inputCanvas.style.cursor = state.hoverIdx !== -1 ? "grab" : "crosshair";
    renderCanvas();
  }
}

// ============================================================================
// Gắn kết sự kiện Kéo thả (Drag & Drop), Chọn file và Nút bấm
// ============================================================================

dropZone.addEventListener("click", (e) => {
  if (e.target === scanBtn) return;
  imageInput.click();
});

imageInput.addEventListener("change", () => {
  if (imageInput.files && imageInput.files[0]) {
    handleSelectedFile(imageInput.files[0]);
  }
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    handleSelectedFile(e.dataTransfer.files[0]);
  }
});

scanBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  runAutoScan();
});

toggleCornersBtn.addEventListener("click", () => {
  setCornerEditMode(!state.showCornerHandles);
});

rewarpBtn.addEventListener("click", runManualRewarp);
applyCornersBtn.addEventListener("click", runManualRewarp);

inputCanvas.addEventListener("mousedown", onPointerDown);
window.addEventListener("mousemove", onPointerMove);
window.addEventListener("mouseup", onPointerUp);

inputCanvas.addEventListener("touchstart", onPointerDown, { passive: false });
window.addEventListener("touchmove", onPointerMove, { passive: false });
window.addEventListener("touchend", onPointerUp);

window.addEventListener("resize", () => {
  if (state.originalImageObj && !workspace.hidden) {
    resizeAndRenderCanvas();
  }
});
