"use client";

import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Clock } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLanguage } from "@/lib/i18n/context";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export function RoadmapSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const { t } = useLanguage();

  const roadmap = [
    { title: t("roadmap.items.binary"), status: "done", detail: t("roadmap.items.binaryDetail") },
    { title: t("roadmap.items.audio"), status: "done", detail: t("roadmap.items.audioDetail") },
    { title: t("roadmap.items.multilingual"), status: "done", detail: t("roadmap.items.multilingualDetail") },
    { title: t("roadmap.items.category"), status: "roadmap", detail: t("roadmap.items.categoryDetail") },
    { title: t("roadmap.items.sms"), status: "roadmap", detail: t("roadmap.items.smsDetail") },
    { title: t("roadmap.items.learning"), status: "roadmap", detail: t("roadmap.items.learningDetail") },
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

  return (
    <section
      ref={sectionRef}
      id="roadmap"
      className="px-4 py-24 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-5xl">
        <div className="mb-12 text-center">
          <h2 className="font-heading text-3xl font-bold text-text-primary sm:text-4xl">
            {t("roadmap.title")}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            {t("roadmap.subtitle")}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {roadmap.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.4 }}
              className={`rounded-xl border p-5 ${
                item.status === "done" ? "border-accent/30 bg-accent/5" : "border-border bg-surface"
              }`}
            >
              <div className="flex items-center gap-2">
                {item.status === "done" ? (
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                ) : (
                  <Clock className="h-5 w-5 text-text-secondary" />
                )}
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    item.status === "done"
                      ? "bg-accent/20 text-accent"
                      : "bg-border/60 text-text-secondary"
                  }`}
                >
                  {item.status === "done" ? t("roadmap.status.done") : t("roadmap.status.roadmap")}
                </span>
              </div>
              <h3 className="mt-3 text-sm font-semibold text-text-primary">{item.title}</h3>
              <p className="mt-1 text-xs text-text-secondary">{item.detail}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
