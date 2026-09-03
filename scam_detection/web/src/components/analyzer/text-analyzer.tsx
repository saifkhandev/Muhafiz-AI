"use client";

import { useState } from "react";
import { analyzeText } from "@/lib/api";
import { TextAnalysisResult } from "@/lib/types";
import { useShield } from "@/lib/shield-context";
import { useLanguage } from "@/lib/i18n/context";
import { ResultCard } from "./result-card";
import { SignalsList } from "./signals-list";
import { Send, Loader2 } from "lucide-react";

export function TextAnalyzer() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<TextAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const { triggerPulse } = useShield();
  const { t } = useLanguage();

  const examples = [
    {
      label: t("analyzer.textAnalyzer.exampleLabels.prize"),
      text: "Bhai aap ko Rs. 50,000 ka inaam mila hai. Fee Rs. 3,000 bhej kar claim karen.",
    },
    {
      label: t("analyzer.textAnalyzer.exampleLabels.bank"),
      text: "Dear customer, your HBL card has been blocked. Click here to verify immediately: http://hbl-verify.com",
    },
    {
      label: t("analyzer.textAnalyzer.exampleLabels.job"),
      text: "Great news! Your CV is selected for Dubai job. Send processing fee Rs. 5,000 on EasyPaisa number 03451234567.",
    },
    {
      label: t("analyzer.textAnalyzer.exampleLabels.legitimate"),
      text: "Your HBL account has been credited with Rs. 25,000. Current balance: Rs. 150,000.",
    },
  ];

  const handleAnalyze = async (messageText?: string) => {
    const textToAnalyze = messageText || text;
    if (!textToAnalyze.trim()) return;
    
    setLoading(true);
    setResult(null);
    try {
      const res = await analyzeText(textToAnalyze);
      setResult(res);
      triggerPulse(res.verdict);
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (exampleText: string) => {
    setText(exampleText);
    handleAnalyze(exampleText);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("analyzer.textAnalyzer.placeholder")}
          rows={4}
          className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary placeholder-text-secondary/50 focus:border-[#818CF8] focus:outline-none focus:ring-2 focus:ring-[#818CF8]/20"
        />
        <button
          onClick={() => handleAnalyze()}
          disabled={loading || !text.trim()}
          className="w-full rounded-xl px-6 py-3 font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ background: 'linear-gradient(90deg, #6366F1 0%, #22D3EE 100%)', color: '#05070A' }}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Analyzing...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <Send className="h-5 w-5" />
              {t("analyzer.textAnalyzer.analyzeButton")}
            </span>
          )}
        </button>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium text-text-secondary">{t("analyzer.textAnalyzer.examples")}</p>
        <div className="flex flex-wrap gap-2">
          {examples.map((ex, i) => (
            <button
              key={i}
              onClick={() => handleExampleClick(ex.text)}
              className="rounded-lg border border-[#818CF8] bg-surface px-3 py-1.5 text-xs font-medium text-[#818CF8] transition-all hover:border-border hover:text-text-primary hover:shadow-[0_0_12px_rgba(129,140,248,0.2)]"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          <ResultCard result={result} />
          <SignalsList signals={result.signals} />
        </div>
      )}
    </div>
  );
}
