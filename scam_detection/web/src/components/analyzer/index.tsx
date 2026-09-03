"use client";

import { useState } from "react";
import { TextAnalyzer } from "./text-analyzer";
import { AudioAnalyzer } from "./audio-analyzer";
import { useLanguage } from "@/lib/i18n/context";
import { MessageSquare, Headphones } from "lucide-react";

type Tab = "text" | "audio";

export function Analyzer() {
  const [activeTab, setActiveTab] = useState<Tab>("text");
  const { t } = useLanguage();

  return (
    <div className="rounded-2xl border border-border bg-surface/50 p-2">
      <div className="flex gap-2 rounded-xl bg-background p-1">
        <button
          onClick={() => setActiveTab("text")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "text" ? "bg-surface text-[#818CF8] border border-[#818CF8]" : "text-text-secondary hover:text-[#818CF8]"
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          {t("analyzer.messageTab")}
        </button>
        <button
          onClick={() => setActiveTab("audio")}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "audio" ? "bg-surface text-[#818CF8] border border-[#818CF8]" : "text-text-secondary hover:text-[#818CF8]"
          }`}
        >
          <Headphones className="h-4 w-4" />
          {t("analyzer.audioTab")}
        </button>
      </div>
      <div className="p-4 sm:p-6">
        {activeTab === "text" ? <TextAnalyzer /> : <AudioAnalyzer />}
      </div>
    </div>
  );
}

