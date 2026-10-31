/* Public visual-observation contract used by the integrated page. */
export type Language = "id" | "en";
export type AnalysisMode = "disease" | "pest";
export type AnalysisStatus = "ok" | "abstain" | "retake";

export interface LocalizedText {
  id: string;
  en: string;
}

export interface ModelProvenance {
  id: string;
  revision: string;
  artifact_sha256: string | null;
  preprocessing_version: string;
}

export interface QualityWarning {
  code: string;
  message: LocalizedText;
}

export interface ImageQuality {
  width: number;
  height: number;
  format: string;
  file_size_bytes: number;
  blur_score: number | null;
  mean_luminance: number | null;
  warnings: QualityWarning[];
  rejection_reason?: LocalizedText | null;
}

interface AnalysisBase {
  status: AnalysisStatus;
  mode: AnalysisMode;
  score_kind: "model_score";
  processing: "local" | "roboflow_cloud";
  model: ModelProvenance;
  quality: ImageQuality;
  limitations: LocalizedText[];
  next_action: LocalizedText;
}

export interface DiseaseCandidate {
  class_id: string;
  label: LocalizedText;
  score: number;
}

export interface DiseaseAnalysisResponse extends AnalysisBase {
  mode: "disease";
  disease: {
    accepted: boolean;
    candidates: DiseaseCandidate[];
    top_score: number | null;
    score_margin: number | null;
    calibration_status: "unavailable" | "partial" | "frozen";
		consistency_status: "not_checked" | "stable" | "unstable";
		view_count: number;
		top_class_agreement: number | null;
		top_score_spread: number | null;
  };
}

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface PestDetection {
  class_id: number;
  class_key: string;
  label: LocalizedText;
  score: number;
  accepted: boolean;
  bbox: BoundingBox;
}

export interface PestAnalysisResponse extends AnalysisBase {
  mode: "pest";
  pest: {
    detections: PestDetection[];
    image_width: number;
    image_height: number;
    calibration_status: "unavailable" | "partial" | "frozen";
  };
}

export type AnalysisResponse = DiseaseAnalysisResponse | PestAnalysisResponse;
