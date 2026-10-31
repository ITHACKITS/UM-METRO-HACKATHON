/* Detection-overlay geometry. */
import type { BoundingBox } from "./types";

export interface PercentBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

const clamp = (value: number): number => Math.min(100, Math.max(0, value));

export function toPercentBox(box: BoundingBox, imageWidth: number, imageHeight: number): PercentBox {
  if (imageWidth <= 0 || imageHeight <= 0) {
    return { left: 0, top: 0, width: 0, height: 0 };
  }

  // Values slightly outside [0, 1] can occur before detector clipping, so retain
  // normalized interpretation while still clamping the rendered overlay.
  const normalized =
    imageWidth > 2 &&
    imageHeight > 2 &&
    Math.max(Math.abs(box.x_min), Math.abs(box.x_max), Math.abs(box.y_min), Math.abs(box.y_max)) <= 2;
  const scaleX = normalized ? 100 : 100 / imageWidth;
  const scaleY = normalized ? 100 : 100 / imageHeight;
  const left = clamp(box.x_min * scaleX);
  const top = clamp(box.y_min * scaleY);
  const right = clamp(box.x_max * scaleX);
  const bottom = clamp(box.y_max * scaleY);

  return {
    left,
    top,
    width: Math.max(0, right - left),
    height: Math.max(0, bottom - top),
  };
}
