"""
STEP 3  — Data Splitting
STEP 5  — Build Strong Baseline Models
STEP 7  — Hyperparameter Optimization
"""
import os
import numpy as np
import pandas as pd
from scipy.sparse import hstack, issparse, csr_matrix

from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_validate,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import LinearSVC
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import make_scorer, f1_score, precision_score, recall_score, roc_auc_score

from src.config import (
    COL_MESSAGE, COL_LANGUAGE, COL_LABEL, LABEL_SCAM,
    RANDOM_SEED, N_FOLDS, TEST_SIZE, VAL_SIZE,
)
from src.preprocessing import ScamTextNormalizer
from src.features import ScamFeatureExtractor


# ──────────────────────────────────────────────────────────────────────────────
# Custom scorer for scam recall (positive class = 1 = Scam)
# ──────────────────────────────────────────────────────────────────────────────
scam_recall_scorer = make_scorer(recall_score, pos_label=1)
scam_precision_scorer = make_scorer(precision_score, pos_label=1)
scam_f1_scorer = make_scorer(f1_score, pos_label=1)
roc_auc_scorer = make_scorer(roc_auc_score, needs_proba=True)

SCORING = {
    "accuracy": "accuracy",
    "f1": scam_f1_scorer,
    "recall": scam_recall_scorer,
    "precision": scam_precision_scorer,
    "roc_auc": roc_auc_scorer,
}


# ──────────────────────────────────────────────────────────────────────────────
def split_data(df: pd.DataFrame):
    """
    Stratified train/val/test split.
    Test set is held out completely untouched.
    """
    # First split: separate test set
    trainval_df, test_df = train_test_split(
        df, test_size=TEST_SIZE, stratify=df[COL_LABEL],
        random_state=RANDOM_SEED,
    )
    # Second split: separate validation from train
    train_df, val_df = train_test_split(
        trainval_df, test_size=VAL_SIZE,
        stratify=trainval_df[COL_LABEL],
        random_state=RANDOM_SEED,
    )
    print(f"[SPLIT] Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    return train_df, val_df, test_df


# ──────────────────────────────────────────────────────────────────────────────
def _build_tfidf_pipeline_word():
    """TF-IDF word n-grams + Logistic Regression."""
    return Pipeline([
        ("normalizer", ScamTextNormalizer()),
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            max_features=10000,
            strip_accents="unicode",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            solver="lbfgs",
        )),
    ])


def _build_tfidf_pipeline_svm():
    """TF-IDF word n-grams + Linear SVM."""
    return Pipeline([
        ("normalizer", ScamTextNormalizer()),
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            max_features=10000,
        )),
        ("clf", LinearSVC(
            max_iter=5000,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            dual="auto",
        )),
    ])


def _build_char_tfidf_pipeline():
    """TF-IDF character n-grams + Logistic Regression."""
    return Pipeline([
        ("normalizer", ScamTextNormalizer()),
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 6),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            max_features=15000,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_SEED,
        )),
    ])


class _CombinedVectorizer(Pipeline):
    """Helper: fit/transform two vectorizers and hstack the result."""

    def __init__(self, word_vec, char_vec):
        self.word_vec = word_vec
        self.char_vec = char_vec

    def fit(self, X, y=None):
        self.word_vec.fit(X, y)
        self.char_vec.fit(X, y)
        return self

    def transform(self, X, y=None):
        w = self.word_vec.transform(X)
        c = self.char_vec.transform(X)
        return hstack([w, c])

    def get_feature_names_out(self, input_features=None):
        return np.concatenate([
            self.word_vec.get_feature_names_out(),
            self.char_vec.get_feature_names_out(),
        ])


def _build_combined_tfidf_pipeline():
    """Combined word + character TF-IDF + Logistic Regression."""
    normalizer = ScamTextNormalizer()
    word_vec = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_df=0.95,
        sublinear_tf=True, max_features=8000,
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=2,
        max_df=0.95, sublinear_tf=True, max_features=8000,
    )

    return {
        "normalizer": normalizer,
        "vectorizer": _CombinedVectorizer(word_vec, char_vec),
        "clf": LogisticRegression(
            max_iter=1000, class_weight="balanced",
            random_state=RANDOM_SEED,
        ),
    }


class _FeatureUnionPipeline:
    """
    Combines TF-IDF features + engineered numeric features.
    We build this as a manual two-step pipeline because FeatureUnion
    with mixed sparse/dense requires careful handling.
    """
    pass


def _build_engineered_pipeline():
    """TF-IDF + engineered scam-indicator features + GradientBoosting."""
    normalizer = ScamTextNormalizer()
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_df=0.95,
        sublinear_tf=True, max_features=6000,
    )
    feat_extractor = ScamFeatureExtractor()
    clf = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        subsample=0.8, random_state=RANDOM_SEED,
    )
    return {
        "normalizer": normalizer,
        "tfidf": tfidf,
        "feature_extractor": feat_extractor,
        "clf": clf,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Candidate model configurations
# ──────────────────────────────────────────────────────────────────────────────

MODEL_CONFIGS = {
    "A_tfidf_word_lr": {
        "type": "simple_pipeline",
        "builder": _build_tfidf_pipeline_word,
        "description": "TF-IDF word (1,2)-grams + Logistic Regression",
    },
    "B_tfidf_word_svm": {
        "type": "simple_pipeline",
        "builder": _build_tfidf_pipeline_svm,
        "description": "TF-IDF word (1,2)-grams + Linear SVM",
    },
    "C_tfidf_char_lr": {
        "type": "simple_pipeline",
        "builder": _build_char_tfidf_pipeline,
        "description": "TF-IDF char (3-6)-grams + Logistic Regression",
    },
    "D_combined_tfidf_lr": {
        "type": "combined",
        "builder": _build_combined_tfidf_pipeline,
        "description": "Combined word+char TF-IDF + Logistic Regression",
    },
    "E_engineered_gb": {
        "type": "engineered",
        "builder": _build_engineered_pipeline,
        "description": "TF-IDF + engineered features + GradientBoosting",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Cross-validation runner
# ──────────────────────────────────────────────────────────────────────────────

def cross_validate_simple_pipeline(pipe, X_texts, y_labels, cv=None):
    """Run stratified k-fold CV on a simple sklearn Pipeline."""
    if cv is None:
        cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    results = cross_validate(
        pipe, X_texts, y_labels,
        cv=cv, scoring=SCORING,
        return_train_score=True,
        n_jobs=-1,
    )
    return results


def cross_validate_combined(components, X_texts, y_labels, cv=None):
    """CV for combined vectorizer pipeline."""
    if cv is None:
        cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    skf = cv
    metrics = {k: [] for k in ["accuracy", "f1", "recall", "precision", "roc_auc"]}
    train_metrics = {k: [] for k in metrics}

    for train_idx, test_idx in skf.split(X_texts, y_labels):
        X_tr = X_texts[train_idx]
        X_te = X_texts[test_idx]
        y_tr = y_labels[train_idx]
        y_te = y_labels[test_idx]

        # Fresh components each fold
        parts = components["builder"]()
        norm = parts["normalizer"]
        vec = parts["vectorizer"]
        clf = parts["clf"]

        X_tr_norm = norm.transform(X_tr)
        X_te_norm = norm.transform(X_te)

        vec.fit(X_tr_norm)
        X_tr_vec = vec.transform(X_tr_norm)
        X_te_vec = vec.transform(X_te_norm)

        from sklearn.base import clone
        clf_fold = clone(clf)
        clf_fold.fit(X_tr_vec, y_tr)

        from sklearn.metrics import (
            accuracy_score, f1_score, precision_score,
            recall_score, roc_auc_score,
        )
        y_pred = clf_fold.predict(X_te_vec)
        y_proba = clf_fold.predict_proba(X_te_vec)[:, 1] if hasattr(clf_fold, "predict_proba") else None

        metrics["accuracy"].append(accuracy_score(y_te, y_pred))
        metrics["f1"].append(f1_score(y_te, y_pred, pos_label=1))
        metrics["recall"].append(recall_score(y_te, y_pred, pos_label=1))
        metrics["precision"].append(precision_score(y_te, y_pred, pos_label=1))
        if y_proba is not None:
            metrics["roc_auc"].append(roc_auc_score(y_te, y_proba))

        # Train metrics
        y_pred_tr = clf_fold.predict(X_tr_vec)
        y_proba_tr = clf_fold.predict_proba(X_tr_vec)[:, 1] if hasattr(clf_fold, "predict_proba") else None
        train_metrics["accuracy"].append(accuracy_score(y_tr, y_pred_tr))
        train_metrics["f1"].append(f1_score(y_tr, y_pred_tr, pos_label=1))
        train_metrics["recall"].append(recall_score(y_tr, y_pred_tr, pos_label=1))
        train_metrics["precision"].append(precision_score(y_tr, y_pred_tr, pos_label=1))
        if y_proba_tr is not None:
            train_metrics["roc_auc"].append(roc_auc_score(y_tr, y_proba_tr))

    results = {}
    for k in metrics:
        vals = metrics[k]
        results[f"test_{k}"] = vals
        results[f"test_{k}_mean"] = np.mean(vals) if vals else 0
        results[f"test_{k}_std"] = np.std(vals) if vals else 0
        tr_vals = train_metrics[k]
        results[f"train_{k}_mean"] = np.mean(tr_vals) if tr_vals else 0

    return results


def cross_validate_engineered(components, X_texts, y_labels, cv=None):
    """CV for engineered features + TF-IDF pipeline."""
    if cv is None:
        cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    skf = cv
    metrics = {k: [] for k in ["accuracy", "f1", "recall", "precision", "roc_auc"]}
    train_metrics = {k: [] for k in metrics}

    for train_idx, test_idx in skf.split(X_texts, y_labels):
        X_tr = X_texts[train_idx]
        X_te = X_texts[test_idx]
        y_tr = y_labels[train_idx]
        y_te = y_labels[test_idx]

        parts = components["builder"]()
        norm = parts["normalizer"]
        tfidf = parts["tfidf"]
        feat_ext = parts["feature_extractor"]
        clf = parts["clf"]

        X_tr_norm = norm.transform(X_tr)
        X_te_norm = norm.transform(X_te)

        # TF-IDF
        from sklearn.base import clone
        tfidf_fold = clone(tfidf)
        X_tr_tfidf = tfidf_fold.fit_transform(X_tr_norm)
        X_te_tfidf = tfidf_fold.transform(X_te_norm)

        # Engineered features
        feat_fold = clone(feat_ext)
        X_tr_eng = feat_fold.fit_transform(X_tr)  # on raw text
        X_te_eng = feat_fold.transform(X_te)

        # Combine: convert TF-IDF to dense, concat with engineered
        from scipy.sparse import issparse
        X_tr_tfidf_dense = X_tr_tfidf.toarray() if issparse(X_tr_tfidf) else X_tr_tfidf
        X_te_tfidf_dense = X_te_tfidf.toarray() if issparse(X_te_tfidf) else X_te_tfidf
        X_tr_combined = np.hstack([X_tr_tfidf_dense, X_tr_eng])
        X_te_combined = np.hstack([X_te_tfidf_dense, X_te_eng])

        clf_fold = clone(clf)
        clf_fold.fit(X_tr_combined, y_tr)

        from sklearn.metrics import (
            accuracy_score, f1_score, precision_score,
            recall_score, roc_auc_score,
        )
        y_pred = clf_fold.predict(X_te_combined)
        y_proba = clf_fold.predict_proba(X_te_combined)[:, 1] if hasattr(clf_fold, "predict_proba") else None

        metrics["accuracy"].append(accuracy_score(y_te, y_pred))
        metrics["f1"].append(f1_score(y_te, y_pred, pos_label=1))
        metrics["recall"].append(recall_score(y_te, y_pred, pos_label=1))
        metrics["precision"].append(precision_score(y_te, y_pred, pos_label=1))
        if y_proba is not None:
            metrics["roc_auc"].append(roc_auc_score(y_te, y_proba))

        y_pred_tr = clf_fold.predict(X_tr_combined)
        y_proba_tr = clf_fold.predict_proba(X_tr_combined)[:, 1] if hasattr(clf_fold, "predict_proba") else None
        train_metrics["accuracy"].append(accuracy_score(y_tr, y_pred_tr))
        train_metrics["f1"].append(f1_score(y_tr, y_pred_tr, pos_label=1))
        train_metrics["recall"].append(recall_score(y_tr, y_pred_tr, pos_label=1))
        train_metrics["precision"].append(precision_score(y_tr, y_pred_tr, pos_label=1))
        if y_proba_tr is not None:
            train_metrics["roc_auc"].append(roc_auc_score(y_tr, y_proba_tr))

    results = {}
    for k in metrics:
        vals = metrics[k]
        results[f"test_{k}"] = vals
        results[f"test_{k}_mean"] = np.mean(vals) if vals else 0
        results[f"test_{k}_std"] = np.std(vals) if vals else 0
        tr_vals = train_metrics[k]
        results[f"train_{k}_mean"] = np.mean(tr_vals) if tr_vals else 0

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Train all candidates
# ──────────────────────────────────────────────────────────────────────────────

def train_all(train_df: pd.DataFrame, le: LabelEncoder) -> dict:
    """
    Train and cross-validate all candidate models.
    Returns a dict of {model_name: cv_results}.
    """
    X_texts = train_df[COL_MESSAGE].values
    y_labels = le.transform(train_df[COL_LABEL].values)

    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    all_results = {}

    for name, config in MODEL_CONFIGS.items():
        print(f"\n[TRAIN] Training {name}: {config['description']} ...")

        if config["type"] == "simple_pipeline":
            pipe = config["builder"]()
            results = cross_validate_simple_pipeline(pipe, X_texts, y_labels, cv)
            # Summarize
            summary = {}
            for metric in ["accuracy", "f1", "recall", "precision", "roc_auc"]:
                test_key = f"test_{metric}"
                vals = results[test_key]
                summary[f"cv_{metric}_mean"] = float(np.mean(vals))
                summary[f"cv_{metric}_std"] = float(np.std(vals))
                summary[f"train_{metric}_mean"] = float(np.mean(results[f"train_{metric}"]))
            all_results[name] = summary

        elif config["type"] == "combined":
            results = cross_validate_combined(config, X_texts, y_labels, cv)
            summary = {}
            for metric in ["accuracy", "f1", "recall", "precision", "roc_auc"]:
                summary[f"cv_{metric}_mean"] = float(results[f"test_{metric}_mean"])
                summary[f"cv_{metric}_std"] = float(results[f"test_{metric}_std"])
                summary[f"train_{metric}_mean"] = float(results[f"train_{metric}_mean"])
            all_results[name] = summary

        elif config["type"] == "engineered":
            results = cross_validate_engineered(config, X_texts, y_labels, cv)
            summary = {}
            for metric in ["accuracy", "f1", "recall", "precision", "roc_auc"]:
                summary[f"cv_{metric}_mean"] = float(results[f"test_{metric}_mean"])
                summary[f"cv_{metric}_std"] = float(results[f"test_{metric}_std"])
                summary[f"train_{metric}_mean"] = float(results[f"train_{metric}_mean"])
            all_results[name] = summary

        s = all_results[name]
        print(f"  CV F1={s['cv_f1_mean']:.4f}+/-{s['cv_f1_std']:.4f}  "
              f"Acc={s['cv_accuracy_mean']:.4f}  "
              f"Recall={s['cv_recall_mean']:.4f}  "
              f"AUC={s['cv_roc_auc_mean']:.4f}")

    return all_results
