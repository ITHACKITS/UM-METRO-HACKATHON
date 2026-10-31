/* Integrated TUAI Sigap visual-observation page. */
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { LangToggle, useLang } from "../lib/i18n";
import { ApiError, analyzePhoto } from "./api";
import { CameraCapture } from "./CameraCapture";
import { copy, modeTitle } from "./copy";
import { toPercentBox } from "./geometry";
import {
	deleteObservation,
	loadHistory,
	type ObservationRecord,
	saveObservation,
} from "./history";
import { BugIcon, CameraIcon, LeafIcon, ShieldIcon, UploadIcon } from "./icons";
import {
	inspectPhoto,
	type PhotoPreflight,
	type PreflightStatus,
} from "./photoQuality";
import type {
	AnalysisMode,
	AnalysisResponse,
	Language,
	LocalizedText,
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

function localized(value: LocalizedText, language: Language): string {
	return value[language];
}

function scorePercent(score: number): string {
	const safeScore = Math.min(1, Math.max(0, score));
	return `${(safeScore * 100).toFixed(1)}%`;
}

function shortHash(hash: string | null): string | null {
	if (!hash) return null;
	return hash.length > 18 ? `${hash.slice(0, 12)}…${hash.slice(-6)}` : hash;
}

function ModeIcon({ mode }: { mode: AnalysisMode }) {
	return mode === "disease" ? <LeafIcon /> : <BugIcon />;
}

function QualityState({
	status,
	language,
}: {
	status: PreflightStatus;
	language: Language;
}) {
	const t = copy[language];
	const label =
		status === "good"
			? t.checkGood
			: status === "warning"
				? t.checkWarning
				: t.checkUnavailable;
	return <span className={`quality-state quality-${status}`}>{label}</span>;
}

function PhotoQualityPanel({
	file,
	language,
	loading,
	preflight,
}: {
	file: File | null;
	language: Language;
	loading: boolean;
	preflight: PhotoPreflight | null;
}) {
	const t = copy[language];

	if (!file) return <p className="quality-empty">{t.preflightEmpty}</p>;
	if (loading)
		return (
			<p className="quality-empty" role="status">
				{t.preflightChecking}
			</p>
		);
	if (!preflight || preflight.status === "unavailable") {
		return <p className="quality-empty">{t.preflightUnavailable}</p>;
	}

	const lightingMessage =
		preflight.lightingKind === "dark"
			? t.lightingDark
			: preflight.lightingKind === "bright"
				? t.lightingBright
				: t.lightingBalanced;

	return (
		<>
			<div className="quality-list">
				<div className="quality-row">
					<div>
						<strong>{t.resolutionCheck}</strong>
						<p>
							{preflight.resolution === "good"
								? t.resolutionGood
								: t.resolutionWarning}
						</p>
					</div>
					<QualityState language={language} status={preflight.resolution} />
				</div>
				<div className="quality-row">
					<div>
						<strong>{t.lightingCheck}</strong>
						<p>{lightingMessage}</p>
					</div>
					<QualityState language={language} status={preflight.lighting} />
				</div>
				<div className="quality-row">
					<div>
						<strong>{t.detailCheck}</strong>
						<p>
							{preflight.detail === "good" ? t.detailGood : t.detailWarning}
						</p>
					</div>
					<QualityState language={language} status={preflight.detail} />
				</div>
			</div>
			<p className="quality-metrics">
				{preflight.metrics?.width} × {preflight.metrics?.height} px ·{" "}
				{t.preflightAdvisory}
			</p>
		</>
	);
}

function ResultImage({
	previewUrl,
	previewAvailable,
	response,
	language,
	alt,
}: {
	previewUrl: string;
	previewAvailable: boolean;
	response: AnalysisResponse | null;
	language: Language;
	alt: string;
}) {
	const isPest = response?.mode === "pest";

	if (!previewAvailable) return null;

	return (
		<div className="result-media">
			<div className="result-image-wrap">
				<img className="result-image" src={previewUrl} alt={alt} />
				{isPest &&
					response.pest.detections.map((detection) => {
						const box = toPercentBox(
							detection.bbox,
							response.pest.image_width,
							response.pest.image_height,
						);
						return (
							<div
								className={`detection-box ${detection.accepted ? "" : "detection-box-tentative"}`}
								key={`${detection.class_id}-${detection.bbox.x_min}-${detection.bbox.y_min}-${detection.bbox.x_max}-${detection.bbox.y_max}`}
								style={{
									left: `${box.left}%`,
									top: `${box.top}%`,
									width: `${box.width}%`,
									height: `${box.height}%`,
								}}
							>
								<span>{localized(detection.label, language)}</span>
							</div>
						);
					})}
			</div>
		</div>
	);
}

function ResultPanel({
	response,
	language,
}: {
	response: AnalysisResponse;
	language: Language;
}) {
	const t = copy[language];
	const statusTitle =
		response.status === "ok"
			? t.okTitle
			: response.status === "abstain"
				? t.abstainTitle
				: t.retakeTitle;

	return (
		<section
			className={`result-card result-${response.status}`}
			aria-live="polite"
		>
			<div className="result-heading">
				<h2>{statusTitle}</h2>
				<p>{t.resultTitle}</p>
			</div>

			{response.mode === "disease" ? (
				<div className="candidate-section">
					{response.status === "ok" && response.disease.candidates.length > 0 ? (
						<>
							<h3>{t.alternatives}</h3>
						<ol className="candidate-list">
							{response.disease.candidates.map((candidate, index) => (
								<li
									className={index === 0 ? "candidate-primary" : ""}
									key={candidate.class_id}
								>
									<div>
										<span className="candidate-rank">
											{String(index + 1).padStart(2, "0")}
										</span>
										<strong>{localized(candidate.label, language)}</strong>
									</div>
									<span className="score-pill">
										{t.modelScore} {scorePercent(candidate.score)}
									</span>
								</li>
							))}
						</ol>
							<p className="score-note">{t.scoreNote}</p>
						</>
					) : response.disease.candidates.length > 0 ? (
						<details className="raw-candidates">
							<summary>{t.rawCandidates}</summary>
							<p>{t.rawCandidatesHelp}</p>
							<ol>
								{response.disease.candidates.map((candidate, index) => (
									<li key={candidate.class_id}>
										<span>{String(index + 1).padStart(2, "0")}</span>
										<strong>{localized(candidate.label, language)}</strong>
										<code>
											{t.rawScore} {candidate.score.toFixed(4)}
										</code>
									</li>
								))}
							</ol>
							{response.disease.view_count > 0 && (
								<p>
									{t.viewConsistency}: {response.disease.view_count} ·{" "}
									{response.disease.consistency_status === "stable"
										? t.consistencyStable
										: t.consistencyUnstable}
								</p>
							)}
						</details>
					) : (
						<p className="muted">{t.retakeTitle}</p>
					)}
				</div>
			) : (
				<PestSummary response={response} language={language} />
			)}

			<div className="result-grid">
				<div className="result-detail">
					<h3>{t.quality}</h3>
					{response.quality.warnings.length === 0 ? (
						<p>{t.qualityOkay}</p>
					) : (
						<ul>
							{response.quality.warnings.map((warning) => (
								<li key={warning.code}>
									{localized(warning.message, language)}
								</li>
							))}
						</ul>
					)}
					<p className="image-meta">
						{response.quality.width} × {response.quality.height} ·{" "}
						{response.quality.format}
					</p>
				</div>

				<div className="result-detail">
					<h3>{t.nextAction}</h3>
					<p>{localized(response.next_action, language)}</p>
				</div>
			</div>

			<div className="result-detail limitations-panel">
				<h3>{t.limitations}</h3>
				<ul>
					{response.limitations.map((limitation) => (
						<li key={`${limitation.id}-${limitation.en}`}>
							{localized(limitation, language)}
						</li>
					))}
				</ul>
			</div>

			<details className="provenance">
				<summary>{t.provenance}</summary>
				<dl>
					<div>
						<dt>Model</dt>
						<dd>{response.model.id}</dd>
					</div>
					<div>
						<dt>{t.processing}</dt>
						<dd>
							{response.processing === "roboflow_cloud"
								? t.processingRoboflow
								: t.processingLocal}
						</dd>
					</div>
					<div>
						<dt>{t.revision}</dt>
						<dd title={response.model.revision}>{response.model.revision}</dd>
					</div>
					<div>
						<dt>{t.artifact}</dt>
						<dd title={response.model.artifact_sha256 ?? undefined}>
							{shortHash(response.model.artifact_sha256) ?? t.unavailableHash}
						</dd>
					</div>
					<div>
						<dt>{t.preprocessing}</dt>
						<dd>{response.model.preprocessing_version}</dd>
					</div>
				</dl>
			</details>
		</section>
	);
}

function PestSummary({
	response,
	language,
}: {
	response: PestAnalysisResponse;
	language: Language;
}) {
	const t = copy[language];
	if (response.pest.detections.length === 0) {
		return (
			<div className="no-detections">
				<strong>{t.pestNone}</strong>
				<p>{t.pestNoneWarning}</p>
			</div>
		);
	}

	return (
		<div className="candidate-section">
			<h3>
				{response.status === "ok" &&
				response.pest.detections.some((item) => item.accepted)
					? t.pestFound
					: t.pestCandidates}
			</h3>
			<ul className="detection-list">
				{response.pest.detections.map((detection) => (
					<li
						key={`${detection.class_id}-${detection.bbox.x_min}-${detection.bbox.y_min}-${detection.bbox.x_max}-${detection.bbox.y_max}`}
					>
						<span className="detection-dot" aria-hidden="true" />
						<strong>{localized(detection.label, language)}</strong>
						<span className="score-pill">
							{t.modelScore} {scorePercent(detection.score)}
						</span>
					</li>
				))}
			</ul>
			<p className="score-note">{t.scoreNote}</p>
		</div>
	);
}

export default function Sigap() {
	const { lang: language } = useLang();
	const [mode, setMode] = useState<AnalysisMode>("disease");
	const [file, setFile] = useState<File | null>(null);
	const [previewUrl, setPreviewUrl] = useState("");
	const [previewAvailable, setPreviewAvailable] = useState(true);
	const [response, setResponse] = useState<AnalysisResponse | null>(null);
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(false);
	const [cameraOpen, setCameraOpen] = useState(false);
	const [preflight, setPreflight] = useState<PhotoPreflight | null>(null);
	const [preflightLoading, setPreflightLoading] = useState(false);
	const [history, setHistory] = useState<ObservationRecord[]>(() =>
		loadHistory(),
	);
	const [historyMode, setHistoryMode] = useState<AnalysisMode>("disease");
	const [saved, setSaved] = useState(false);
	const [allowRemoteFallback, setAllowRemoteFallback] = useState(false);
	const [confirmLeafSubject, setConfirmLeafSubject] = useState(false);
	const abortRef = useRef<AbortController | null>(null);
	const fileInputRef = useRef<HTMLInputElement | null>(null);
	const resultRef = useRef<HTMLDivElement | null>(null);
	const t = copy[language];

	useEffect(() => {
		if (!file) {
			setPreviewUrl("");
			return;
		}
		const nextUrl = URL.createObjectURL(file);
		setPreviewUrl(nextUrl);
		setPreviewAvailable(true);
		return () => URL.revokeObjectURL(nextUrl);
	}, [file]);

	useEffect(() => () => abortRef.current?.abort(), []);

	useEffect(() => {
		if (!file) {
			setPreflight(null);
			setPreflightLoading(false);
			return;
		}
		let active = true;
		setPreflightLoading(true);
		void inspectPhoto(file, mode).then((result) => {
			if (!active) return;
			setPreflight(result);
			setPreflightLoading(false);
		});
		return () => {
			active = false;
		};
	}, [file, mode]);

	const guidance = useMemo(
		() =>
			mode === "disease"
				? { title: t.diseaseGuideTitle, items: t.diseaseGuides }
				: { title: t.pestGuideTitle, items: t.pestGuides },
		[mode, t],
	);
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
		setConfirmLeafSubject(false);
	}

	function validateFile(nextFile: File): string | null {
		if (nextFile.size > MAX_FILE_BYTES) return t.fileTooLarge;
		const mimeAllowed = nextFile.type
			? ALLOWED_MIME.has(nextFile.type.toLowerCase())
			: false;
		if (!mimeAllowed && !ALLOWED_EXTENSIONS.test(nextFile.name))
			return t.unsupportedFile;
		return null;
	}

	function chooseFile(event: ChangeEvent<HTMLInputElement>) {
		const nextFile = event.target.files?.[0] ?? null;
		if (nextFile) acceptFile(nextFile);
		event.target.value = "";
	}

	function acceptFile(nextFile: File) {
		resetAnalysis();
		setConfirmLeafSubject(false);
		const validationError = validateFile(nextFile);
		if (validationError) {
			setFile(null);
			setError(validationError);
			return;
		}
		setFile(nextFile);
	}

	function storeResult() {
		if (!response || saved) return;
		try {
			setHistory((existing) => saveObservation(response, language, existing));
			setHistoryMode(response.mode);
			setSaved(true);
		} catch {
			setError(
				language === "id"
					? "Peramban memblokir penyimpanan lokal."
					: "The browser blocked local storage.",
			);
		}
	}

	function removeRecord(id: string) {
		try {
			setHistory((existing) => deleteObservation(id, existing));
		} catch {
			setError(
				language === "id"
					? "Ringkasan belum dapat dihapus."
					: "The summary could not be deleted.",
			);
		}
	}

	async function submit() {
		if (!file || loading) return;
		resetAnalysis();
		const controller = new AbortController();
		abortRef.current = controller;
		setLoading(true);

		try {
			const result = await analyzePhoto(
				file,
				mode,
				controller.signal,
				mode === "pest" && allowRemoteFallback,
				mode === "disease" && confirmLeafSubject,
			);
			setResponse(result);
			window.setTimeout(
				() =>
					resultRef.current?.scrollIntoView?.({
						behavior: "smooth",
						block: "start",
					}),
				50,
			);
		} catch (caught) {
			if (caught instanceof DOMException && caught.name === "AbortError") {
				setError(t.cancelled);
			} else if (caught instanceof ApiError) {
				setError(
					caught.localized?.[language] ??
						(caught.status === null || caught.status === 503
							? t.backendUnavailable
							: caught.message),
				);
			} else {
				setError(t.genericError);
			}
		} finally {
			if (abortRef.current === controller) abortRef.current = null;
			setLoading(false);
		}
	}

	function cancel() {
		abortRef.current?.abort();
	}

	return (
		<div className="sigap-shell">
			<div className="grain" aria-hidden="true" />
			<header className="site-header">
				<Link className="brand" to="/" aria-label="TUAI">
					<Logo size={42} />
					<small>TUAI Sigap · Cek Daun &amp; Hama</small>
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
					fileInputRef.current?.click();
				}}
			/>

			<main id="top">
				<div className="workspace">
					<header className="workbench-intro">
						<div>
							<h1>{t.workTitle}</h1>
							<p>{t.workIntro}</p>
						</div>
						<p className="privacy-note">
							<ShieldIcon />
							<span>{t.privacy}</span>
						</p>
					</header>

					<section className="mode-selector" aria-labelledby="mode-heading">
						<h2 id="mode-heading" className="sr-only">
							{t.stepMode}
						</h2>
						<div
							className="mode-tabs"
							role="radiogroup"
							aria-label={t.stepMode}
						>
							{(["disease", "pest"] as const).map((option) => {
								const active = option === mode;
								return (
									<label
										className={`mode-tab ${active ? "mode-active" : ""}`}
										key={option}
									>
										<input
											checked={active}
											name="analysis-mode"
											onChange={() => selectMode(option)}
											type="radio"
											value={option}
										/>
										<span className="mode-icon">
											<ModeIcon mode={option} />
										</span>
										<span className="mode-copy">
											<strong>
												{option === "disease" ? t.diseaseTitle : t.pestTitle}
											</strong>
										</span>
									</label>
								);
							})}
						</div>
						<p className="mode-description">
							{mode === "disease" ? t.diseaseBlurb : t.pestBlurb}
						</p>
					</section>

					<input
						accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
						capture="environment"
						className="sr-only"
						id="photo-camera-input"
						onChange={chooseFile}
						type="file"
					/>
					<input
						accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
						className="sr-only"
						id="photo-gallery-input"
						onChange={chooseFile}
						ref={fileInputRef}
						type="file"
					/>

					<fieldset className="capture-actions">
						<legend className="sr-only">{t.stepPhoto}</legend>
						<button
							className="capture-action capture-primary"
							type="button"
							onClick={() => setCameraOpen(true)}
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
					</fieldset>

					<section className="photo-workbench" aria-labelledby="photo-heading">
						<div className="photo-stage">
							<h2 id="photo-heading" className="sr-only">
								{t.stepPhoto}
							</h2>
							{!file ? (
								<div className="photo-empty">
									<CameraIcon />
									<div>
										<strong>{t.choosePhoto}</strong>
										<p>{guidance.items[0]}</p>
										<small>{t.acceptedFiles}</small>
									</div>
								</div>
							) : (
								<div className="preview-card">
									<ResultImage
										alt={t.previewAlt}
										language={language}
										previewAvailable={previewAvailable}
										previewUrl={previewUrl}
										response={response}
									/>
									{!previewAvailable && (
										<p className="preview-fallback">{t.previewUnavailable}</p>
									)}
									<img
										alt=""
										aria-hidden="true"
										className="preview-probe"
										onError={() => setPreviewAvailable(false)}
										src={previewUrl}
									/>
									<div className="file-row">
										<div>
											<strong title={file.name}>{file.name}</strong>
											<span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
										</div>
										<button
											type="button"
											onClick={() => fileInputRef.current?.click()}
										>
											{t.replacePhoto}
										</button>
									</div>
								</div>
							)}
						</div>

						<div className="quality-panel">
							<div className="quality-heading">
								<h2>{t.preflightTitle}</h2>
								<p>{t.preflightIntro}</p>
							</div>
							<PhotoQualityPanel
								file={file}
								language={language}
								loading={preflightLoading}
								preflight={preflight}
							/>
							<details className="capture-guidance">
								<summary>{guidance.title}</summary>
								<ul>
									{guidance.items.map((item) => (
										<li key={item}>{item}</li>
									))}
								</ul>
							</details>

							{mode === "pest" && (
								<label className="cloud-fallback-consent">
									<input
										checked={allowRemoteFallback}
										onChange={(event) =>
											setAllowRemoteFallback(event.target.checked)
										}
										type="checkbox"
									/>
									<span>
										<strong>{t.cloudFallbackLabel}</strong>
										<small>{t.cloudFallbackHelp}</small>
									</span>
								</label>
							)}

							{mode === "disease" && file && (
								<label className="subject-confirmation">
									<input
										checked={confirmLeafSubject}
										onChange={(event) =>
											setConfirmLeafSubject(event.target.checked)
										}
										type="checkbox"
									/>
									<span>
										<strong>{t.leafConfirmationLabel}</strong>
										<small>{t.leafConfirmationHelp}</small>
									</span>
								</label>
							)}

							{error && (
								<div className="error-message" role="alert">
									<span aria-hidden="true">!</span>
									<p>{error}</p>
								</div>
							)}

							<div className="action-row">
								<button
									className="analyze-button"
									disabled={
										!file || loading || (mode === "disease" && !confirmLeafSubject)
									}
									onClick={submit}
									type="button"
								>
									{loading ? (
										<span className="spinner" aria-hidden="true" />
									) : (
										<ModeIcon mode={mode} />
									)}
									{loading ? t.analyzing : t.analyze}
								</button>
								{loading && (
									<button
										className="cancel-button"
										onClick={cancel}
										type="button"
									>
										{t.cancel}
									</button>
								)}
							</div>
							<label
								className="native-camera-fallback"
								htmlFor="photo-camera-input"
							>
								{t.nativeCameraAction}
							</label>
						</div>
					</section>

					{response && (
						<div className="result-anchor" ref={resultRef}>
							<div className="result-experience">
								<div className="result-visual">
									<ResultImage
										alt={t.previewAlt}
										language={language}
										previewAvailable={previewAvailable}
										previewUrl={previewUrl}
										response={response}
									/>
									{!previewAvailable && (
										<p className="preview-fallback">{t.previewUnavailable}</p>
									)}
								</div>
								<ResultPanel language={language} response={response} />
							</div>
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
									className="cancel-button result-link"
									onClick={() => {
										setResponse(null);
										setCameraOpen(true);
									}}
									type="button"
								>
									{t.retakePhoto}
								</button>
							</div>
						</div>
					)}

					<section
						className="history-card"
						aria-labelledby="sigap-history-title"
					>
						<div className="history-heading">
							<div>
								<h2 id="sigap-history-title">{t.historyTitle}</h2>
								<p>{t.historyIntro}</p>
							</div>
							<span>{history.length}/20</span>
						</div>
						<div
							className="history-tabs"
							role="tablist"
							aria-label={t.historyTitle}
						>
							{(["disease", "pest"] as const).map((historyOption) => (
								<button
									aria-controls="history-panel"
									aria-selected={historyMode === historyOption}
									className={
										historyMode === historyOption ? "history-tab-active" : ""
									}
									id={`history-tab-${historyOption}`}
									key={historyOption}
									onClick={() => setHistoryMode(historyOption)}
									role="tab"
									type="button"
								>
									<strong>{modeTitle(historyOption, language)}</strong>
									<span>
										{historyCounts[historyOption]} {t.historyItems}
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
											<em>{t.notReviewed}</em>
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
