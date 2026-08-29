import { TextAnalysisResult, AudioAnalysisResult } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail || data.message || message;
    } catch {
      // ignore
    }
    throw new ApiError(message, res.status);
  }
  return res.json() as Promise<T>;
}

export async function analyzeText(text: string): Promise<TextAnalysisResult> {
  const res = await fetch(`${API_BASE_URL}/api/analyze-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return handleResponse<TextAnalysisResult>(res);
}

export async function analyzeAudio(audioFile: File): Promise<AudioAnalysisResult> {
  const formData = new FormData();
  formData.append("audio", audioFile);

  const res = await fetch(`${API_BASE_URL}/api/analyze-audio`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<AudioAnalysisResult>(res);
}

export async function checkHealth(): Promise<{
  status: string;
  model: string;
  threshold: number;
  stt: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/health`);
  return handleResponse(res);
}
