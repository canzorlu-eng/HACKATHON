export interface HealthResponse {
  status: string;
  app_env: string;
  version: string;
}

export interface ProfileResponse {
  user_id: string;
  height_cm: number;
  weight_kg: number;
  fit_preference: "slim" | "regular" | "relaxed" | "oversize";
  has_body_image: boolean;
  created_at: string;
}

export interface GarmentUploadResponse {
  analysis_id: string;
  message: string;
  garment_image_ref: string;
  recommended_size: string | null;
  confidence_score: number | null;
  confidence_pct: string | null;
  explanation_tr: string | null;
  risk_level: "low" | "medium" | "high" | null;
  risk_level_tr: string | null;
  risk_factors_tr: string[] | null;
  uncertainty_tr: string | null;
  community_insights_tr: string[] | null;
}

export interface HistoryItem {
  analysis_id: string;
  created_at: string;
  garment_image_ref: string;
  recommended_size: string | null;
  risk_level: "low" | "medium" | "high" | null;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
}

export interface AnalysisDetailResponse {
  analysis_id: string;
  user_id: string;
  garment_image_ref: string;
  recommended_size: string | null;
  recommended_confidence: number | null;
  risk_level: "low" | "medium" | "high" | null;
  formatted_response: Record<string, unknown> | null;
  created_at: string;
}

export type FitPreference = "slim" | "regular" | "relaxed" | "oversize";
