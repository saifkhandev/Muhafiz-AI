
->Pakistan-first protection against phone-based fraud

Muhafiz AI is a multilingual decision-support web application built to help people in Pakistan recognize scam messages and suspicious calls before they share an OTP, send money, click a link, or disclose personal information. It addresses fraud patterns that are especially familiar locally: fake BISP/Ehsaas assistance, bank and wallet impersonation, SIM-block threats, prize schemes, fake job fees, courier/customs payments, and caller-led social engineering.

The gap is linguistic as well as technical. Many existing anti-spam tools are optimized for English, while real users receive a mix of English, Urdu script, Roman Urdu, and code-switched text. Muhafiz AI accepts messages in all four forms and provides an understandable verdict, probability-based risk score, visible scam signals, and a recommended action. The goal is not to promise perfect detection; it is to give a person a fast, explainable reason to pause and verify through an official channel.

->A real model designed for the deployment environment

The text engine is not a mock or a keyword-only demo. It uses Pakistan-aware normalization followed by a combined word 1–2 gram and character 3–5 gram TF-IDF representation, a class-balanced LinearSVC, Platt probability calibration, and a 0.63 validation-selected decision threshold. This design was chosen deliberately: it runs below 10 ms per text message on CPU, has a small model footprint, does not require a GPU or paid AI API, and uses character features to better tolerate Roman Urdu spelling variation.

For recorded calls, Muhafiz AI uses local faster-whisper medium in INT8 CPU mode to create timestamped speech segments. It removes filler speech, builds overlapping windows so a fraudulent sentence is not split apart, classifies the windows in batch, and aggregates them into a High/Medium/Low call risk. The result shows the timestamped segments that contributed to the verdict. A strong fragment alone cannot force High risk; whole-call fraud context must corroborate it.

->Evidence, not one inflated headline

We test across several deliberately different suites and report their differences instead of hiding them:

- **Blind-50:** 98.0% accuracy, with 24 of 25 scams caught and all 25 safe messages passed.
- **V4 100-message holdout:** 95.0% accuracy, 90.0% scam recall, and no false positives.
- **Hard-505 adversarial suite:** 99.01% accuracy and 99.61% recall.
- **Fresh All-4 multilingual suite (318 messages):** 95.60% accuracy, 93.03% scam recall, and no false positives.

The All-4 result is the most important caution: Roman Urdu was the weakest language at 86.57% accuracy with nine missed scams. This is why we present Muhafiz AI as decision support, not an automatic blocking system. The system also records known error types—such as fake job fees, SIM-block claims, and payment-detail phishing—to guide the next data-collection cycle.

->Reliability work beyond training

We improved reliability without casually retraining on test data. Two later retraining attempts regressed on independent checks and were rejected. Instead, we added narrow contextual guardrails only for verified failure modes—for example, phishing that combines account-review language, a verification request, and an urgency/service threat. Every guardrail has a regression test and returns an identifiable rule name, making the correction auditable.

We also evaluated two new synthetic candidate datasets as diagnostics only. They are intentionally excluded from training because training on examples after evaluating against them would contaminate the results. A public Spam-SMS dataset was rejected because it lacked clear licensing/provenance and had duplicate, conflicting, and incompatible labels.

->Impact and honest next step

Muhafiz AI demonstrates a practical model for accessible fraud awareness: multilingual support, transparent reasoning, no paid inference requirement, and a polished web experience. The public frontend is live; local audio analysis supports a compelling demo, while free-tier cloud audio is transparently disabled rather than simulated.

The project is ready to demonstrate a credible end-to-end AI system. It is not yet a national production anti-fraud service. The next phase is clear: collect licensed and human-reviewed real SMS and consented call data, especially Roman Urdu; establish larger time-separated evaluation sets; calibrate thresholds against real harm; add privacy-preserving feedback; and harden deployment with monitoring, queueing, authentication, rate limits, and rollback. That path turns a strong hackathon proof of concept into a responsibly deployable public-safety tool.
