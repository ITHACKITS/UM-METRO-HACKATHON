import type { AnalysisMode, AnalysisResponse, Language } from "./types";

export const HISTORY_KEY = "tuai-sigap-observations-v1";
const MAX_RECORDS = 20;

export interface ObservationRecord {
	id: string;
	createdAt: string;
	mode: AnalysisMode;
	status: AnalysisResponse["status"];
	primaryLabel: string;
	modelScore: number | null;
	nextAction: string;
	reviewStatus: "not_reviewed";
}

function isRecord(value: unknown): value is ObservationRecord {
	if (!value || typeof value !== "object") return false;
	const item = value as Partial<ObservationRecord>;
	return Boolean(
		typeof item.id === "string" &&
			typeof item.createdAt === "string" &&
			(item.mode === "disease" || item.mode === "pest") &&
			["ok", "abstain", "retake"].includes(item.status ?? "") &&
			typeof item.primaryLabel === "string" &&
			(item.modelScore === null || typeof item.modelScore === "number") &&
			typeof item.nextAction === "string" &&
			item.reviewStatus === "not_reviewed",
	);
}

export function loadHistory(): ObservationRecord[] {
	try {
		const parsed: unknown = JSON.parse(
			localStorage.getItem(HISTORY_KEY) ?? "[]",
		);
		return Array.isArray(parsed)
			? parsed.filter(isRecord).slice(0, MAX_RECORDS)
			: [];
	} catch {
		return [];
	}
}

function persist(records: ObservationRecord[]): ObservationRecord[] {
	const limited = records.slice(0, MAX_RECORDS);
	localStorage.setItem(HISTORY_KEY, JSON.stringify(limited));
	return limited;
}

export function saveObservation(
	response: AnalysisResponse,
	language: Language,
	existing: ObservationRecord[],
): ObservationRecord[] {
	const top =
		response.mode === "disease"
			? response.disease.candidates[0]
			: response.pest.detections[0];
	const record: ObservationRecord = {
		id:
			globalThis.crypto?.randomUUID?.() ??
			`${Date.now()}-${Math.random().toString(16).slice(2)}`,
		createdAt: new Date().toISOString(),
		mode: response.mode,
		status: response.status,
		primaryLabel:
			top?.label[language] ??
			(language === "id" ? "Tidak ada kandidat" : "No candidate"),
		modelScore: top?.score ?? null,
		nextAction: response.next_action[language],
		reviewStatus: "not_reviewed",
	};
	return persist([record, ...existing]);
}

export function deleteObservation(
	id: string,
	existing: ObservationRecord[],
): ObservationRecord[] {
	return persist(existing.filter((record) => record.id !== id));
}
