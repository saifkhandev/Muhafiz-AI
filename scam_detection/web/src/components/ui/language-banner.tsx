"use client";

import { useState, useEffect } from "react";
import { useLanguage } from "@/lib/i18n/context";
import { X } from "lucide-react";

export function LanguageBanner() {
  const { language, setLanguage, t } = useLanguage();
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Show banner only if language is English and user hasn't dismissed it
    const dismissed = localStorage.getItem("languageBannerDismissed");
    if (!dismissed && language === "en") {
      setShow(true);
    }
  }, [language]);

  const handleSwitch = () => {
    setLanguage("ur");
    setShow(false);
  };

  const handleDismiss = () => {
    localStorage.setItem("languageBannerDismissed", "true");
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="sticky top-0 z-50 border-b border-border/60 bg-surface/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <p className="text-sm text-text-primary">
          {t("languageBanner.text")}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSwitch}
            className="rounded-lg bg-[#818CF8] px-4 py-1.5 text-sm font-medium text-background transition-opacity hover:opacity-90"
          >
            {t("languageBanner.button")}
          </button>
          <button
            onClick={handleDismiss}
            className="rounded-lg p-1.5 text-text-secondary transition-colors hover:text-text-primary"
            aria-label={t("languageBanner.dismiss")}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
