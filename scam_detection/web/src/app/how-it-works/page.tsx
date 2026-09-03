"use client";

import { PageLayout } from "@/components/ui/page-layout";
import { HowItWorksSection } from "@/components/sections/how-it-works";
import { useLanguage } from "@/lib/i18n/context";
import {
  MessageSquare,
  Headphones,
  Cpu,
  FileSearch,
  Gauge,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";

export default function HowItWorksPage() {
  const { t } = useLanguage();

  const faqs = [
    {
      question: t("howItWorksPage.faq.q1"),
      answer: t("howItWorksPage.faq.a1"),
    },
    {
      question: t("howItWorksPage.faq.q2"),
      answer: t("howItWorksPage.faq.a2"),
    },
    {
      question: t("howItWorksPage.faq.q3"),
      answer: t("howItWorksPage.faq.a3"),
    },
    {
      question: t("howItWorksPage.faq.q4"),
      answer: t("howItWorksPage.faq.a4"),
    },
  ];

  const detailedSteps = [
    {
      icon: MessageSquare,
      title: t("howItWorksPage.steps.textInput"),
      desc: t("howItWorksPage.steps.textInputDesc"),
    },
    {
      icon: FileSearch,
      title: t("howItWorksPage.steps.preprocessing"),
      desc: t("howItWorksPage.steps.preprocessingDesc"),
    },
    {
      icon: Cpu,
      title: t("howItWorksPage.steps.classifier"),
      desc: t("howItWorksPage.steps.classifierDesc"),
    },
    {
      icon: Gauge,
      title: t("howItWorksPage.steps.result"),
      desc: t("howItWorksPage.steps.resultDesc"),
    },
  ];

  const audioSteps = [
    {
      icon: Headphones,
      title: t("howItWorksPage.steps.audioUpload"),
      desc: t("howItWorksPage.steps.audioUploadDesc"),
    },
    {
      icon: Cpu,
      title: t("howItWorksPage.steps.whisper"),
      desc: t("howItWorksPage.steps.whisperDesc"),
    },
    {
      icon: FileSearch,
      title: t("howItWorksPage.steps.segment"),
      desc: t("howItWorksPage.steps.segmentDesc"),
    },
    {
      icon: Gauge,
      title: t("howItWorksPage.steps.verdict"),
      desc: t("howItWorksPage.steps.verdictDesc"),
    },
  ];

  const limitations = t("howItWorksPage.limitations");

  return (
    <PageLayout>
      <HowItWorksSection />

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl space-y-16">
          <div>
            <h2 className="mb-8 text-center font-heading text-2xl font-bold text-text-primary sm:text-3xl">
              {t("howItWorksPage.textPipelineTitle")}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {detailedSteps.map((step) => (
                <div
                  key={step.title}
                  className="rounded-xl border border-border bg-surface p-5"
                >
                  <step.icon className="h-8 w-8 text-accent" />
                  <h3 className="mt-4 font-heading text-lg font-semibold text-text-primary">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-text-secondary">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="mb-8 text-center font-heading text-2xl font-bold text-text-primary sm:text-3xl">
              {t("howItWorksPage.audioPipelineTitle")}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {audioSteps.map((step) => (
                <div
                  key={step.title}
                  className="rounded-xl border border-border bg-surface p-5"
                >
                  <step.icon className="h-8 w-8 text-accent" />
                  <h3 className="mt-4 font-heading text-lg font-semibold text-text-primary">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-text-secondary">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface/50 p-6 sm:p-10">
            <div className="mb-8 flex items-center gap-3">
              <ShieldCheck className="h-6 w-6 text-accent" />
              <h2 className="font-heading text-2xl font-bold text-text-primary">
                {t("howItWorksPage.factsTitle")}
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">{t("howItWorksPage.facts.version")}</p>
                <p className="font-semibold text-text-primary">{t("howItWorksPage.facts.versionValue")}</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">{t("howItWorksPage.facts.architecture")}</p>
                <p className="font-semibold text-text-primary">{t("howItWorksPage.facts.architectureValue")}</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">{t("howItWorksPage.facts.threshold")}</p>
                <p className="font-semibold text-text-primary">{t("howItWorksPage.facts.thresholdValue")}</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">{t("howItWorksPage.facts.training")}</p>
                <p className="font-semibold text-text-primary">{t("howItWorksPage.facts.trainingValue")}</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">{t("howItWorksPage.facts.adversarial")}</p>
                <p className="font-semibold text-text-primary">{t("howItWorksPage.facts.adversarialValue")}</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">{t("howItWorksPage.facts.holdout")}</p>
                <p className="font-semibold text-text-primary">{t("howItWorksPage.facts.holdoutValue")}</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-warning/30 bg-warning/5 p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
              <div>
                <h3 className="font-heading text-lg font-semibold text-text-primary">
                  {t("howItWorksPage.limitationsTitle")}
                </h3>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-text-secondary">
                  {Array.isArray(limitations) ? (
                    limitations.map((item: string, i: number) => (
                      <li key={i}>{item}</li>
                    ))
                  ) : (
                    <>
                      <li>{t("howItWorksPage.facts.training")} - {t("howItWorksPage.facts.trainingValue")}</li>
                    </>
                  )}
                </ul>
              </div>
            </div>
          </div>

          <div>
            <h2 className="mb-8 text-center font-heading text-2xl font-bold text-text-primary sm:text-3xl">
              {t("howItWorksPage.faqTitle")}
            </h2>
            <div className="space-y-4">
              {faqs.map((faq) => (
                <div
                  key={faq.question}
                  className="rounded-xl border border-border bg-surface p-5"
                >
                  <h3 className="font-heading text-lg font-semibold text-text-primary">
                    {faq.question}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                    {faq.answer}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
