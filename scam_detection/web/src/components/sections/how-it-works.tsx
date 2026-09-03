"use client";

import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { MessageSquare, Headphones, Cpu, FileSearch, Gauge } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLanguage } from "@/lib/i18n/context";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

function Pipeline({ steps, title }: { steps: Array<{ icon: any; label: string; desc: string }>; title: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { t } = useLanguage();

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const ctx = gsap.context(() => {
      const line = containerRef.current?.querySelector(".pipeline-line") as SVGPathElement | null;
      const boxes = containerRef.current?.querySelectorAll(".pipeline-box");
      if (!line || !boxes) return;

      const length = line.getTotalLength();
      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length });

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 75%",
          once: true,
        },
      });

      tl.to(line, {
        strokeDashoffset: 0,
        duration: 1.2,
        ease: "none",
      });

      boxes.forEach((box, i) => {
        const start = (i / (boxes.length - 1)) * 1.2;
        tl.fromTo(
          box,
          { opacity: 0.35, scale: 0.98 },
          { opacity: 1, scale: 1, duration: 0.25, ease: "power2.out" },
          start - 0.1
        );
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <h4 className="mb-4 text-center text-sm font-semibold uppercase tracking-wider text-text-secondary">
        {title}
      </h4>
      <div className="relative grid grid-cols-2 gap-4 sm:grid-cols-4">
        <svg
          className="absolute top-8 left-0 hidden h-4 w-full sm:block"
          preserveAspectRatio="none"
        >
          <path
            className="pipeline-line"
            d="M0 8 H100%"
            stroke="#818CF8"
            strokeWidth="2"
            fill="none"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        {steps.map((step, i) => (
          <div
            key={step.label}
            className="pipeline-box relative z-10 rounded-xl border border-border bg-surface p-4 text-center"
          >
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-accent">
              <step.icon className="h-5 w-5" />
            </div>
            <p className="mt-3 text-sm font-semibold text-text-primary">{step.label}</p>
            <p className="mt-1 text-xs text-text-secondary">{step.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HowItWorksSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const { t } = useLanguage();

  const textSteps = [
    { icon: MessageSquare, label: t("howItWorks.textSteps.paste"), desc: t("howItWorks.textSteps.pasteDesc") },
    { icon: FileSearch, label: t("howItWorks.textSteps.preprocess"), desc: t("howItWorks.textSteps.preprocessDesc") },
    { icon: Cpu, label: t("howItWorks.textSteps.model"), desc: t("howItWorks.textSteps.modelDesc") },
    { icon: Gauge, label: t("howItWorks.textSteps.verdict"), desc: t("howItWorks.textSteps.verdictDesc") },
  ];

  const audioSteps = [
    { icon: Headphones, label: t("howItWorks.audioSteps.upload"), desc: t("howItWorks.audioSteps.uploadDesc") },
    { icon: Cpu, label: t("howItWorks.audioSteps.stt"), desc: t("howItWorks.audioSteps.sttDesc") },
    { icon: FileSearch, label: t("howItWorks.audioSteps.segment"), desc: t("howItWorks.audioSteps.segmentDesc") },
    { icon: Gauge, label: t("howItWorks.audioSteps.risk"), desc: t("howItWorks.audioSteps.riskDesc") },
  ];

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        sectionRef.current,
        { opacity: 0.9, y: 24, scale: 0.98 },
        {
          opacity: 1,
          y: 0,
          scale: 1,
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

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className="px-4 py-24 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-7xl">
        <div className="mb-12 text-center">
          <h2 className="font-heading text-3xl font-bold text-text-primary sm:text-4xl">
            {t("howItWorks.title")}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            {t("howItWorks.subtitle")}
          </p>
        </div>

        <div className="space-y-12 rounded-2xl border border-border bg-surface/50 p-6 sm:p-10">
          <Pipeline steps={textSteps} title={t("howItWorks.textPipeline")} />
          <Pipeline steps={audioSteps} title={t("howItWorks.audioPipeline")} />
        </div>

      </div>
    </section>
  );
}
