"use client";

import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { CheckCircle2, Circle } from "lucide-react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const roadmap = [
  { title: "Binary Scam/Safe classification", status: "done", detail: "Shipped in V4" },
  { title: "Audio call analysis (STT → classifier)", status: "done", detail: "Shipped with Whisper medium" },
  { title: "Multilingual support", status: "done", detail: "EN + Urdu + Roman Urdu + Mixed" },
  { title: "Scam-category classification", status: "roadmap", detail: "Bank, job, BISP, lottery, etc." },
  { title: "Live SMS / browser interception", status: "roadmap", detail: "Requires telecom/browser extension integration" },
  { title: "Continuous learning pipeline", status: "roadmap", detail: "User reports → periodic retraining" },
];

export function RoadmapSection() {
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
      id="roadmap"
      className="px-4 py-24 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-5xl">
        <div className="mb-10 text-center">
          <h2 className="font-heading text-3xl font-bold text-text-primary sm:text-4xl">
            Roadmap
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            What&apos;s shipped and what comes next.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {roadmap.map((item, i) => (
            <motion.div
              key={item.title}
              whileHover={{ y: -4 }}
              className={`rounded-xl border p-5 ${
                item.status === "done"
                  ? "border-accent/30 bg-accent/5"
                  : "border-border bg-surface"
              }`}
            >
              <div className="flex items-start gap-3">
                {item.status === "done" ? (
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-accent" />
                ) : (
                  <Circle className="h-5 w-5 shrink-0 text-text-secondary" />
                )}
                <div>
                  <p className="text-sm font-semibold text-text-primary">{item.title}</p>
                  <p className="mt-1 text-xs text-text-secondary">{item.detail}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
