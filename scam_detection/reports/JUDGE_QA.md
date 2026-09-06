# Muhafiz AI — Judge Q&A and Objection Preparation

Use these answers precisely. Do not convert scoped benchmark results into a claim that every scam will be caught.

## Model and evaluation

### “Why use TF-IDF and LinearSVC instead of a transformer?”
We chose a calibrated word-and-character TF-IDF LinearSVC because it runs below 10 ms per text message on CPU, has a roughly 3 MB model footprint, works without a GPU or paid inference API, and is interpretable enough for a deployment-focused hackathon. Roman Urdu spelling variation benefits from character n-grams. A multilingual transformer comparison is a planned post-hackathon experiment, not a result we claim today.

### “Are your headline metrics cherry-picked?”
No single metric is presented as universal. Current checks include Blind-50 at 98.0% accuracy (24/25 scam recall, 25/25 safe specificity), a 100-message V4 holdout at 95.0%, Hard-505 at 99.01%, and a fresh 318-message All-4 evaluation at 95.60%. The All-4 suite is especially important because it exposes weaker Roman Urdu performance.

### “Why is the Hard-505 score high while All-4 is lower?”
They answer different questions. Hard-505 is a curated adversarial stress suite tied to known fraud/safe patterns. All-4 contains fresh multilingual records and is a more realistic test of generalization. We report both and do not average them.

### “What is the real Roman Urdu result?”
On the current 318-message All-4 report, Roman Urdu scored 86.57% accuracy, 81.25% scam recall, and 9 false negatives out of 67 records. English was 99.15%, Urdu 93.94%, and Mixed 100% on that particular fixture. Roman Urdu is the current highest-priority data gap.

### “Why is 0.63 the decision threshold?”
The LinearSVC is Platt-calibrated to a probability, then the threshold is selected on validation data using a balanced F1/F2/specificity composite. The higher-than-0.5 threshold reduces false alarms for legitimate bank and service notifications. It has a cost: some subtle scams fall below the threshold, so future recalibration requires a reserved, independently labeled validation set.

### “Do you understand your false negatives?”
Yes. The current All-4 report has 14 false negatives and no false positives. Nine are Roman Urdu, including fee-based jobs, SIM-block claims, courier charges, prize offers, and boss-impersonation payment demands. The V4 holdout missed five disguised scams, including fake charity, subscription, property, and card-security notices. These are concrete data-collection targets, not hidden failures.

### “What about false positives?”
The current All-4 suite had zero false positives, while Hard-505 had four: legitimate hospital/medical/health-card messages and a loan approval. This shows the trade-off: fraud terms such as amounts, payments, and loans occur in legitimate messages. We explicitly optimize for cautious guidance rather than automatic blocking.

## Data quality and synthetic data

### “Is 1,637 examples enough for production?”
No. It is enough to demonstrate a trained, multilingual proof of concept, not enough to claim national production coverage. The core data has 868 records; V3 and adversarial expansions bring the documented V4 training total to 1,637. The post-hackathon priority is more licensed, source-documented, human-reviewed real data.

### “Did you train on the two new synthetic datasets?”
No. Data Set 01 and Data Set 02 each have 50 synthetic records and are preserved as evaluation/diagnostic candidates only. They are excluded from `run_retrain_v3_pipeline.py`. Training on examples after evaluating against them would contaminate the measurement and encourage template overfitting.

### “How did you check the candidate datasets?”
We checked schema completeness, labels, normalized duplicates, conflicting labels, and normalized overlap with the 868-record core dataset and with each other. They had no recorded overlap or label conflict, but synthetic provenance and speaker markers in call transcripts still make them unsuitable as training evidence without independent review.

### “Why did you reject the public Spam-SMS repository?”
Its license and source provenance were not documented; it contained heavy duplication and conflicting labels; its Fraud/Promotional/Normal taxonomy cannot safely be converted to Muhafiz’s Scam/Safe definition; and it contains no Urdu-script coverage. A large dataset with incompatible labels would degrade the system more than it helps.

### “How do you avoid leakage?”
The retraining loader deduplicates by message content, and validation uses group-aware leakage-safe splitting. Candidate data remains outside the loader. The final Blind-50, All-4 evaluation, and verified call fixture are used for evaluation/regression rather than threshold tuning.

## Guardrails and explainability

### “Are guardrails just hard-coded answers?”
No. The classifier produces the base probability first. Guardrails are limited post-processing corrections for verified failure modes and require multiple signals. For example, the account-security rule requires account/service context, a verification demand, and urgency/service-threat language; a passive “service is active” notice does not fire it.

### “Can you explain a decision to a user?”
The API returns a verdict, calibrated risk score, detected language, matched scam-signal categories, recommended action, model version, and threshold. Where a guardrail changes the base decision, the internal prediction result records the guardrail rule identifier. Call results also return timestamped segment scores and contextual call patterns.

### “Do you have a durable audit log?”
We have reproducible evaluation reports, saved predictions/confusion matrices, artifact metadata, model version/threshold in API responses, and timing logs that deliberately avoid call content. A production-grade immutable request/audit store with privacy controls is a future hardening requirement; we do not claim it is already built.

## Call analysis and scale

### “How does call detection work?”
Audio is decoded, transcribed by local faster-whisper medium in INT8 CPU mode, cleaned and grouped into overlapping time windows, classified in batch by the text model, and aggregated using maximum risk, duration-weighted mean risk, scam-window ratio, and whole-call patterns. The result is High/Medium/Low plus timestamped evidence.

### “What prevented a dramatic call false positive?”
An isolated high-risk fragment can no longer force High on its own. High requires both a strong window and corroborating full-call fraud context. This protects against a noisy fragment while retaining a visible Medium risk for review.

### “What evidence supports call accuracy?”
The supplied card-phishing transcript regression now returns High risk, with card-verification and fraud-department impersonation patterns. However, the verified call benchmark currently contains one labeled record. That proves a regression case, not broad call-model accuracy. A balanced, consented real-call corpus is essential next.

### “Why does audio take 23–35 seconds?”
Speech-to-text dominates CPU latency. In local tests, faster-whisper medium averaged 24.7 seconds and small averaged 6.3 seconds, but small materially changed Urdu/Hindi transcripts and risk scores on two samples without ground truth. We keep medium as the accuracy baseline and show honest progress rather than pretending audio is real time.

### “Can this scale?”
Text inference is lightweight and can scale horizontally behind FastAPI. Audio is the costlier path because each worker loads Whisper and needs significant RAM. The documented deployment therefore uses one audio-capable local/demo worker; a scalable production design needs asynchronous jobs, queueing, object storage with retention rules, autoscaling, and a separate STT service.

## Deployment, privacy, and product claims

### “Does the model send messages or calls to a third-party AI API?”
No paid external inference API is required. The classifier and faster-whisper run in the project environment. In production, data-retention policy and access controls still need to be formalized.

### “Is the public site doing real inference?”
The live Vercel frontend is reachable and exposes the real analysis workflow. The documented Render free-tier backend disables audio because Whisper requires about 1.5 GB of model/RAM capacity; text remains active and audio returns an honest unavailable response. Full audio is demonstrated locally when the model is installed.

### “Is this a production anti-fraud guarantee?”
No. Muhafiz AI is a decision-support tool. It advises users to verify through official channels and never claims to replace banks, telecoms, regulators, or human investigation.

### “What would you do next if funded?”
Acquire licensed, source-documented, human-reviewed multilingual SMS and consented call transcripts; create time-separated train/validation/test splits; calibrate thresholds against cost-sensitive objectives; compare mBERT/XLM-R to the CPU baseline; add privacy-preserving feedback/reporting; and harden deployment with monitoring, rate limits, queues, authentication, and rollback.

## Safe one-sentence close
“Muhafiz AI is strong evidence that a fast, transparent Pakistan-first detector can help users pause before acting; our next responsibility is to grow the real labeled data and operational safeguards before claiming production protection.”
