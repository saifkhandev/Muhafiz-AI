"""
STEP 6 — Feature Engineering
Non-leaky engineered features derived ONLY from Message Content.
"""
import re
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from src.preprocessing import (
    URGENCY_KEYWORDS, FINANCIAL_KEYWORDS, CREDENTIAL_KEYWORDS,
    PRIZE_KEYWORDS, THREAT_KEYWORDS, OTP_KEYWORDS, has_urdu,
    ALL_LEGIT_BRANDS, DO_NOT_SHARE_PATTERNS, TXN_ID_PATTERNS,
)


# ──────────────────────────────────────────────────────────────────────────────
class ScamFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extract engineered scam-indicator features from raw message text.

    All features are derived only from the message text itself (no label info).
    Returns a numeric feature matrix.
    """

    FEATURE_NAMES = [
        "msg_length",
        "word_count",
        "avg_word_length",
        "digit_count",
        "digit_ratio",
        "uppercase_ratio",
        "exclamation_count",
        "question_count",
        "url_count",
        "phone_pattern_count",
        "currency_count",
        "percentage_count",
        "repeated_char_ratio",
        "caps_word_ratio",
        "urgency_score",
        "financial_score",
        "credential_score",
        "prize_score",
        "threat_score",
        "otp_score",
        "has_url",
        "has_phone",
        "has_currency",
        "has_percentage",
        "has_code_placeholder",
        "has_money_placeholder",
        "suspicious_domain_count",
        "shortened_url_count",
        "request_money_score",
        "urgency_threat_combined",
        "has_urdu_script",
        "total_scam_keyword_score",
        # --- NEW FEATURES (Phase 2 optimization) ---
        "has_legit_brand",
        "has_txn_id",
        "has_receipt_pattern",
        "has_do_not_share",
        "money_request_score",
        "personal_tone_score",
        "is_service_notification",
    ]

    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        rows = []
        for text in X:
            rows.append(self._extract(str(text)))
        return np.array(rows)

    def get_feature_names_out(self, input_features=None):
        return np.array(self.FEATURE_NAMES)

    # ── internal extraction ──────────────────────────────────────────────
    def _extract(self, text: str) -> list:
        t = text.strip()
        t_lower = t.lower()

        # Basic text stats
        msg_length = len(t)
        words = t.split()
        word_count = len(words)
        avg_word_len = (
            np.mean([len(w) for w in words]) if word_count > 0 else 0.0
        )

        # Character-level stats
        digit_count = sum(c.isdigit() for c in t)
        digit_ratio = digit_count / max(msg_length, 1)
        upper_count = sum(c.isupper() for c in t)
        uppercase_ratio = upper_count / max(msg_length, 1)

        # Punctuation counts
        excl_count = t.count("!") + t.count("！")
        ques_count = t.count("?") + t.count("؟")

        # Pattern counts
        urls = re.findall(r"https?://\S+", t_lower)
        url_count = len(urls)
        phone_patterns = len(
            re.findall(r"(\+?92[-\s]?)?0?3\d{2}[-\s]?\d{7}", t)
        )
        currency_matches = len(
            re.findall(
                r"(?:rs\.?|₨)\s*[\d,]+|\$\s*[\d,]+|£\s*[\d,]+",
                t_lower,
            )
        )
        pct_count = len(re.findall(r"\d+\.?\d*\s*%", t))

        # Repeated character patterns (e.g., "freeeee", "!!!!", "??")
        repeated = len(re.findall(r"(.)\1{3,}", t))
        repeated_char_ratio = repeated / max(word_count, 1)

        # ALL-CAPS words ratio
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 1)
        caps_word_ratio = caps_words / max(word_count, 1)

        # Keyword scores (normalized by message length)
        urgency_score = self._keyword_score(t_lower, URGENCY_KEYWORDS)
        financial_score = self._keyword_score(t_lower, FINANCIAL_KEYWORDS)
        credential_score = self._keyword_score(t_lower, CREDENTIAL_KEYWORDS)
        prize_score = self._keyword_score(t_lower, PRIZE_KEYWORDS)
        threat_score = self._keyword_score(t_lower, THREAT_KEYWORDS)
        otp_score = self._keyword_score(t_lower, OTP_KEYWORDS)

        # Binary flags
        has_url = int(url_count > 0 or "__url__" in t_lower)
        has_phone = int(phone_patterns > 0 or "__phone__" in t_lower)
        has_currency = int(currency_matches > 0 or "__money__" in t_lower)
        has_pct = int(pct_count > 0 or "__percent__" in t_lower)
        has_code = int("__code__" in t_lower)
        has_money_tag = int("__money__" in t_lower or "__usd__" in t_lower or "__gbp__" in t_lower)

        # Suspicious / shortened URL domains
        suspicious_domains = [
            "bit.ly", "tinyurl", "goo.gl", "t.co", "ow.ly", "is.gd",
            "buff.ly", "rebrand.ly", "cutt.ly",
        ]
        susp_domain_count = sum(
            1 for d in suspicious_domains if d in t_lower
        )

        # Non-standard domains that look suspicious
        weird_domains = re.findall(
            r"https?://(?:www\.)?([a-z0-9-]+\.[a-z]{2,4})",
            t_lower,
        )
        # Count short or suspicious-looking domains
        shortened_url_count = sum(
            1 for url in urls
            if any(d in url for d in suspicious_domains)
        )

        # Money-request indicators
        money_request_patterns = [
            r"(?:send|bhej|transfer|deposit|pay|collect)\s*(?:me|us|rs|now)?",
            r"(?:fee|charges|payment|deposit)\s*(?:bhej|send|pay|den|dein|karein)",
            r"(?:amount|pais[ea]|raqu|رقم)\s*(?:send|bhej|transfer|بھیجیں)",
        ]
        request_money_score = sum(
            1 for p in money_request_patterns
            if re.search(p, t_lower)
        )

        # Urgency + threat combined
        urgency_threat_combined = int(urgency_score > 0 and threat_score > 0)

        # Urdu script presence
        has_urdu_script = int(has_urdu(t))

        # Total scam keyword score
        total_score = (
            urgency_score
            + financial_score
            + credential_score
            + prize_score
            + threat_score
            + otp_score
        )

        # --- NEW FEATURES (Phase 2 optimization) ---
        # Known legitimate brand/service present
        has_legit_brand = int(
            any(brand in t_lower for brand in ALL_LEGIT_BRANDS)
        )

        # Transaction ID pattern present
        has_txn_id = int(
            any(p in t_lower for p in TXN_ID_PATTERNS)
        )

        # Receipt/confirmation language
        receipt_keywords = [
            "successfully", "confirmed", "completed", "delivered",
            "generated", "receipt", "statement", "reminder",
            "successfully sent", "successfully received",
            "activate ho gaya", "complete ho gaya", "confirm ho gaya",
            "generate ho gaya", "dispatch ho gaya",
            "\u0645\u06a9\u0645\u0644", "\u06a9\u0627\u0645\u06cc\u0627\u0628\u06cc",
            "\u0648\u0635\u0648\u0644", "\u062a\u0635\u062f\u06cc\u0642",
        ]
        has_receipt_pattern = int(
            any(kw in t_lower for kw in receipt_keywords)
        )

        # "Do not share" warning present (strong safe signal)
        has_do_not_share = int(
            any(p in t_lower for p in DO_NOT_SHARE_PATTERNS)
        )

        # Explicit money request intensity
        money_req_patterns = [
            r"(?:send|bhej|transfer|deposit|pay)\s+(?:me|us|rs|now|karo|karein)",
            r"(?:fee|charges|payment)\s+(?:bhej|send|pay|karein|den)",
            r"(?:amount|pais[ea]|raqu)\s+(?:send|bhej|transfer)",
            r"(?:rs\.?|\u20a8)\s*[\d,]+\s+(?:bhej|send|transfer|deposit|pay)",
            r"(?:mujhe|humko|humien)\s+(?:rs|pais[ea])\s*[\d,]*\s*(?:bhej|send|chahiye)",
            r"(?:account|account)\s+(?:mein|par|ko)\s+(?:transfer|bhej)",
        ]
        money_request_score = sum(
            1 for p in money_req_patterns if re.search(p, t_lower)
        )

        # Personal/informal tone indicators
        personal_patterns = [
            r"\b(?:beta|bhai|baji|ammi|papa|chacha|mama|phupho|khala|dadi|nani|uncle|aunty)\b",
            r"\b(?:dear|sis|bro|mom|dad|friend|cousin)\b",
            r"\b(?:yaar|bhaijan|bhabi|bhanja|bhatiji)\b",
            r"(?:dinner|lunch|chai|biryani|khana|kheer|pakode)",
            r"(?:gym|cricket|movie|mehndi|walima|eid)",
        ]
        personal_tone_score = sum(
            1 for p in personal_patterns if re.search(p, t_lower)
        )

        # Service notification pattern (informational, not requesting action)
        service_patterns = [
            r"(?:activated|renewed|completed|delivered|confirmed|generated|dispatched)",
            r"(?:charges?|fare|bill)\s*(?::|\s)\s*rs",
            r"(?:valid\s+for|validity|due\s+date|next\s+billing)",
            r"(?:rate\s+your|rider|driver|tracking|receipt)",
            r"(?:activate ho gaya|complete ho gaya|confirm ho gaya)",
            r"(?:generate ho gaya|dispatch ho gaya|renew ho gaya)",
            r"(?:\*\d+#|dial\s+\*)",  # USSD codes (legit telecom)
        ]
        is_service_notification = sum(
            1 for p in service_patterns if re.search(p, t_lower)
        )

        return [
            msg_length, word_count, avg_word_len,
            digit_count, digit_ratio, uppercase_ratio,
            excl_count, ques_count,
            url_count, phone_patterns, currency_matches, pct_count,
            repeated_char_ratio, caps_word_ratio,
            urgency_score, financial_score, credential_score,
            prize_score, threat_score, otp_score,
            has_url, has_phone, has_currency, has_pct,
            has_code, has_money_tag,
            susp_domain_count, shortened_url_count,
            request_money_score, urgency_threat_combined,
            has_urdu_script, total_score,
            # NEW features
            has_legit_brand, has_txn_id, has_receipt_pattern,
            has_do_not_share, money_request_score,
            personal_tone_score, is_service_notification,
        ]

    @staticmethod
    def _keyword_score(text_lower: str, keywords: list) -> int:
        """Count how many keywords from a list appear in the text."""
        return sum(1 for kw in keywords if kw in text_lower)
