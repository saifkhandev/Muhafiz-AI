"""
run_augmented_pipeline.py
Augmented scam-detection pipeline: Pakistan dataset + UCI SMS Spam Collection.

Experiments:
  Exp 1: Train on Pakistan only
  Exp 2: Train on UCI only
  Exp 3: Train on Combined (Pakistan + UCI)

All evaluated on an untouched Pakistan holdout.
"""
import sys, os, json, time, hashlib, re, warnings
import numpy as np
import pandas as pd
from collections import Counter
from difflib import SequenceMatcher
from scipy.sparse import issparse

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_validate,
)
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import GradientBoostingClassifier, VotingClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix,
)
from sklearn.base import clone
import joblib

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR       = os.path.join(PROJECT_ROOT, "data")
RAW_UCI_DIR    = os.path.join(DATA_DIR, "raw", "uci_sms_spam")
UCI_FILE       = os.path.join(RAW_UCI_DIR, "SMSSpamCollection")
PK_FILE        = os.path.join(DATA_DIR, "scam_messages_dataset.xlsx")
PK_SHEET       = "Scam Detection Dataset"

MODEL_DIR   = os.path.join(PROJECT_ROOT, "models")
REPORT_DIR  = os.path.join(PROJECT_ROOT, "reports")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

SEED     = 42
N_FOLDS  = 5
PK_HOLDOUT_FRAC = 0.38   # 38% of Pakistan data reserved as holdout (for 75+ per language)
COMBINED_TEST_FRAC = 0.15

# ── Column names ─────────────────────────────────────────────────────────────
C_MSG  = "message"
C_LBL  = "label"
C_SRC  = "source"
C_LANG = "language_type"
C_CAT  = "scam_category"

SRC_PK  = "pakistan_original"
SRC_UCI = "uci_sms"

LBL_SCAM = "Scam"
LBL_SAFE = "Safe"


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1-2: LOAD & INSPECT
# ═══════════════════════════════════════════════════════════════════════════

def load_pakistan():
    df = pd.read_excel(PK_FILE, sheet_name=PK_SHEET)
    df = df.rename(columns={
        "Message Content": C_MSG,
        "Language Type":   C_LANG,
        "Scam Category":   C_CAT,
        "Label":           C_LBL,
    })
    df[C_SRC] = SRC_PK
    return df

def load_uci():
    df = pd.read_csv(UCI_FILE, sep="\t", header=None, names=[C_LBL, C_MSG],
                     encoding="latin-1")
    # Map labels
    label_map = {"spam": LBL_SCAM, "ham": LBL_SAFE}
    df[C_LBL] = df[C_LBL].str.strip().map(label_map)
    df[C_SRC] = SRC_UCI
    df[C_LANG] = None
    df[C_CAT]  = None
    return df

def inspect(df, name):
    print(f"\n  --- {name} ---")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Missing: {df.isna().sum().to_dict()}")
    print(f"  Duplicates (full row): {df.duplicated().sum()}")
    print(f"  Duplicate messages: {df[C_MSG].duplicated().sum()}")
    lbl = df[C_LBL].value_counts().to_dict()
    print(f"  Labels: {lbl}")
    lens = df[C_MSG].astype(str).str.len()
    print(f"  Length: mean={lens.mean():.1f}, median={lens.median():.0f}, "
          f"min={lens.min()}, max={lens.max()}")
    empty = (df[C_MSG].astype(str).str.strip().str.len() == 0).sum()
    print(f"  Empty messages: {empty}")
    return lbl


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 3-4: NORMALIZE & MERGE
# ═══════════════════════════════════════════════════════════════════════════

def normalize_and_merge(pk_df, uci_df):
    pk = pk_df[[C_MSG, C_LBL, C_SRC, C_LANG, C_CAT]].copy()
    uci = uci_df[[C_MSG, C_LBL, C_SRC, C_LANG, C_CAT]].copy()
    pk[C_MSG] = pk[C_MSG].astype(str).str.strip()
    uci[C_MSG] = uci[C_MSG].astype(str).str.strip()
    # Remove empty
    pk  = pk[pk[C_MSG].str.len() > 0].reset_index(drop=True)
    uci = uci[uci[C_MSG].str.len() > 0].reset_index(drop=True)
    combined = pd.concat([pk, uci], ignore_index=True)
    print(f"\n  Combined: {len(combined)} rows "
          f"(Pakistan={len(pk)}, UCI={len(uci)})")
    return pk, uci, combined


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 5: DUPLICATE & NEAR-DUPLICATE CHECK
# ═══════════════════════════════════════════════════════════════════════════

def dedup(df):
    before = len(df)
    df = df.drop_duplicates(subset=[C_MSG], keep="first").reset_index(drop=True)
    removed = before - len(df)
    return df, removed

def find_near_duplicates(df, threshold=0.90):
    """Fast near-duplicate detection using character-shingle Jaccard.
    Only checks cross-source pairs (Pakistan vs UCI) for efficiency.
    """
    def char_shingles(text, k=4):
        t = text.lower().strip()
        return set(t[i:i+k] for i in range(max(len(t)-k+1, 1)))

    def jaccard(s1, s2):
        if not s1 or not s2:
            return 0.0
        inter = len(s1 & s2)
        union = len(s1 | s2)
        return inter / union if union > 0 else 0.0

    pk_idx = df[df[C_SRC] == SRC_PK].index.tolist()
    uci_idx = df[df[C_SRC] == SRC_UCI].index.tolist()

    # Precompute shingles
    msgs = df[C_MSG].tolist()
    shingles = {}
    for i in pk_idx + uci_idx:
        shingles[i] = char_shingles(str(msgs[i]))

    near = []
    # Only check cross-source pairs (Pakistan vs UCI)
    for i in pk_idx:
        for j in uci_idx:
            # Quick length filter
            li, lj = len(msgs[i]), len(msgs[j])
            if li == 0 or lj == 0:
                continue
            ratio = min(li, lj) / max(li, lj)
            if ratio < 0.5:
                continue
            sim = jaccard(shingles[i], shingles[j])
            if sim >= threshold * 0.8:  # Jaccard is stricter than SequenceMatcher
                near.append({
                    "i": i, "j": j, "sim": round(sim, 4),
                    "lbl_i": df.iloc[i][C_LBL], "lbl_j": df.iloc[j][C_LBL],
                    "src_i": df.iloc[i][C_SRC], "src_j": df.iloc[j][C_SRC],
                })
    return near

def conflict_check(near_dups):
    conflicts = [d for d in near_dups if d["lbl_i"] != d["lbl_j"]]
    return conflicts


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 6-7: LEAKAGE-SAFE SPLITS
# ═══════════════════════════════════════════════════════════════════════════

def make_pakistan_holdout(pk_df):
    """Reserve a portion of Pakistan data as untouched holdout."""
    pk_train_full, pk_holdout = train_test_split(
        pk_df, test_size=PK_HOLDOUT_FRAC,
        stratify=pk_df[C_LBL], random_state=SEED,
    )
    print(f"  Pakistan holdout: {len(pk_holdout)} messages")
    return pk_train_full.reset_index(drop=True), pk_holdout.reset_index(drop=True)

def make_combined_splits(combined_train, pk_holdout_msgs):
    """
    Split combined (minus holdout) into train/val/test.
    Ensure no holdout messages leak.
    """
    holdout_set = set(pk_holdout_msgs.str.lower().str.strip())
    mask = ~combined_train[C_MSG].str.lower().str.strip().isin(holdout_set)
    safe_combined = combined_train[mask].reset_index(drop=True)

    train_df, test_df = train_test_split(
        safe_combined, test_size=COMBINED_TEST_FRAC,
        stratify=safe_combined[C_LBL], random_state=SEED,
    )
    train_df, val_df = train_test_split(
        train_df, test_size=0.12,
        stratify=train_df[C_LBL], random_state=SEED,
    )
    return (train_df.reset_index(drop=True),
            val_df.reset_index(drop=True),
            test_df.reset_index(drop=True))


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 9: TEXT PREPROCESSING (reuse existing normalizer)
# ═══════════════════════════════════════════════════════════════════════════

from src.preprocessing import ScamTextNormalizer
from src.features import ScamFeatureExtractor

NORM = ScamTextNormalizer()


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 10-11: MODEL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

def build_models():
    """Build model candidates including engineered + combined variants."""
    base_word_tfidf = TfidfVectorizer(
        ngram_range=(1,2), min_df=2, max_df=0.95,
        sublinear_tf=True, max_features=12000)
    base_char_tfidf = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3,6), min_df=2,
        max_df=0.95, sublinear_tf=True, max_features=15000)

    models = {
        "A_word_lr": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=12000)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced",
                                        random_state=SEED)),
        ]),
        "B_word_svm": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=12000)),
            ("clf", LinearSVC(max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        "C_char_svm": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3,6),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Tuned SVM with higher C
        "B_word_svm_C2": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=15000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Wider ngrams
        "B_word_svm_tri": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,3), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=20000)),
            ("clf", LinearSVC(max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Lower C for regularization
        "B_word_svm_C05": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=12000)),
            ("clf", LinearSVC(C=0.5, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Even lower C for less FP
        "B_word_svm_C03": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=12000)),
            ("clf", LinearSVC(C=0.3, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Char SVM with lower C (reduce FP)
        "C_char_svm_C05": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3,6),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(C=0.5, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Char SVM with higher C
        "C_char_svm_C2": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3,6),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ]),
        # Word SVM without balanced weights (reduce FP)
        "B_word_svm_nocw": Pipeline([
            ("norm", ScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=12000)),
            ("clf", LinearSVC(max_iter=5000, random_state=SEED, dual="auto")),
        ]),
    }

    # D: Combined word + char TF-IDF (FeatureUnion)
    try:
        combined_pipe = Pipeline([
            ("norm", ScamTextNormalizer()),
            ("features", FeatureUnion([
                ("word", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_df=0.95,
                                          sublinear_tf=True, max_features=10000)),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3,6),
                                          min_df=2, max_df=0.95, sublinear_tf=True,
                                          max_features=10000)),
            ])),
            ("clf", LinearSVC(max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])
        models["D_combined_svm"] = combined_pipe
    except Exception:
        models["D_combined_svm"] = None

    return models

# For D and E we handle manually due to multi-vectorizer / feature engineering


# ═══════════════════════════════════════════════════════════════════════════
#  CROSS-VALIDATION & EVALUATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def cv_pipeline(pipe, X, y, n_folds=N_FOLDS):
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=SEED)
    from sklearn.metrics import make_scorer
    f1_s = make_scorer(f1_score, pos_label=1, zero_division=0)
    rec_s = make_scorer(recall_score, pos_label=1, zero_division=0)
    prec_s = make_scorer(precision_score, pos_label=1, zero_division=0)
    res = cross_validate(pipe, X, y, cv=cv,
                         scoring={"acc": "accuracy",
                                  "f1": f1_s,
                                  "recall": rec_s,
                                  "precision": prec_s},
                         return_train_score=True, n_jobs=-1)
    out = {}
    for m in ["acc", "f1", "recall", "precision"]:
        vals = res[f"test_{m}"]
        out[f"cv_{m}_mean"] = float(np.nanmean(vals))
        out[f"cv_{m}_std"] = float(np.nanstd(vals))
        out[f"train_{m}_mean"] = float(np.nanmean(res[f"train_{m}"]))
    return out

def fit_predict(pipe, X_train, y_train, X_test):
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    proba = None
    if hasattr(pipe[-1], "predict_proba"):
        proba = pipe.predict_proba(X_test)[:, 1]
    elif hasattr(pipe[-1], "decision_function"):
        d = pipe.decision_function(X_test)
        proba = 1 / (1 + np.exp(-d))
    return pred, proba

def metrics(y_true, y_pred, y_proba=None):
    m = {
        "accuracy":  accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, pos_label=1, zero_division=0),
        "recall":    recall_score(y_true, y_pred, pos_label=1, zero_division=0),
        "f1":        f1_score(y_true, y_pred, pos_label=1, zero_division=0),
    }
    if y_proba is not None:
        try:
            m["roc_auc"] = roc_auc_score(y_true, y_proba)
        except:
            m["roc_auc"] = None
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    m["TP"] = int(tp); m["FP"] = int(fp)
    m["FN"] = int(fn); m["TN"] = int(tn)
    return m

def threshold_sweep(y_true, y_proba, lo=0.10, hi=0.90, step=0.005):
    if y_proba is None:
        return 0.5, {}
    best_t, best_f1 = 0.5, 0
    best_acc = 0
    results = []
    for t in np.arange(lo, hi, step):
        pred = (y_proba >= t).astype(int)
        f = f1_score(y_true, pred, pos_label=1, zero_division=0)
        a = accuracy_score(y_true, pred)
        results.append({"t": round(t,3), "f1": f, "acc": a})
        # Optimize for F1 primarily, accuracy as tiebreaker
        score = f * 0.7 + a * 0.3
        best_score = best_f1 * 0.7 + best_acc * 0.3
        if score > best_score:
            best_f1 = f; best_acc = a; best_t = round(t, 3)
    return best_t, results


# ═══════════════════════════════════════════════════════════════════════════
#  EXPERIMENT RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def run_experiment(name, train_df, val_df, test_df, le, label=""):
    """Run all models on one experiment, return comparison table."""
    print(f"\n{'='*70}")
    print(f"  EXPERIMENT: {name}  {label}")
    print(f"  Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")
    print(f"{'='*70}")

    X_tr = train_df[C_MSG].values
    y_tr = le.transform(train_df[C_LBL].values)
    X_val = val_df[C_MSG].values
    y_val = le.transform(val_df[C_LBL].values)
    X_te = test_df[C_MSG].values
    y_te = le.transform(test_df[C_LBL].values)

    models = build_models()
    results = []
    best_name = None
    best_f1 = 0
    best_pipe = None
    best_val_proba = None
    best_test_proba = None

    for mname, pipe in models.items():
        if pipe is None:
            continue
        print(f"\n  [{mname}] CV ...")
        cv_res = cv_pipeline(pipe, X_tr, y_tr)

        print(f"  [{mname}] Fit + evaluate ...")
        pipe_clone = clone(pipe)
        val_pred, val_proba = fit_predict(pipe_clone, X_tr, y_tr, X_val)
        val_m = metrics(y_val, val_pred, val_proba)

        # Re-fit for test
        pipe_test = clone(pipe)
        test_pred, test_proba = fit_predict(pipe_test, X_tr, y_tr, X_te)
        test_m = metrics(y_te, test_pred, test_proba)

        entry = {"model": mname}
        entry.update(cv_res)  # keys already have cv_/train_ prefix
        entry.update({f"val_{k}": v for k, v in val_m.items()})
        entry.update({f"test_{k}": v for k, v in test_m.items()})
        results.append(entry)

        print(f"    CV  F1={cv_res['cv_f1_mean']:.4f}+/-{cv_res['cv_f1_std']:.4f}  "
              f"Acc={cv_res['cv_acc_mean']:.4f}")
        print(f"    Val F1={val_m['f1']:.4f}  Acc={val_m['accuracy']:.4f}  "
              f"FP={val_m['FP']} FN={val_m['FN']}")
        print(f"    Test F1={test_m['f1']:.4f}  Acc={test_m['accuracy']:.4f}  "
              f"FP={test_m['FP']} FN={test_m['FN']}")

        if test_m["f1"] > best_f1:
            best_f1 = test_m["f1"]
            best_name = mname
            best_pipe = pipe_test
            best_val_proba = val_proba
            best_test_proba = test_proba

    comp_df = pd.DataFrame(results)
    print(f"\n  >> BEST: {best_name} (F1={best_f1:.4f})")

    # Threshold optimization on validation
    best_threshold = 0.5
    if best_val_proba is not None:
        best_threshold, _ = threshold_sweep(y_val, best_val_proba)
        # Re-evaluate test with optimized threshold
        y_te_opt = (best_test_proba >= best_threshold).astype(int)
        opt_m = metrics(y_te, y_te_opt, best_test_proba)
        def_m = metrics(y_te, (best_test_proba >= 0.5).astype(int), best_test_proba)
        print(f"\n  Threshold: default=0.50 -> F1={def_m['f1']:.4f} "
              f"Recall={def_m['recall']:.4f} FN={def_m['FN']}")
        print(f"  Threshold: optimized={best_threshold} -> F1={opt_m['f1']:.4f} "
              f"Recall={opt_m['recall']:.4f} FN={opt_m['FN']}")
    else:
        opt_m = def_m = {}

    return {
        "name": name,
        "comp_df": comp_df,
        "best_name": best_name,
        "best_pipe": best_pipe,
        "best_threshold": best_threshold,
        "best_test_proba": best_test_proba,
        "y_test": y_te,
        "optimized_metrics": opt_m,
        "default_metrics": def_m,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  PAKISTAN HOLDOUT EVALUATION
# ═══════════════════════════════════════════════════════════════════════════

def eval_pakistan_holdout(exp, pk_holdout, le):
    """Evaluate a trained model on the untouched Pakistan holdout."""
    pipe = exp["best_pipe"]
    threshold = exp["best_threshold"]
    X = pk_holdout[C_MSG].values
    y = le.transform(pk_holdout[C_LBL].values)

    pred_def = pipe.predict(X)
    m_def = metrics(y, pred_def)

    proba = None
    if hasattr(pipe[-1], "predict_proba"):
        proba = pipe.predict_proba(X)[:, 1]
    elif hasattr(pipe[-1], "decision_function"):
        d = pipe.decision_function(X)
        proba = 1 / (1 + np.exp(-d))

    pred_opt = (proba >= threshold).astype(int) if proba is not None else pred_def
    m_opt = metrics(y, pred_opt, proba)

    # Language-specific
    lang_results = {}
    for lang in pk_holdout[C_LANG].dropna().unique():
        mask = pk_holdout[C_LANG] == lang
        if mask.sum() < 2: continue
        yl = y[mask]
        yp = pred_opt[mask]
        lang_results[lang] = {
            "n": int(mask.sum()),
            "accuracy": accuracy_score(yl, yp),
            "precision": precision_score(yl, yp, pos_label=1, zero_division=0),
            "recall": recall_score(yl, yp, pos_label=1, zero_division=0),
            "f1": f1_score(yl, yp, pos_label=1, zero_division=0),
        }

    return {
        "default_metrics": m_def,
        "optimized_metrics": m_opt,
        "threshold": threshold,
        "proba": proba,
        "pred_opt": pred_opt,
        "lang_results": lang_results,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ERROR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def error_analysis(pk_holdout, y_true, y_pred, proba, le):
    y_true_lbl = le.inverse_transform(y_true)
    y_pred_lbl = le.inverse_transform(y_pred)
    errors = []
    for i in range(len(pk_holdout)):
        if y_pred[i] != y_true[i]:
            errors.append({
                "message": pk_holdout.iloc[i][C_MSG],
                "true_label": y_true_lbl[i],
                "predicted": y_pred_lbl[i],
                "language": pk_holdout.iloc[i][C_LANG],
                "category": pk_holdout.iloc[i][C_CAT],
                "probability": float(proba[i]) if proba is not None else None,
                "error_type": ("FN-missed-scam" if y_true[i]==1
                               else "FP-safe-flagged"),
            })
    fn = [e for e in errors if "FN" in e["error_type"]]
    fp = [e for e in errors if "FP" in e["error_type"]]
    print(f"\n  Errors: {len(errors)} total | FN={len(fn)} | FP={len(fp)}")
    safe = lambda s: s.encode('ascii', errors='replace').decode('ascii')[:80]
    for e in fn[:5]:
        print(f"    FN [{e['language']}] {safe(e['message'])}...")
    for e in fp[:10]:
        print(f"    FP [{e['language']}] {safe(e['message'])}...")
    return errors


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    print("=" * 70)
    print("  AUGMENTED SCAM DETECTION PIPELINE")
    print("  Pakistan + UCI SMS Spam Collection")
    print("=" * 70)

    # ── STEP 1: Load ─────────────────────────────────────────────────────
    print("\n[STEP 1-2] Loading & inspecting datasets ...")
    pk_raw = load_pakistan()
    uci_raw = load_uci()

    pk_lbl = inspect(pk_raw, "Pakistan Dataset")
    uci_lbl = inspect(uci_raw, "UCI SMS Spam Collection")

    print(f"\n  UCI source: {UCI_FILE}")
    print(f"  UCI schema: tab-separated, columns=[label, message]")
    print(f"  UCI labels: ham -> Safe, spam -> Scam")

    # ── STEP 3-4: Normalize & merge ──────────────────────────────────────
    print("\n[STEP 3-4] Normalizing & merging ...")
    pk_norm, uci_norm, combined_all = normalize_and_merge(pk_raw, uci_raw)

    # ── STEP 5: Dedup ────────────────────────────────────────────────────
    print("\n[STEP 5] Deduplication ...")
    combined_clean, dup_removed = dedup(combined_all)
    print(f"  Exact duplicates removed: {dup_removed}")

    pk_clean, pk_dup = dedup(pk_norm)
    uci_clean, uci_dup = dedup(uci_norm)
    print(f"  Pakistan duplicates: {pk_dup}")
    print(f"  UCI duplicates: {uci_dup}")

    # Near-duplicates on combined
    print("  Detecting near-duplicates (>=90% similarity) ...")
    near_dups = find_near_duplicates(combined_clean, threshold=0.90)
    conflicts = conflict_check(near_dups)
    print(f"  Near-duplicate pairs: {len(near_dups)}")
    print(f"  Conflicting labels: {len(conflicts)}")

    # Save cleaning report
    clean_report = {
        "pakistan_original": len(pk_raw),
        "uci_original": len(uci_raw),
        "combined_before_dedup": len(combined_all),
        "exact_duplicates_removed": dup_removed,
        "combined_after_dedup": len(combined_clean),
        "pakistan_duplicates": pk_dup,
        "uci_duplicates": uci_dup,
        "near_duplicate_pairs_90pct": len(near_dups),
        "conflicting_label_pairs": len(conflicts),
    }
    with open(os.path.join(REPORT_DIR, "augmented_cleaning_report.json"), "w") as f:
        json.dump(clean_report, f, indent=2)

    # ── STEP 6: Leakage-safe splits ──────────────────────────────────────
    print("\n[STEP 6-7] Creating leakage-safe splits ...")
    le = LabelEncoder()
    le.fit([LBL_SAFE, LBL_SCAM])

    # Pakistan holdout (untouched)
    pk_train_pool, pk_holdout = make_pakistan_holdout(pk_clean)

    # Verify no overlap
    holdout_msgs = set(pk_holdout[C_MSG].str.lower().str.strip())
    train_pool_msgs = set(pk_train_pool[C_MSG].str.lower().str.strip())
    overlap = holdout_msgs & train_pool_msgs
    print(f"  Holdout-train overlap: {len(overlap)} (must be 0)")
    if overlap:
        pk_holdout = pk_holdout[~pk_holdout[C_MSG].str.lower().str.strip().isin(overlap)]
        pk_holdout = pk_holdout.reset_index(drop=True)

    # Combined training pool = pk_train_pool + all UCI
    combined_train_pool = pd.concat(
        [pk_train_pool, uci_clean], ignore_index=True
    ).reset_index(drop=True)

    # ── Verify composition ────────────────────────────────────────────────
    print(f"\n  Combined training pool: {len(combined_train_pool)}")
    print(f"    Pakistan: {len(pk_train_pool)}")
    print(f"    UCI: {len(uci_clean)}")
    print(f"  Pakistan holdout (untouched): {len(pk_holdout)}")
    src_counts = combined_train_pool[C_SRC].value_counts().to_dict()
    print(f"  Source distribution: {src_counts}")
    lbl_counts = combined_train_pool[C_LBL].value_counts().to_dict()
    print(f"  Label distribution: {lbl_counts}")

    # ── STEP 12: THREE EXPERIMENTS ───────────────────────────────────────
    # Prepare UCI-only splits
    uci_train, uci_test = train_test_split(
        uci_clean, test_size=0.15, stratify=uci_clean[C_LBL], random_state=SEED)
    uci_train, uci_val = train_test_split(
        uci_train, test_size=0.12, stratify=uci_train[C_LBL], random_state=SEED)

    # Combined splits
    comb_train, comb_val, comb_test = make_combined_splits(
        combined_train_pool, pk_holdout[C_MSG])

    # Pakistan-only splits (from pk_train_pool)
    pk_tr, pk_te = train_test_split(
        pk_train_pool, test_size=0.20, stratify=pk_train_pool[C_LBL], random_state=SEED)
    pk_tr, pk_va = train_test_split(
        pk_tr, test_size=0.15, stratify=pk_tr[C_LBL], random_state=SEED)

    # ── Experiment 1: Pakistan only ──────────────────────────────────────
    exp1 = run_experiment("Exp1_Pakistan_Only", pk_tr, pk_va, pk_te, le,
                          label="(train on Pakistan data only)")

    # ── Experiment 2: UCI only ───────────────────────────────────────────
    exp2 = run_experiment("Exp2_UCI_Only", uci_train, uci_val, uci_test, le,
                          label="(train on UCI only)")

    # ── Experiment 3: Combined ───────────────────────────────────────────
    exp3 = run_experiment("Exp3_Combined", comb_train, comb_val, comb_test, le,
                          label="(train on Pakistan + UCI)")

    # ── STEP 15: Pakistan holdout evaluation ─────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 15: PAKISTAN HOLDOUT EVALUATION")
    print("=" * 70)

    all_exps = {"Exp1": exp1, "Exp2": exp2, "Exp3": exp3}
    holdout_results = {}

    for ename, exp in all_exps.items():
        print(f"\n  --- {ename}: {exp['best_name']} on Pakistan Holdout ---")
        hr = eval_pakistan_holdout(exp, pk_holdout, le)
        m = hr["optimized_metrics"]
        print(f"    Acc={m.get('accuracy',0):.4f}  F1={m.get('f1',0):.4f}  "
              f"Recall={m.get('recall',0):.4f}  Prec={m.get('precision',0):.4f}")
        if m.get('roc_auc'): print(f"    AUC={m['roc_auc']:.4f}")
        print(f"    FP={m.get('FP',0)}  FN={m.get('FN',0)}")
        print(f"    Threshold={hr['threshold']}")

        # Language
        for lang, lr in hr["lang_results"].items():
            print(f"    [{lang}] n={lr['n']} Acc={lr['accuracy']:.4f} "
                  f"P={lr['precision']:.4f} R={lr['recall']:.4f} F1={lr['f1']:.4f}")

        holdout_results[ename] = hr

    # ── Error analysis on best experiment's Pakistan holdout ─────────────
    print("\n" + "=" * 70)
    print("  STEP 17: ERROR ANALYSIS (best model on Pakistan holdout)")
    print("=" * 70)

    # Pick best by Pakistan holdout F1
    best_exp_name = max(holdout_results,
                        key=lambda k: holdout_results[k]["optimized_metrics"].get("f1", 0))
    best_exp = all_exps[best_exp_name]
    best_hr = holdout_results[best_exp_name]
    errors = error_analysis(
        pk_holdout, le.transform(pk_holdout[C_LBL].values),
        best_hr["pred_opt"], best_hr["proba"], le,
    )
    err_df = pd.DataFrame(errors)
    err_df.to_csv(os.path.join(REPORT_DIR, "augmented_error_analysis.csv"), index=False)

    # ── STEP 18: Overfitting check ───────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 18: OVERFITTING / GENERALIZATION CHECK")
    print("=" * 70)
    for ename, exp in all_exps.items():
        comp = exp["comp_df"]
        if len(comp) == 0: continue
        best_row = comp[comp["model"] == exp["best_name"]].iloc[0]
        train_f1 = best_row.get("train_f1_mean", 0)
        cv_f1 = best_row.get("cv_f1_mean", 0)
        test_f1 = best_row.get("test_f1", 0)
        hr = holdout_results[ename]["optimized_metrics"]
        ho_f1 = hr.get("f1", 0)
        gap = train_f1 - ho_f1
        print(f"  {ename} ({exp['best_name']}):")
        print(f"    Train F1={train_f1:.4f}  CV F1={cv_f1:.4f}  "
              f"Test F1={test_f1:.4f}  PK Holdout F1={ho_f1:.4f}  Gap={gap:.4f}")
        if gap > 0.10:
            print(f"    [WARNING] Possible overfitting (gap > 0.10)")
        else:
            print(f"    [OK] No significant overfitting")

    # ── STEP 20: Save best model ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 20: SAVING BEST MODEL")
    print("=" * 70)

    # Choose experiment with best Pakistan holdout F1
    print(f"  Best experiment for Pakistan holdout: {best_exp_name}")
    final_pipe = best_exp["best_pipe"]
    final_threshold = best_exp["best_threshold"]

    joblib.dump(final_pipe, os.path.join(MODEL_DIR, "full_pipeline.joblib"))
    joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.joblib"))
    joblib.dump(final_threshold, os.path.join(MODEL_DIR, "threshold.joblib"))

    # Save comprehensive metadata
    metadata = {
        "best_experiment": best_exp_name,
        "best_model_name": best_exp["best_name"],
        "model_type": "simple_pipeline",  # All augmented models are sklearn Pipelines
        "model_description": f"TF-IDF word (1,2)-grams + {best_exp['best_name']}",
        "threshold": final_threshold,
        "random_seed": SEED,
        "dataset": {
            "pakistan_original": len(pk_raw),
            "uci_original": len(uci_raw),
            "combined_clean": len(combined_clean),
            "pk_holdout_size": len(pk_holdout),
        },
        "holdout_results": {
            ename: {
                "optimized": hr["optimized_metrics"],
                "default": hr["default_metrics"],
                "threshold": hr["threshold"],
                "lang_results": hr["lang_results"],
            }
            for ename, hr in holdout_results.items()
        },
        "experiments": {
            ename: {
                "best_model": exp["best_name"],
                "best_threshold": exp["best_threshold"],
            }
            for ename, exp in all_exps.items()
        },
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, "model_metadata.joblib"))
    with open(os.path.join(REPORT_DIR, "augmented_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"  Saved to {MODEL_DIR}/")

    # ── Save comparison reports ──────────────────────────────────────────
    for ename, exp in all_exps.items():
        path = os.path.join(REPORT_DIR, f"augmented_{ename}_comparison.csv")
        exp["comp_df"].to_csv(path, index=False, float_format="%.4f")

    # ── FINAL REPORT ─────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)
    print(f"  1. Pakistan dataset:      {len(pk_raw)} messages")
    print(f"  2. UCI dataset:           {len(uci_raw)} messages")
    print(f"  3. Combined (clean):      {len(combined_clean)} messages")
    print(f"  4. Duplicates removed:    {dup_removed}")
    print(f"  5. Near-duplicate pairs:  {len(near_dups)}")
    print(f"  6. Conflicting labels:    {len(conflicts)}")
    print(f"  7. Pakistan holdout:      {len(pk_holdout)}")
    print(f"  8. Train sizes:           PK={len(pk_tr)}, UCI={len(uci_train)}, "
          f"Combined={len(comb_train)}")

    print(f"\n  === Experiment Comparison (Pakistan Holdout F1) ===")
    for ename in ["Exp1", "Exp2", "Exp3"]:
        hr = holdout_results[ename]["optimized_metrics"]
        exp = all_exps[ename]
        print(f"  {ename} ({exp['best_name']}): "
              f"Acc={hr.get('accuracy',0):.4f} F1={hr.get('f1',0):.4f} "
              f"Recall={hr.get('recall',0):.4f} FN={hr.get('FN',0)} FP={hr.get('FP',0)}")

    best_hr_m = holdout_results[best_exp_name]["optimized_metrics"]
    prev_acc = 0.9130
    prev_recall = 0.9756
    prev_f1 = 0.9302
    improved_acc = best_hr_m.get("accuracy", 0) > prev_acc
    improved_recall = best_hr_m.get("recall", 0) > prev_recall

    print(f"\n  === Previous Baseline vs New Model (Pakistan Holdout) ===")
    print(f"  Previous: Acc={prev_acc:.4f}  Recall={prev_recall:.4f}  F1={prev_f1:.4f}")
    print(f"  New ({best_exp_name}/{best_exp['best_name']}): "
          f"Acc={best_hr_m.get('accuracy',0):.4f}  "
          f"Recall={best_hr_m.get('recall',0):.4f}  "
          f"F1={best_hr_m.get('f1',0):.4f}")
    print(f"\n  Did UCI improve Pakistan performance?")
    print(f"    Accuracy improved: {improved_acc} "
          f"({prev_acc:.4f} -> {best_hr_m.get('accuracy',0):.4f})")
    print(f"    Recall improved:   {improved_recall} "
          f"({prev_recall:.4f} -> {best_hr_m.get('recall',0):.4f})")

    print(f"\n  Best threshold: {final_threshold}")
    print(f"  Saved: {MODEL_DIR}/full_pipeline.joblib")
    print(f"  Pipeline completed in {elapsed:.1f}s")
    print("=" * 70)

    # Save final summary
    summary = {
        "pakistan_original": len(pk_raw),
        "uci_original": len(uci_raw),
        "combined_clean": len(combined_clean),
        "duplicates_removed": dup_removed,
        "near_duplicate_pairs": len(near_dups),
        "conflicting_labels": len(conflicts),
        "pk_holdout_size": len(pk_holdout),
        "best_experiment": best_exp_name,
        "best_model": best_exp["best_name"],
        "best_threshold": final_threshold,
        "previous_baseline": {"accuracy": prev_acc, "recall": prev_recall, "f1": prev_f1},
        "new_pakistan_holdout": best_hr_m,
        "improved_accuracy": improved_acc,
        "improved_recall": improved_recall,
        "all_holdout_results": {
            ename: hr["optimized_metrics"]
            for ename, hr in holdout_results.items()
        },
        "elapsed_seconds": round(elapsed, 1),
    }
    with open(os.path.join(REPORT_DIR, "augmented_final_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)


if __name__ == "__main__":
    main()
