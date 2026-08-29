"use client";

import { useState } from "react";
import { analyzeText } from "@/lib/api";
import { TextAnalysisResult } from "@/lib/types";
import { useShield } from "@/lib/shield-context";
import { ResultCard } from "./result-card";
import { SignalsList } from "./signals-list";
import { Send, Loader2 } from "lucide-react";

const exampleMessages = [
  {
    label: "Prize scam (Roman Urdu)",
    text: "Bhai aap ko Rs. 50,000 ka inaam mila hai. Fee Rs. 3,000 bhej kar claim karen.",
  },
  {
    label: "Bank phishing (English)",
    text: "Dear customer, your HBL card has been blocked. Click here to verify immediately: http://hbl-verify.com",
  },
  {
    label: "Job scam (Mixed)",
    text: "Great news! Your CV is selected for Dubai job. Send processing fee Rs. 5,000 on EasyPaisa number 03451234567.",
  },
  {
    label: "Legitimate bank alert",
    text: "Your HBL account has been credited with Rs. 25,000. Current balance: Rs. 150,000.",
  },
  {
    label: "Ordinary personal message",
    text: "Aoa, meeting at 3pm tomorrow at the office. Please bring the report.",
  },
];

export function TextAnalyzer() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<TextAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { triggerPulse } = useShield();

  const handleAnalyze = async () => {
    const trimmed = text.trim();
    if (!trimmed) {
      setError("Please enter a message to analyze.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await analyzeText(trimmed);
      setResult(res);
      triggerPulse(res.verdict);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExample = (exampleText: string) => {
    setText(exampleText);
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-surface p-6">
        <label htmlFor="message" className="block text-sm font-medium text-text-primary">
          Paste a message
        </label>
        <p className="text-xs text-text-secondary">
          Supports English, Urdu, Roman Urdu, and Mixed languages.
        </p>
        <textarea
          id="message"
          rows={5}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste the suspicious SMS, WhatsApp, or call transcript here..."
          className="mt-3 w-full rounded-xl border border-border bg-background px-4 py-3 text-text-primary placeholder:text-text-secondary/50 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />

        {error && (
          <div className="mt-3 rounded-lg border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
            {error}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Analyze Message
              </>
            )}
          </button>
          <span className="text-xs text-text-secondary">Under 10ms response time</span>
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium text-text-secondary">Or try an example:</p>
        <div className="flex flex-wrap gap-2">
          {exampleMessages.map((ex) => (
            <button
              key={ex.label}
              onClick={() => handleExample(ex.text)}
              className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      <ResultCard result={result} isLoading={loading && !result} />
      {result && !loading && <SignalsList signals={result.signals} />}
    </div>
  );
}
