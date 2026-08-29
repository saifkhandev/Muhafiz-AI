import { PageLayout } from "@/components/ui/page-layout";
import { ExamplesSection } from "@/components/sections/examples-section";

export default function ExamplesPage() {
  return (
    <PageLayout>
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <h1 className="font-heading text-3xl font-bold text-text-primary sm:text-4xl">
              Examples
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
              Run real examples through the V4 model and see distinct, non-mocked results.
            </p>
          </div>
          <ExamplesSection />
        </div>
      </section>
    </PageLayout>
  );
}
