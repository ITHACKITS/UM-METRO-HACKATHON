import { useCallback, useEffect, useRef, useState } from "react";

import type { AnalysisMode, Language } from "./types";

const messages = {
	id: {
		title: "Ambil foto langsung",
		starting: "Menyiapkan kamera belakang…",
		capture: "Ambil foto",
		close: "Tutup kamera",
		upload: "Unggah foto",
		disease: "Gejala daun",
		pest: "Hama terlihat",
		diseaseTip:
			"Dekatkan satu daun sampai pola gejala terlihat jelas di dalam bingkai.",
		pestTip:
			"Pastikan serangga terlihat jelas di dalam sasaran kecil—bukan hanya bekas kerusakannya.",
		privacy: "Foto diproses untuk pemeriksaan ini dan tidak disimpan.",
		unavailable:
			"Kamera langsung tidak tersedia di peramban ini. Gunakan tombol kamera bawaan atau galeri.",
		insecure: "Kamera langsung memerlukan HTTPS atau localhost.",
		denied:
			"Izin kamera tidak diberikan. Izinkan kamera di pengaturan peramban atau gunakan galeri.",
		failed:
			"Kamera tidak dapat dibuka. Pastikan tidak sedang digunakan aplikasi lain.",
		noFrame: "Kamera belum siap. Tunggu sebentar lalu coba lagi.",
	},
	en: {
		title: "Take a photo now",
		starting: "Preparing the rear camera…",
		capture: "Take photo",
		close: "Close camera",
		upload: "Upload photo",
		disease: "Leaf symptoms",
		pest: "Visible pest",
		diseaseTip:
			"Move close until one leaf and its symptom pattern are clear inside the frame.",
		pestTip:
			"Keep the insect clearly visible inside the small target—not only the damage it caused.",
		privacy: "The photo is processed for this check and is not stored.",
		unavailable:
			"Direct camera access is unavailable in this browser. Use the native camera button or gallery.",
		insecure: "Direct camera access requires HTTPS or localhost.",
		denied:
			"Camera permission was not granted. Allow it in browser settings or use the gallery.",
		failed:
			"The camera could not be opened. Check whether another app is using it.",
		noFrame: "The camera is not ready yet. Wait a moment and try again.",
	},
} as const;

interface CameraCaptureProps {
	language: Language;
	mode: AnalysisMode;
	open: boolean;
	onCapture: (file: File) => void;
	onClose: () => void;
	onModeChange: (mode: AnalysisMode) => void;
	onUpload: () => void;
}

function cameraError(error: unknown, language: Language): string {
	const t = messages[language];
	if (!window.isSecureContext) return t.insecure;
	if (!navigator.mediaDevices?.getUserMedia) return t.unavailable;
	if (
		error instanceof DOMException &&
		["NotAllowedError", "SecurityError"].includes(error.name)
	) {
		return t.denied;
	}
	return t.failed;
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
	const [error, setError] = useState("");
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
			return;
		}

		let active = true;
		setStarting(true);
		setError("");

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
				if (videoRef.current) {
					videoRef.current.srcObject = stream;
					await videoRef.current.play();
				}
			} catch (caught) {
				if (active) setError(cameraError(caught, language));
			} finally {
				if (active) setStarting(false);
			}
		}

		void start();
		return () => {
			active = false;
			stop();
		};
	}, [language, open, stop]);

	function capture() {
		const video = videoRef.current;
		if (
			!video ||
			video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
			!video.videoWidth
		) {
			setError(t.noFrame);
			return;
		}

		const canvas = document.createElement("canvas");
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;
		const context = canvas.getContext("2d");
		if (!context) {
			setError(t.failed);
			return;
		}
		context.drawImage(video, 0, 0, canvas.width, canvas.height);
		canvas.toBlob(
			(blob) => {
				if (!blob) {
					setError(t.failed);
					return;
				}
				const stamp = new Date().toISOString().replace(/[:.]/g, "-");
				onCapture(
					new File([blob], `tuai-sigap-${stamp}.jpg`, { type: "image/jpeg" }),
				);
				stop();
				onClose();
			},
			"image/jpeg",
			0.92,
		);
	}

	if (!open) return null;

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
				<div
					className="camera-mode-tabs"
					role="radiogroup"
					aria-label={t.title}
				>
					<label className={mode === "disease" ? "camera-mode-active" : ""}>
						<input
							checked={mode === "disease"}
							name="camera-mode"
							onChange={() => onModeChange("disease")}
							type="radio"
							value="disease"
						/>
						<span>{t.disease}</span>
					</label>
					<label className={mode === "pest" ? "camera-mode-active" : ""}>
						<input
							checked={mode === "pest"}
							name="camera-mode"
							onChange={() => onModeChange("pest")}
							type="radio"
							value="pest"
						/>
						<span>{t.pest}</span>
					</label>
				</div>
				<div className="camera-viewport">
					<video ref={videoRef} muted playsInline aria-label={t.title} />
					<div
						className={`camera-guide camera-guide-${mode}`}
						aria-hidden="true"
					>
						<span>{mode === "disease" ? t.disease : t.pest}</span>
					</div>
					{starting && <p role="status">{t.starting}</p>}
					{error && (
						<p className="camera-error" role="alert">
							{error}
						</p>
					)}
				</div>
				<div className="camera-tip">
					<strong>{mode === "disease" ? t.disease : t.pest}</strong>
					<span>{mode === "disease" ? t.diseaseTip : t.pestTip}</span>
					<small>{t.privacy}</small>
				</div>
				<div className="camera-controls">
					<button type="button" className="cancel-button" onClick={onUpload}>
						{t.upload}
					</button>
					<button
						type="button"
						className="analyze-button"
						disabled={starting || Boolean(error)}
						onClick={capture}
					>
						{t.capture}
					</button>
				</div>
			</div>
		</div>
	);
}
