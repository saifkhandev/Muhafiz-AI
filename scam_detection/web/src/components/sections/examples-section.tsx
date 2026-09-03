"use client";

import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { analyzeText } from "@/lib/api";
import { TextAnalysisResult } from "@/lib/types";
import { ResultCard } from "@/components/analyzer/result-card";
import { SignalsList } from "@/components/analyzer/signals-list";
import { useShield } from "@/lib/shield-context";
import { useLanguage } from "@/lib/i18n/context";
import { Loader2 } from "lucide-react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const exampleTexts = [
  "Bhai aap ko Rs. 50,000 ka inaam mila hai. Fee Rs. 3,000 bhej kar claim karen.",
  "Dear customer, your HBL card has been blocked. Click here to verify immediately: http://hbl-verify.com",
  "Great news! Your CV is selected for Dubai job. Send processing fee Rs. 5,000 on EasyPaisa number 03451234567.",
  "Your HBL account has been credited with Rs. 25,000. Current balance: Rs. 150,000.",
  "Aoa, meeting at 3pm tomorrow at the office. Please bring the report.",
];

export function ExamplesSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const [result, setResult] = useState<TextAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const { triggerPulse } = useShield();
  const { t } = useLanguage();

  const examples = [
    {
      category: t("examples.categories.prize"),
      lang: t("examples.languages.romanUrdu"),
      text: exampleTexts[0],
    },
    {
      category: t("examples.categories.bank"),
      lang: t("examples.languages.english"),
      text: exampleTexts[1],
    },
    {
      category: t("examples.categories.job"),
      lang: t("examples.languages.mixed"),
      text: exampleTexts[2],
    },
    {
      category: t("examples.categories.legitimate"),
      lang: t("examples.languages.english"),
      text: exampleTexts[3],
    },
    {
      category: t("examples.categories.ordinary"),
      lang: t("examples.languages.english"),
      text: exampleTexts[4],
    },
  ];

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        sectionRef.current,
        { opacity: 0.9, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: "power2.out",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top 80%",
            once: true,
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const handleRun = async (index: number) => {
    setActive(index);
    setLoading(true);
    setResult(null);
    try {
      const res = await analyzeText(examples[index].text);
      setResult(res);
      triggerPulse(res.verdict);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      ref={sectionRef}
      id="examples"
      className="px-4 py-24 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-5xl">
        <div className="mb-10 text-center">
          <h2 className="font-heading text-3xl font-bold text-text-primary sm:text-4xl">
            {t("examples.title")}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            {t("examples.subtitle")}
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-3">
            {examples.map((ex, i) => (
              <motion.button
                key={i}
                onClick={() => handleRun(i)}
                whileHover={{ x: 4 }}
                className={`w-full rounded-xl border p-4 text-left transition-colors ${
                  active === i ? "border-[#818CF8] bg-background shadow-[0_0_15px_rgba(129,140,248,0.2)]" : "border-border bg-surface hover:border-[#818CF8]/50 hover:shadow-[0_0_10px_rgba(129,140,248,0.1)]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-text-primary">{ex.category}</span>
                  <span className="text-xs text-text-secondary">{ex.lang}</span>
                </div>
                <p className="mt-2 text-sm text-text-secondary line-clamp-2">{ex.text}</p>
              </motion.button>
            ))}
          </div>

          <div>
            {loading && (
              <div className="flex items-center justify-center rounded-2xl border border-border bg-surface p-12">
                <Loader2 className="h-8 w-8 animate-spin text-accent" />
              </div>
            )}
            {!loading && result && (
              <div className="space-y-4">
                <ResultCard result={result} />
                <SignalsList signals={result.signals} />
              </div>
            )}
            {!loading && !result && (
              <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-border bg-surface/50 p-12 text-center">
                <p className="text-sm text-text-secondary">
                  {t("examples.runButton")}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
