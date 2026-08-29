"use client";

import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { MessageSquare, Headphones, Cpu, FileSearch, Gauge } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const textSteps = [
  { icon: MessageSquare, label: "Paste message", desc: "SMS, WhatsApp, or transcript" },
  { icon: FileSearch, label: "Preprocess", desc: "Tokenize & detect language" },
  { icon: Cpu, label: "V4 model", desc: "TF-IDF + calibrated LinearSVC" },
  { icon: Gauge, label: "Verdict", desc: "Scam/Safe with probability" },
];

const audioSteps = [
  { icon: Headphones, label: "Upload call", desc: "mp3, wav, m4a, webm" },
  { icon: Cpu, label: "Whisper STT", desc: "faster-whisper medium" },
  { icon: FileSearch, label: "Segment scoring", desc: "Each chunk classified" },
  { icon: Gauge, label: "Call risk", desc: "Aggregated High/Medium/Low" },
];

const metrics = [
  { label: "Adversarial test (505 messages)", value: "99.60%", detail: "accuracy" },
  { label: "Fresh holdout (100 unseen)", value: "94.0%", detail: "accuracy" },
  { label: "Text inference", value: "<10ms", detail: "per message" },
  { label: "Audio inference", value: "23–35s", detail: "per call" },
];

function Pipeline({ steps, title }: { steps: typeof textSteps; title: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

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
            stroke="#2DD4BF"
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
            How It Works
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            Two real pipelines — text and audio — both powered by the same calibrated V4 model.
          </p>
        </div>

        <div className="space-y-12 rounded-2xl border border-border bg-surface/50 p-6 sm:p-10">
          <Pipeline steps={textSteps} title="Text Message Analysis" />
          <Pipeline steps={audioSteps} title="Call Audio Analysis" />
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {metrics.map((m) => (
            <motion.div
              key={m.label}
              whileHover={{ y: -4 }}
              className="rounded-xl border border-border bg-surface p-5 text-center"
            >
              <p className="font-heading text-3xl font-bold text-accent">{m.value}</p>
              <p className="mt-1 text-sm font-medium text-text-primary">{m.label}</p>
              <p className="text-xs text-text-secondary">{m.detail}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
