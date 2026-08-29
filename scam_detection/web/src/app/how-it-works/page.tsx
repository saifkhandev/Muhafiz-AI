import { PageLayout } from "@/components/ui/page-layout";
import { HowItWorksSection } from "@/components/sections/how-it-works";
import {
  MessageSquare,
  Headphones,
  Cpu,
  FileSearch,
  Gauge,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";

const faqs = [
  {
    question: "Why TF-IDF + SVM instead of BERT or a transformer?",
    answer:
      "The V4 model hits 99.60% accuracy on 505 adversarial messages, runs in under 10ms per text message, and requires no GPU. TF-IDF + LinearSVC is fully explainable, fast to deploy, and sufficient for this dataset size. Transformers were deprioritized in favor of adversarial testing, FP reduction, and audio pipeline integration.",
  },
  {
    question: "What about real deployment?",
    answer:
      "The system is built as a REST API architecture (FastAPI backend + Next.js frontend) and is cloud-deployable as-is. The backend can be containerized and scaled independently of the frontend.",
  },
  {
    question: "What are the current limitations?",
    answer:
      "The model was trained on 1,637 messages. Roman Urdu remains the hardest case. Scam patterns evolve, so periodic retraining is needed. The model is binary Scam/Safe only — it does not classify scam category (bank, job, BISP, etc.).",
  },
  {
    question: "What were the 5 false negatives in the fresh holdout test?",
    answer:
      "They were scam messages deliberately disguised as ordinary legitimate notifications: a fake store-closure notice, a fake subscription renewal, a fake real-estate installment reminder, a fake charity confirmation, and a fake card-security alert. This is a genuinely hard, ambiguous category near the decision boundary, not a simple bug.",
  },
];

const detailedSteps = [
  {
    icon: MessageSquare,
    title: "Text input",
    desc: "User pastes an SMS, WhatsApp message, or transcript. Supports English, Urdu, Roman Urdu, and Mixed.",
  },
  {
    icon: FileSearch,
    title: "Preprocessing",
    desc: "Text is normalized, tokenized, and vectorized with TF-IDF using word n-grams and character n-grams.",
  },
  {
    icon: Cpu,
    title: "V4 classifier",
    desc: "LinearSVC wrapped in CalibratedClassifierCV outputs a genuine probability at threshold 0.63.",
  },
  {
    icon: Gauge,
    title: "Result",
    desc: "Verdict (Scam/Safe), risk score 0-100, detected language, rule-based signals, and recommended action.",
  },
];

const audioSteps = [
  {
    icon: Headphones,
    title: "Audio upload",
    desc: "User uploads mp3, wav, m4a, webm, aac, ogg, or flac. Max duration is enforced server-side.",
  },
  {
    icon: Cpu,
    title: "Whisper transcription",
    desc: "faster-whisper medium model (INT8, CPU) transcribes the call into timestamped segments.",
  },
  {
    icon: FileSearch,
    title: "Segment classification",
    desc: "Each non-silent segment is classified by the same V4 text model.",
  },
  {
    icon: Gauge,
    title: "Call-level verdict",
    desc: "Segment scores are aggregated into an overall High / Medium / Low risk verdict.",
  },
];

export default function HowItWorksPage() {
  return (
    <PageLayout>
      <HowItWorksSection />

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl space-y-16">
          <div>
            <h2 className="mb-8 text-center font-heading text-2xl font-bold text-text-primary sm:text-3xl">
              Text Pipeline
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
              Audio Pipeline
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
                V4 Model Facts
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">Model version</p>
                <p className="font-semibold text-text-primary">V4_adversarial_505</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">Architecture</p>
                <p className="font-semibold text-text-primary">TF-IDF + LinearSVC (CalibratedClassifierCV)</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">Decision threshold</p>
                <p className="font-semibold text-text-primary">0.63</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">Training data</p>
                <p className="font-semibold text-text-primary">1,637 messages</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">Adversarial test</p>
                <p className="font-semibold text-text-primary">99.60% accuracy, 0.4% FPR</p>
              </div>
              <div className="rounded-xl bg-background p-4">
                <p className="text-xs text-text-secondary">Fresh holdout</p>
                <p className="font-semibold text-text-primary">94.0% accuracy, 98.0% specificity</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-warning/30 bg-warning/5 p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
              <div>
                <h3 className="font-heading text-lg font-semibold text-text-primary">
                  Honest limitations
                </h3>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-text-secondary">
                  <li>1,637 training messages — strong for the hackathon scope but small for production scale.</li>
                  <li>Roman Urdu remains the hardest language case.</li>
                  <li>Static patterns need periodic retraining as scammers evolve.</li>
                  <li>No scam-category classification yet (binary Scam/Safe only).</li>
                  <li>Five fresh-holdout false negatives were disguised-as-legitimate scams near the 0.63 threshold.</li>
                </ul>
              </div>
            </div>
          </div>

          <div>
            <h2 className="mb-8 text-center font-heading text-2xl font-bold text-text-primary sm:text-3xl">
              FAQ
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
