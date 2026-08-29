export interface Signal {
  category: string;
  matchedTerms: string[];
}

export interface TextAnalysisResult {
  verdict: "Scam" | "Safe";
  riskScore: number;
  riskLabel: "Low" | "Medium" | "High";
  detectedLanguage: "English" | "Urdu" | "Roman Urdu" | "Mixed";
  signals: Signal[];
  recommendedAction: string;
  modelName: string;
  thresholdUsed: number;
}

export interface AudioSegment {
  text: string;
  startTime: number;
  endTime: number;
  label: "Scam" | "Safe" | "Skipped";
  scamProbability: number;
}

export interface AudioAnalysisResult {
  overallRisk: "High" | "Medium" | "Low";
  riskScore: number;
  callDurationSeconds: number;
  totalSegments: number;
  skippedSegments: number;
  transcriptionModel: string;
  languageDetected: string;
  segments: AudioSegment[];
}

export type AnalysisVerdict = "Scam" | "Safe" | null;

export interface ShieldPulseEvent {
  verdict: AnalysisVerdict;
  timestamp: number;
}
