import { PageLayout } from "@/components/ui/page-layout";
import { RoadmapSection } from "@/components/sections/roadmap-section";
import { Users, Target } from "lucide-react";

export default function RoadmapPage() {
  return (
    <PageLayout>
      <RoadmapSection />

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="grid gap-8 lg:grid-cols-2">
            <div className="rounded-2xl border border-border bg-surface/50 p-6 sm:p-8">
              <div className="flex items-center gap-3">
                <Target className="h-6 w-6 text-accent" />
                <h2 className="font-heading text-2xl font-bold text-text-primary">Mission</h2>
              </div>
              <p className="mt-4 text-text-secondary">
                Reduce financial fraud and social-engineering harm in Pakistan by giving people an
                accessible, explainable AI tool to check suspicious messages and calls before they act.
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-surface/50 p-6 sm:p-8">
              <div className="flex items-center gap-3">
                <Users className="h-6 w-6 text-accent" />
                <h2 className="font-heading text-2xl font-bold text-text-primary">Team</h2>
              </div>
              <p className="mt-4 text-text-secondary">
                Built for the Alibaba AI Hackathon — Karachi Regional Round. Muhafiz AI combines
                machine-learning research, FastAPI backend engineering, and Next.js frontend design
                into a single demo-ready product.
              </p>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
