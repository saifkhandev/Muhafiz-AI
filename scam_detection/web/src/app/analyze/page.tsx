import { PageLayout } from "@/components/ui/page-layout";
import { Analyzer } from "@/components/analyzer";

export default function AnalyzePage() {
  return (
    <PageLayout>
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-10 text-center">
            <h1 className="font-heading text-3xl font-bold text-text-primary sm:text-4xl">
              Analyze
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
              Paste a message or upload a call recording. Every result comes from the real V4 model — no mock data.
            </p>
          </div>
          <Analyzer />
        </div>
      </section>
    </PageLayout>
  );
}
