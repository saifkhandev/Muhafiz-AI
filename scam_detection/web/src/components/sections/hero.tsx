"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Shield } from "@/components/shield";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";

export function Hero() {
  const heroRef = useRef<HTMLElement>(null);
  const { t } = useLanguage();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
  }, []);

  return (
    <section
      ref={heroRef}
      id="hero"
      className="relative overflow-hidden px-4 pt-16 pb-24 sm:px-6 lg:px-8 lg:pt-24 lg:pb-32"
    >
      {/* Background gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(129,140,248,0.12),_transparent_50%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_rgba(229,72,77,0.08),_transparent_50%)]" />

      <div className="relative mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2">
        <div className="order-2 lg:order-1">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0 }}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-text-secondary"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-[#818CF8]" />
            {t("hero.badge")}
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-6 font-heading text-4xl font-bold leading-tight tracking-tight text-text-primary sm:text-5xl lg:text-6xl"
          >
            {t("hero.title1")}{" "}
            <span className="gradient-text">{t("hero.title2")}</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-6 max-w-lg text-lg leading-relaxed text-text-secondary"
          >
            {t("hero.description")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-8 flex flex-wrap gap-4"
          >
            <Link
              href="/analyze"
              className="inline-flex items-center gap-2 rounded-lg px-6 py-3 font-semibold text-background transition-opacity hover:opacity-90"
              style={{ background: 'linear-gradient(90deg, #6366F1 0%, #22D3EE 100%)', color: '#05070A' }}
            >
              {t("hero.analyzeNow")}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/how-it-works"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-6 py-3 font-semibold text-text-primary transition-all hover:border-[#818CF8] hover:text-[#818CF8] hover:shadow-[0_0_15px_rgba(129,140,248,0.3)]"
            >
              {t("hero.howItWorks")}
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-10 grid grid-cols-3 gap-4 border-t border-border/60 pt-6"
          >
            <div>
              <p className="font-heading text-2xl font-bold text-text-primary">{t("hero.stats.trainingMessages")}</p>
              <p className="text-xs text-text-secondary">{t("hero.stats.trainingMessagesLabel")}</p>
            </div>
            <div>
              <p className="font-heading text-2xl font-bold text-text-primary">{t("hero.stats.textInference")}</p>
              <p className="text-xs text-text-secondary">{t("hero.stats.textInferenceLabel")}</p>
            </div>
            <div>
              <p className="font-heading text-2xl font-bold text-text-primary">{t("hero.stats.audioInference")}</p>
              <p className="text-xs text-text-secondary">{t("hero.stats.audioInferenceLabel")}</p>
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="order-1 flex h-[320px] items-center justify-center lg:order-2 lg:h-[520px]"
        >
          <Shield className="h-full w-full" />
        </motion.div>
      </div>
    </section>
  );
}
