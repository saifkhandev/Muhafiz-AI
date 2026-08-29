"use client";

import { motion } from "framer-motion";
import { AudioSegment } from "@/lib/types";
import { AlertTriangle, CheckCircle, VolumeX } from "lucide-react";

interface AudioSegmentsProps {
  segments: AudioSegment[];
}

export function AudioSegments({ segments }: AudioSegmentsProps) {
  const displaySegments = segments.filter((s) => s.label !== "Skipped").slice(0, 20);

  if (!displaySegments.length) {
    return (
      <div className="mt-6 rounded-xl border border-border/60 bg-background p-4 text-sm text-text-secondary">
        No transcribed segments to display.
      </div>
    );
  }

  return (
    <div className="mt-6">
      <h4 className="mb-3 text-sm font-semibold text-text-primary">Segment-by-segment breakdown</h4>
      <div className="space-y-2">
        {displaySegments.map((segment, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.15, duration: 0.25 }}
            className={`rounded-xl border p-3 ${
              segment.label === "Scam"
                ? "border-danger/30 bg-danger/5"
                : "border-safe/30 bg-safe/5"
            }`}
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 shrink-0">
                {segment.label === "Scam" ? (
                  <AlertTriangle className="h-4 w-4 text-danger" />
                ) : segment.label === "Skipped" ? (
                  <VolumeX className="h-4 w-4 text-text-secondary" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-safe" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary break-words">{segment.text}</p>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-text-secondary">
                  <span>
                    {segment.startTime.toFixed(1)}s - {segment.endTime.toFixed(1)}s
                  </span>
                  <span className="font-semibold">
                    {segment.scamProbability.toFixed(1)}% scam probability
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
