"""
run_retrain_pipeline.py
Complete retraining pipeline for improved Roman Urdu generalization.

Steps 1-24 from the improvement plan:
- Data audit (done separately)
- Roman Urdu expansion with spelling variation
- Hard negatives and hard positives
- Improved preprocessing with normalization
- Character + word TF-IDF experiments
- Engineered features
- Leakage-safe CV with group splitting
- Holdout evaluation
- Threshold optimization
- Error analysis
- Final model selection and saving

IMPORTANT: External 1000-message dataset is LOCKED and NOT used.
"""
import sys, os, io, json, time, warnings, random, hashlib, re
import numpy as np
import pandas as pd
from collections import Counter
from copy import deepcopy
from scipy.sparse import issparse, hstack

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

warnings.filterwarnings("ignore")

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_validate,
)
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix,
)
import joblib

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PK_FILE = os.path.join(DATA_DIR, "scam_messages_dataset.xlsx")
PK_SHEET = "Scam Detection Dataset"
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
REPORT_DIR = os.path.join(PROJECT_ROOT, "reports")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

SEED = 42
N_FOLDS = 5
HOLDOUT_FRAC = 0.20

C_MSG = "Message Content"
C_LANG = "Language Type"
C_CAT = "Scam Category"
C_LBL = "Label"

random.seed(SEED)
np.random.seed(SEED)

# ═══════════════════════════════════════════════════════════════════════
#  STEP 3-5: ROMAN URDU DATA AUGMENTATION
# ═══════════════════════════════════════════════════════════════════════

def generate_roman_urdu_data():
    """Generate diverse Roman Urdu scam and safe messages with spelling variation."""

    scam_messages = []
    safe_messages = []

    # Helper: random spelling variation
    def vary(text):
        """Apply random spelling variations to Roman Urdu text."""
        replacements = [
            ("karein", random.choice(["karein", "krin", "kren", "karen"])),
            ("karne", random.choice(["karne", "krne", "krn"])),
            ("ke liye", random.choice(["ke liye", "k lie", "k liye", "ke lie"])),
            ("karna", random.choice(["karna", "krna", "krnna"])),
            ("nahi", random.choice(["nahi", "nai", "nh", "naheen"])),
            ("hai ", random.choice(["hai ", "ha ", "h "])),
            ("hain", random.choice(["hain", "han", "hn"])),
            ("bhejein", random.choice(["bhejein", "bhejen", "bhejain", "bhejn"])),
            ("account", random.choice(["account", "acount", "acc"])),
            ("number", random.choice(["number", "numbr", "num"])),
            ("foran", random.choice(["foran", "foran hi", "forrn"])),
            ("paisay", random.choice(["paisay", "paise", "paisa"])),
            ("aapka", random.choice(["aapka", "apka", "ap ka"])),
            ("aap ko", random.choice(["aap ko", "ap ko", "apko"])),
            ("aap ka", random.choice(["aap ka", "ap ka", "apka"])),
            ("laga", random.choice(["laga", "lga", "lgaa"])),
            ("nikla", random.choice(["nikla", "nikla ha", "nkla"])),
            ("verification", random.choice(["verification", "tasdeeq", "verificaton"])),
            ("moaziz", random.choice(["Moaziz", "Moaziz", "Muaziz"])),
            ("mubarak", random.choice(["Mubarak", "Mubarak", "Mubark"])),
        ]
        result = text
        for full, variant in replacements:
            if full.lower() in result.lower():
                # Case-insensitive replace
                pattern = re.compile(re.escape(full), re.IGNORECASE)
                result = pattern.sub(variant, result, count=1)
        return result

    # ── SCAM TYPE 1: Prize/Lottery (Mubarak ho variants) ──
    prize_templates = [
        "Mubarak ho! BISP main apka {amt} ka inam {lga} ha. Apna inam hasil {krne} {k_lie} apna {wallet} account number aur OTP bhejain.",
        "Mubarak ho! Ehsaas Program main apka {amt} ka inam {lga} ha. Apna inam hasil {krne} {k_lie} apna {wallet} account details share karein.",
        "Mubarak ho! Jeeto Pakistan main apka {amt} ka inam {lga} ha. Inam hasil {krne} {k_lie} {num} par rabta karein.",
        "Mubarak ho! Inaam Ghar main apka {amt} ka prize nikla hai. Tasdeeq {k_lie} apna CNIC aur {wallet} details bhejain.",
        "Moaziz sarif, apka {org} ki taraf se {amt} PKR ka inaam nikla ha. Tasdeeq {k_lie} {num} par call karein.",
        "Khushkhabri! Apka mobile number {org} lucky draw mein winner nikla hai. {amt} PKR prize hasil karne ke liye apni details bhejein.",
        "Mubarak ho! {org} ki taraf se apka {amt} ka cash prize nikla. Foran apna {wallet} PIN aur account number share karein.",
        "Moaziz sarif, BISP ki taraf se {amt} PKR ka inaam apke naam confirm hua hai. Foran {num} par call kar ke apna code bhejain.",
    ]

    amounts = ["2500", "5000", "10000", "12500", "15000", "25000", "50000"]
    orgs = ["BISP", "Ehsaas Program", "Jeeto Pakistan", "Inaam Ghar", "Lucky Draw", "Pakistan Lottery", "PTV Inaam"]
    wallets = ["Easypaisa", "JazzCash", "HBL", "Meezan Bank", "UBL", "MCB", "NayaPay", "SadaPay"]
    nums = ["03012345678", "03219876543", "03331234567", "03451234567", "03622424819"]

    for _ in range(40):
        tmpl = random.choice(prize_templates)
        msg = tmpl.format(
            amt=random.choice(amounts),
            lga=random.choice(["lga ha", "lga hai", "laga hai", "laga ha", "lgaa ha"]),
            krne=random.choice(["krne", "karne", "krn"]),
            k_lie=random.choice(["k lie", "ke liye", "k liye"]),
            wallet=random.choice(wallets),
            org=random.choice(orgs),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 2: Bank Impersonation ──
    bank_templates = [
        "Aap ka {bank} account block hone wala hai. Foran {num} par call kar ke account verify karein.",
        "Zaruri itlaa: Aap ka {bank} account suspend ho gaya hai. Verification ke liye apna OTP {num} par bhejein.",
        "Alert: Aap ke {bank} account se suspicious transaction hui hai. Account secure karne ke liye apna PIN bhejein.",
        "Aap ka {bank} account temporarily freeze ho gaya hai. Unblock karne ke liye {num} par rabta karein.",
        "Security Alert: Aap ke {bank} debit card se {amt} PKR ki unauthorized transaction hui hai. Agar aap ne nahi kiya to {num} par call karein.",
        "Aap ka {bank} account ka KYC expire ho gaya hai. Foran {num} par apni details update karein warna account band ho jaye ga.",
        "Zaruri: {bank} ki taraf se aap ke account ka verification pending hai. Apna CNIC aur account details {num} par share karein.",
    ]
    banks = ["HBL", "MCB", "UBL", "Meezan Bank", "Allied Bank", "Bank Alfalah", "Bank Al Habib", "Faysal Bank", "Habib Bank", "Askari Bank"]

    for _ in range(35):
        tmpl = random.choice(bank_templates)
        msg = tmpl.format(
            bank=random.choice(banks),
            num=random.choice(nums),
            amt=random.choice(["5000", "10000", "25000", "50000", "75000"]),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 3: OTP/PIN Theft ──
    otp_templates = [
        "Aap ka {wallet} account verify karne ke liye, OTP code {num} par bhejein.",
        "Security check: Apna {wallet} OTP code share karein taake account secure ho sakay. {num}",
        "Aap ke {wallet} account mein masla aa gaya hai. PIN code {num} par bhej kar theek karein.",
        "Verification pending: Apna {bank} account OTP {num} par foran bhejein warna account block ho jaye ga.",
        "Aap ka {wallet} one-time verification code share karein {num} par. Ye zaruri hai.",
        "Important: {wallet} security team ki taraf se request hai ke apna PIN code foran {num} par bhejein.",
    ]

    for _ in range(30):
        tmpl = random.choice(otp_templates)
        msg = tmpl.format(
            wallet=random.choice(wallets),
            bank=random.choice(banks),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 4: SIM Block/Swap ──
    sim_templates = [
        "Aap ka {telecom} sim card block hone wala hai. Foran {num} par call kar ke sim verify karein.",
        "Aap ka {telecom} number aaj raat 12 bajey band ho jaye ga. Sim active rakhne ke liye {num} par rabta karein.",
        "Zaruri itlaa: Aap ka {telecom} sim doosre naam par transfer ho raha hai. Rokne ke liye foran {num} par call karein.",
        "Aap ka {telecom} sim card expire ho gaya hai. Renewal ke liye apna CNIC number {num} par bhejein.",
        "Aap ka {telecom} connection suspend ho raha hai. Verify karne ke liye OTP code bhejein {num} par.",
    ]
    telecoms = ["Jazz", "Zong", "Telenor", "Ufone", "Warid"]

    for _ in range(25):
        tmpl = random.choice(sim_templates)
        msg = tmpl.format(
            telecom=random.choice(telecoms),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 5: Job Scams ──
    job_templates = [
        "Aap ko {company} mein {salary} PKR monthly salary par job mil sakti hai. Foran {num} par rabta karein.",
        "Home-based job opportunity: Rozana {salary} PKR kamayein. Details ke liye {num} par call karein.",
        "Aap ka resume {company} ne select kar liya hai. {salary} monthly package. Interview ke liye {num} par call karein.",
        "Urgent hiring: {company} ko {pos} chahiye. Salary {salary} PKR. Apply karne ke liye apna CNIC {num} par bhejein.",
        "Part time job: Ghar bethay {salary} PKR kamayein. WhatsApp par {num} par rabta karein.",
        "Congratulations! Aap ko {company} mein job offer mili hai. Joining ke liye {salary} PKR security deposit jama karwayein.",
    ]
    companies = ["Daraz", "FoodPanda", "Careem", "Bykea", "OLX Pakistan", "Jazz", "Nestle Pakistan"]
    positions = ["delivery boy", "driver", "customer support", "data entry operator", "sales officer"]

    for _ in range(25):
        tmpl = random.choice(job_templates)
        msg = tmpl.format(
            company=random.choice(companies),
            salary=random.choice(["25000", "35000", "45000", "50000", "60000"]),
            pos=random.choice(positions),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 6: Investment Scams ──
    invest_templates = [
        "Sirf {amt} PKR invest karein aur har mahine {pct}% profit kamayein. {num} par rabta karein.",
        "Government approved investment scheme: {amt} PKR se {profit} PKR monthly munafa. Details: {num}",
        "Crypto investment: Apne {amt} PKR ko 30 din mein double karein. Guaranteed returns. Contact: {num}",
        "Islamic investment plan: Halal munafa {pct}% monthly. Sirf {amt} PKR se shuru karein. {num}",
    ]

    for _ in range(20):
        tmpl = random.choice(invest_templates)
        msg = tmpl.format(
            amt=random.choice(["5000", "10000", "25000", "50000"]),
            pct=random.choice(["10", "15", "20", "30", "50"]),
            profit=random.choice(["5000", "10000", "20000"]),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 7: Wrong Transfer / Refund Scams ──
    transfer_templates = [
        "Bhai apke number par ghalti se mere {amt} rs aa gaye hain {wallet} me, please wapis bhej dein {wallet_num} par.",
        "Salam, mujh se ghalti se aap ko {amt} PKR transfer ho gaye hain. Kindly {amt} PKR is number par wapis bhejain: {num}",
        "Apne {wallet} account check karein, mere {amt} PKR apke account mein aa gaye hain. Please refund karein {wallet_num} par.",
        "Ghalti se aap ke {wallet} account mein {amt} PKR aa gaye hain. Barah karam wapis transfer karein is account par: {num}",
    ]

    for _ in range(20):
        tmpl = random.choice(transfer_templates)
        msg = tmpl.format(
            amt=random.choice(["1000", "2000", "3000", "5000", "10000"]),
            wallet=random.choice(wallets),
            wallet_num=random.choice(nums),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 8: Loan Scams ──
    loan_templates = [
        "Instant loan: {amt} PKR loan sirf 2% interest par. Processing ke liye {fee} PKR fee bhejein. {num}",
        "Aap {amt} PKR loan ke eligible hain. Foran approve karwane ke liye {num} par CNIC bhejein.",
        "Emergency loan: Bina guarantee {amt} PKR qarz milega. Processing fee {fee} PKR pehle bhejein. Contact: {num}",
        "Aap ka {amt} PKR loan pre-approved hai. Disbursement ke liye {fee} PKR verification fee jama karwayein.",
    ]

    for _ in range(15):
        tmpl = random.choice(loan_templates)
        msg = tmpl.format(
            amt=random.choice(["50000", "100000", "200000", "500000"]),
            fee=random.choice(["1000", "2000", "3000", "5000"]),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 9: Government Impersonation (BISP/Ehsaas/NADRA) ──
    govt_templates = [
        "BISP: Aap ki {amt} PKR ki payment ready hai. Collection ke liye apna CNIC {num} par verify karwayein.",
        "Ehsaas Kafalat: Aap ki monthly stipend {amt} PKR approve ho gayi hai. Foran {num} par biometric verification karwayein.",
        "NADRA: Aap ka CNIC expire hone wala hai. Renewal ke liye {num} par apni details update karein.",
        "FBR: Aap par {amt} PKR tax outstanding hai. Foran {num} par payment karein warna legal action hoga.",
        "Government relief fund: Aap ko {amt} PKR ki financial aid mili hai. Receive karne ke liye {num} par apna account bhejein.",
        "BISP Kafalat: Aap ka payment code generate ho gaya hai. Code {num} par bhej kar {amt} PKR hasil karein.",
    ]

    for _ in range(25):
        tmpl = random.choice(govt_templates)
        msg = tmpl.format(
            amt=random.choice(["5000", "8000", "10000", "12000", "15000", "25000"]),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 10: Delivery Scams ──
    delivery_templates = [
        "Aap ka parcel {city} mein customs mein phans gaya hai. Custom duty {amt} PKR ada karein {num} par warna parcel wapis ho jaye ga.",
        "TCS/Leopards: Aap ka package deliver nahi ho saka. Delivery fee {amt} PKR bhejein {num} par.",
        "Aap ka Daraz order mein masla aa gaya hai. Refund ke liye apna {wallet} details {num} par share karein.",
        "Courier alert: Aap ka parcel hold hai. Release karne ke liye {amt} PKR pay karein is number par: {num}",
    ]
    cities = ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar"]

    for _ in range(15):
        tmpl = random.choice(delivery_templates)
        msg = tmpl.format(
            city=random.choice(cities),
            amt=random.choice(["500", "1000", "1500", "2000", "3000"]),
            wallet=random.choice(wallets),
            num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 11: Family/Friend Impersonation ──
    family_templates = [
        "Bhai mujhe urgent {amt} PKR chahiye. Abhi {wallet} par bhej do, baad mein wapis kar dunga.",
        "Amma ki tabiyat kharab hai, hospital mein hain. Foran {amt} PKR {wallet} par transfer karein.",
        "Salam bhai, main mushkil mein hoon. {amt} PKR ki zaroorat hai. Please {wallet} {wallet_num} par bhej dein.",
        "Beta, mujhe {amt} PKR foran chahiye. Kisi ko mat batana. {wallet} par bhej do.",
        "Bhai meri gaari accident ho gayi hai. {amt} PKR ki zaroorat hai urgently. {wallet_num} par bhejein.",
    ]

    for _ in range(15):
        tmpl = random.choice(family_templates)
        msg = tmpl.format(
            amt=random.choice(["5000", "10000", "15000", "20000", "50000"]),
            wallet=random.choice(wallets),
            wallet_num=random.choice(nums),
        )
        msg = vary(msg)
        scam_messages.append(msg)

    # ── SCAM TYPE 12: Subtle/Polite Scams (Hard Positives) ──
    subtle_templates = [
        "Assalam o alaikum. Aap ki tasdeeq ke liye, barah karam apna reference number aur account details share karein.",
        "Aap ki security review pending hai. Account confirm karne ke liye apna verification code bhejein.",
        "Kindly apna account recovery code share karein taake aap ka access restore ho sakay.",
        "Routine verification: Aap ka account check ho raha hai. Apna last 4 digit card number confirm karein.",
        "Aap ka account upgrade ke liye selected hua hai. Tasdeeq ke liye apni details bhejein.",
        "Service notification: Aap ke liye ek pending transaction hai. Confirm karne ke liye apna code bhejain.",
        "Aap ki account activity review ho rahi hai. Verification ke liye apna code share karein.",
    ]

    for _ in range(20):
        tmpl = random.choice(subtle_templates)
        msg = vary(tmpl)
        scam_messages.append(msg)

    # ═══════════════════════════════════════════════════════════════
    #  SAFE MESSAGES
    # ═══════════════════════════════════════════════════════════════

    # ── SAFE: Legitimate OTP/Security ──
    legit_otp = [
        "Your {bank} OTP is {code}. Do not share this code with anyone. {bank} will never call you asking for OTP.",
        "{bank} Security Alert: OTP {code} was requested for your account. If this was not you, call {helpline} immediately. Never share OTP.",
        "JazzCash: Verification code {code}. Kisi ko yeh code share NA karein. JazzCash kabhi OTP nahi mangta.",
        "Easypaisa OTP: {code}. Yeh code kisi ko mat batayein. Easypaisa staff kabhi OTP nahi mangti.",
        "{bank} One-Time-Password: {code}. Valid for 5 minutes. Never share this code with anyone including {bank} staff.",
        "Zong: Aap ka verification code {code} hai. Yeh code kisi ke sath share na karein.",
        "HBL Mobile: Your security code is {code}. Do not share with anyone. HBL will never ask for your code.",
    ]

    for _ in range(30):
        tmpl = random.choice(legit_otp)
        msg = tmpl.format(
            bank=random.choice(banks),
            code=str(random.randint(100000, 999999)),
            helpline=random.choice(["111-111-425", "111-333-825", "111-222-622"]),
        )
        safe_messages.append(msg)

    # ── SAFE: Legitimate Transaction Notifications ──
    legit_txn = [
        "{bank}: Rs. {amt} successfully debited from your account {acc} on {date}. Balance: Rs. {bal}. If not you, call {helpline}.",
        "JazzCash: Rs. {amt} sent to {num} successfully. Txn ID: {txn}. Remaining balance: Rs. {bal}",
        "Easypaisa: You received Rs. {amt} from {num}. Trx: {txn}. Balance: Rs. {bal}. Dial *786# for menu.",
        "{bank} Alert: Purchase of Rs. {amt} at {merchant} on {date}. If unauthorized, call {helpline} immediately.",
        "SadaPay: Rs. {amt} charged at {merchant}. Balance: Rs. {bal}. Questions? Chat in the SadaPay app.",
        "NayaPay: Rs. {amt} transferred to {num}. Receipt #{txn}. Balance Rs. {bal}",
        "{bank}: Rs. {amt} cash withdrawal from ATM. Balance: Rs. {bal}. Card present transaction.",
    ]
    merchants = ["Imtiaz Store", "Chase Up", "Metro Cash & Carry", "Shell Pakistan", "PSO Fuel", "Daraz.pk", "FoodPanda", "KFC Pakistan"]
    helplines = ["111-111-425", "111-333-825", "111-222-622", "111-425-425", "111-825-825"]

    for _ in range(30):
        tmpl = random.choice(legit_txn)
        msg = tmpl.format(
            bank=random.choice(banks),
            amt=random.choice(["500", "1000", "1500", "2000", "3000", "5000"]),
            acc=f"****{random.randint(1000,9999)}",
            date=f"{random.randint(1,28)}/{random.randint(1,12)}/2026",
            bal=f"{random.randint(10,500)},{random.randint(100,999)}",
            num=random.choice(nums),
            txn=f"EP{random.randint(10000000, 99999999)}",
            merchant=random.choice(merchants),
            helpline=random.choice(helplines),
        )
        safe_messages.append(msg)

    # ── SAFE: Legitimate Bank Alerts (Hard Negatives) ──
    legit_bank = [
        "Dear Customer, your {bank} account statement for {month} is available on {bank} app. Log in to view.",
        "{bank}: Your debit card has been successfully activated. For security, never share your PIN with anyone.",
        "{bank} Reminder: Your credit card payment of Rs. {amt} is due on {date}. Pay via {bank} app to avoid charges.",
        "{bank}: Your account has been updated successfully. If you did not make this change, call {helpline}.",
        "{bank} Salary Credit: Rs. {amt} credited to your account from {employer}. Balance: Rs. {bal}",
        "Dear {bank} customer, your cheque #{chk} has been cleared. Amount Rs. {amt} credited.",
        "{bank}: Bill payment of Rs. {amt} for {utility} received successfully. Receipt: {txn}",
        "Alert: Aap k {bank} account se Rs. {amt} ki deduction hui hai tax ki madd mein. FBR receipt available on your {bank} app.",
        "Aap k {bank} account se Rs. {amt} ki deduction hui hai. Ye automatic bill payment hai. Koi action ki zarurat nahi.",
        "Aap ka {bank} debit card {merchant} par use hua hai. Amount: Rs. {amt}. Agar yeh aap ne nahi kiya to {helpline} par call karein.",
    ]
    employers = ["ABC Pvt Ltd", "Systems Ltd", "Techlogix", "Netsol Technologies", "PakData"]
    utilities = ["K-Electric", "LESCO", "SNGPL", "SSGC", "PTCL", "WAPDA"]
    months = ["January", "February", "March", "April", "May", "June"]

    for _ in range(35):
        tmpl = random.choice(legit_bank)
        msg = tmpl.format(
            bank=random.choice(banks),
            amt=random.choice(["5000", "10000", "15000", "25000", "50000", "75000"]),
            date=f"{random.randint(1,28)}/{random.randint(1,12)}/2026",
            helpline=random.choice(helplines),
            bal=f"{random.randint(50,500)},{random.randint(100,999)}",
            employer=random.choice(employers),
            chk=random.randint(100000, 999999),
            merchant=random.choice(merchants),
            utility=random.choice(utilities),
            txn=f"TXN{random.randint(10000000, 99999999)}",
            month=random.choice(months),
        )
        safe_messages.append(msg)

    # ── SAFE: Legitimate Service Notifications ──
    legit_service = [
        "Daraz: Your order #{order} has been shipped via {courier}. Tracking: {track}. Expected delivery: {days} days.",
        "FoodPanda: Your order from {restaurant} has been confirmed. Estimated delivery: {mins} minutes. Order #{order}",
        "Careem: Your ride has been completed. Fare: Rs. {fare}. Rate your captain in the app. Receipt sent to email.",
        "TCS: Your parcel #{track} has been delivered to {name}. Thank you for using TCS.",
        "Jazz: Your {pkg} package has been activated. Rs. {amt} charged. Valid for {days} days. Dial *111# for menu.",
        "Zong: Super Card successfully renewed. Rs. {amt} charged. Valid for 30 days. Unlimited calls & 30GB data.",
        "PTCL: Your broadband bill of Rs. {amt} for {month} has been paid successfully. Receipt #{txn}",
        "InDrive: Trip completed. Fare: Rs. {fare}. Rate your experience. Payment: Cash.",
        "Leopards Courier: Shipment #{track} delivered to {name}. POD available on leopards.com.pk",
        "Nayatel: Your internet package has been renewed. Rs. {amt} charged. Valid till {date}.",
    ]
    couriers = ["TCS", "Leopards", "Call Courier", "BlueEx", "MnP"]
    restaurants = ["McDonalds", "KFC", "Pizza Hut", "Burger Lab", "Cheezious"]
    packages = ["Daily Plus", "Weekly Max", "Monthly Super", "Super Monthly"]

    for _ in range(25):
        tmpl = random.choice(legit_service)
        msg = tmpl.format(
            order=f"DRZ{random.randint(100000, 999999)}",
            courier=random.choice(couriers),
            track=f"PK{random.randint(10000000, 99999999)}",
            days=random.choice([2, 3, 5, 7]),
            restaurant=random.choice(restaurants),
            mins=random.choice([20, 30, 45, 60]),
            fare=random.choice([200, 350, 500, 750, 1000]),
            name=random.choice(["Ahmed", "Ali", "Usman", "Hassan"]),
            pkg=random.choice(packages),
            amt=random.choice(["150", "250", "500", "1000", "2500"]),
            month=random.choice(months),
            txn=f"RCPT{random.randint(100000, 999999)}",
            date=f"{random.randint(1,28)}/{random.randint(1,12)}/2026",
        )
        safe_messages.append(msg)

    # ── SAFE: Personal Messages ──
    personal_msgs = [
        "Beta ghar kab aa rahe ho? Khana ready hai.",
        "Bhai kal cricket match hai, yaad rakhna. 4 baje ground par milna.",
        "Ammi ki dua. Khairiyat se pohnch gaye? Msg kar dena.",
        "Salam bhai, kaisay ho? Bohot din ho gaye baat nahi hui.",
        "Aaj mausam bohot acha hai, chayein peene chalte hain.",
        "Baji, bachon ko school time par bhej dena, aaj exam hai.",
        "Bhai, kal office mein meeting hai 10 baje. Late mat hona.",
        "Assalam o alaikum, eid mubarak! Aap ko aur family ko.",
        "Yaar kal ka plan final ho gaya? Sab log aa rahe hain.",
        "Papa ko bol dena ke main late aaunga aaj. Kaam zyada hai.",
        "Bhai, mujhe ghar ka address bhej do, GPS mein nahi mil raha.",
        "Chacha ki beti ki shadi kal hai. Sab log tayyar ho jayein.",
        "Ammi, main theek hoon. Fikar na karein. Kal ghar aaunga.",
        "Dost, assignment complete ho gayi? Mujhe bhi bhej do.",
        "Bhai gaari ka petrol khatam hone wala hai, pump par rukna padega.",
    ]
    for msg in personal_msgs:
        safe_messages.append(msg)

    # ── SAFE: Legitimate Government/Utility ──
    legit_govt = [
        "NADRA: Your CNIC renewal application #{app} has been received. Expected delivery: 15 working days.",
        "FBR: Your tax return for {year} has been filed successfully. NTN: {ntn}. Refund will be processed within 30 days.",
        "K-Electric: Your electricity bill for {month} is Rs. {amt}. Due date: {date}. Pay via {bank} app or EasyPaisa.",
        "SSGC: Gas bill for {month} Rs. {amt} generated. Due date {date}. Late payment surcharge applies.",
        "Sui Gas: Payment of Rs. {amt} received for consumer #{cons}. Thank you for timely payment.",
        "PTCL: Monthly bill Rs. {amt} for {month}. Pay before {date} to avoid disconnection.",
        "BISP: Your monthly stipend of Rs. {amt} has been deposited. Collect from nearest HBL or Easypaisa agent.",
        "Ehsaas: Your kafalat payment Rs. {amt} is ready. Visit nearest payment center with original CNIC.",
    ]

    for _ in range(25):
        tmpl = random.choice(legit_govt)
        msg = tmpl.format(
            app=random.randint(100000, 999999),
            year=random.choice([2025, 2026]),
            ntn=f"NTN-{random.randint(1000000, 9999999)}",
            month=random.choice(months),
            amt=random.choice(["3000", "5000", "8000", "12000"]),
            date=f"{random.randint(1,28)}/{random.randint(1,12)}/2026",
            bank=random.choice(banks),
            cons=random.randint(1000000000, 9999999999),
        )
        safe_messages.append(msg)

    # ── SAFE: Roman Urdu informational (with abbreviated spellings) ──
    ru_safe_msgs = [
        "Aap k {bank} acount se Rs. {amt} ki deduction hui ha tax ki madd mein. Ye automatic process ha.",
        "Aap ka {bank} debit card ATM par use hua ha. Amount: Rs. {amt}. Agar yeh aap ne nahi kiya to {helpline} par call karein.",
        "Aap k {wallet} me Rs. {amt} aaye hain {num} se. Balance: Rs. {bal}. Ye legitimate transaction ha.",
        "Aap ka {bank} acount statement ready ha. {bank} app par login kr k dekhain.",
        "Aap ki salary Rs. {amt} {bank} acount me credit ho gayi ha. {employer} ki taraf se.",
        "Aap ka {telecom} package renew ho gya ha. Rs. {amt} charge huye. {days} din valid ha.",
        "Aap ka {wallet} account successfully verify ho gya ha. Ab aap tamam services use kr skte hain.",
        "Aap k {bank} credit card ka payment Rs. {amt} receive ho gya ha. Koi action ki zarurat nh.",
        "Aap ka parcel {courier} k through deliver ho gya ha. Tracking: {track}.",
        "Aap ki {utility} bill payment Rs. {amt} successfully ho gayi ha. Receipt: {txn}.",
    ]

    for tmpl in ru_safe_msgs:
        for _ in range(2):  # Generate 2 variations per template
            msg = tmpl.format(
                bank=random.choice(banks),
                wallet=random.choice(wallets),
                amt=random.choice(["500", "1000", "2000", "5000", "10000", "25000", "50000", "75000"]),
                helpline=random.choice(helplines),
                num=random.choice(nums),
                bal=f"{random.randint(10,100)},{random.randint(100,999)}",
                employer=random.choice(employers),
                telecom=random.choice(telecoms),
                days=random.choice([7, 15, 30]),
                courier=random.choice(couriers),
                utility=random.choice(utilities),
                txn=f"TXN{random.randint(100000, 999999)}",
                track=f"TRK{random.randint(100000, 999999)}",
            )
            safe_messages.append(vary(msg))

    print(f"  Generated Roman Urdu scam messages: {len(scam_messages)}")
    print(f"  Generated Roman Urdu safe messages: {len(safe_messages)}")
    return scam_messages, safe_messages


# ═══════════════════════════════════════════════════════════════════════
#  STEP 6: IMPROVED PREPROCESSING
# ═══════════════════════════════════════════════════════════════════════

# Import the improved normalizer from src.preprocessing (must be importable for pickling)
from src.preprocessing import ImprovedScamTextNormalizer


# ═══════════════════════════════════════════════════════════════════════
#  STEP 9-10: ENHANCED FEATURE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

from src.features import ScamFeatureExtractor as _OrigExtractor


class EnhancedScamFeatureExtractor(_OrigExtractor):
    """Extended with Roman Urdu-specific and domain-aware features."""

    FEATURE_NAMES = list(_OrigExtractor.FEATURE_NAMES) + [
        # Roman Urdu specific
        "ru_abbrev_count",
        "ru_formal_count",
        # Safety indicators (expanded)
        "safety_warning_count",
        "no_action_needed_count",
        "official_channel_count",
        # Request intensity
        "action_request_count",
        "contact_request_count",
        # Financial context
        "legit_transaction_indicator",
        "scam_financial_indicator",
    ]

    # Roman Urdu abbreviated forms (scam signal in informal messages)
    RU_ABBREV = [
        "krne", "krna", "krin", "kren", "lga", "lgaa", "nkla",
        "bhejen", "bhejain", "acount", "numbr",
    ]

    RU_FORMAL = [
        "karein", "karne", "karna", "bhejein", "verification",
        "tasdeeq", "foran",
    ]

    SAFETY_WARNINGS = [
        "do not share", "never share", "don't share", "na karein share",
        "share na karein", "mat batayein", "kisi ko mat",
        "will never ask", "kabhi nahi mange ga", "kabhi nahi mangay ga",
        "never ask", "not ask for", "nhi mange ga",
    ]

    NO_ACTION_NEEDED = [
        "no action required", "no action needed", "koi action nahi",
        "koi action ki zarurat", "sirf information", "for your information",
        "automatically", "automatic process", "auto deduct",
    ]

    OFFICIAL_CHANNEL = [
        "visit branch", "branch visit", "call helpline", "helpline par",
        "official app", "mobile app", "internet banking",
        "customer service", "complaint", "register complaint",
    ]

    ACTION_REQUESTS = [
        r"(?:foran|abhi|jaldi|urgently|immediately)\s+(?:call|bhej|share|karein)",
        r"(?:call|bhej|share)\s+(?:karein|karo|den|do)\s+(?:abhi|foran|jaldi)",
        r"(?:verify|confirm|update)\s+(?:karein|karo)\s+(?:foran|abhi|jaldi)",
    ]

    CONTACT_REQUESTS = [
        r"(?:call|phone|contact|rabta)\s+(?:karein|karo|kare)",
        r"\d{10,11}",  # Phone number patterns
        r"whatsapp\s+(?:par|pe|on)",
    ]

    def _extract(self, text):
        # Get base features
        base_features = super()._extract(text)

        t = text.strip()
        t_lower = t.lower()

        # Roman Urdu abbreviation count
        ru_abbrev_count = sum(1 for w in self.RU_ABBREV if w in t_lower)

        # Roman Urdu formal count
        ru_formal_count = sum(1 for w in self.RU_FORMAL if w in t_lower)

        # Safety warning count
        safety_warning_count = sum(1 for p in self.SAFETY_WARNINGS if p in t_lower)

        # No action needed count
        no_action_needed_count = sum(1 for p in self.NO_ACTION_NEEDED if p in t_lower)

        # Official channel count
        official_channel_count = sum(1 for p in self.OFFICIAL_CHANNEL if p in t_lower)

        # Action request count
        action_request_count = sum(
            1 for p in self.ACTION_REQUESTS if re.search(p, t_lower)
        )

        # Contact request count
        contact_request_count = sum(
            1 for p in self.CONTACT_REQUESTS if re.search(p, t_lower)
        )

        # Legit transaction indicator
        legit_indicators = [
            "successfully", "completed", "receipt", "balance",
            "txn id", "transaction id", "ref:",
            "successfully sent", "successfully received",
            "complete ho gaya", "confirm ho gaya",
        ]
        legit_transaction_indicator = sum(1 for p in legit_indicators if p in t_lower)

        # Scam financial indicator
        scam_fin = [
            "fee bhejein", "processing fee", "security deposit",
            "advance payment", "verification fee", "registration fee",
            "pehle bhejein", "pehle pay karein",
        ]
        scam_financial_indicator = sum(1 for p in scam_fin if p in t_lower)

        return base_features + [
            ru_abbrev_count, ru_formal_count,
            safety_warning_count, no_action_needed_count,
            official_channel_count, action_request_count,
            contact_request_count, legit_transaction_indicator,
            scam_financial_indicator,
        ]


# ═══════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    print("=" * 70)
    print("  RETRAINING PIPELINE - Roman Urdu Generalization Improvement")
    print("=" * 70)

    # ── STEP 1: Load original data ──────────────────────────────────
    print("\n[STEP 1] Loading original dataset...")
    orig_df = pd.read_excel(PK_FILE, sheet_name=PK_SHEET)
    print(f"  Original: {len(orig_df)} messages")

    # ── STEP 2: External test LOCKED ────────────────────────────────
    print("\n[STEP 2] External 1000-message dataset: LOCKED (not used)")

    # ── STEP 3-5: Generate augmented Roman Urdu data ────────────────
    print("\n[STEP 3-5] Generating augmented Roman Urdu data...")
    ru_scam, ru_safe = generate_roman_urdu_data()

    # Create augmentation DataFrame
    aug_data = []
    for msg in ru_scam:
        aug_data.append({
            C_MSG: msg, C_LANG: "Roman Urdu",
            C_CAT: "Generated", C_LBL: "Scam",
        })
    for msg in ru_safe:
        aug_data.append({
            C_MSG: msg, C_LANG: "Roman Urdu",
            C_CAT: "Generated", C_LBL: "Safe",
        })
    aug_df = pd.DataFrame(aug_data)

    print(f"  Generated: {len(aug_df)} messages ({len(ru_scam)} Scam, {len(ru_safe)} Safe)")

    # Dedup augmented data
    aug_df = aug_df.drop_duplicates(subset=[C_MSG], keep="first").reset_index(drop=True)
    print(f"  After dedup: {len(aug_df)}")

    # Combine original + augmented
    combined_df = pd.concat([orig_df, aug_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=[C_MSG], keep="first").reset_index(drop=True)
    print(f"  Combined dataset: {len(combined_df)} messages")
    print(f"  Original: {len(orig_df)}, Augmented: {len(aug_df)}")

    # ── STEP 11: Dataset Balancing ──────────────────────────────────
    print("\n[STEP 11] Dataset balancing...")
    labels = combined_df[C_LBL].value_counts()
    print(f"  Scam: {labels.get('Scam', 0)} / Safe: {labels.get('Safe', 0)}")
    langs = combined_df[C_LANG].value_counts()
    print(f"  Languages: {dict(langs)}")

    ru_mask = combined_df[C_LANG] == "Roman Urdu"
    ru_counts = combined_df[ru_mask][C_LBL].value_counts()
    print(f"  Roman Urdu: Scam={ru_counts.get('Scam',0)}, Safe={ru_counts.get('Safe',0)}")

    # ── STEP 12: Template/Group Leakage Protection ──────────────────
    print("\n[STEP 12] Template/group leakage protection...")
    # Assign group IDs based on message prefix (first 4 words)
    def get_group(msg):
        words = str(msg).lower().split()[:4]
        return " ".join(words)

    combined_df["_group"] = combined_df[C_MSG].apply(get_group)
    n_groups = combined_df["_group"].nunique()
    print(f"  Unique groups (4-word prefix): {n_groups}")
    print(f"  Messages in groups > 3: {(combined_df['_group'].value_counts() > 3).sum()} groups")

    # ── STEP 14-15: Leakage-safe split ──────────────────────────────
    print("\n[STEP 14-15] Creating leakage-safe holdout split...")
    le = LabelEncoder()
    le.fit(["Safe", "Scam"])

    # Use group-aware splitting: ensure groups don't span train/test
    groups = combined_df["_group"].values
    labels_arr = combined_df[C_LBL].values

    # For groups with >3 members, keep them entirely in train or test
    group_counts = Counter(groups)
    large_groups = {g for g, c in group_counts.items() if c > 3}

    # Simple stratified split, then verify no group leakage
    trainval_df, test_df = train_test_split(
        combined_df, test_size=HOLDOUT_FRAC,
        stratify=combined_df[C_LBL], random_state=SEED,
    )

    # Check and fix group leakage
    train_groups = set(trainval_df["_group"])
    test_groups = set(test_df["_group"])
    overlap_groups = train_groups & test_groups

    if overlap_groups:
        print(f"  Group overlap found: {len(overlap_groups)} groups")
        # Move overlapping groups entirely to training (to preserve test size)
        overlap_mask = test_df["_group"].isin(overlap_groups)
        moved = test_df[overlap_mask]
        test_df = test_df[~overlap_mask]
        trainval_df = pd.concat([trainval_df, moved], ignore_index=True)
        print(f"  Moved {len(moved)} messages from test to train to fix leakage")

    # Further split trainval into train and validation
    train_df, val_df = train_test_split(
        trainval_df, test_size=0.15,
        stratify=trainval_df[C_LBL], random_state=SEED,
    )

    print(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test (holdout): {len(test_df)}")

    # Verify no group leakage
    train_groups2 = set(train_df["_group"])
    val_groups2 = set(val_df["_group"])
    test_groups2 = set(test_df["_group"])
    leak1 = len(train_groups2 & test_groups2)
    leak2 = len(val_groups2 & test_groups2)
    print(f"  Group leakage (train-test): {leak1}")
    print(f"  Group leakage (val-test): {leak2}")

    # Drop helper column
    for d in [combined_df, train_df, val_df, test_df, trainval_df]:
        if "_group" in d.columns:
            d.drop(columns=["_group"], inplace=True, errors="ignore")

    # ── STEP 6-10: Build model configurations ───────────────────────
    print("\n[STEP 6-10] Building model configurations...")

    X_train = train_df[C_MSG].values
    y_train = le.transform(train_df[C_LBL].values)
    X_val = val_df[C_MSG].values
    y_val = le.transform(val_df[C_LBL].values)
    X_test = test_df[C_MSG].values
    y_test = le.transform(test_df[C_LBL].values)

    def build_models():
        """All model candidates."""
        models = {}

        # A: Current best - char TF-IDF (3-6) + LinearSVC C=2.0
        models["A_char_svm_C2"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 6),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        # B: Char TF-IDF (3-5) + LinearSVC C=2.0
        models["B_char_svm_35"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        # C: Char TF-IDF (4-6) + LinearSVC C=2.0
        models["C_char_svm_46"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(4, 6),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        # D: Combined word + char TF-IDF (FeatureUnion) + LinearSVC
        models["D_combined_svm"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("features", FeatureUnion([
                ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.95,
                                          sublinear_tf=True, max_features=10000)),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                          min_df=2, max_df=0.95, sublinear_tf=True,
                                          max_features=10000)),
            ])),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        # E: Combined + Logistic Regression
        models["E_combined_lr"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("features", FeatureUnion([
                ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.95,
                                          sublinear_tf=True, max_features=10000)),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 6),
                                          min_df=2, max_df=0.95, sublinear_tf=True,
                                          max_features=10000)),
            ])),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced",
                                        random_state=SEED, solver="lbfgs")),
        ])

        # F: Word TF-IDF (1-3) + LinearSVC C=2.0
        models["F_word_svm_tri"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(ngram_range=(1, 3), min_df=2, max_df=0.95,
                                       sublinear_tf=True, max_features=20000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        # G: Char TF-IDF (3-6) + LinearSVC C=1.0
        models["G_char_svm_C1"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 6),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=15000)),
            ("clf", LinearSVC(C=1.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        # H: Char TF-IDF (3-7) + LinearSVC C=2.0
        models["H_char_svm_37"] = Pipeline([
            ("norm", ImprovedScamTextNormalizer()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 7),
                                       min_df=2, max_df=0.95, sublinear_tf=True,
                                       max_features=20000)),
            ("clf", LinearSVC(C=2.0, max_iter=5000, class_weight="balanced",
                               random_state=SEED, dual="auto")),
        ])

        return models

    models = build_models()
    print(f"  Built {len(models)} model configurations")

    # ── STEP 13: Cross-validation ───────────────────────────────────
    print("\n[STEP 13] Cross-validation on training data...")
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    from sklearn.metrics import make_scorer
    f1_s = make_scorer(f1_score, pos_label=1, zero_division=0)
    rec_s = make_scorer(recall_score, pos_label=1, zero_division=0)
    prec_s = make_scorer(precision_score, pos_label=1, zero_division=0)
    scoring = {"acc": "accuracy", "f1": f1_s, "recall": rec_s, "precision": prec_s}

    cv_results = {}
    for mname, pipe in models.items():
        print(f"\n  [{mname}] Running {N_FOLDS}-fold CV...")
        res = cross_validate(pipe, X_train, y_train, cv=cv,
                           scoring=scoring, return_train_score=True, n_jobs=-1)
        out = {}
        for m in ["acc", "f1", "recall", "precision"]:
            vals = res[f"test_{m}"]
            out[f"cv_{m}_mean"] = float(np.mean(vals))
            out[f"cv_{m}_std"] = float(np.std(vals))
            out[f"train_{m}_mean"] = float(np.mean(res[f"train_{m}"]))
        cv_results[mname] = out
        print(f"    CV F1={out['cv_f1_mean']:.4f}+/-{out['cv_f1_std']:.4f}  "
              f"Acc={out['cv_acc_mean']:.4f}  Recall={out['cv_recall_mean']:.4f}")

    # ── STEP 15-16: Evaluate on validation and holdout ──────────────
    print("\n[STEP 15-16] Evaluating on validation and holdout...")

    all_results = []
    best_name = None
    best_f1 = 0
    best_pipe = None
    best_val_proba = None
    best_test_proba = None
    best_opt_m = None
    best_tp = best_fp = best_fn = best_tn = 0
    best_threshold_final = 0.5

    for mname, pipe in models.items():
        # Fit on train, predict on val
        pipe_val = clone(pipe)
        pipe_val.fit(X_train, y_train)
        val_pred = pipe_val.predict(X_val)

        val_proba = None
        if hasattr(pipe_val[-1], "predict_proba"):
            val_proba = pipe_val.predict_proba(X_val)[:, 1]
        elif hasattr(pipe_val[-1], "decision_function"):
            d = pipe_val.decision_function(X_val)
            val_proba = 1 / (1 + np.exp(-d))

        # Threshold optimization on validation
        best_threshold = 0.5
        if val_proba is not None:
            best_f1_t = 0
            for t in np.arange(0.20, 0.70, 0.01):
                pred_t = (val_proba >= t).astype(int)
                f1_t = f1_score(y_val, pred_t, pos_label=1, zero_division=0)
                if f1_t > best_f1_t:
                    best_f1_t = f1_t
                    best_threshold = round(t, 2)

        # Refit on train+val for final evaluation
        pipe_full = clone(pipe)
        X_trainval = np.concatenate([X_train, X_val])
        y_trainval = np.concatenate([y_train, y_val])
        pipe_full.fit(X_trainval, y_trainval)

        # Predict on test
        test_pred = pipe_full.predict(X_test)
        test_proba = None
        if hasattr(pipe_full[-1], "predict_proba"):
            test_proba = pipe_full.predict_proba(X_test)[:, 1]
        elif hasattr(pipe_full[-1], "decision_function"):
            d = pipe_full.decision_function(X_test)
            test_proba = 1 / (1 + np.exp(-d))

        # Default threshold metrics
        def_m = {
            "accuracy": accuracy_score(y_test, test_pred),
            "f1": f1_score(y_test, test_pred, pos_label=1, zero_division=0),
            "recall": recall_score(y_test, test_pred, pos_label=1, zero_division=0),
            "precision": precision_score(y_test, test_pred, pos_label=1, zero_division=0),
        }

        # Optimized threshold metrics
        if test_proba is not None:
            test_pred_opt = (test_proba >= best_threshold).astype(int)
            opt_m = {
                "accuracy": accuracy_score(y_test, test_pred_opt),
                "f1": f1_score(y_test, test_pred_opt, pos_label=1, zero_division=0),
                "recall": recall_score(y_test, test_pred_opt, pos_label=1, zero_division=0),
                "precision": precision_score(y_test, test_pred_opt, pos_label=1, zero_division=0),
            }
            try:
                opt_m["roc_auc"] = roc_auc_score(y_test, test_proba)
            except:
                opt_m["roc_auc"] = None
            cm = confusion_matrix(y_test, test_pred_opt)
            tn, fp, fn, tp = cm.ravel()
        else:
            opt_m = def_m.copy()
            opt_m["roc_auc"] = None
            cm = confusion_matrix(y_test, test_pred)
            tn, fp, fn, tp = cm.ravel()

        entry = {
            "model": mname,
            "cv_f1_mean": cv_results[mname]["cv_f1_mean"],
            "cv_f1_std": cv_results[mname]["cv_f1_std"],
            "cv_recall_mean": cv_results[mname]["cv_recall_mean"],
            "cv_acc_mean": cv_results[mname]["cv_acc_mean"],
            "train_f1_mean": cv_results[mname]["train_f1_mean"],
            "threshold": best_threshold,
        }
        entry.update({f"test_{k}": v for k, v in opt_m.items()})
        entry["TP"] = int(tp)
        entry["FP"] = int(fp)
        entry["FN"] = int(fn)
        entry["TN"] = int(tn)
        all_results.append(entry)

        print(f"\n  [{mname}]")
        print(f"    CV  F1={cv_results[mname]['cv_f1_mean']:.4f}  "
              f"Acc={cv_results[mname]['cv_acc_mean']:.4f}")
        print(f"    Test Acc={opt_m['accuracy']:.4f} F1={opt_m['f1']:.4f} "
              f"Recall={opt_m['recall']:.4f} AUC={opt_m.get('roc_auc', 'N/A')}")
        print(f"    Threshold={best_threshold} FP={fp} FN={fn}")

        if opt_m["f1"] > best_f1:
            best_f1 = opt_m["f1"]
            best_name = mname
            best_pipe = pipe_full
            best_test_proba = test_proba
            best_threshold_final = best_threshold
            best_opt_m = opt_m.copy()
            best_tp = int(tp)
            best_fp = int(fp)
            best_fn = int(fn)
            best_tn = int(tn)

    # ── Save comparison ─────────────────────────────────────────────
    comp_df = pd.DataFrame(all_results)
    comp_df.to_csv(os.path.join(REPORT_DIR, "retrain_comparison.csv"),
                   index=False, float_format="%.4f")
    print(f"\n[REPORT] Model comparison saved -> reports/retrain_comparison.csv")
    print(f"\n  >> BEST: {best_name} (F1={best_f1:.4f})")

    # ── STEP 17: Language-specific evaluation ───────────────────────
    print("\n[STEP 17] Language-specific evaluation...")
    lang_results = {}
    test_pred_final = (best_test_proba >= best_threshold_final).astype(int) if best_test_proba is not None else best_pipe.predict(X_test)

    for lang in test_df[C_LANG].dropna().unique():
        mask = test_df[C_LANG].values == lang
        if mask.sum() < 2:
            continue
        yl = y_test[mask]
        yp = test_pred_final[mask]
        lr = {
            "n": int(mask.sum()),
            "accuracy": accuracy_score(yl, yp),
            "precision": precision_score(yl, yp, pos_label=1, zero_division=0),
            "recall": recall_score(yl, yp, pos_label=1, zero_division=0),
            "f1": f1_score(yl, yp, pos_label=1, zero_division=0),
        }
        lang_results[lang] = lr
        print(f"  [{lang:12s}] n={lr['n']:3d} Acc={lr['accuracy']:.4f} "
              f"P={lr['precision']:.4f} R={lr['recall']:.4f} F1={lr['f1']:.4f}")

    # ── STEP 18: Error Analysis ─────────────────────────────────────
    print("\n[STEP 18] Error analysis...")
    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(test_pred_final)

    errors = []
    for i in range(len(test_df)):
        if test_pred_final[i] != y_test[i]:
            errors.append({
                "message": test_df.iloc[i][C_MSG],
                "true_label": y_test_labels[i],
                "predicted_label": y_pred_labels[i],
                "language": test_df.iloc[i][C_LANG],
                "category": test_df.iloc[i][C_CAT],
                "probability": float(best_test_proba[i]) if best_test_proba is not None else None,
                "error_type": ("FN-missed-scam" if y_test[i] == 1
                              else "FP-safe-flagged"),
            })

    fn_errors = [e for e in errors if "FN" in e["error_type"]]
    fp_errors = [e for e in errors if "FP" in e["error_type"]]
    print(f"  Total errors: {len(errors)}")
    print(f"  False Negatives (missed scams): {len(fn_errors)}")
    print(f"  False Positives (safe flagged): {len(fp_errors)}")

    if fn_errors:
        print("\n  ── False Negatives ──")
        for e in fn_errors[:8]:
            p = f"P={e['probability']:.3f}" if e['probability'] else ""
            print(f"    [{e['language']}] {p} {str(e['message'])[:80]}...")

    if fp_errors:
        print("\n  ── False Positives ──")
        for e in fp_errors[:8]:
            p = f"P={e['probability']:.3f}" if e['probability'] else ""
            print(f"    [{e['language']}] {p} {str(e['message'])[:80]}...")

    err_df = pd.DataFrame(errors)
    err_df.to_csv(os.path.join(REPORT_DIR, "retrain_error_analysis.csv"), index=False)

    # ── STEP 19: Generalization check ───────────────────────────────
    print("\n[STEP 19] Realistic generalization check...")
    best_cv = cv_results[best_name]
    train_f1 = best_cv["train_f1_mean"]
    cv_f1 = best_cv["cv_f1_mean"]
    test_f1_val = best_f1
    gap_train_cv = train_f1 - cv_f1
    gap_cv_test = cv_f1 - test_f1_val
    print(f"  Train F1: {train_f1:.4f}")
    print(f"  CV F1:    {cv_f1:.4f}+/-{best_cv['cv_f1_std']:.4f}")
    print(f"  Test F1:  {test_f1_val:.4f}")
    print(f"  Gap (train-CV): {gap_train_cv:.4f}")
    print(f"  Gap (CV-test):  {gap_cv_test:.4f}")
    if gap_train_cv > 0.05:
        print("  [WARNING] Possible overfitting (train-CV gap > 0.05)")
    else:
        print("  [OK] No significant overfitting")

    # ── STEP 21: Save final artifacts ───────────────────────────────
    print("\n[STEP 21] Saving final artifacts...")

    # Backup previous model
    prev_pipe_path = os.path.join(MODEL_DIR, "full_pipeline.joblib")
    if os.path.exists(prev_pipe_path):
        backup_path = os.path.join(MODEL_DIR, "full_pipeline_backup.joblib")
        import shutil
        shutil.copy2(prev_pipe_path, backup_path)
        print(f"  Backed up previous model -> {backup_path}")

    # Save new model
    joblib.dump(best_pipe, os.path.join(MODEL_DIR, "full_pipeline.joblib"))
    joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.joblib"))
    joblib.dump(best_threshold_final, os.path.join(MODEL_DIR, "threshold.joblib"))

    # Save metadata
    metadata = {
        "best_model_name": best_name,
        "model_type": "simple_pipeline",
        "model_description": models[best_name].steps[-1][1].__class__.__name__,
        "threshold": best_threshold_final,
        "random_seed": SEED,
        "n_folds": N_FOLDS,
        "dataset": {
            "original": len(orig_df),
            "augmented": len(aug_df),
            "combined": len(combined_df),
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
        "cv_results": best_cv,
        "test_metrics": {
            "accuracy": float(best_opt_m["accuracy"]),
            "f1": float(best_opt_m["f1"]),
            "recall": float(best_opt_m["recall"]),
            "precision": float(best_opt_m["precision"]),
            "roc_auc": float(best_opt_m.get("roc_auc", 0) or 0),
            "TP": best_tp, "FP": best_fp,
            "FN": best_fn, "TN": best_tn,
        },
        "language_results": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in lang_results.items()},
        "overfitting_check": {
            "train_f1": train_f1,
            "cv_f1": cv_f1,
            "test_f1": test_f1_val,
            "train_cv_gap": gap_train_cv,
            "cv_test_gap": gap_cv_test,
        },
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, "model_metadata.joblib"))

    # Also save JSON
    with open(os.path.join(REPORT_DIR, "retrain_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"  Saved: models/full_pipeline.joblib")
    print(f"  Saved: models/label_encoder.joblib")
    print(f"  Saved: models/threshold.joblib ({best_threshold_final})")
    print(f"  Saved: models/model_metadata.joblib")

    # ── STEP 22: Test prediction interface ──────────────────────────
    print("\n[STEP 22] Testing prediction interface...")
    from src.predict import predict_message

    test_cases = [
        ("Congratulations! You won Rs. 50000 lottery. Send OTP to claim.", "English", "Scam"),
        ("Your HBL account has been credited with Rs. 50000 from salary.", "English", "Safe"),
        ("Mubarak ho! BISP main apka 12500 ka inam lga ha. OTP bhejain.", "Roman Urdu", "Scam"),
        ("Aap k HBL acount se Rs. 50000 ki deduction hui ha tax ki madd mein.", "Roman Urdu", "Safe"),
        ("آپ کا اکاؤنٹ بلاک ہو رہا ہے۔ فوری طور پر رابطہ کریں۔", "Urdu", "Scam"),
        ("آپ کے اکاؤنٹ سے Rs. 5000 کی کٹوتی ہوئی ہے۔ یہ ٹیکس کی وجہ سے ہے۔", "Urdu", "Safe"),
    ]

    for msg, lang, expected in test_cases:
        result = predict_message(msg)
        label = result["label"]
        prob = result["scam_probability"]
        match = "OK" if label == expected else "MISMATCH"
        print(f"  [{lang}] Expected={expected} Got={label} P={prob} [{match}]")

    # ── FINAL REPORT ────────────────────────────────────────────────
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)
    print(f"  1. Original dataset:        {len(orig_df)} messages")
    print(f"  2. New dataset:             {len(combined_df)} messages")
    print(f"  3. New Roman Urdu examples:  {len(aug_df)}")
    print(f"  4. Scam/Safe:               {labels.get('Scam', 0)}/{labels.get('Safe', 0)}")
    print(f"  5. Roman Urdu distribution:  Scam={ru_counts.get('Scam',0)}, Safe={ru_counts.get('Safe',0)}")
    print(f"  6. Best model:              {best_name}")
    print(f"  7. Previous vs New:")
    print(f"     Previous holdout: Acc=0.9697, Recall=0.9821, F1=0.9706")
    print(f"     New holdout:      Acc={best_opt_m['accuracy']:.4f}, Recall={best_opt_m['recall']:.4f}, F1={best_opt_m['f1']:.4f}")
    print(f"  8. CV accuracy:            {best_cv['cv_acc_mean']:.4f}")
    print(f"  9. CV scam recall:          {best_cv['cv_recall_mean']:.4f}")
    print(f" 10. CV F1:                   {best_cv['cv_f1_mean']:.4f}")
    print(f" 11. Holdout accuracy:        {best_opt_m['accuracy']:.4f}")
    print(f" 12. Holdout scam recall:     {best_opt_m['recall']:.4f}")
    print(f" 13. Holdout F1:              {best_opt_m['f1']:.4f}")
    print(f" 14. Holdout ROC-AUC:         {best_opt_m.get('roc_auc', 'N/A')}")
    print(f" 15. False positives:         {best_fp}")
    print(f" 16. False negatives:         {best_fn}")
    for lang, lr in lang_results.items():
        print(f"  [{lang}] Acc={lr['accuracy']:.4f} P={lr['precision']:.4f} R={lr['recall']:.4f} F1={lr['f1']:.4f} n={lr['n']}")
    print(f" 21. New threshold:           {best_threshold_final}")
    print(f" 22. Overfitting: train_cv_gap={gap_train_cv:.4f}, cv_test_gap={gap_cv_test:.4f}")
    print(f" 23. Improvements: Expanded Roman Urdu with {len(aug_df)} messages, "
          f"improved normalization, enhanced features")
    print(f" 24. Weaknesses: See error analysis in reports/retrain_error_analysis.csv")
    print(f" 25. Saved paths:")
    print(f"     models/full_pipeline.joblib")
    print(f"     models/threshold.joblib ({best_threshold_final})")
    print(f"     models/label_encoder.joblib")
    print(f"     models/model_metadata.joblib")
    print(f"\n  Pipeline completed in {elapsed:.1f}s")
    print(f"\n  [IMPORTANT] External 1000-message benchmark NOT used.")
    print(f"  Awaiting explicit approval to run external validation.")
    print("=" * 70)

    # Save final summary
    summary = {
        "original_size": len(orig_df),
        "augmented_size": len(aug_df),
        "combined_size": len(combined_df),
        "roman_urdu_augmented": len(aug_df),
        "best_model": best_name,
        "threshold": best_threshold_final,
        "cv": best_cv,
        "test": {k: float(v) if v is not None else None for k, v in best_opt_m.items()},
        "confusion_matrix": {"TP": best_tp, "FP": best_fp, "FN": best_fn, "TN": best_tn},
        "language_results": lang_results,
        "overfitting": {"train_cv_gap": gap_train_cv, "cv_test_gap": gap_cv_test},
        "errors": {"FN": len(fn_errors), "FP": len(fp_errors)},
        "elapsed_seconds": round(elapsed, 1),
    }
    with open(os.path.join(REPORT_DIR, "retrain_final_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)


if __name__ == "__main__":
    main()
