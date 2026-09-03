"use client";

import { useLanguage } from "@/lib/i18n/context";
import { Globe } from "lucide-react";

export function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();

  return (
    <button
      onClick={() => setLanguage(language === "en" ? "ur" : "en")}
      className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary transition-all hover:border-[#818CF8] hover:text-[#818CF8]"
      aria-label="Switch language"
    >
      <Globe className="h-3.5 w-3.5" />
      <span>{language === "en" ? "اردو" : "EN"}</span>
    </button>
  );
}
