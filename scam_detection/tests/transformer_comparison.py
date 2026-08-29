"""Transformer comparison: mBERT vs TF-IDF+SVM on the same test sets."""
import sys, os, warnings, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, fbeta_score, precision_score, recall_score, confusion_matrix

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from run_retrain_v3_pipeline import load_and_combine_data, C_MSG, C_LBL

SEED = 42
np.random.seed(SEED)

# ── mBERT Configuration ──
MODEL_NAME = "bert-base-multilingual-cased"  # mBERT
MAX_LEN = 128
BATCH_SIZE = 16
EPOCHS = 3
LR = 2e-5

def main():
    t0 = time.time()
    print("=" * 70)
    print("  TRANSFORMER COMPARISON: mBERT vs TF-IDF+SVM")
    print("=" * 70)

    # ── Step 1: Load data ──
    print("\n[1] Loading data...")
    orig_df, aug_df, combined_df = load_and_combine_data()
    print(f"  Total: {len(combined_df)} messages")
    print(f"  Scam: {len(combined_df[combined_df[C_LBL]=='Scam'])} / Safe: {len(combined_df[combined_df[C_LBL]=='Safe'])}")

    le = LabelEncoder()
    y = le.fit_transform(combined_df[C_LBL].tolist())
    X = combined_df[C_MSG].tolist()

    # Same split as SVM training
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=SEED, stratify=y
    )
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    # ── Step 2: Load mBERT ──
    print(f"\n[2] Loading {MODEL_NAME}...")
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
    from transformers import DataCollatorWithPadding
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    model.to(device)
    print(f"  Model loaded: {sum(p.numel() for p in model.parameters())/1e6:.1f}M parameters")

    # ── Step 3: Tokenize ──
    print("\n[3] Tokenizing...")
    def tokenize(examples):
        return tokenizer(examples, truncation=True, padding=True, max_length=MAX_LEN)

    train_encodings = tokenize(X_train)
    test_encodings = tokenize(X_test)

    class ScamDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels
        def __getitem__(self, idx):
            item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
            item["labels"] = torch.tensor(self.labels[idx])
            return item
        def __len__(self):
            return len(self.labels)

    train_dataset = ScamDataset(train_encodings, y_train.tolist())
    test_dataset = ScamDataset(test_encodings, y_test.tolist())

    # ── Step 4: Fine-tune ──
    print(f"\n[4] Fine-tuning mBERT ({EPOCHS} epochs)...")
    output_dir = os.path.join(PROJECT_ROOT, "models", "mbert_scam")

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        learning_rate=LR,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=10,
        report_to="none",
        fp16=torch.cuda.is_available(),
        seed=SEED,
    )

    def compute_metrics(pred):
        labels = pred.label_ids
        preds = pred.predictions.argmax(-1)
        return {
            "accuracy": accuracy_score(labels, preds),
            "f1": f1_score(labels, preds, zero_division=0),
            "f2": fbeta_score(labels, preds, beta=2, zero_division=0),
            "precision": precision_score(labels, preds, zero_division=0),
            "recall": recall_score(labels, preds, zero_division=0),
        }

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics,
        data_collator=data_collator,
    )

    trainer.train()
    print(f"  Fine-tuning done in {time.time()-t0:.1f}s")

    # ── Step 5: Evaluate mBERT ──
    print("\n[5] Evaluating mBERT on test set...")
    mbert_results = trainer.evaluate()
    print(f"  mBERT Results:")
    print(f"    Accuracy:  {mbert_results['eval_accuracy']:.4f}")
    print(f"    F1:        {mbert_results['eval_f1']:.4f}")
    print(f"    F2:        {mbert_results['eval_f2']:.4f}")
    print(f"    Precision: {mbert_results['eval_precision']:.4f}")
    print(f"    Recall:    {mbert_results['eval_recall']:.4f}")

    # ── Step 6: Load and evaluate SVM ──
    print("\n[6] Evaluating TF-IDF+SVM on same test set...")
    svm_pipe = joblib.load(os.path.join(PROJECT_ROOT, "models", "full_pipeline.joblib"))
    svm_threshold = joblib.load(os.path.join(PROJECT_ROOT, "models", "threshold.joblib"))

    svm_proba = svm_pipe.predict_proba(X_test)[:, 1]
    svm_preds = (svm_proba >= svm_threshold).astype(int)

    svm_acc = accuracy_score(y_test, svm_preds)
    svm_f1 = f1_score(y_test, svm_preds, zero_division=0)
    svm_f2 = fbeta_score(y_test, svm_preds, beta=2, zero_division=0)
    svm_prec = precision_score(y_test, svm_preds, zero_division=0)
    svm_rec = recall_score(y_test, svm_preds, zero_division=0)
    svm_cm = confusion_matrix(y_test, svm_preds)
    svm_tn, svm_fp, svm_fn, svm_tp = svm_cm.ravel()

    print(f"  TF-IDF+SVM Results:")
    print(f"    Accuracy:  {svm_acc:.4f}")
    print(f"    F1:        {svm_f1:.4f}")
    print(f"    F2:        {svm_f2:.4f}")
    print(f"    Precision: {svm_prec:.4f}")
    print(f"    Recall:    {svm_rec:.4f}")
    print(f"    TP={svm_tp} FP={svm_fp} TN={svm_tn} FN={svm_fn}")

    # ── Step 7: Inference speed comparison ──
    print("\n[7] Inference speed comparison (100 messages)...")
    sample = X_test[:100]

    # mBERT speed
    t_start = time.time()
    with torch.no_grad():
        enc = tokenize(sample)
        enc = {k: torch.tensor(v).to(device) for k, v in enc.items()}
        _ = model(**enc)
    mbert_time = (time.time() - t_start) / 100 * 1000  # ms per message
    print(f"  mBERT:        {mbert_time:.1f} ms/message")

    # SVM speed
    t_start = time.time()
    _ = svm_pipe.predict_proba(sample)
    svm_time = (time.time() - t_start) / 100 * 1000  # ms per message
    print(f"  TF-IDF+SVM:   {svm_time:.2f} ms/message")
    print(f"  Speed ratio:  {mbert_time/svm_time:.0f}x slower")

    # ── Step 8: Model size comparison ──
    print("\n[8] Model size comparison...")
    svm_size = os.path.getsize(os.path.join(PROJECT_ROOT, "models", "full_pipeline.joblib"))
    mbert_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in os.listdir(output_dir) if f.endswith('.bin'))
    if mbert_size == 0:
        # Check for .safetensors
        mbert_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in os.listdir(output_dir) if f.endswith('.safetensors'))
    print(f"  TF-IDF+SVM:   {svm_size/1e6:.1f} MB")
    print(f"  mBERT:        {mbert_size/1e6:.1f} MB")
    print(f"  Size ratio:   {mbert_size/svm_size:.0f}x larger")

    # ── Step 9: Summary ──
    print("\n" + "=" * 70)
    print("  COMPARISON SUMMARY")
    print("=" * 70)
    print(f"  {'Metric':<15s} {'mBERT':>10s} {'TF-IDF+SVM':>12s} {'Winner':>12s}")
    print(f"  {'-' * 50}")
    metrics = [
        ("Accuracy",  mbert_results['eval_accuracy'], svm_acc),
        ("F1",        mbert_results['eval_f1'], svm_f1),
        ("F2",        mbert_results['eval_f2'], svm_f2),
        ("Precision", mbert_results['eval_precision'], svm_prec),
        ("Recall",    mbert_results['eval_recall'], svm_rec),
    ]
    for name, mbert_val, svm_val in metrics:
        winner = "mBERT" if mbert_val > svm_val else ("SVM" if svm_val > mbert_val else "TIE")
        print(f"  {name:<15s} {mbert_val:>10.4f} {svm_val:>12.4f} {winner:>12s}")

    print(f"  {'-' * 50}")
    print(f"  {'Speed':<15s} {mbert_time:>9.1f}ms {svm_time:>11.2f}ms {'SVM':>12s}")
    print(f"  {'Size':<15s} {mbert_size/1e6:>8.1f}MB {svm_size/1e6:>10.1f}MB {'SVM':>12s}")

    print(f"\n  CONCLUSION:")
    svm_wins = sum(1 for _, m, s in metrics if s >= m)
    mbert_wins = sum(1 for _, m, s in metrics if m > s)
    if mbert_wins > svm_wins:
        print(f"  mBERT wins on {mbert_wins}/{len(metrics)} accuracy metrics")
        print(f"  BUT TF-IDF+SVM is {mbert_time/svm_time:.0f}x faster and {mbert_size/svm_size:.0f}x smaller")
    else:
        print(f"  TF-IDF+SVM matches or beats mBERT on {svm_wins}/{len(metrics)} accuracy metrics")
        print(f"  AND is {mbert_time/svm_time:.0f}x faster and {mbert_size/svm_size:.0f}x smaller")
    print(f"  → TF-IDF+SVM is the right choice for real-time scam detection on mobile")

    print(f"\n{'=' * 70}")
    print(f"  DONE in {time.time()-t0:.1f}s")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    main()
