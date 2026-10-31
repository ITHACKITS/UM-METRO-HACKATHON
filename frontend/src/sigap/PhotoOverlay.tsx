/* Draws what the model found over a photo: pest boxes or the disease highlight. */
import { useEffect, useRef } from "react";

import { toPercentBox } from "./geometry";
import type {
	AnalysisResponse,
	BoundingBox,
	DiseaseHeatmap,
	Language,
} from "./types";

function percentStyle(box: BoundingBox, width: number, height: number) {
	const percent = toPercentBox(box, width, height);
	return {
		left: `${percent.left}%`,
		top: `${percent.top}%`,
		width: `${percent.width}%`,
		height: `${percent.height}%`,
	};
}

function Heatmap({
	heatmap,
	width,
	height,
}: {
	heatmap: DiseaseHeatmap;
	width: number;
	height: number;
}) {
	const canvasRef = useRef<HTMLCanvasElement | null>(null);

	useEffect(() => {
		const canvas = canvasRef.current;
		const rows = heatmap.grid.length;
		const columns = heatmap.grid[0]?.length ?? 0;
		if (!canvas || !rows || !columns) return;
		canvas.width = columns;
		canvas.height = rows;
		const context = canvas.getContext("2d");
		if (!context) return;
		const pixels = context.createImageData(columns, rows);
		heatmap.grid.forEach((row, y) => {
			row.forEach((value, x) => {
				const index = (y * columns + x) * 4;
				pixels.data[index] = 255;
				pixels.data[index + 1] = 70;
				pixels.data[index + 2] = 0;
				// Only the strongest cells show, so the highlight stays on the symptom.
				const strength = Math.max(0, (value - 0.45) / 0.55);
				pixels.data[index + 3] = Math.round(strength ** 1.4 * 190);
			});
		});
		context.putImageData(pixels, 0, 0);
	}, [heatmap]);

	return (
		<canvas
			aria-hidden="true"
			className="disease-heatmap"
			ref={canvasRef}
			style={percentStyle(heatmap.region, width, height)}
		/>
	);
}

export function PhotoOverlay({
	response,
	language,
}: {
	response: AnalysisResponse;
	language: Language;
}) {
	if (response.mode === "disease") {
		const heatmap = response.disease.heatmap;
		return heatmap ? (
			<Heatmap
				heatmap={heatmap}
				width={response.quality.width}
				height={response.quality.height}
			/>
		) : null;
	}
	const { detections, image_width: width, image_height: height } = response.pest;
	// Name each pest once: the same label on every box hides the insects themselves.
	const named = new Set<string>();
	return (
		<>
			{detections.map((detection) => {
				const nearTop = detection.bbox.y_min / height < 0.08;
				const showLabel = !named.has(detection.class_key);
				named.add(detection.class_key);
				return (
					<div
						className={`detection-box ${detection.accepted ? "" : "detection-box-tentative"} ${nearTop ? "detection-box-inside" : ""}`}
						key={`${detection.class_id}-${detection.bbox.x_min}-${detection.bbox.y_min}-${detection.bbox.x_max}`}
						style={percentStyle(detection.bbox, width, height)}
					>
						{showLabel && <span>{detection.label[language]}</span>}
					</div>
				);
			})}
		</>
	);
}
