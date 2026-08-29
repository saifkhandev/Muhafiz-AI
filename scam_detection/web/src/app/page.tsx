import { PageLayout } from "@/components/ui/page-layout";
import { Hero } from "@/components/sections/hero";
import { HowItWorksSection } from "@/components/sections/how-it-works";
import { AnalyzerSection } from "@/components/sections/analyzer-section";
import { ExamplesSection } from "@/components/sections/examples-section";
import { RoadmapSection } from "@/components/sections/roadmap-section";

export default function Home() {
  return (
    <PageLayout>
      <Hero />
      <HowItWorksSection />
      <AnalyzerSection />
      <ExamplesSection />
      <RoadmapSection />
    </PageLayout>
  );
}
