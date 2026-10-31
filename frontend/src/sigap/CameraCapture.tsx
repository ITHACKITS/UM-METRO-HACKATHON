/* Rear-camera view that detects while the user frames the shot. */
import { useCallback, useEffect, useRef, useState } from "react";

import { analyzePhoto } from "./api";
import { PhotoOverlay } from "./PhotoOverlay";
import type { AnalysisMode, AnalysisResponse, Language } from "./types";

const messages = {
	id: {
		title: "Ambil foto",
		starting: "Menyiapkan kamera…",
		capture: "Ambil foto",
		close: "Tutup",
		upload: "Unggah foto",
		disease: "Gejala daun",
		pest: "Hama terlihat",
		scanningDisease: "Letakkan satu daun di dalam kotak",
		scanningPest: "Arahkan ke serangga",
		seen: "Terlihat",
		maybe: "Mungkin",
		confirm: "ambil foto untuk memastikan",
		unavailable: "Kamera tidak tersedia di peramban ini. Gunakan unggah foto.",
		insecure: "Kamera langsung memerlukan koneksi HTTPS. Gunakan unggah foto.",
		denied: "Izin kamera ditolak. Izinkan di pengaturan peramban atau unggah foto.",
		failed: "Kamera tidak dapat dibuka. Pastikan tidak dipakai aplikasi lain.",
		noFrame: "Kamera sedang disiapkan. Tunggu sebentar lalu coba lagi.",
	},
	en: {
		title: "Take a photo",
		starting: "Starting the camera…",
		capture: "Take photo",
		close: "Close",
		upload: "Upload photo",
		disease: "Leaf symptoms",
		pest: "Visible pest",
		scanningDisease: "Place one leaf inside the box",
		scanningPest: "Point at the insect",
		seen: "Visible",
		maybe: "Maybe",
		confirm: "take a photo to confirm",
		unavailable: "The camera is unavailable in this browser. Use upload instead.",
		insecure: "Direct camera access needs an HTTPS connection. Use upload instead.",
		denied: "Camera permission was denied. Allow it in browser settings or upload.",
		failed: "The camera could not be opened. Check that no other app is using it.",
		noFrame: "The camera is not ready yet. Wait a moment and try again.",
	},
} as const;

// Frames stay small because they only guide framing; the final photo is sent at full size.
const LIVE_FRAME_LONG_SIDE = 854;
const LIVE_PAUSE_MS = 350;

interface CameraCaptureProps {
	language: Language;
	mode: AnalysisMode;
	open: boolean;
	onCapture: (file: File) => void;
	onClose: () => void;
	onModeChange: (mode: AnalysisMode) => void;
	onUpload: () => void;
}

type CameraProblem = "insecure" | "unavailable" | "denied" | "failed" | "noFrame";

function cameraProblem(error: unknown): CameraProblem {
	if (!window.isSecureContext) return "insecure";
	if (!navigator.mediaDevices?.getUserMedia) return "unavailable";
	if (
		error instanceof DOMException &&
		["NotAllowedError", "SecurityError"].includes(error.name)
	) {
		return "denied";
	}
	return "failed";
}

function grabFrame(video: HTMLVideoElement, longSide?: number): Promise<Blob | null> {
	const scale = longSide
		? Math.min(1, longSide / Math.max(video.videoWidth, video.videoHeight))
		: 1;
	const canvas = document.createElement("canvas");
	canvas.width = Math.round(video.videoWidth * scale);
	canvas.height = Math.round(video.videoHeight * scale);
	const context = canvas.getContext("2d");
	if (!context) return Promise.resolve(null);
	context.drawImage(video, 0, 0, canvas.width, canvas.height);
	return new Promise((resolve) =>
		canvas.toBlob(resolve, "image/jpeg", longSide ? 0.75 : 0.92),
	);
}

function liveStatus(
	response: AnalysisResponse | null,
	mode: AnalysisMode,
	t: (typeof messages)[Language],
	language: Language,
): { text: string; found: boolean } {
	const scanning = mode === "disease" ? t.scanningDisease : t.scanningPest;
	if (!response || response.mode !== mode) return { text: scanning, found: false };
	if (response.mode === "pest") {
		const accepted = response.pest.detections.filter((item) => item.accepted);
		if (accepted.length) {
			const labels = [...new Set(accepted.map((item) => item.label[language]))];
			return { text: `${t.seen}: ${labels.join(", ")}`, found: true };
		}
		const first = response.pest.detections[0];
		return first
			? { text: `${t.maybe}: ${first.label[language]} (${t.confirm})`, found: false }
			: { text: scanning, found: false };
	}
	const top = response.disease.candidates[0];
	if (response.disease.accepted && top && top.class_id !== "healthy") {
		return { text: `${t.seen}: ${top.label[language]}`, found: true };
	}
	return { text: scanning, found: false };
}

export function CameraCapture({
	language,
	mode,
	open,
	onCapture,
	onClose,
	onModeChange,
	onUpload,
}: CameraCaptureProps) {
	const videoRef = useRef<HTMLVideoElement | null>(null);
	const streamRef = useRef<MediaStream | null>(null);
	const [starting, setStarting] = useState(false);
	const [ready, setReady] = useState(false);
	const [problem, setProblem] = useState<CameraProblem | null>(null);
	const [aspect, setAspect] = useState("16 / 9");
	const [live, setLive] = useState<AnalysisResponse | null>(null);
	const t = messages[language];

	const stop = useCallback(() => {
		streamRef.current?.getTracks().forEach((track) => {
			track.stop();
		});
		streamRef.current = null;
		if (videoRef.current) videoRef.current.srcObject = null;
	}, []);

	useEffect(() => {
		if (!open) {
			stop();
			setReady(false);
			setLive(null);
			return;
		}

		let active = true;
		setStarting(true);
		setProblem(null);

		async function start() {
			try {
				if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
					throw new DOMException("Camera unavailable", "NotSupportedError");
				}
				const stream = await navigator.mediaDevices.getUserMedia({
					audio: false,
					video: {
						facingMode: { ideal: "environment" },
						width: { ideal: 1920 },
						height: { ideal: 1080 },
					},
				});
				if (!active) {
					stream.getTracks().forEach((track) => {
						track.stop();
					});
					return;
				}
				streamRef.current = stream;
				const video = videoRef.current;
				if (video) {
					video.srcObject = stream;
					await video.play();
					setAspect(`${video.videoWidth} / ${video.videoHeight}`);
					setReady(true);
				}
			} catch (caught) {
				if (active) setProblem(cameraProblem(caught));
			} finally {
				if (active) setStarting(false);
			}
		}

		void start();
		return () => {
			active = false;
			stop();
		};
	}, [open, stop]);

	// Keeps checking frames while the camera is open, one request at a time.
	useEffect(() => {
		if (!open || !ready) return;
		let active = true;
		const controller = new AbortController();
		setLive(null);

		async function loop() {
			while (active) {
				const video = videoRef.current;
				if (video?.videoWidth) {
					try {
						const blob = await grabFrame(video, LIVE_FRAME_LONG_SIDE);
						if (blob && active) {
							const frame = new File([blob], "frame.jpg", { type: "image/jpeg" });
							const result = await analyzePhoto(frame, mode, controller.signal, true);
							if (active) setLive(result);
						}
					} catch {
						// A missed frame only delays the overlay; the shutter still works.
					}
				}
				await new Promise((resolve) => window.setTimeout(resolve, LIVE_PAUSE_MS));
			}
		}

		void loop();
		return () => {
			active = false;
			controller.abort();
		};
	}, [mode, open, ready]);

	async function capture() {
		const video = videoRef.current;
		if (
			!video ||
			video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
			!video.videoWidth
		) {
			setProblem("noFrame");
			return;
		}
		const blob = await grabFrame(video);
		if (!blob) {
			setProblem("failed");
			return;
		}
		const stamp = new Date().toISOString().replace(/[:.]/g, "-");
		onCapture(new File([blob], `tuai-sigap-${stamp}.jpg`, { type: "image/jpeg" }));
		stop();
		onClose();
	}

	if (!open) return null;

	const status = liveStatus(live, mode, t, language);

	return (
		<div
			className="camera-dialog"
			role="dialog"
			aria-modal="true"
			aria-labelledby="camera-title"
		>
			<div className="camera-panel">
				<div className="camera-heading">
					<h2 id="camera-title">{t.title}</h2>
					<button type="button" onClick={onClose}>
						{t.close}
					</button>
				</div>
				<div className="camera-mode-tabs" role="radiogroup" aria-label={t.title}>
					{(["disease", "pest"] as const).map((option) => (
						<label
							className={mode === option ? "camera-mode-active" : ""}
							key={option}
						>
							<input
								checked={mode === option}
								name="camera-mode"
								onChange={() => onModeChange(option)}
								type="radio"
								value={option}
							/>
							<span>{t[option]}</span>
						</label>
					))}
				</div>
				<div className="camera-viewport">
					<div className="camera-stage" style={{ aspectRatio: aspect }}>
						<video ref={videoRef} muted playsInline aria-label={t.title} />
						{live && live.mode === mode && (
							<PhotoOverlay language={language} response={live} />
						)}
						{mode === "disease" && (
							<div className="camera-guide camera-guide-disease" aria-hidden="true">
								<span>{t.disease}</span>
							</div>
						)}
					</div>
					{starting && <p role="status">{t.starting}</p>}
					{problem && (
						<p className="camera-error" role="alert">
							{t[problem]}
						</p>
					)}
				</div>
				<div className="camera-tip" aria-live="polite">
					<strong>{t[mode]}</strong>
					{!problem && (
						<span className={status.found ? "camera-live-found" : ""}>{status.text}</span>
					)}
				</div>
				<div className="camera-controls">
					<button type="button" className="cancel-button" onClick={onUpload}>
						{t.upload}
					</button>
					<button
						type="button"
						className="analyze-button"
						disabled={starting || (Boolean(problem) && problem !== "noFrame")}
						onClick={() => void capture()}
					>
						{t.capture}
					</button>
				</div>
			</div>
		</div>
	);
}
