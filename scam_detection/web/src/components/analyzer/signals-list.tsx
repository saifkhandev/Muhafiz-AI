"use client";

import { motion } from "framer-motion";
import { Signal } from "@/lib/types";
import { useLanguage } from "@/lib/i18n/context";
import {
  Clock,
  Banknote,
  KeyRound,
  Gift,
  AlertOctagon,
  MessageSquareWarning,
} from "lucide-react";

const iconMap: Record<string, React.ReactNode> = {
  "Urgency / time pressure": <Clock className="h-4 w-4" />,
  "Financial request": <Banknote className="h-4 w-4" />,
  "Credential / OTP request": <KeyRound className="h-4 w-4" />,
  "Prize / lottery": <Gift className="h-4 w-4" />,
  "Threat / account block": <AlertOctagon className="h-4 w-4" />,
  "OTP-specific": <MessageSquareWarning className="h-4 w-4" />,
};

interface SignalsListProps {
  signals: Signal[];
}

export function SignalsList({ signals }: SignalsListProps) {
  const { t } = useLanguage();
  
  if (!signals.length) {
    return (
      <div className="rounded-xl border border-border/60 bg-surface p-4">
        <p className="text-sm text-text-secondary">
          {t("analyzer.signals.noSignals")}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/60 bg-surface p-4">
      <h4 className="text-sm font-semibold text-text-primary">{t("analyzer.signals.detectedSignals")}</h4>
      <p className="text-xs text-text-secondary/70">
        {t("analyzer.signals.subtitle")}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {signals.map((signal, index) => (
          <motion.div
            key={signal.category}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06, duration: 0.25 }}
            className="group relative rounded-lg border border-border bg-background px-3 py-2"
          >
            <div className="flex items-center gap-2 text-sm text-text-primary">
              <span className="text-accent">{iconMap[signal.category]}</span>
              <span>{signal.category}</span>
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {signal.matchedTerms.slice(0, 5).map((term, termIndex) => (
                <span
                  key={`${signal.category}-${termIndex}`}
                  className="rounded bg-border/40 px-1.5 py-0.5 text-xs text-text-secondary"
                >
                  {term}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

