import { useState, useRef, useCallback, useEffect } from "react";
import styles from "./CropModal.module.css";

/**
 * Image crop modal — lets users pan and zoom an image within a crop frame.
 *
 * Props:
 *   src        — object URL or data URL of the image to crop
 *   aspect     — aspect ratio of the crop area (width/height), e.g. 1 for circle/square, 3 for cover
 *   shape      — "circle" or "rect" (affects the mask overlay)
 *   onConfirm  — called with a Blob of the cropped image
 *   onCancel   — called when user dismisses
 */
export default function CropModal({ src, aspect = 1, shape = "rect", onConfirm, onCancel }) {
  const containerRef = useRef(null);
  const imgRef = useRef(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, posX: 0, posY: 0 });
  const [cropSize, setCropSize] = useState({ w: 0, h: 0 });
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });

  // Compute crop area size based on container and aspect ratio
  useEffect(() => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setContainerSize({ w: rect.width, h: rect.height });
    const maxW = rect.width - 48;
    const maxH = rect.height - 120;
    let w, h;
    if (maxW / maxH > aspect) {
      h = maxH;
      w = h * aspect;
    } else {
      w = maxW;
      h = w / aspect;
    }
    setCropSize({ w, h });
  }, [aspect]);

  const handleImgLoad = () => {
    const img = imgRef.current;
    setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });

    // Fit image to cover the crop area
    const scaleX = cropSize.w / img.naturalWidth;
    const scaleY = cropSize.h / img.naturalHeight;
    const fitScale = Math.max(scaleX, scaleY);
    setScale(fitScale);
    setPos({ x: 0, y: 0 });
    setImgLoaded(true);
  };

  // Re-fit when cropSize changes and image is already loaded
  useEffect(() => {
    if (!imgRef.current || !cropSize.w) return;
    const img = imgRef.current;
    if (img.naturalWidth === 0) return;
    const scaleX = cropSize.w / img.naturalWidth;
    const scaleY = cropSize.h / img.naturalHeight;
    const fitScale = Math.max(scaleX, scaleY);
    setScale(fitScale);
    setPos({ x: 0, y: 0 });
  }, [cropSize]);

  // Clamp position so image always covers the crop area
  const clampPos = useCallback((x, y, s) => {
    if (!naturalSize.w) return { x, y };
    const imgW = naturalSize.w * s;
    const imgH = naturalSize.h * s;
    const maxX = Math.max(0, (imgW - cropSize.w) / 2);
    const maxY = Math.max(0, (imgH - cropSize.h) / 2);
    return {
      x: Math.max(-maxX, Math.min(maxX, x)),
      y: Math.max(-maxY, Math.min(maxY, y)),
    };
  }, [naturalSize, cropSize]);

  // Mouse/touch drag handlers
  const onPointerDown = (e) => {
    e.preventDefault();
    setDragging(true);
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    dragStart.current = { x: clientX, y: clientY, posX: pos.x, posY: pos.y };
  };

  const onPointerMove = useCallback((e) => {
    if (!dragging) return;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const dx = clientX - dragStart.current.x;
    const dy = clientY - dragStart.current.y;
    const clamped = clampPos(dragStart.current.posX + dx, dragStart.current.posY + dy, scale);
    setPos(clamped);
  }, [dragging, scale, clampPos]);

  const onPointerUp = useCallback(() => {
    setDragging(false);
  }, []);

  useEffect(() => {
    if (!dragging) return;
    window.addEventListener("mousemove", onPointerMove);
    window.addEventListener("mouseup", onPointerUp);
    window.addEventListener("touchmove", onPointerMove, { passive: false });
    window.addEventListener("touchend", onPointerUp);
    return () => {
      window.removeEventListener("mousemove", onPointerMove);
      window.removeEventListener("mouseup", onPointerUp);
      window.removeEventListener("touchmove", onPointerMove);
      window.removeEventListener("touchend", onPointerUp);
    };
  }, [dragging, onPointerMove, onPointerUp]);

  // Scroll to zoom
  const onWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    setScale((prev) => {
      const minScale = Math.max(cropSize.w / naturalSize.w, cropSize.h / naturalSize.h) || 0.1;
      const next = Math.max(minScale, Math.min(prev + delta, 5));
      const clamped = clampPos(pos.x, pos.y, next);
      setPos(clamped);
      return next;
    });
  };

  // Confirm — draw cropped area to canvas and export as blob
  const handleConfirm = () => {
    const canvas = document.createElement("canvas");
    const outputSize = shape === "circle" ? 400 : Math.round(cropSize.w * 2);
    const outputH = shape === "circle" ? 400 : Math.round(cropSize.h * 2);
    canvas.width = outputSize;
    canvas.height = outputH;
    const ctx = canvas.getContext("2d");

    // Calculate which part of the original image is visible in the crop area
    const imgW = naturalSize.w * scale;
    const imgH = naturalSize.h * scale;
    // Image center is at (containerCenter + pos.x, containerCenter + pos.y)
    // Crop area is centered in the container
    // So the crop area's top-left in image-space is:
    const cropLeftInImg = (imgW / 2 - cropSize.w / 2 - pos.x) / scale;
    const cropTopInImg = (imgH / 2 - cropSize.h / 2 - pos.y) / scale;
    const cropWInImg = cropSize.w / scale;
    const cropHInImg = cropSize.h / scale;

    ctx.drawImage(
      imgRef.current,
      cropLeftInImg,
      cropTopInImg,
      cropWInImg,
      cropHInImg,
      0,
      0,
      outputSize,
      outputH,
    );

    canvas.toBlob(
      (blob) => { if (blob) onConfirm(blob); },
      "image/webp",
      0.9,
    );
  };

  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <span className={styles.title}>Adjust image</span>
        </div>

        <div
          ref={containerRef}
          className={styles.cropContainer}
          onMouseDown={onPointerDown}
          onTouchStart={onPointerDown}
          onWheel={onWheel}
        >
          {/* The full image, translated and scaled */}
          <img
            ref={imgRef}
            src={src}
            alt=""
            className={styles.cropImg}
            onLoad={handleImgLoad}
            draggable={false}
            style={{
              transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`,
              opacity: imgLoaded ? 1 : 0,
            }}
          />

          {/* Mask overlay with transparent hole */}
          {cropSize.w > 0 && (
            <div className={styles.maskWrap}>
              <svg width="100%" height="100%" className={styles.mask}>
                <defs>
                  <mask id="crop-mask">
                    <rect width="100%" height="100%" fill="white" />
                    {shape === "circle" ? (
                      <circle
                        cx="50%"
                        cy="50%"
                        r={cropSize.w / 2}
                        fill="black"
                      />
                    ) : (
                      <rect
                        x={(containerSize.w - cropSize.w) / 2}
                        y={(containerSize.h - cropSize.h) / 2}
                        width={cropSize.w}
                        height={cropSize.h}
                        rx="8"
                        fill="black"
                      />
                    )}
                  </mask>
                </defs>
                <rect
                  width="100%"
                  height="100%"
                  fill="rgba(0,0,0,0.6)"
                  mask="url(#crop-mask)"
                />
              </svg>
              {/* Crop border */}
              {shape === "circle" ? (
                <div
                  className={styles.cropBorderCircle}
                  style={{ width: cropSize.w, height: cropSize.w }}
                />
              ) : (
                <div
                  className={styles.cropBorderRect}
                  style={{ width: cropSize.w, height: cropSize.h }}
                />
              )}
            </div>
          )}
        </div>

        {/* Zoom slider */}
        <div className={styles.controls}>
          <span className={styles.zoomLabel}>-</span>
          <input
            type="range"
            min={Math.max(cropSize.w / (naturalSize.w || 1), cropSize.h / (naturalSize.h || 1), 0.1)}
            max={5}
            step={0.01}
            value={scale}
            onChange={(e) => {
              const next = parseFloat(e.target.value);
              setScale(next);
              setPos((prev) => clampPos(prev.x, prev.y, next));
            }}
            className={styles.slider}
          />
          <span className={styles.zoomLabel}>+</span>
        </div>

        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={onCancel}>Cancel</button>
          <button className={styles.confirmBtn} onClick={handleConfirm} disabled={!imgLoaded}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
