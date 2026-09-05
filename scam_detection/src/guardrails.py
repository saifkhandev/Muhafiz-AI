"""
Targeted post-processing guardrails for the V4 scam detection model.

These rules fix narrow, verified failure modes without retraining the model.
They are applied after the base model prediction and can be individually
disabled or logged.

Design principles:
- Only override when the pattern is unambiguous.
- Use conservative probabilities (far from the 0.63 threshold) so the
  override is decisive but not hidden.
- Never downgrade a scam to safe unless a strong safe signal is present.
"""
import re
from typing import Optional, Tuple

from src.preprocessing import ALL_LEGIT_BRANDS, DO_NOT_SHARE_PATTERNS

# Wallet / mobile-money / telecom setup and confirmation phrases
WALLET_SETUP_PATTERNS = [
    "mpin",
    "mobile account",
    "mobile banking",
    "debit card pin",
    "credit card pin",
    "account activated",
    "account activate",
    "account successfully",
    "account bana",
    "account khol",
    "pin has been",
    "pin is set",
    "pin generated",
    "password has been reset",
    "password reset successfully",
]

# Investment / portfolio / account-statement safe markers.
# Deliberately excludes "matured"/"maturity"/"profit" because those also
# appear in scams that demand tax/penalty payments.
INVESTMENT_SAFE_PATTERNS = [
    "nav", "portfolio",
    "kse-100", "kse 100", "index", "dividend",
    "bonus shares", "annual increment", "revised salary",
    "mutual fund redemption", "defence savings certificate",
    "national savings",
]

# Delivery / parcel / order contexts
DELIVERY_CONTEXT_WORDS = [
    "parcel", "package", "delivery", "delivered",
    "courier", "rider", "order", "shipment", "ship",
]

# Explicit requests for OTP / code
OTP_REQUEST_PATTERNS = [
    r"tell\s+us\s+(?:the\s+)?otp",
    r"share\s+(?:the\s+)?otp",
    r"provide\s+(?:the\s+)?otp",
    r"reply\s+with\s+(?:the\s+)?otp",
    r"send\s+(?:the\s+)?otp",
    r"otp\s+(?:bata|bhej|share)",
    r"code\s+(?:bata|bhej|share)",
    r"verification\s+code\s+(?:bata|bhej|share)",
    r"(?:bata|bhej|share)\s+(?:karein|kare|karo)\s+(?:otp|code)",
]

# Request verbs / payment-instruction markers used by scams
REQUEST_VERBS = [
    "bhejein", "bhejo", "bhejen", "bhejain", "bhejn",
    "send", "pay", "jama karwayein", "jama karwao",
    "transfer karein", "reply with", "call", "contact",
    "batayein", "bataen", "batao", "batain",
]

# Reference-number patterns often used by impersonation scams
REFERENCE_PATTERN = re.compile(r"\b(?:[A-Z]{2,5}-\d{3,9}|SR-\d{6}|AR-\d{5}|FN-\d{6}|TX-\d{5}|CON-\d{6}|WLT-\d{6}|PKL-\d{5}|PK-?\d{6})\b")

# Account / security review phishing context
ACCOUNT_SECURITY_CONTEXT = [
    "account", "profile", "security review", "security check", "routine check",
    "account verification", "verify your account", "service", "services",
]

# Urgency / service-termination threats used in phishing
URGENCY_THREAT_PHRASES = [
    "keep active", "keep your services", "avoid suspension", "will be suspended",
    "will be disabled", "will be deactivated", "prevent", "immediate action",
    "within 24 hours", "within 48 hours", "expires", "expiration",
]

# Soft verification/demand language used by scams without explicit threats
VERIFICATION_DEMAND_PATTERNS = [
    r"confirm\s+(?:your\s+(?:registered\s+)?)?(?:information|details)",
    r"verify\s+(?:submitted\s+)?(?:information|details|documents)",
    r"document\s+verif",
    r"review\s+(?:the\s+)?(?:record|details|information)",
    r"complete\s+(?:your\s+)?(?:profile|verification|documents)",
    r"submit\s+(?:your\s+)?(?:information|details|documents)",
]

# Indirect financial-request patterns common in romance/job/loan scams
INDIRECT_PAYMENT_PATTERNS = [
    r"emergency\s+payment",
    r"unexpected\s+travel\s+expense",
    r"small\s+security\s+deposit",
    r"financial\s+help.*emergency",
    r"emergency.*financial\s+help",
]

# Utility / fake bill scams — passive bill notices are safe, threats are scams
UTILITY_BILL_KEYWORDS = [
    "electricity", "electric", "bill", "bijli", "gas bill", "sui gas",
    "sngpl", "ssgc", "water bill", "utility bill", "k-electric", "leco",
    "wapda", "gas", "paani", "bijli ka bill",
]
UTILITY_THREAT_KEYWORDS = [
    "disconnected", "disconnect", "cut off", "cutoff", "suspended", "blocked",
    "legal action", "fine", "penalty", "immediately", "within 24 hours",
    "band ho jaye", "kaat diya jaye", "kat", "saza", "case",
]

# Romance / family-emergency emotional manipulation + money request
ROMANCE_EMOTIONAL_MARKERS = [
    "i love you", "love you so much", "miss you", "my love", "my heart",
    "i need you", "please help me", "meri madad karo", "main tumhari",
    "sick mother", "sick father", "hospital", "operation", "medicine",
    "mother is sick", "father is sick", "family emergency", "emergency",
]
FAMILY_MONEY_REQUEST_PATTERNS = [
    r"(?:send|bhej|transfer)\s+(?:me|mujhe|mere)\s+(?:rs\.?|rupees|money|paise|paisa)",
    r"(?:rs\.?|rupees)\s*[\d,]+",
    r"(?:send|bhej)\s+(?:money|paise|paisa|rupay)",
    r"(?:mujhe|mere)\s+(?:rs\.?|rupees|paise)",
]

# Safe-signal patterns for messages describing reporting/blocking threats
REPORTING_SAFE_PATTERNS = [
    r"reported\s+(?:the\s+)?(?:threatening|blackmail|suspicious)",
    r"blocked\s+(?:the\s+)?(?:number|account|sender)",
    r"saved\s+screenshots",
    r"ignore\s+(?:the\s+)?(?:fake|blackmail)",
]

# First-person personal transfer patterns (I sent you money via wallet)
PERSONAL_TRANSFER_PATTERNS = [
    r"(?:maine|i)\s+(?:ne|have)?\s*.*(?:bhej\s+di|sent|transfer)\s+(?:diye|kar\s+di|kiya)",
    r"(?:maine|i)\s+\w+\s+(?:bhej|send|transfer)\s+.*(?:check|receive)",
]

DO_NOT_SHARE_PATTERNS_LOWER = [p.lower() for p in DO_NOT_SHARE_PATTERNS]


def _contains_any(text: str, patterns) -> bool:
    return any(p.lower() in text.lower() for p in patterns)


def _contains_regex_any(text: str, regex_patterns) -> bool:
    return any(re.search(p, text.lower()) for p in regex_patterns)


def _has_legit_brand(text: str) -> bool:
    return any(brand.lower() in text.lower() for brand in ALL_LEGIT_BRANDS)


def _has_payment_request(text: str) -> bool:
    return _contains_any(text, REQUEST_VERBS)


def apply_guardrails(
    message: str,
    base_proba: float,
    base_label: str,
) -> Tuple[float, str, Optional[str]]:
    msg_lower = message.lower()

    # Pattern A: legitimate wallet / MPIN / telecom setup or confirmation
    has_wallet_setup = _contains_any(message, WALLET_SETUP_PATTERNS)
    has_legit_brand = _has_legit_brand(message)
    has_do_not_share = _contains_any(message, DO_NOT_SHARE_PATTERNS_LOWER)
    has_payment_request = _has_payment_request(message)

    # Strong override: wallet setup language + legit brand + explicit
    # "do not share" safe signal and no payment/transfer request.
    if (
        has_wallet_setup
        and has_legit_brand
        and has_do_not_share
        and not has_payment_request
    ):
        return 0.05, "Safe", "wallet_setup_safe_override"

    # Additional MPIN-creation / app-download override: messages that tell
    # the user to create/set MPIN or download the official app, with no
    # request to send money or share credentials with a third party.
    mpin_create_setup = (
        "mpin" in msg_lower
        and has_legit_brand
        and not has_payment_request
        and any(p in msg_lower for p in [
            "create", "bana", "bnae", "banae", "set", "download",
            "app", "application",
        ])
    )
    if mpin_create_setup:
        return 0.06, "Safe", "mpin_create_safe_override"

    # Pattern B: legitimate investment / portfolio / account statement.
    # Only fire on unambiguous passive statement markers and reject any
    # message with a demand/penalty pattern.
    if _contains_any(message, INVESTMENT_SAFE_PATTERNS) and not _has_payment_request(message):
        demand_patterns = [
            r"(?:fee|tax|penalty|charges)\s+.{0,25}\s*(?:bhej|pay|send|jama|required)",
            r"(?:fee|tax|penalty|charges)\s+rs\.?\s*[\d,]+",
            r"if not\s+(?:renewed|paid|updated|verified)",
            r"penalty\s+rs\.?\s*[\d,]+",
            r"tax\s+rs\.?\s*[\d,]+",
        ]
        if not any(re.search(p, msg_lower) for p in demand_patterns):
            return 0.08, "Safe", "investment_safe_override"

    # Pattern C: OTP-request delivery scam
    if (
        _contains_any(message, DELIVERY_CONTEXT_WORDS)
        and _contains_regex_any(message, OTP_REQUEST_PATTERNS)
    ):
        return 0.95, "Scam", "delivery_otp_scam_override"

    # Pattern D: soft impersonation verification scam
    # Scams that use a reference number + soft verification language + link/portal.
    has_reference = REFERENCE_PATTERN.search(message)
    has_verification_demand = _contains_regex_any(message, VERIFICATION_DEMAND_PATTERNS)
    has_link = any(k in msg_lower for k in ["http", "link", "portal", ".com", ".pk", ".net"])
    if has_reference and has_verification_demand and has_link and not has_payment_request:
        return 0.92, "Scam", "reference_verification_scam_override"

    # Pattern J: account security review / service-termination phishing
    # Requires account/service context + verification demand + urgency/threat.
    has_account_security = _contains_any(message, ACCOUNT_SECURITY_CONTEXT)
    has_urgency_threat = _contains_any(message, URGENCY_THREAT_PHRASES)
    if has_account_security and has_verification_demand and has_urgency_threat:
        return 0.93, "Scam", "account_security_review_scam_override"

    # Pattern E: indirect financial request scams
    if _contains_regex_any(message, INDIRECT_PAYMENT_PATTERNS):
        return 0.93, "Scam", "indirect_payment_scam_override"

    # Pattern H: fake utility-bill threat scams
    # Passive bill reminders are safe; threats of disconnection + payment demand are scams.
    has_utility_context = _contains_any(message, UTILITY_BILL_KEYWORDS)
    has_utility_threat = _contains_any(message, UTILITY_THREAT_KEYWORDS)
    if has_utility_context and has_utility_threat and has_payment_request:
        return 0.94, "Scam", "utility_bill_threat_scam_override"

    # Pattern I: romance / family-emergency money scams
    # Requires emotional manipulation marker plus an explicit money request.
    has_emotional_marker = _contains_any(message, ROMANCE_EMOTIONAL_MARKERS)
    has_family_money_request = _contains_regex_any(message, FAMILY_MONEY_REQUEST_PATTERNS)
    if has_emotional_marker and has_family_money_request:
        return 0.94, "Scam", "romance_emergency_scam_override"

    # Pattern F: messages describing reporting/blocking a threat are safe
    if _contains_regex_any(message, REPORTING_SAFE_PATTERNS):
        return 0.07, "Safe", "threat_reporting_safe_override"

    # Pattern G: first-person personal wallet/bank transfers are safe
    if _contains_regex_any(message, PERSONAL_TRANSFER_PATTERNS) and _has_legit_brand(message):
        return 0.08, "Safe", "personal_transfer_safe_override"

    return base_proba, base_label, None
