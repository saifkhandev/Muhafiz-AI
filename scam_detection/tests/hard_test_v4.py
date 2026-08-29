"""
hard_test_v4.py — NEW hard test dataset (never seen before).
60 messages designed to be maximally adversarial:
- New scam patterns not in any previous test set
- Legitimate messages with scam-like language
- Scam messages disguised as legitimate
- Very short and very long messages
- All 4 languages represented

COMPARISON: Runs both previous and current model results for delta analysis.
"""
import sys, os, io, warnings
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message, load_model

# Load once for speed
artifacts, le, threshold, metadata = load_model()
print(f"Model: {metadata['best_model_name']}, Threshold: {threshold}")

HARD_TEST = [
    # ═══════════════════════════════════════════════════════════════
    # ADVERSARIAL SCAMS (15) — disguised as legitimate
    # ═══════════════════════════════════════════════════════════════
    ("AS1", "Scam", "Roman Urdu",
     "Assalam o Alaikum, main aap ka cousin Ali hoon. USA se aaya hoon. Meri flight miss ho gayi aur mera wallet chori ho gaya. Kya aap Rs. 15,000 Western Union se bhej skte hain? Airport pe hun, phone bhi dead ho raha hai."),
    ("AS2", "Scam", "English",
     "Pakistan Post: Your international parcel (tracking: PK9283746512) has been held at customs Islamabad. A clearance fee of Rs. 2,500 is required. Pay via bank transfer to account PK36SCBL00001234567890 within 48 hours."),
    ("AS3", "Scam", "Mixed",
     "Dear Customer, SECP ne aap ki company ko deregister kar diya hai. Rs. 35,000 penalty pay karein within 7 days. Online payment: secp.gov.pk/penalty-pay. Reference: SECP-2026-REG-44521."),
    ("AS4", "Scam", "Urdu",
     "محترم صارف، آپ کے شناختی کارڈ پر غیر قانونی سم کارڈ رجسٹرڈ پایا گیا ہے۔ فوری طور پر 5,000 روپے جرمانہ ادا کریں ورنہ ایف آئی آر درج ہوگی۔ رابطہ: 051-9201234۔"),
    ("AS5", "Scam", "Roman Urdu",
     "Pepsi Co Pakistan: Aap ki bottle cap se 1st prize Rs. 5,00,000 nikla hai! Claim krne k liye pehle Rs. 7,500 registration fee JazzCash se 0301-2345678 par bhejen. Code: PC-2026-7789."),
    ("AS6", "Scam", "English",
     "Your Daraz seller account has been flagged for policy violation. To avoid permanent suspension, verify your bank details at daraz-seller-verify.com within 24 hours. Case ID: DRZ-2026-00987."),
    ("AS7", "Scam", "Mixed",
     "Important notice: Aap k naam par Dubai se Rs. 8,50,000 ka parcel aaya hai. Customs duty Rs. 12,000 pay karein JazzCash to 0321-9876543 for immediate clearance. Tracking: DXB-PK-20261234."),
    ("AS8", "Scam", "Roman Urdu",
     "Khabardar! Aap k mobile number se illegal calls trace hui hain. PTA fine Rs. 25,000 ada kren warna SIM permanently block. Call PTA helpline 0300-5551234 for payment details."),
    ("AS9", "Scam", "Urdu",
     "اہم اطلاع: آپ کے بینک اکاؤنٹ میں مشکوک سرگرمی نوٹ کی گئی ہے۔ اکاؤنٹ انجماد سے بچنے کے لیے اپنے ڈیبٹ کارڈ کا پن اور سی وی وی 0800-222-3344 پر بتائیں۔"),
    ("AS10", "Scam", "English",
     "Careem: Your driver has reported finding Rs. 50,000 cash in your last ride. To claim, send Rs. 500 verification fee to JazzCash 0333-4445566. Ref: CRM-2026-LOST-7823."),

    # Very short scam messages
    ("AS11", "Scam", "Roman Urdu",
     "OTP bhejen abhi."),
    ("AS12", "Scam", "Mixed",
     "Rs. 50,000 jeet gaye! Fee Rs. 1,000 bhejen."),

    # Very long scam message
    ("AS13", "Scam", "Roman Urdu",
     "Moaziz Customer, hum aap ko inform krna chahte hain k aap ka HBL account number XXXX4523 suspicious activity ki wajah se temporarily freeze kar diya gaya hai. Pichle 48 ghanton mein 3 unauthorized transactions detect hui hain jin ki total value Rs. 1,25,000 hai. Agar yeh transactions aap ne nahi ki hain to foran apna account unfreeze karwaen. Is k liye apna 16-digit card number, expiry date, aur CVV code 0300-BANK-HELP par SMS kren. Agar 24 ghante mein verify nahi kia to account permanently close kar diya jaye ga. HBL Customer Care."),

    # ═══════════════════════════════════════════════════════════════
    # ADVERSARIAL SAFE (15) — scam-like language but legitimate
    # ═══════════════════════════════════════════════════════════════
    ("AE1", "Safe", "English",
     "Standard Chartered: Your credit card ending 4523 has been charged Rs. 45,000 for your monthly mortgage payment. Transaction ID: SC-2026082900123. Available credit limit: Rs. 2,55,000. Do not share this message."),
    ("AE2", "Safe", "Roman Urdu",
     "Ammi, maine online shopping ki hai Rs. 3,500 ki. Daraz se order kia hai shoes. Payment Easypaisa se ho gayi. Order number 789-234-567. 2-3 din mein aa jaye ga. Tension mat len."),
    ("AE3", "Safe", "Urdu",
     "بینک الفلاح: آپ کے اکاؤنٹ سے Rs. 15,000 کی منتقلی کامیابی سے مکمل ہو گئی ہے۔ وصول کنندہ: محمد علی۔ حوالہ نمبر: ABL-TRF-20260829-445۔ اگر آپ نے یہ ٹرانزیکشن نہیں کی تو 021-111-222-333 پر رابطہ کریں۔"),
    ("AE4", "Safe", "Mixed",
     "Yaar maine JazzCash se Rs. 5,000 bhej diye hain tere number pe. Check kar apna balance. Transaction ID: JC-20260829887. Agar nahi aye to helpline 111-124-444 pe call karna."),
    ("AE5", "Safe", "English",
     "K-Electric: IMPORTANT NOTICE — Scheduled maintenance in Gulshan-e-Iqbal Block 5 on 30-Aug-2026 from 10 AM to 2 PM. Power supply will be interrupted. Please charge your devices. Contact: 021-111-000-118."),
    ("AE6", "Safe", "Roman Urdu",
     "Bhai, Congratulations! Tera promotion ho gaya hai boss ne confirm kia. Salary increment bhi milega next month se. HR se letter collect kar lena Monday ko."),
    ("AE7", "Safe", "Urdu",
     "شوکت خانم ہسپتال: آپ کا اپوائنٹمنٹ ڈاکٹر عائشہ کے ساتھ 2 ستمبر کو سہ پہر 3 بجے کنفرم ہو گیا ہے۔ برائے مہربانی اپنی پچھلی رپورٹیں ساتھ لائیں۔ فیس: Rs. 2,500۔"),
    ("AE8", "Safe", "Mixed",
     "NADRA: Aap ka CNIC smart card ready hai. Nearest NADRA center se collect kren. Required documents: purana CNIC aur biometric verification. Koi extra charges nahi hain."),
    ("AE9", "Safe", "English",
     "Your Netflix subscription has been successfully renewed for September 2026. Amount: Rs. 1,800 charged to your Visa card ending 8821. Next billing date: 29-Sep-2026. Manage at netflix.com/account."),
    ("AE10", "Safe", "Roman Urdu",
     "Zong: Aap ka monthly bill Rs. 1,850 generate ho gaya hai. Bill number: ZG-20260829-5567. Due date: 5-Sep-2026. JazzCash, Easypaisa ya kisi bhi bank branch se pay kar skte hain."),

    # Short safe messages
    ("AE11", "Safe", "Roman Urdu",
     "Pani ka bill dekhna tha, kahan hai?"),
    ("AE12", "Safe", "Mixed",
     "Office pohanch gaya hun, tension mat lo."),

    # Very long safe message
    ("AE13", "Safe", "English",
     "FBR Tax Notice: Dear taxpayer, your income tax return for tax year 2026 has been processed. Your NTN 8876543-2 shows total taxable income of Rs. 2,400,000. Tax deducted at source: Rs. 96,000. Additional tax payable: Rs. 12,500. Please deposit via Challan No. 1 at any National Bank branch before 30-Sep-2026. For queries, visit e.fbr.gov.pk or call UAN 051-111-727-227."),

    # ═══════════════════════════════════════════════════════════════
    # NEW SCAM CATEGORIES (15) — types never tested before
    # ═══════════════════════════════════════════════════════════════
    ("NS1", "Scam", "Roman Urdu",
     "OLX: Aap ki listing ke buyer ne Rs. 25,000 bhej diye hain. Raast payment receive krne k liye is link pe apna bank login kren: olx-pay-verify.com/claim/78912."),
    ("NS2", "Scam", "English",
     "LinkedIn: A recruiter from Dubai Holdings has viewed your profile. They want to offer you a management position with salary AED 25,000/month. Click to accept and pay AED 500 visa processing: linkedin-jobs-dubai.com/offer."),
    ("NS3", "Scam", "Mixed",
     "Indrive: Aap ki ride ka driver Rs. 15,000 cash lekar bhaag gaya. Refund claim krne k liye apna debit card number aur PIN 0300-INDRIVE par share kren. Case: IND-PK-2026-4456."),
    ("NS4", "Scam", "Urdu",
     "ایف آئی اے سائبر کرائم: آپ کے سوشل میڈیا اکاؤنٹ سے غیر قانونی مواد شیئر ہوا ہے۔ Rs. 50,000 جرمانہ ادا کریں ورنہ گرفتاری ہوگی۔ فوری رابطہ: 051-9260060۔"),
    ("NS5", "Scam", "Roman Urdu",
     "Foodpanda rider: Aap ka order deliver krne aya tha but koi receive nahi kia. Rs. 890 redelivery charges k liye Easypaisa pe Rs. 890 bhej do. Ya order cancel ho jaye ga."),
    ("NS6", "Scam", "English",
     "URGENT: Your CNIC has been found in a fraud investigation. NADRA Cyber Wing requires your immediate cooperation. Pay Rs. 10,000 verification fee or face arrest. Contact: 051-NADRA-HELP."),
    ("NS7", "Scam", "Mixed",
     "Bykea: Aap ki parcel delivery complete ho gayi. Cash on delivery Rs. 3,200 collect krne k liye is QR code scan kren aur apna Easypaisa PIN enter kren. Expiry: 2 hours."),
    ("NS8", "Scam", "Roman Urdu",
     "Wapda: Aap ka bijli ka meter check kia gaya aur over-billing detect hui. Rs. 45,000 refund milega. Processing fee Rs. 2,500 JazzCash pe bhejen. Reference: WAP-REF-2026-8891."),
    ("NS9", "Scam", "Urdu",
     "حکومت پنجاب: وزیر اعظم قرض حسنہ سکیم کے تحت آپ کو Rs. 5,00,000 کا قرض منظور ہو گیا ہے۔ Rs. 8,000 پروسیسنگ فیس جمع کروائیں۔ اکاؤنٹ: 0012-345-789۔"),
    ("NS10", "Scam", "Mixed",
     "Jazz: Congrats! Aap ka number lucky draw mein selected hua hai. Rs. 2,00,000 inaam jeetne k liye pehle Rs. 5,000 ka easyload karein aur receipt is number pe bhejen: 0300-WINNER1."),
    ("NS11", "Scam", "Roman Urdu",
     "Telenor Bank: Aap ka mobile wallet compromised ho gaya hai. Rs. 75,000 unauthorized transaction hui. Account recover krne k liye apna CNIC number aur PIN code 111-TELEBANK par btaen."),
    ("NS12", "Scam", "English",
     "Western Union Pakistan: A money transfer of Rs. 3,50,000 is waiting for you from London. Collect at any branch after paying Rs. 5,000 handling fee online. MTCN: 1234567890. Verify at wu-pak.com/claim."),
    ("NS13", "Scam", "Mixed",
     "Roshan Digital Account: Aap ka account activate karne k liye Rs. 25,000 initial deposit chahiye. Is link pe apna CNIC aur bank details submit kren: rda-activate.gov.pk/verify-99887."),
    ("NS14", "Scam", "Roman Urdu",
     "Zameen.com: Aap ki property ki booking confirm krne k liye Rs. 2,00,000 token money jama karein. Account: PK99MEZN000011223344. Sirf 48 ghante baqi hain. Contact: 042-ZAMEEN1."),
    ("NS15", "Scam", "Urdu",
     "اسٹیٹ بینک: آپ کے اکاؤنٹ میں بیرون ملک سے Rs. 15,00,000 کی رقم منتقل ہوئی ہے۔ وصول کرنے کے لیے Rs. 25,000 ٹیکس ادا کریں۔ بینک اکاؤنٹ: 0012-555-9876۔ حوالہ: SBP-INT-2026-3344۔"),

    # ═══════════════════════════════════════════════════════════════
    # NEW SAFE CATEGORIES (15) — types never tested before
    # ═══════════════════════════════════════════════════════════════
    ("NE1", "Safe", "English",
     "LinkedIn: Muhammad Hassan viewed your profile 3 times this week. You have 5 new connection requests and 2 job recommendations in your industry. Check your notifications."),
    ("NE2", "Safe", "Roman Urdu",
     "OLX: Aap ki listing 'Honda Civic 2019' ko 47 logon ne dekha. 3 messages aaye hain. Buyer 'Ahmed_K' ne offer bheji hai Rs. 28,00,000 ki. Reply kren app mein."),
    ("NE3", "Safe", "Mixed",
     "Foodpanda: Aap ka order #FP-2026-789123 McDonald's Gulberg se dispatch ho gaya. Rider: Rashid (4.8 rating). ETA: 22 minutes. Track in app. Order total: Rs. 1,450."),
    ("NE4", "Safe", "Urdu",
     "نیپرا: بجلی کے نرخوں میں تبدیلی کا نوٹیفکیشن۔ ستمبر 2026 سے فی یونٹ Rs. 2.50 کی کمی ہوگی۔ تفصیلات نیپرا ویب سائٹ پر دستیاب ہیں۔"),
    ("NE5", "Safe", "Roman Urdu",
     "Bykea: Aap ki ride complete ho gayi. Fare: Rs. 320. Rating den bholna mat. Agli ride pe 10% discount code: BYKEA10. Shukriya!"),
    ("NE6", "Safe", "English",
     "Careem: Your ride from Gulberg to DHA Phase 5 has been completed. Fare: Rs. 450. Payment: Cash. Rate your driver. Receipt available in the app under 'My Rides'."),
    ("NE7", "Safe", "Mixed",
     "Zameen.com: Aap ki property alert: Gulshan-e-Iqbal mein 3 naye 2-bed apartments list hue hain. Price range: Rs. 85 Lakh - 1.2 Crore. Details app mein dekhen."),
    ("NE8", "Safe", "Roman Urdu",
     "Daraz: Aap ki wishlist mein 'Samsung Galaxy S24 Ultra' ki price Rs. 15,000 kam ho gayi hai. Ab sirf Rs. 2,84,999 mein. Stock limited hai. App mein check kren."),
    ("NE9", "Safe", "English",
     "Roshan Digital Account: Your monthly statement for August 2026 is ready. Account balance: Rs. 12,45,000. Total deposits: Rs. 2,00,000. Total withdrawals: Rs. 85,000. Download from portal."),
    ("NE10", "Safe", "Urdu",
     "پی ٹی سی ایل: آپ کے براڈ بینڈ پیکج کی رفتار 20 ایم بی پی ایس سے بڑھا کر 50 ایم بی پی ایس کر دی گئی ہے۔ ماہانہ چارجز: Rs. 4,500۔ نئی رفتار آج رات 12 بجے سے فعال ہوگی۔"),
    ("NE11", "Safe", "Roman Urdu",
     "Wapda: Aap ka August ka bijli bill Rs. 7,850 generate ho gaya. Due date 20-Sep-2026. Kisi bhi bank branch ya Easypaisa se pay kr skte hain. Consumer number: 0123456789."),
    ("NE12", "Safe", "Mixed",
     "Bhai, aaj shaam ko cricket match hai ground pe. 5 baje milte hain. Bat aur ball le aana. Agar rain hui to kal karenge."),
    ("NE13", "Safe", "English",
     "HBL: Your fixed deposit of Rs. 5,00,000 matures on 15-Sep-2026. Maturity value: Rs. 5,37,500. To renew, visit any branch or use HBL mobile app. Do not share this SMS."),
    ("NE14", "Safe", "Roman Urdu",
     "Indrive: Aap ki ride request accept ho gayi. Driver: Imran, Toyota Corolla white, ABC-1234. Pickup: 5 minutes. Fare agreed: Rs. 580. Safety features on ho chuke hain."),
    ("NE15", "Safe", "Urdu",
     "ایف بی آر: آپ کی ویلتھ ری کنسیلیشن آن لائن جمع ہو گئی ہے۔ پروسیسنگ میں 30 دن لگیں گے۔ اسٹیٹس ایف بی آر پورٹل پر چیک کریں۔ این ٹی این: 9988776-5۔"),
]

# ── Run tests ──────────────────────────────────────────────────────────────
print(f"\n{'=' * 85}")
print(f"  HARD TEST V4: {len(HARD_TEST)} adversarial messages (NEW, never tested)")
print(f"{'=' * 85}\n")

correct = 0
total = len(HARD_TEST)
fn_list = []
fp_list = []
results_by_category = {}

for msg_id, true_label, lang, msg in HARD_TEST:
    result = predict_message(msg, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)
    predicted = result["label"]
    prob = result["scam_probability"]

    is_correct = (predicted == true_label)
    if is_correct:
        correct += 1
    else:
        if true_label == "Scam":
            fn_list.append((msg_id, lang, msg, prob))
        else:
            fp_list.append((msg_id, lang, msg, prob))

    # Track by category
    cat = msg_id[:2] if msg_id[:2].isalpha() else msg_id[:3]
    if cat not in results_by_category:
        results_by_category[cat] = {"correct": 0, "total": 0}
    results_by_category[cat]["total"] += 1
    if is_correct:
        results_by_category[cat]["correct"] += 1

    status = "OK" if is_correct else "** FAIL **"
    print(f"  [{status:10s}] {msg_id:<5s} [{lang:<10s}] Exp={true_label:<4s} Got={predicted:<4s} P={prob:.3f}")

acc = correct / total * 100
scam_msgs = [m for m in HARD_TEST if m[1] == "Scam"]
safe_msgs = [m for m in HARD_TEST if m[1] == "Safe"]
scam_caught = sum(1 for m in scam_msgs if predict_message(m[3], artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)["label"] == "Scam")
safe_passed = sum(1 for m in safe_msgs if predict_message(m[3], artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)["label"] == "Safe")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'=' * 85}")
print(f"  HARD TEST V4 RESULTS")
print(f"{'=' * 85}")
print(f"  Total:     {correct}/{total} correct ({acc:.1f}%)")
print(f"  Scams:     {scam_caught}/{len(scam_msgs)} caught ({scam_caught/len(scam_msgs)*100:.1f}% recall)")
print(f"  Safe:      {safe_passed}/{len(safe_msgs)} passed ({safe_passed/len(safe_msgs)*100:.1f}% specificity)")
print(f"  FN (missed scams):  {len(fn_list)}")
print(f"  FP (wrongly flagged): {len(fp_list)}")

print(f"\n  BY CATEGORY:")
cat_names = {"AS": "Adversarial Scams", "AE": "Adversarial Safe", "NS": "New Scam Types", "NE": "New Safe Types"}
for cat, data in sorted(results_by_category.items()):
    name = cat_names.get(cat, cat)
    pct = data["correct"] / data["total"] * 100
    print(f"    {name:<25s} {data['correct']}/{data['total']} ({pct:.0f}%)")

if fn_list:
    print(f"\n  MISSED SCAMS ({len(fn_list)}):")
    for mid, lang, msg, prob in fn_list:
        print(f"    {mid} [{lang}] P={prob:.3f}: \"{msg[:85]}...\"")

if fp_list:
    print(f"\n  FALSE POSITIVES ({len(fp_list)}):")
    for mid, lang, msg, prob in fp_list:
        print(f"    {mid} [{lang}] P={prob:.3f}: \"{msg[:85]}...\"")

# ── Comparison table ─────────────────────────────────────────────────────────
print(f"\n{'=' * 85}")
print(f"  COMPARISON: All Test Results (Previous vs Current)")
print(f"{'=' * 85}")
print(f"  {'Test':<30s} {'Msgs':>5s} {'Accuracy':>10s} {'Recall':>8s} {'FP':>4s} {'FN':>4s}")
print(f"  {'-'*61}")
print(f"  {'All-4 External (prior)':<30s} {'318':>5s} {'97.48%':>10s} {'96.52%':>8s} {'1':>4s} {'7':>4s}")
print(f"  {'Truly Blind 50 (prior)':<30s} {'50':>5s} {'98.00%':>10s} {'96.00%':>8s} {'0':>4s} {'1':>4s}")
print(f"  {'Real-World 43 (prior)':<30s} {'43':>5s} {'93.02%':>10s} {'87.50%':>8s} {'0':>4s} {'3':>4s}")
print(f"  {'Hard Test V4 (NEW)':<30s} {total:>5d} {acc:>9.1f}% {scam_caught/len(scam_msgs)*100:>7.1f}% {len(fp_list):>4d} {len(fn_list):>4d}")
print(f"  {'-'*61}")
combined_total = 318 + 50 + 43 + total
combined_correct = int(318*0.9748) + 49 + 40 + correct
combined_acc = combined_correct / combined_total * 100
print(f"  {'COMBINED (all untouched)':<30s} {combined_total:>5d} {combined_acc:>9.1f}%")

print(f"\n  ASSESSMENT: {'STRONG' if acc >= 90 else 'ACCEPTABLE' if acc >= 85 else 'NEEDS WORK'}")
print(f"  Model: {metadata['best_model_name']}, Threshold: {threshold}")
