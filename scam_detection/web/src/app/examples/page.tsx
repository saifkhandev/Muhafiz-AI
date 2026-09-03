"use client";

import { PageLayout } from "@/components/ui/page-layout";
import { ExamplesSection } from "@/components/sections/examples-section";

export default function ExamplesPage() {
  return (
    <PageLayout>
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <ExamplesSection />
        </div>
      </section>
    </PageLayout>
  );
}
