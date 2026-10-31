import type { AnalysisMode } from "./types";

export type PreflightStatus = "good" | "warning" | "unavailable";

export interface PhotoMetrics {
	width: number;
	height: number;
	meanLuminance: number;
	detailScore: number;
}

export interface PhotoPreflight {
	status: "ready" | "unavailable";
	metrics: PhotoMetrics | null;
	resolution: PreflightStatus;
	lighting: PreflightStatus;
	detail: PreflightStatus;
	lightingKind: "balanced" | "dark" | "bright" | "unknown";
}

const LIGHT_MIN = 45;
const LIGHT_MAX = 215;
const DETAIL_MIN = 7;

export function assessPhotoMetrics(
	metrics: PhotoMetrics,
	mode: AnalysisMode,
): PhotoPreflight {
	const minimumSide = mode === "disease" ? 224 : 480;
	const shortestSide = Math.min(metrics.width, metrics.height);
	const lightingKind =
		metrics.meanLuminance < LIGHT_MIN
			? "dark"
			: metrics.meanLuminance > LIGHT_MAX
				? "bright"
				: "balanced";

	return {
		status: "ready",
		metrics,
		resolution: shortestSide >= minimumSide ? "good" : "warning",
		lighting: lightingKind === "balanced" ? "good" : "warning",
		detail: metrics.detailScore >= DETAIL_MIN ? "good" : "warning",
		lightingKind,
	};
}

function unavailable(): PhotoPreflight {
	return {
		status: "unavailable",
		metrics: null,
		resolution: "unavailable",
		lighting: "unavailable",
		detail: "unavailable",
		lightingKind: "unknown",
	};
}

async function decodeImage(file: File): Promise<{
	source: CanvasImageSource;
	width: number;
	height: number;
	release: () => void;
}> {
	if (typeof window.createImageBitmap === "function") {
		const bitmap = await window.createImageBitmap(file, {
			imageOrientation: "from-image",
		});
		return {
			source: bitmap,
			width: bitmap.width,
			height: bitmap.height,
			release: () => bitmap.close(),
		};
	}

	const url = URL.createObjectURL(file);
	const image = new Image();
	image.decoding = "async";
	image.src = url;
	await image.decode();
	return {
		source: image,
		width: image.naturalWidth,
		height: image.naturalHeight,
		release: () => URL.revokeObjectURL(url),
	};
}

export async function inspectPhoto(
	file: File,
	mode: AnalysisMode,
): Promise<PhotoPreflight> {
	let decoded: Awaited<ReturnType<typeof decodeImage>> | null = null;
	try {
		decoded = await decodeImage(file);
		const scale = Math.min(1, 256 / Math.max(decoded.width, decoded.height));
		const width = Math.max(1, Math.round(decoded.width * scale));
		const height = Math.max(1, Math.round(decoded.height * scale));
		const canvas = document.createElement("canvas");
		canvas.width = width;
		canvas.height = height;
		const context = canvas.getContext("2d", { willReadFrequently: true });
		if (!context) return unavailable();
		context.drawImage(decoded.source, 0, 0, width, height);
		const pixels = context.getImageData(0, 0, width, height).data;
		const luminance = new Float32Array(width * height);
		let luminanceSum = 0;

		for (
			let index = 0, pixel = 0;
			index < pixels.length;
			index += 4, pixel += 1
		) {
			const value =
				pixels[index] * 0.2126 +
				pixels[index + 1] * 0.7152 +
				pixels[index + 2] * 0.0722;
			luminance[pixel] = value;
			luminanceSum += value;
		}

		let edgeSum = 0;
		let edgeCount = 0;
		for (let y = 0; y < height - 1; y += 1) {
			for (let x = 0; x < width - 1; x += 1) {
				const index = y * width + x;
				edgeSum += Math.abs(luminance[index] - luminance[index + 1]);
				edgeSum += Math.abs(luminance[index] - luminance[index + width]);
				edgeCount += 2;
			}
		}

		return assessPhotoMetrics(
			{
				width: decoded.width,
				height: decoded.height,
				meanLuminance: luminanceSum / luminance.length,
				detailScore: edgeCount > 0 ? edgeSum / edgeCount : 0,
			},
			mode,
		);
	} catch {
		return unavailable();
	} finally {
		decoded?.release();
	}
}
