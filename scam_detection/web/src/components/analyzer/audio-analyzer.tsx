"use client";

import { useState, useRef, useCallback } from "react";
import { analyzeAudio } from "@/lib/api";
import { AudioAnalysisResult } from "@/lib/types";
import { useShield } from "@/lib/shield-context";
import { AudioSegments } from "./audio-segments";
import { Upload, Mic, Square, Loader2, AlertTriangle, CheckCircle } from "lucide-react";

type AnalysisStage =
  | "idle"
  | "uploading"
  | "transcribing"
  | "analyzing"
  | "calculating"
  | "done"
  | "error";

const STAGE_MESSAGES: Record<Exclude<AnalysisStage, "idle" | "done" | "error">, string> = {
  uploading: "Uploading audio...",
  transcribing: "Transcribing speech (this takes about 20–30 seconds)...",
  analyzing: "Analyzing transcript segments...",
  calculating: "Calculating call risk...",
};

const MAX_DURATION_SECONDS = 300; // placeholder; updated after health check
const ALLOWED_TYPES = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp3", "audio/mp4", "audio/webm", "audio/aac", "audio/ogg", "audio/flac"];
const ALLOWED_EXTS = [".mp3", ".wav", ".m4a", ".webm", ".aac", ".ogg", ".flac"];

export function AudioAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AudioAnalysisResult | null>(null);
  const [stage, setStage] = useState<AnalysisStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordTime, setRecordTime] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recordIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { triggerPulse } = useShield();

  const validateFile = (selected: File): string | null => {
    const ext = selected.name.slice(selected.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_TYPES.includes(selected.type) && !ALLOWED_EXTS.includes(ext)) {
      return "Unsupported audio format. Please upload mp3, wav, m4a, webm, aac, ogg, or flac.";
    }
    return null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    const validationError = validateFile(selected);
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }
    setFile(selected);
    setResult(null);
    setError(null);
  };

  const advanceStage = useCallback((targetStage: Exclude<AnalysisStage, "idle" | "done" | "error">) => {
    setStage(targetStage);
    const stages = ["uploading", "transcribing", "analyzing", "calculating"];
    const idx = stages.indexOf(targetStage);
    setProgress(((idx + 1) / stages.length) * 100);
  }, []);

  const handleAnalyze = async () => {
    if (!file) {
      setError("Please upload or record an audio file first.");
      return;
    }
    setError(null);
    setResult(null);

    try {
      advanceStage("uploading");
      await new Promise((r) => setTimeout(r, 300));

      advanceStage("transcribing");
      const res = await analyzeAudio(file);

      advanceStage("analyzing");
      await new Promise((r) => setTimeout(r, 200));

      advanceStage("calculating");
      await new Promise((r) => setTimeout(r, 200));

      setResult(res);
      setStage("done");
      setProgress(100);
      triggerPulse(res.overallRisk === "High" ? "Scam" : "Safe");
    } catch (err) {
      setStage("error");
      setError(err instanceof Error ? err.message : "Audio analysis failed. Please try again.");
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const recordedFile = new File([blob], "recording.webm", { type: "audio/webm" });
        setFile(recordedFile);
        setResult(null);
        setError(null);
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordTime(0);
      recordIntervalRef.current = setInterval(() => {
        setRecordTime((t) => t + 1);
      }, 1000);
    } catch {
      setError("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    if (recordIntervalRef.current) clearInterval(recordIntervalRef.current);
  };

  const isLoading = stage !== "idle" && stage !== "done" && stage !== "error";
  const overallVerdict = result ? (result.overallRisk === "High" ? "Scam" : "Safe") : null;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-col gap-6 md:flex-row">
          <label className="flex flex-1 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-background px-6 py-10 transition-colors hover:border-accent">
            <Upload className="h-10 w-10 text-text-secondary" />
            <span className="mt-3 text-sm font-medium text-text-primary">
              {file ? file.name : "Drop an audio file or click to browse"}
            </span>
            <span className="mt-1 text-xs text-text-secondary">
              mp3, wav, m4a, webm, aac, ogg, flac
            </span>
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.webm,.aac,.ogg,.flac,audio/*"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>

          <div className="flex flex-col items-center justify-center gap-3">
            <span className="text-xs text-text-secondary">or</span>
            {!isRecording ? (
              <button
                onClick={startRecording}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:border-accent hover:text-accent"
              >
                <Mic className="h-4 w-4" />
                Record sample
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="inline-flex items-center gap-2 rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white"
              >
                <Square className="h-4 w-4" />
                Stop ({recordTime}s)
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
            {error}
          </div>
        )}

        {isLoading && (
          <div className="mt-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-secondary">{STAGE_MESSAGES[stage as keyof typeof STAGE_MESSAGES]}</span>
              <span className="text-text-secondary">{Math.round(progress)}%</span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-border/60">
              <div
                className="h-full rounded-full bg-accent transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        <div className="mt-6 flex items-center gap-3">
          <button
            onClick={handleAnalyze}
            disabled={isLoading || !file}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Analyze Audio
              </>
            )}
          </button>
          <span className="text-xs text-text-secondary">Takes ~20-30 seconds</span>
        </div>
      </div>

      {result && !isLoading && (
        <div className="rounded-2xl border border-border bg-surface p-6">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${
                overallVerdict === "Scam" ? "bg-danger/20 text-danger" : "bg-safe/20 text-safe"
              }`}
            >
              {overallVerdict === "Scam" ? (
                <AlertTriangle className="h-6 w-6" />
              ) : (
                <CheckCircle className="h-6 w-6" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="font-heading text-2xl font-bold">
                  {overallVerdict === "Scam" ? "High-Risk Call" : "Low-Risk Call"}
                </h3>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    result.overallRisk === "High"
                      ? "bg-danger/20 text-danger"
                      : result.overallRisk === "Medium"
                      ? "bg-warning/20 text-warning"
                      : "bg-safe/20 text-safe"
                  }`}
                >
                  {result.overallRisk} Risk
                </span>
              </div>
              <div className="mt-3 grid gap-2 text-sm text-text-secondary sm:grid-cols-3">
                <div>
                  Risk score: <span className="text-text-primary font-semibold">{result.riskScore.toFixed(1)}%</span>
                </div>
                <div>
                  Duration: <span className="text-text-primary font-semibold">{result.callDurationSeconds.toFixed(1)}s</span>
                </div>
                <div>
                  Segments: <span className="text-text-primary font-semibold">{result.totalSegments - result.skippedSegments}</span> analyzed ({result.skippedSegments} skipped)
                </div>
              </div>
              <p className="mt-2 text-xs text-text-secondary/70">
                Transcription: {result.transcriptionModel} · Detected language: {result.languageDetected}
              </p>
              <p className="mt-4 text-xs text-text-secondary/70">
                Muhafiz AI is a decision-support tool, not a guarantee. When in doubt, verify directly with the official organization.
              </p>
            </div>
          </div>

          <AudioSegments segments={result.segments} />
        </div>
      )}
    </div>
  );
}
