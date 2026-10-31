/* TUAI Sigap component tests. */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LangProvider } from "../lib/i18n";
import Sigap from "./Sigap";

function renderSigap() {
	return render(
		<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
			<LangProvider>
				<Sigap />
			</LangProvider>
		</MemoryRouter>,
	);
}

const base = {
	processing: "local",
	score_kind: "model_score",
	model: { id: "m", revision: "r", artifact_sha256: null, preprocessing_version: "p" },
	quality: {
		width: 640,
		height: 480,
		format: "JPEG",
		file_size_bytes: 4,
		blur_score: 120,
		mean_luminance: 128,
		warnings: [],
		rejection_reason: null,
	},
	limitations: [{ id: "Perkiraan dari satu foto.", en: "An estimate from one photo." }],
	next_action: { id: "Langkah", en: "Step" },
	recommendations: [],
	general_steps: [],
};

const blast = { id: "Blas", en: "Blast" };

function diseaseResponse(overrides: Record<string, unknown>) {
	return {
		...base,
		status: "abstain",
		mode: "disease",
		disease: {
			accepted: false,
			candidates: [{ class_id: "blast", label: blast, score: 0.6 }],
			top_score: 0.6,
			score_margin: 0.1,
			calibration_status: "operating",
			consistency_status: "stable",
			view_count: 2,
			top_class_agreement: 1,
			top_score_spread: 0.04,
			heatmap: null,
			closest_match: null,
		},
		...overrides,
	};
}

function mockAnalysis(body: unknown) {
	const fetchMock = vi.fn().mockResolvedValue({
		ok: true,
		status: 200,
		json: async () => body,
	});
	vi.stubGlobal("fetch", fetchMock);
	return fetchMock;
}

function upload() {
	fireEvent.change(screen.getByLabelText(/unggah foto/i), {
		target: { files: [new File(["leaf"], "leaf.jpg", { type: "image/jpeg" })] },
	});
}

afterEach(() => {
	vi.unstubAllGlobals();
	localStorage.clear();
});

describe("TUAI Sigap", () => {
	it("starts simply, in Indonesian, with the two checks", () => {
		renderSigap();
		expect(
			screen.getByRole("heading", { name: /cek daun dan hama padi/i }),
		).toBeInTheDocument();
		expect(screen.getByRole("radio", { name: /gejala daun/i })).toBeChecked();
		expect(screen.getByRole("radio", { name: /cari hama/i })).not.toBeChecked();
	});

	it("never mentions the cloud service, consent, or unfinished work", () => {
		renderSigap();
		fireEvent.click(screen.getByRole("radio", { name: /cari hama/i }));
		const page = document.body.textContent?.toLowerCase() ?? "";
		for (const word of ["roboflow", "cloud", "fallback", "prototipe", "belum", "eksperimen"]) {
			expect(page).not.toContain(word);
		}
		expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
	});

	it("switches the whole interface to English", () => {
		renderSigap();
		fireEvent.click(screen.getByRole("button", { name: /english|^en$/i }));
		expect(
			screen.getByRole("heading", { name: /check rice leaves and pests/i }),
		).toBeInTheDocument();
	});

	it("analyzes as soon as a photo is chosen and shows sourced steps", async () => {
		const fetchMock = mockAnalysis(
			diseaseResponse({
				status: "ok",
				disease: {
					...diseaseResponse({}).disease,
					accepted: true,
					candidates: [{ class_id: "blast", label: blast, score: 0.9 }],
				},
				recommendations: [
					{
						label: blast,
						steps: [{ id: "Genangi sawah.", en: "Flood the field." }],
						source_name: "IRRI Rice Knowledge Bank",
						source_url: "https://www.knowledgebank.irri.org/x",
					},
				],
			}),
		);
		renderSigap();
		upload();

		expect(
			await screen.findByRole("heading", { name: /kemungkinan: blas/i }),
		).toBeInTheDocument();
		expect(screen.getByText("Genangi sawah.")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: /irri/i })).toHaveAttribute(
			"href",
			"https://www.knowledgebank.irri.org/x",
		);
		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/sigap/v1/analyze");
		const body = (fetchMock.mock.calls[0]?.[1] as RequestInit).body as FormData;
		expect(body.get("mode")).toBe("disease");
		expect(body.get("live")).toBeNull();
	});

	it("says uncertain, with the closest match and no percentages", async () => {
		mockAnalysis(
			diseaseResponse({
				disease: { ...diseaseResponse({}).disease, closest_match: blast },
				general_steps: [{ id: "Foto ulang.", en: "Retake." }],
			}),
		);
		renderSigap();
		upload();

		expect(
			await screen.findByRole("heading", { name: /tidak pasti/i }),
		).toBeInTheDocument();
		expect(screen.getByText(/paling mirip: blas/i)).toBeInTheDocument();
		expect(screen.getByText("Foto ulang.")).toBeInTheDocument();
		expect(document.body.textContent).not.toMatch(/\d%/);
	});

	it("does not call an empty pest photo safe", async () => {
		mockAnalysis({
			...base,
			status: "ok",
			mode: "pest",
			general_steps: [{ id: "Periksa pangkal rumpun.", en: "Check the base." }],
			pest: {
				detections: [],
				image_width: 640,
				image_height: 480,
				calibration_status: "operating",
			},
		});
		renderSigap();
		fireEvent.click(screen.getByRole("radio", { name: /cari hama/i }));
		upload();

		expect(
			await screen.findByRole("heading", { name: /tidak ada hama yang terlihat di foto/i }),
		).toBeInTheDocument();
		expect(screen.getByText("Periksa pangkal rumpun.")).toBeInTheDocument();
	});

	it("brings back the workbench, history lanes, and note", () => {
		renderSigap();
		expect(screen.getByText(/tidak ada foto dipilih/i)).toBeInTheDocument();
		expect(screen.getByRole("heading", { name: /pemeriksaan foto/i })).toBeInTheDocument();
		expect(screen.getByRole("tab", { name: /cek gejala daun/i })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByRole("heading", { name: /pemeriksaan awal/i })).toBeInTheDocument();
	});

	it("draws one box per detection and names each pest once", async () => {
		const label = { id: "Wereng batang cokelat", en: "Brown planthopper" };
		const detection = {
			class_id: 7,
			class_key: "brown_plant_hopper",
			label,
			score: 0.9,
			accepted: true,
			bbox: { x_min: 100, y_min: 100, x_max: 200, y_max: 200 },
		};
		mockAnalysis({
			...base,
			status: "ok",
			mode: "pest",
			pest: {
				detections: [
					detection,
					{ ...detection, bbox: { x_min: 300, y_min: 100, x_max: 400, y_max: 200 } },
				],
				image_width: 640,
				image_height: 480,
				calibration_status: "operating",
			},
		});
		renderSigap();
		fireEvent.click(screen.getByRole("radio", { name: /cari hama/i }));
		upload();

		expect(await screen.findByText(/2 terlihat/i)).toBeInTheDocument();
		expect(document.querySelectorAll(".detection-box")).toHaveLength(2);
		expect(document.querySelectorAll(".detection-box span")).toHaveLength(1);
	});

	it("shows a clear error when the service is down", async () => {
		vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
		renderSigap();
		upload();
		expect(await screen.findByRole("alert")).toHaveTextContent(
			/tidak tersedia saat ini/i,
		);
		expect(screen.getByRole("button", { name: /coba lagi/i })).toBeInTheDocument();
	});

	it("opens the camera dialog with both checks and an upload option", () => {
		const getUserMedia = vi.fn().mockRejectedValue(new DOMException("no", "NotAllowedError"));
		vi.stubGlobal("isSecureContext", true);
		Object.defineProperty(navigator, "mediaDevices", {
			configurable: true,
			value: { getUserMedia },
		});
		renderSigap();
		fireEvent.click(screen.getByRole("button", { name: /buka kamera/i }));
		const dialog = screen.getByRole("dialog", { name: /ambil foto/i });
		expect(within(dialog).getByRole("radio", { name: /gejala daun/i })).toBeChecked();
		expect(within(dialog).getByRole("button", { name: /unggah foto/i })).toBeInTheDocument();
		expect(getUserMedia).toHaveBeenCalledTimes(1);
	});
});
