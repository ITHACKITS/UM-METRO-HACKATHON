/* Typed TUAI Sigap API client. */
import type { AnalysisMode, AnalysisResponse, LocalizedText } from "./types";

const configuredBase = (
	import.meta.env.VITE_API_BASE_URL as string | undefined
)?.trim();
const API_BASE = configuredBase?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
	readonly status: number | null;
	readonly code: string | null;
	readonly localized: LocalizedText | null;

	constructor(
		message: string,
		status: number | null = null,
		code: string | null = null,
		localized: LocalizedText | null = null,
	) {
		super(message);
		this.name = "ApiError";
		this.status = status;
		this.code = code;
		this.localized = localized;
	}
}

function extractErrorMessage(
	payload: unknown,
	fallback: string,
): { message: string; code: string | null; localized: LocalizedText | null } {
	if (!payload || typeof payload !== "object") {
		return { message: fallback, code: null, localized: null };
	}

	const detail = "detail" in payload ? payload.detail : payload;
	if (typeof detail === "string") {
		return { message: detail, code: null, localized: null };
	}

	if (detail && typeof detail === "object") {
		const rawMessage = "message" in detail ? detail.message : null;
		const localized =
			rawMessage &&
			typeof rawMessage === "object" &&
			"id" in rawMessage &&
			typeof rawMessage.id === "string" &&
			"en" in rawMessage &&
			typeof rawMessage.en === "string"
				? { id: rawMessage.id, en: rawMessage.en }
				: null;
		const message =
			typeof rawMessage === "string" ? rawMessage : (localized?.id ?? fallback);
		const code =
			"code" in detail && typeof detail.code === "string" ? detail.code : null;
		return { message, code, localized };
	}

	return { message: fallback, code: null, localized: null };
}

function hasAnalysisShape(value: unknown): value is AnalysisResponse {
	if (!value || typeof value !== "object") return false;
	if (
		!("status" in value) ||
		!("mode" in value) ||
		!("model" in value) ||
		!("quality" in value)
	) {
		return false;
	}
	return value.mode === "disease"
		? "disease" in value
		: value.mode === "pest" && "pest" in value;
}

export async function analyzePhoto(
	file: File,
	mode: AnalysisMode,
	signal?: AbortSignal,
	allowRemoteFallback = false,
	confirmLeafSubject = false,
): Promise<AnalysisResponse> {
	const body = new FormData();
	body.append("file", file, file.name);
	body.append("mode", mode);
	body.append("allow_remote_fallback", String(allowRemoteFallback));
	body.append("confirm_leaf_subject", String(confirmLeafSubject));

	let response: Response;
	try {
		response = await fetch(`${API_BASE}/api/sigap/v1/analyze`, {
			method: "POST",
			body,
			signal,
		});
	} catch (error) {
		if (error instanceof DOMException && error.name === "AbortError")
			throw error;
		throw new ApiError("Layanan analisis tidak dapat dihubungi.");
	}

	let payload: unknown = null;
	try {
		payload = await response.json();
	} catch {
		// A non-JSON error is still represented by the HTTP status below.
	}

	if (!response.ok) {
		const fallback = `Analisis gagal (HTTP ${response.status}).`;
		const parsed = extractErrorMessage(payload, fallback);
		throw new ApiError(
			parsed.message,
			response.status,
			parsed.code,
			parsed.localized,
		);
	}

	if (!hasAnalysisShape(payload)) {
		throw new ApiError(
			"Respons layanan tidak sesuai kontrak.",
			response.status,
			"invalid_response",
		);
	}

	return payload;
}
