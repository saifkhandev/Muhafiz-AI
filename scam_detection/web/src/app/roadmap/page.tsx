"use client";

import { PageLayout } from "@/components/ui/page-layout";
import { RoadmapSection } from "@/components/sections/roadmap-section";
import { useLanguage } from "@/lib/i18n/context";
import { Users, Target } from "lucide-react";

export default function RoadmapPage() {
  const { t } = useLanguage();

  return (
    <PageLayout>
      <RoadmapSection />

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="grid gap-8 lg:grid-cols-2">
            <div className="rounded-2xl border border-border bg-surface/50 p-6 sm:p-8">
              <div className="flex items-center gap-3">
                <Target className="h-6 w-6 text-accent" />
                <h2 className="font-heading text-2xl font-bold text-text-primary">{t("roadmapPage.mission")}</h2>
              </div>
              <p className="mt-4 text-text-secondary">
                {t("roadmapPage.missionText")}
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-surface/50 p-6 sm:p-8">
              <div className="flex items-center gap-3">
                <Users className="h-6 w-6 text-accent" />
                <h2 className="font-heading text-2xl font-bold text-text-primary">{t("roadmapPage.team")}</h2>
              </div>
              <p className="mt-4 text-text-secondary">
                {t("roadmapPage.teamText")}
              </p>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
