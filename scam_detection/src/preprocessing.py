"""
STEP 4 — Text Preprocessing Pipeline
Designed for multilingual scam detection (English, Roman Urdu, Urdu, Mixed).

Key principle: DO NOT remove scam-signal patterns (URLs, phone numbers,
currency amounts, OTP terms, etc.). These are predictive features.
"""
import re
import unicodedata
from sklearn.base import BaseEstimator, TransformerMixin


# ──────────────────────────────────────────────────────────────────────────────
# Scam-indicator keyword lists (multilingual)
# ──────────────────────────────────────────────────────────────────────────────

URGENCY_KEYWORDS = [
    # English
    "urgent", "immediately", "now", "hurry", "quick", "fast", "today",
    "tonight", "deadline", "expire", "expires", "limited", "last chance",
    "act now", "don't wait", "time sensitive", "right away", "asap",
    "final warning", "final notice", "last opportunity",
    # Roman Urdu
    "abhi", "foran", "jaldi", "fauran", "turant", "bina deri",
    "aaj hi", "kal tak", "sirf aaj", "waqt khatam", "jaldi karein",
    "fora", "abhi karein", "der na karein",
    # Urdu
    "فوری", "ابھی", "جلدی", "فورا", "آج ہی", "آخری موقع", "ابھی کریں",
]

FINANCIAL_KEYWORDS = [
    # English
    "rs", "rupees", "rs.", "amount", "payment", "transfer", "deposit",
    "fee", "charges", "bank", "account", "credit card", "debit card",
    "loan", "investment", "profit", "return", "interest", "money",
    "send money", "pay", "cash", "balance", "withdraw", "transaction",
    "cheque", "check", "fund", "refund", "tax",
    # Roman Urdu
    "paise", "raqu", "paisa", " Jama", "jama", "bhejein", "bhejo",
    "raqu bhejein", "transfer karein", "fee bhejein", " Jama karwayein",
    "qarz", "munafa", "munafah",
    # Urdu
    "روپے", "رقم", "ادائیگی", "فیس", "بینک", "اکاؤنٹ", "منتقلی",
    "جمع", "منافع", "قرض", "ٹیکس", "بیلنس",
]

CREDENTIAL_KEYWORDS = [
    # English
    "password", "pin", "cn ic", "cnic", "otp", "code", "verify",
    "verification", "login", "username", "credential", "identity",
    "personal information", "date of birth", "dob",
    # Roman Urdu
    "cnic", "password", "pin", "code", "verify", "verification",
    "login", "details share karein", "details batayein", "maloomat",
    # Urdu
    "پاس ورڈ", "پن", "شناختی کارڈ", "تصدیق", "کوڈ", "لاگ ان",
    "تفصیلات",
]

PRIZE_KEYWORDS = [
    # English
    "winner", "won", "prize", "reward", "lucky", "lottery",
    "congratulations", "selected", "free", "gift", "bonus",
    "draw", "jackpot", "cashback",
    # Roman Urdu
    "jeet", "inaam", "mubarak", "qur'a andazi", "qura andazi",
    "lucky draw", "free", "inam", "prize", "congratulations",
    "mubarak ho", "naseeb",
    # Urdu
    "انعام", "مبارک", "قرعہ اندازی", "جیت", "مفت", "انعام",
    "خوشخبری",
]

THREAT_KEYWORDS = [
    # English
    "block", "blocked", "suspend", "suspended", "freeze", "frozen",
    "deactivate", "terminate", "legal action", "police", "arrest",
    "close", "closed", "compromised", "hacked", "unauthorized",
    "illegal", "penalty", "fine",
    # Roman Urdu
    "block", "band", "suspend", "freeze", "khatam", "khatre mein",
    "legal", "police", "pakra jaye ga", "saza", "jail",
    "terminate", "band ho jaye ga",
    # Urdu
    "بلاک", "بند", "منجمد", "معطل", "قانونی کارروائی", "پولیس",
    "غیر مجاز", "غیر قانونی",
]

OTP_KEYWORDS = [
    "otp", "one-time", "one time", "verification code", "verify code",
    "sms code", "security code", "auth code", "passcode",
    "\u062a\u0635\u062f\u06cc\u0642\u06cc \u06a9\u0648\u0688", "\u06a9\u0648\u0688",
]


# --------------------------------------------------------------------------
# Brand/service recognition lists for Pakistani context
# --------------------------------------------------------------------------

PK_TELECOM_BRANDS = [
    "jazz", "zong", "telenor", "ufone", "warid", "mobilink",
    "ptcl", "nayatel", "stormfiber", "transworld",
]

PK_BANKING_BRANDS = [
    "hbl", "meezan", "ubl", "mcb", "allied bank", "bank alfalah",
    "bank al habib", "faysal bank", "standard chartered", "habib bank",
    "samba bank", "summit bank", "askari bank", "national bank",
    "easypaisa", "jazzcash", "sadapay", "nayapay", "upaisa",
]

PK_SERVICE_BRANDS = [
    "careem", "indrive", "bykea", "yango", "foodpanda", "daraz",
    "telemart", "cheetay", "leopards", "tcs", "call courier",
    "netflix", "spotify", "amazon", "pakwheels", "olx",
    "paksim", "swvl", "yayvo", "metro cash",
]

PK_GOVT_SERVICES = [
    "nadra", "fbr", "bisp", "ehsaas", "pta", "secp", "sbp",
    "hec", "dirbs", "excise", "leco", "ssgc", "sngpl",
    "k-electric", "wapda", "ptcl", "punjab.gov", "sehat card",
]

PK_HEALTH_BRANDS = [
    "aga khan", "shifa", "chughtai", "shaukat khanum", "lums",
    "nust", "lrbt", "indus hospital", "edhi", "saylani",
    "al-khidmat", "shifa foundation",
]

ALL_LEGIT_BRANDS = (
    PK_TELECOM_BRANDS + PK_BANKING_BRANDS + PK_SERVICE_BRANDS
    + PK_GOVT_SERVICES + PK_HEALTH_BRANDS
)

# "Do not share" patterns - strong safe signal for OTP messages
DO_NOT_SHARE_PATTERNS = [
    "do not share", "never share", "don't share", "do not disclose",
    "kisi ko mat batayein", "share na karein", "kisi ko nahi batana",
    "mat batayein", "share nahi karna",
    "\u0634\u06cc\u0626\u0631 \u0646\u06c1 \u06a9\u0631\u06cc\u06ba",
    "\u06a9\u0633\u06cc \u06a9\u0648 \u0646\u06c1 \u0628\u062a\u0627\u0626\u06cc\u06ba",
    "\u06a9\u0633\u06cc \u06a9\u06d2 \u0633\u0627\u062a\u06be \u0634\u06cc\u0626\u0631 \u0646\u06c1 \u06a9\u0631\u06cc\u06ba",
]

# Transaction/receipt patterns
TXN_ID_PATTERNS = [
    "transaction id", "txn id", "ref:", "receipt", "order #",
    "tracking id", "trx:", "ep", "jc",
]


# ──────────────────────────────────────────────────────────────────────────────
# Text normalizer
# ──────────────────────────────────────────────────────────────────────────────

class ScamTextNormalizer(BaseEstimator, TransformerMixin):
    """
    Custom text normalizer that preserves scam-signal patterns.

    Transformations:
    - Lowercase (for English/Roman Urdu portions)
    - Normalize unicode (handle different representations)
    - Normalize whitespace
    - Preserve URLs, phone numbers, currency amounts, OTP codes
    - Replace specific numbers (like OTP digits) with placeholder ONLY
      if they look like random digits (not currency amounts)
    """

    def __init__(self, lowercase: bool = True, normalize_unicode: bool = True):
        self.lowercase = lowercase
        self.normalize_unicode = normalize_unicode

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        result = []
        for text in X:
            result.append(self._normalize(str(text)))
        return result

    def _normalize(self, text: str) -> str:
        # Unicode normalization
        if self.normalize_unicode:
            text = unicodedata.normalize("NFKC", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Preserve URLs as-is (replace with placeholder tag)
        urls = re.findall(r"https?://\S+", text)
        for i, url in enumerate(urls):
            text = text.replace(url, f" __URL{i}__ ")
        text = re.sub(r"https?://\S+", " __URL__ ", text)

        # Lowercase (safe for Urdu – doesn't affect Urdu script)
        if self.lowercase:
            text = text.lower()

        # Restore URLs
        for i, url in enumerate(urls):
            text = text.replace(f" __url{i}__ ", f" __URL__ ")

        # Normalize phone-number-like patterns → keep them
        # Patterns like 03XX-XXXXXXX, +92..., 03XX XXXXXXX
        text = re.sub(
            r"(\+?92[-\s]?)?0?3\d{2}[-\s]?\d{7}",
            " __PHONE__ ",
            text,
        )

        # Normalize currency amounts: "Rs. 5000", "Rs 5,000", "₨10000"
        text = re.sub(
            r"(?:rs\.?|₨)\s*[\d,]+(?:\.\d+)?",
            " __MONEY__ ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\$\s*[\d,]+(?:\.\d+)?",
            " __USD__ ",
            text,
        )
        text = re.sub(
            r"£\s*[\d,]+(?:\.\d+)?",
            " __GBP__ ",
            text,
        )

        # Percentages
        text = re.sub(r"\d+\.?\d*\s*%", " __PERCENT__ ", text)

        # OTP-like codes (sequences of 4-8 digits not part of money)
        text = re.sub(r"\b\d{4,8}\b", " __CODE__ ", text)

        # Collapse remaining whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text


# ──────────────────────────────────────────────────────────────────────────────
# Lightweight Urdu normalizer helpers
# ──────────────────────────────────────────────────────────────────────────────

def is_urdu_char(ch: str) -> bool:
    """Return True if the character is in the Arabic/Urdu Unicode block."""
    cp = ord(ch)
    return (
        (0x0600 <= cp <= 0x06FF)   # Arabic
        or (0x0750 <= cp <= 0x077F)  # Arabic Supplement
        or (0xFB50 <= cp <= 0xFDFF)  # Arabic Presentation Forms-A
        or (0xFE70 <= cp <= 0xFEFF)  # Arabic Presentation Forms-B
    )


def has_urdu(text: str) -> bool:
    """Return True if the text contains any Urdu/Arabic characters."""
    return any(is_urdu_char(ch) for ch in text)


# ──────────────────────────────────────────────────────────────────────────────
# Improved normalizer with Roman Urdu spelling normalization (Phase 3)
# ──────────────────────────────────────────────────────────────────────────────

class ImprovedScamTextNormalizer(ScamTextNormalizer):
    """Extended normalizer with Roman Urdu spelling normalization.

    Normalizes common abbreviated/misspelled Roman Urdu words to their
    canonical forms so that character n-grams capture consistent patterns.
    """

    # Maps variant -> canonical form
    ROMAN_URDU_NORM = {
        "krne": "karne", "krna": "karna", "krin": "karein",
        "kren": "karein", "krnna": "karna",
        "bhejen": "bhejein", "bhejain": "bhejein", "bhejn": "bhejein",
        "lga": "laga", "lgaa": "laga",
        "nkla": "nikla",
        "nh": "nahi", "nai": "nahi",
        "hn": "hain", "han": "hain",
        "acount": "account", "acc": "account",
        "numbr": "number",
        "forrn": "foran",
        # V3 additions
        "btayen": "batayein", "btayn": "batayein",
        "krwayen": "karwaen", "karwaen": "karwaen",
        "kmaen": "kamaen", "kmao": "kamao",
        "adaeyi": "adaigi", "adaiyi": "adaigi",
        "frahm": "faraaham", "fraham": "faraaham",
        "fraham": "faraaham",
        "zaroori": "zaruri", "zarori": "zaruri",
        "mukammal": "mukammal", "mokammal": "mukammal",
        "taqreeban": "taqreeban", "taqreeb": "taqreeban",
        "mahana": "mahana", "mahina": "mahana",
        "jama": "jama", "jamah": "jama",
    }

    # Multi-word patterns (handled with simple string replacement)
    ROMAN_URDU_NORM_PHRASES = {
        "k lie": "ke liye",
        "k liye": "ke liye",
        "ke lie": "ke liye",
        # V3 additions
        "k badle": "ke badle",
        "k sath": "ke saath",
        "k bad": "ke baad",
        "k pehle": "ke pehle",
        "k according": "ke according",
        "ki wajah": "ki wajah se",
    }

    def _normalize(self, text):
        # Apply Roman Urdu word-level normalization BEFORE parent normalization
        result = text.lower() if self.lowercase else text
        # V3: Normalize USSD codes (*786#, *123# etc.) to a consistent token
        result = re.sub(r'\*[0-9]+#', '<USSD_CODE>', result)
        # Single-word normalizations using word boundaries
        for variant, canonical in self.ROMAN_URDU_NORM.items():
            result = re.sub(
                r'\b' + re.escape(variant) + r'\b',
                canonical, result, flags=re.IGNORECASE,
            )
        # Multi-word phrase normalizations (simple replace)
        for variant, canonical in self.ROMAN_URDU_NORM_PHRASES.items():
            result = re.sub(
                re.escape(variant), canonical, result, flags=re.IGNORECASE,
            )
        # Collapse repeated characters (e.g., "freeeee" -> "free")
        result = re.sub(r'(.)\1{3,}', r'\1\1', result)
        # Now apply parent normalization (lowercase, phone/URL/money replacement)
        return super()._normalize(result)
