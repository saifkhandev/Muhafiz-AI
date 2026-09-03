"use client";

import { motion, AnimatePresence } from "framer-motion";
import { TextAnalysisResult } from "@/lib/types";
import { useLanguage } from "@/lib/i18n/context";
import { AlertTriangle, CheckCircle, Shield } from "lucide-react";

interface ResultCardProps {
  result: TextAnalysisResult | null;
  isLoading?: boolean;
}

export function ResultCard({ result, isLoading }: ResultCardProps) {
  const { t } = useLanguage();
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 animate-pulse rounded-full bg-border" />
          <div className="h-6 w-32 animate-pulse rounded bg-border" />
        </div>
        <div className="mt-4 h-4 w-full animate-pulse rounded bg-border" />
        <div className="mt-2 h-4 w-2/3 animate-pulse rounded bg-border" />
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      {result && (
        <motion.div
          key={result.verdict}
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={`relative overflow-hidden rounded-2xl border p-6 ${
            result.verdict === "Scam"
              ? "border-danger/40 bg-danger/5"
              : "border-safe/40 bg-safe/5"
          }`}
        >
          {/* Color wash */}
          <motion.div
            initial={{ x: "-100%", opacity: 0.3 }}
            animate={{ x: "100%", opacity: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className={`absolute inset-0 ${
              result.verdict === "Scam" ? "bg-danger" : "bg-safe"
            }`}
          />

          <div className="relative flex items-start gap-4">
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${
                result.verdict === "Scam" ? "bg-danger/20 text-danger" : "bg-safe/20 text-safe"
              }`}
            >
              {result.verdict === "Scam" ? (
                <AlertTriangle className="h-6 w-6" />
              ) : (
                <CheckCircle className="h-6 w-6" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="font-heading text-2xl font-bold">
                  {result.verdict === "Scam" ? t("analyzer.result.likelyScam") : t("analyzer.result.looksSafe")}
                </h3>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    result.riskLabel === "High"
                      ? "bg-danger/20 text-danger"
                      : result.riskLabel === "Medium"
                      ? "bg-warning/20 text-warning"
                      : "bg-safe/20 text-safe"
                  }`}
                >
                  {result.riskLabel} Risk
                </span>
              </div>

              <div className="mt-3 flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{t("analyzer.result.riskScore")}</span>
                    <span className="font-semibold">{result.riskScore.toFixed(1)}%</span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-border/60">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${result.riskScore}%` }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className={`h-full rounded-full ${
                        result.verdict === "Scam"
                          ? "bg-gradient-to-r from-danger to-danger/70"
                          : "bg-gradient-to-r from-safe to-safe/70"
                      }`}
                    />
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                <div className="flex items-center gap-2 text-text-secondary">
                  <Shield className="h-4 w-4 text-accent" />
                  <span>{t("analyzer.result.language")}: <span className="text-text-primary">{result.detectedLanguage}</span></span>
                </div>
                <div className="flex items-center gap-2 text-text-secondary">
                  <Shield className="h-4 w-4 text-accent" />
                  <span>{t("analyzer.result.model")}: <span className="text-text-primary">{result.modelName}</span></span>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-border/60 bg-background/50 p-4">
                <p className="text-sm font-medium text-text-primary">
                  {t("analyzer.result.recommendedAction")}
                </p>
                <p className="mt-1 text-sm text-text-secondary">
                  {result.recommendedAction}
                </p>
              </div>

              <p className="mt-4 text-xs text-text-secondary/70">
                {t("analyzer.result.warning")}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
