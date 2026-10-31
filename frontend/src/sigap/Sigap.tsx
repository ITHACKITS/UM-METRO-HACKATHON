/* TUAI Sigap: choose a check, add a photo, read the result beside it. */
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { LangToggle, useLang } from "../lib/i18n";
import { ApiError, analyzePhoto } from "./api";
import { CameraCapture } from "./CameraCapture";
import { copy, modeTitle } from "./copy";
import {
	deleteObservation,
	loadHistory,
	type ObservationRecord,
	saveObservation,
} from "./history";
import { BugIcon, CameraIcon, LeafIcon, ShieldIcon, UploadIcon } from "./icons";
import { inspectPhoto, type PhotoPreflight, type PreflightStatus } from "./photoQuality";
import { PhotoOverlay } from "./PhotoOverlay";
import type {
	AnalysisMode,
	AnalysisResponse,
	Language,
	PestAnalysisResponse,
} from "./types";
import "./sigap.css";

const MAX_FILE_BYTES = 12 * 1024 * 1024;
const ALLOWED_MIME = new Set([
	"image/jpeg",
	"image/png",
	"image/webp",
	"image/heic",
	"image/heif",
]);
const ALLOWED_EXTENSIONS = /\.(jpe?g|png|webp|heic|heif)$/i;
const IMAGE_ACCEPT =
	"image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif";

function ModeIcon({ mode }: { mode: AnalysisMode }) {
	return mode === "disease" ? <LeafIcon /> : <BugIcon />;
}

function pestSummary(response: PestAnalysisResponse, language: Language) {
	const counts = new Map<string, number>();
	for (const detection of response.pest.detections) {
		if (!detection.accepted) continue;
		const label = detection.label[language];
		counts.set(label, (counts.get(label) ?? 0) + 1);
	}
	return [...counts.entries()];
}

function headline(response: AnalysisResponse, language: Language) {
	const t = copy[language];
	if (response.status === "retake") return t.retakeTitle;
	if (response.status === "abstain") return t.uncertainTitle;
	if (response.mode === "disease") {
		const top = response.disease.candidates[0];
		return top?.class_id === "healthy"
			? t.noSymptomTitle
			: `${t.likelyPrefix}: ${top?.label[language]}`;
	}
	return pestSummary(response, language).length ? t.pestFoundTitle : t.noPestTitle;
}

function closestMatch(response: AnalysisResponse, language: Language) {
	if (response.status !== "abstain") return null;
	if (response.mode === "disease") {
		return response.disease.closest_match?.[language] ?? null;
	}
	const top = response.pest.detections[0];
	return top ? top.label[language] : null;
}

function ResultPanel({
	response,
	language,
}: {
	response: AnalysisResponse;
	language: Language;
}) {
	const t = copy[language];
	const closest = closestMatch(response, language);
	const pests = response.mode === "pest" ? pestSummary(response, language) : [];
	const single = response.recommendations.length === 1;

	return (
		<section className={`result-card result-${response.status}`} aria-live="polite">
			<div className="result-heading">
				<h2>{headline(response, language)}</h2>
				{closest && (
					<p>
						{t.closestMatch}: {closest}
					</p>
				)}
				{response.status === "retake" && <p>{response.next_action[language]}</p>}
				{pests.length > 0 && (
					<ul className="pest-counts">
						{pests.map(([label, count]) => (
							<li key={label}>
								<strong>{label}</strong>
								<span>
									{count} {t.visibleCount}
								</span>
							</li>
						))}
					</ul>
				)}
			</div>

			{(response.recommendations.length > 0 || response.general_steps.length > 0) && (
				<div className="next-steps">
					<h3>{t.whatToDo}</h3>
					{response.recommendations.map((recommendation) => (
						<div key={recommendation.source_url}>
							{!single && <h4>{recommendation.label[language]}</h4>}
							<ol>
								{recommendation.steps.map((step) => (
									<li key={step.en}>{step[language]}</li>
								))}
							</ol>
							<p className="source-line">
								{t.source}:{" "}
								<a href={recommendation.source_url} rel="noreferrer" target="_blank">
									{recommendation.source_name}
								</a>
							</p>
						</div>
					))}
					{response.general_steps.length > 0 && (
						<ol>
							{response.general_steps.map((step) => (
								<li key={step.en}>{step[language]}</li>
							))}
						</ol>
					)}
				</div>
			)}

			{response.status !== "retake" && response.quality.warnings.length > 0 && (
				<p className="photo-note">
					{t.photoNote}: {response.quality.warnings[0].message[language]}
				</p>
			)}

			<details className="about-result">
				<summary>{t.aboutResult}</summary>
				{response.limitations.map((limitation) => (
					<p key={limitation.en}>{limitation[language]}</p>
				))}
				<p>{response.mode === "disease" ? t.aboutDisease : t.aboutPest}</p>
			</details>
		</section>
	);
}

function PreflightRow({
	label,
	status,
	warning,
	language,
}: {
	label: string;
	status: PreflightStatus;
	warning: string;
	language: Language;
}) {
	const t = copy[language];
	if (status === "unavailable") return null;
	return (
		<div className="quality-row quality-row-compact">
			<div>
				<strong>{label}</strong>
				{status === "warning" && <p>{warning}</p>}
			</div>
			<span className={`quality-state quality-${status}`}>
				{status === "good" ? t.checkGood : t.checkWarning}
			</span>
		</div>
	);
}

export default function Sigap() {
	const { lang: language } = useLang();
	const [mode, setMode] = useState<AnalysisMode>("disease");
	const [file, setFile] = useState<File | null>(null);
	const [preview, setPreview] = useState<{ file: File; url: string } | null>(null);
	const [response, setResponse] = useState<AnalysisResponse | null>(null);
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(false);
	const [cameraOpen, setCameraOpen] = useState(false);
	const [preflight, setPreflight] = useState<PhotoPreflight | null>(null);
	const [history, setHistory] = useState<ObservationRecord[]>(() => loadHistory());
	const [historyMode, setHistoryMode] = useState<AnalysisMode>("disease");
	const [saved, setSaved] = useState(false);
	const abortRef = useRef<AbortController | null>(null);
	const galleryRef = useRef<HTMLInputElement | null>(null);
	const nativeCameraRef = useRef<HTMLInputElement | null>(null);
	const t = copy[language];

	useEffect(() => {
		if (!file) {
			setPreview(null);
			return;
		}
		const url = URL.createObjectURL(file);
		setPreview({ file, url });
		return () => URL.revokeObjectURL(url);
	}, [file]);

	useEffect(() => () => abortRef.current?.abort(), []);

	useEffect(() => {
		if (!file) {
			setPreflight(null);
			return;
		}
		let active = true;
		void inspectPhoto(file, mode).then((result) => {
			if (active) setPreflight(result);
		});
		return () => {
			active = false;
		};
	}, [file, mode]);

	const visibleHistory = useMemo(
		() => history.filter((record) => record.mode === historyMode),
		[history, historyMode],
	);
	const historyCounts = useMemo(
		() => ({
			disease: history.filter((record) => record.mode === "disease").length,
			pest: history.filter((record) => record.mode === "pest").length,
		}),
		[history],
	);

	function resetAnalysis() {
		abortRef.current?.abort();
		abortRef.current = null;
		setLoading(false);
		setResponse(null);
		setError("");
		setSaved(false);
	}

	function selectMode(nextMode: AnalysisMode) {
		if (nextMode === mode) return;
		resetAnalysis();
		setMode(nextMode);
		// A photo framed for one check says little about the other, so start fresh.
		setFile(null);
	}

	async function analyze(photo: File, photoMode: AnalysisMode) {
		resetAnalysis();
		const controller = new AbortController();
		abortRef.current = controller;
		setLoading(true);
		try {
			setResponse(await analyzePhoto(photo, photoMode, controller.signal));
		} catch (caught) {
			if (caught instanceof DOMException && caught.name === "AbortError") {
				setError(t.cancelled);
			} else if (caught instanceof ApiError) {
				setError(
					caught.localized?.[language] ??
						(caught.status === null || caught.status >= 500
							? t.backendUnavailable
							: caught.message),
				);
			} else {
				setError(t.genericError);
			}
		} finally {
			if (abortRef.current === controller) {
				abortRef.current = null;
				setLoading(false);
			}
		}
	}

	function acceptFile(nextFile: File) {
		resetAnalysis();
		const mimeAllowed = ALLOWED_MIME.has(nextFile.type.toLowerCase());
		const problem =
			nextFile.size > MAX_FILE_BYTES
				? t.fileTooLarge
				: !mimeAllowed && !ALLOWED_EXTENSIONS.test(nextFile.name)
					? t.unsupportedFile
					: null;
		if (problem) {
			setFile(null);
			setError(problem);
			return;
		}
		setFile(nextFile);
		void analyze(nextFile, mode);
	}

	function chooseFile(event: ChangeEvent<HTMLInputElement>) {
		const nextFile = event.target.files?.[0] ?? null;
		if (nextFile) acceptFile(nextFile);
		event.target.value = "";
	}

	function openCamera() {
		// Plain-HTTP phone access cannot open the live view, but the phone's own camera works.
		if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
			nativeCameraRef.current?.click();
			return;
		}
		setCameraOpen(true);
	}

	function storeResult() {
		if (!response || saved) return;
		try {
			setHistory((existing) => saveObservation(response, language, existing));
			setHistoryMode(response.mode);
			setSaved(true);
		} catch {
			setError(t.storageBlocked);
		}
	}

	function removeRecord(id: string) {
		try {
			setHistory((existing) => deleteObservation(id, existing));
		} catch {
			setError(t.storageBlocked);
		}
	}

	const guides = mode === "disease" ? t.diseaseGuides : t.pestGuides;
	const lightingWarning =
		preflight?.lightingKind === "dark" ? t.lightingDark : t.lightingBright;

	return (
		<div className="sigap-shell">
			<div className="grain" aria-hidden="true" />
			<header className="site-header">
				<Link className="brand" to="/" aria-label="TUAI">
					<Logo size={42} />
					<small>{t.suite}</small>
				</Link>
				<LangToggle />
			</header>

			<CameraCapture
				language={language}
				mode={mode}
				open={cameraOpen}
				onCapture={acceptFile}
				onClose={() => setCameraOpen(false)}
				onModeChange={selectMode}
				onUpload={() => {
					setCameraOpen(false);
					galleryRef.current?.click();
				}}
			/>

			<main id="top">
				<div className="workspace">
					<header className="workbench-intro">
						<div>
							<h1>{t.title}</h1>
							<p>{t.intro}</p>
						</div>
						<p className="privacy-note">
							<ShieldIcon />
							<span>{t.estimateNote}</span>
						</p>
					</header>

					<section className="mode-selector">
						<div className="mode-tabs" role="radiogroup" aria-label={t.modeLabel}>
							{(["disease", "pest"] as const).map((option) => (
								<label
									className={`mode-tab ${option === mode ? "mode-active" : ""}`}
									key={option}
								>
									<input
										checked={option === mode}
										name="analysis-mode"
										onChange={() => selectMode(option)}
										type="radio"
										value={option}
									/>
									<span className="mode-icon">
										<ModeIcon mode={option} />
									</span>
									<span className="mode-copy">
										<strong>{modeTitle(option, language)}</strong>
									</span>
								</label>
							))}
						</div>
						<p className="mode-description">
							{mode === "disease" ? t.diseaseHint : t.pestHint}
						</p>
					</section>

					<input
						accept={IMAGE_ACCEPT}
						capture="environment"
						className="sr-only"
						onChange={chooseFile}
						ref={nativeCameraRef}
						tabIndex={-1}
						type="file"
					/>
					<input
						accept={IMAGE_ACCEPT}
						className="sr-only"
						id="photo-gallery-input"
						onChange={chooseFile}
						ref={galleryRef}
						type="file"
					/>

					<div className="capture-actions">
						<button
							className="capture-action capture-primary"
							type="button"
							onClick={openCamera}
						>
							<CameraIcon />
							<span>
								<strong>{t.cameraAction}</strong>
								<small>{t.cameraHelp}</small>
							</span>
						</button>
						<label className="capture-action" htmlFor="photo-gallery-input">
							<UploadIcon />
							<span>
								<strong>{t.galleryAction}</strong>
								<small>{t.galleryHelp}</small>
							</span>
						</label>
					</div>

					<section className="photo-workbench">
						<div className="photo-stage">
							{!file ? (
								<div className="photo-empty">
									<CameraIcon />
									<div>
										<strong>{t.choosePhoto}</strong>
										<p>{guides[0]}</p>
										<small>{t.acceptedFiles}</small>
									</div>
								</div>
							) : (
								<div className="preview-card">
									<div className="result-media">
										<div className="result-image-wrap">
											<img
												alt={t.previewAlt}
												className="result-image"
												src={preview?.file === file ? preview.url : undefined}
											/>
											{response && (
												<PhotoOverlay language={language} response={response} />
											)}
										</div>
									</div>
									<div className="file-row">
										<div>
											<strong title={file.name}>{file.name}</strong>
											<span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
										</div>
										<button type="button" onClick={() => galleryRef.current?.click()}>
											{t.replacePhoto}
										</button>
									</div>
								</div>
							)}
						</div>

						<div className={`quality-panel ${response ? "quality-panel-result" : ""}`}>
							{response ? (
								<>
									<ResultPanel language={language} response={response} />
									<div className="result-actions">
										<button
											className="analyze-button"
											disabled={saved}
											onClick={storeResult}
											type="button"
										>
											{saved ? t.resultSaved : t.saveResult}
										</button>
										<button
											className="cancel-button"
											onClick={() => {
												resetAnalysis();
												setFile(null);
												openCamera();
											}}
											type="button"
										>
											{t.retakePhoto}
										</button>
									</div>
								</>
							) : (
								<>
									<div className="quality-heading">
										<h2>{t.preflightTitle}</h2>
									</div>
									{!file || !preflight || preflight.status === "unavailable" ? (
										<p className="quality-empty">{t.preflightEmpty}</p>
									) : (
										<div className="quality-list">
											<PreflightRow
												label={t.resolutionCheck}
												language={language}
												status={preflight.resolution}
												warning={t.resolutionWarning}
											/>
											<PreflightRow
												label={t.lightingCheck}
												language={language}
												status={preflight.lighting}
												warning={lightingWarning}
											/>
											<PreflightRow
												label={t.detailCheck}
												language={language}
												status={preflight.detail}
												warning={t.detailWarning}
											/>
										</div>
									)}
									<details className="capture-guidance">
										<summary>{t.guideTitle}</summary>
										<ul>
											{guides.map((item) => (
												<li key={item}>{item}</li>
											))}
										</ul>
									</details>

									{error && (
										<div className="error-message" role="alert">
											<span aria-hidden="true">!</span>
											<p>{error}</p>
											{file && !loading && (
												<button type="button" onClick={() => void analyze(file, mode)}>
													{t.tryAgain}
												</button>
											)}
										</div>
									)}

									<div className="action-row">
										<button
											className={`analyze-button ${loading ? "analyze-loading" : ""}`}
											disabled={!file || loading}
											onClick={() => file && void analyze(file, mode)}
											type="button"
										>
											{loading ? (
												<span className="spinner" aria-hidden="true" />
											) : (
												<ModeIcon mode={mode} />
											)}
											<span role={loading ? "status" : undefined}>
												{loading ? t.analyzing : t.checkAction}
											</span>
										</button>
										{loading && (
											<button
												className="cancel-button"
												onClick={() => abortRef.current?.abort()}
												type="button"
											>
												{t.cancel}
											</button>
										)}
									</div>
								</>
							)}
						</div>
					</section>

					<section className="history-card" aria-labelledby="sigap-history-title">
						<div className="history-heading">
							<div>
								<h2 id="sigap-history-title">{t.historyTitle}</h2>
								<p>{t.historyIntro}</p>
							</div>
							<span>{history.length}/20</span>
						</div>
						<div className="history-tabs" role="tablist" aria-label={t.historyTitle}>
							{(["disease", "pest"] as const).map((option) => (
								<button
									aria-controls="history-panel"
									aria-selected={historyMode === option}
									className={historyMode === option ? "history-tab-active" : ""}
									id={`history-tab-${option}`}
									key={option}
									onClick={() => setHistoryMode(option)}
									role="tab"
									type="button"
								>
									<strong>{modeTitle(option, language)}</strong>
									<span>
										{historyCounts[option]} {t.historyItems}
									</span>
								</button>
							))}
						</div>
						<div
							aria-labelledby={`history-tab-${historyMode}`}
							id="history-panel"
							role="tabpanel"
						>
							{visibleHistory.length === 0 ? (
								<p className="history-empty">{t.historyEmpty}</p>
							) : (
								<ol className="history-list">
									{visibleHistory.map((record) => (
										<li key={record.id}>
											<div>
												<span>
													{new Intl.DateTimeFormat(
														language === "id" ? "id-ID" : "en-GB",
														{ dateStyle: "medium", timeStyle: "short" },
													).format(new Date(record.createdAt))}
												</span>
												<strong>{record.primaryLabel}</strong>
												<small>{record.nextAction}</small>
											</div>
											<button
												type="button"
												onClick={() => removeRecord(record.id)}
												aria-label={`${t.deleteRecord}: ${record.primaryLabel}`}
											>
												{t.deleteRecord}
											</button>
										</li>
									))}
								</ol>
							)}
						</div>
					</section>

					<aside className="disclaimer-card">
						<span>
							<ShieldIcon />
						</span>
						<div>
							<h2>{t.disclaimerTitle}</h2>
							<p>{t.disclaimer}</p>
						</div>
					</aside>
				</div>
			</main>

			<footer>
				<span>{t.footer}</span>
				<span>TUAI · 2026</span>
			</footer>
		</div>
	);
}
