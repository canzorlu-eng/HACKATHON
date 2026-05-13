import type {
  AnalysisDetailResponse,
  FitPreference,
  GarmentUploadResponse,
  HealthResponse,
  HistoryListResponse,
  ProfileResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`İstek başarısız oldu: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/health`, { signal, cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export async function createProfile(data: {
  height_cm: number;
  weight_kg: number;
  fit_preference: FitPreference;
  body_image?: File;
}): Promise<ProfileResponse> {
  const form = new FormData();
  form.append("height_cm", String(data.height_cm));
  form.append("weight_kg", String(data.weight_kg));
  form.append("fit_preference", data.fit_preference);
  if (data.body_image) {
    form.append("body_image", data.body_image);
  }

  const response = await fetch(`${BASE_URL}/api/v1/profile`, {
    method: "POST",
    body: form,
  });

  return handleResponse<ProfileResponse>(response);
}

export async function analyzeGarment(data: {
  user_id: string;
  garment_image: File;
}): Promise<GarmentUploadResponse> {
  const form = new FormData();
  form.append("user_id", data.user_id);
  form.append("garment_image", data.garment_image);

  const response = await fetch(`${BASE_URL}/api/v1/analyze`, {
    method: "POST",
    body: form,
  });

  return handleResponse<GarmentUploadResponse>(response);
}

export async function getHistory(user_id: string): Promise<HistoryListResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/history/${encodeURIComponent(user_id)}`, {
    cache: "no-store",
  });
  return handleResponse<HistoryListResponse>(response);
}

export async function getAnalysis(
  user_id: string,
  analysis_id: string
): Promise<AnalysisDetailResponse> {
  const response = await fetch(
    `${BASE_URL}/api/v1/history/${encodeURIComponent(user_id)}/${encodeURIComponent(analysis_id)}`,
    { cache: "no-store" }
  );
  return handleResponse<AnalysisDetailResponse>(response);
}
