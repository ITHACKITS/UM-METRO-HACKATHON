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

afterEach(() => {
	vi.unstubAllGlobals();
	localStorage.clear();
});

describe("TUAI CV interface", () => {
	it("starts in Indonesian with separate disease and visible-pest modes", () => {
		renderSigap();
		expect(
			screen.getByRole("heading", { name: /periksa fotonya lebih dulu/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("radio", { name: /cek gejala daun/i }),
		).toBeChecked();
		expect(
			screen.getByRole("radio", { name: /cari hama yang terlihat/i }),
		).not.toBeChecked();
		expect(
			screen.getByText(/foto diproses saat ini saja/i),
		).toBeInTheDocument();
	});

	it("changes guidance when pest mode is selected", () => {
		renderSigap();
		fireEvent.click(
			screen.getByRole("radio", { name: /cari hama yang terlihat/i }),
		);
		expect(screen.getAllByText(/pastikan serangga terlihat/i)).not.toHaveLength(
			0,
		);
		expect(
			screen.getByRole("radio", { name: /cari hama yang terlihat/i }),
		).toBeChecked();
		expect(
			screen.getByRole("checkbox", { name: /izinkan fallback hama/i }),
		).not.toBeChecked();
		expect(
			screen.getByText(/foto dikirim ke layanan cloud eksternal roboflow/i),
		).toBeInTheDocument();
	});

	it("offers a complete English interface without changing the selected mode", () => {
		renderSigap();
		fireEvent.click(screen.getByRole("button", { name: /english/i }));
		expect(
			screen.getByRole("heading", { name: /check the photo first/i }),
		).toBeInTheDocument();
		expect(
			screen.getByText(/processes this photo for the current request/i),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /bahasa indonesia/i }),
		).toBeInTheDocument();
	});

	it("opens a task-specific camera with upload fallback", () => {
		renderSigap();
		fireEvent.click(screen.getByRole("button", { name: /buka kamera/i }));
		const dialog = screen.getByRole("dialog", { name: /ambil foto langsung/i });
		expect(
			within(dialog).getByRole("radio", { name: /gejala daun/i }),
		).toBeChecked();
		expect(
			within(dialog).getByRole("button", { name: /unggah foto/i }),
		).toBeInTheDocument();
	});

	it("keeps disease and pest history in separate local lanes", () => {
		renderSigap();
		const history = screen.getByRole("region", { name: /riwayat observasi/i });
		expect(
			within(history).getByRole("tab", { name: /cek gejala daun/i }),
		).toHaveAttribute("aria-selected", "true");
		fireEvent.click(
			within(history).getByRole("tab", { name: /cari hama yang terlihat/i }),
		);
		expect(
			within(history).getByRole("tab", { name: /cari hama yang terlihat/i }),
		).toHaveAttribute("aria-selected", "true");
	});

	it("requires a close-up leaf confirmation and hides abstained percentages", async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => ({
				status: "abstain",
				mode: "disease",
				processing: "local",
				score_kind: "model_score",
				model: {
					id: "prithivMLmods/Rice-Leaf-Disease",
					revision: "170d10e",
					artifact_sha256: null,
					preprocessing_version:
						"hf-auto-image-processor-slow@revision+exif-rgb+tta3-consistency-v2",
				},
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
				limitations: [
					{
						id: "Belum dikalibrasi dengan foto Lampung.",
						en: "Not calibrated with Lampung photos.",
					},
				],
				next_action: {
					id: "Minta PPL memeriksa daun.",
					en: "Ask an extension officer to inspect the leaf.",
				},
				disease: {
					accepted: false,
					candidates: [
						{
							class_id: "bacterial_leaf_blight",
							label: {
								id: "Hawar daun bakteri / kresek",
								en: "Bacterial leaf blight",
							},
							score: 0.61,
						},
					],
					top_score: 0.61,
					score_margin: 0.1,
					calibration_status: "unavailable",
					consistency_status: "stable",
					view_count: 3,
					top_class_agreement: 1,
					top_score_spread: 0.04,
				},
			}),
		});
		vi.stubGlobal("fetch", fetchMock);

		renderSigap();
		const file = new File(["leaf"], "leaf.jpg", { type: "image/jpeg" });
		fireEvent.change(screen.getByLabelText(/unggah foto/i), {
			target: { files: [file] },
		});
		const analyze = screen.getByRole("button", { name: /periksa foto/i });
		expect(analyze).toBeDisabled();
		fireEvent.click(
			screen.getByRole("checkbox", { name: /konfirmasi subjek foto daun/i }),
		);
		expect(analyze).toBeEnabled();
		fireEvent.click(analyze);

		expect(
			await screen.findByText(/model belum dapat memberi indikasi/i),
		).toBeInTheDocument();
		expect(screen.getByText(/hawar daun bakteri/i)).toBeInTheDocument();
		expect(screen.queryByText(/skor model 61.0%/i)).not.toBeInTheDocument();
		expect(
			screen.getByText(/peringkat mentah model untuk pemeriksaan teknis/i),
		).toBeInTheDocument();
		expect(screen.getByText(/nilai mentah 0.6100/i)).toBeInTheDocument();
		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/sigap/v1/analyze");
		const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
		expect(request.body).toBeInstanceOf(FormData);
		expect((request.body as FormData).get("allow_remote_fallback")).toBe(
			"false",
		);
		expect((request.body as FormData).get("confirm_leaf_subject")).toBe("true");
	});
});
