"""
final_blind_test.py
TRULY BLIND final test — messages written fresh, never used in any training or tuning.
This is the definitive generalization test before the hackathon presentation.

METHODOLOGY:
- 50 messages written AFTER all training, threshold tuning, and model selection
- No pattern from any previous error analysis was used
- Covers all 4 languages, diverse scam types, and legitimate messages
- Model has NEVER seen these messages or patterns derived from them
"""
import sys, os, io, warnings
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message
import joblib

# Load threshold for reference
threshold = joblib.load(os.path.join(PROJECT_ROOT, "models", "threshold.joblib"))
print(f"Model threshold: {threshold}")

# ── 50 FRESH MESSAGES (never seen, never scored) ──
BLIND_TEST = [
    # === SCAMS (25 messages, diverse types) ===

    # Pakistani mobile wallet scams
    ("S1", "Scam", "English",
     "JazzCash Alert: Your account will be suspended in 2 hours due to expired KYC. Update now at jazzcash.com.pk/verify or call 051-111-124444."),
    ("S2", "Scam", "Roman Urdu",
     "EasyPaisa: Aap k wallet se Rs. 8500 ki unauthorized payment hui hai. Cancel krne k liye apna PIN aur OTP 0302-8877665 par share kren."),

    # Government impersonation
    ("S3", "Scam", "Urdu",
     "ایف بی آر: آپ کا این ٹی این معطل ہو گیا ہے۔ 75,000 روپے جرمانہ ادا کریں ورنہ گرفتاری ہوگی۔ فوری رابطہ: 051-9221084۔"),
    ("S4", "Scam", "Roman Urdu",
     "NADRA: Aap ki family ka CNIC fraud case mein involve ha. Rs. 25,000 settlement fee ada na krne par FIR darj hogi. Contact 051-111786100."),

    # Romance/trust scams
    ("S5", "Scam", "Roman Urdu",
     "Salam, main Dubai mein kaam krta hoon. Aap ki profile dekh kr bohat pasand aayi. Kya hum WhatsApp par baat kr skte hain? Mera number +971501234567."),
    ("S6", "Scam", "English",
     "Dear, I am Prince Abdullah from Saudi Arabia. I have $2.5 million USD to transfer. I need a trustworthy partner. Reply with your bank details."),

    # Tech support scams
    ("S7", "Scam", "Mixed",
     "Microsoft Security Alert: Aap k computer mein virus detect hua hai. Call Microsoft certified technician at 0800-555-0199 for immediate fix."),
    ("S8", "Scam", "Urdu",
     "آپ کے فون میں خطرناک وائرس پایا گیا ہے۔ فوری طور پر 0800-123-4567 پر کال کریں ورنہ آپ کا تمام ڈیٹا حذف ہو جائے گا۔"),

    # Real estate / property scams
    ("S9", "Scam", "Roman Urdu",
     "DHA Phase 9 mein 1 kanal plot sirf Rs. 45 Lakh mein. Booking k liye Rs. 5 Lakh advance bhejen. Limited plots available. Contact 042-35761234."),
    ("S10", "Scam", "English",
     "Bahria Town Karachi: Premium plot in Precinct 12 at 40% below market rate. Pay Rs. 10 Lakh token money to secure. Contact sales: 021-111-000-222."),

    # Education scams
    ("S11", "Scam", "Roman Urdu",
     "NUST mein guaranteed admission! Rs. 2 Lakh fee de kr apni seat confirm kren. Koi test nahi chahiye. Contact education consultant 0333-9988776."),
    ("S12", "Scam", "Urdu",
     "بیرون ملک اسکالرشپ: ترکی میں مفت تعلیم۔ رجسٹریشن فیس 15,000 روپے۔ ویزا کی ضمانت۔ ابھی رابطہ کریں 042-99887766۔"),

    # Crypto / investment
    ("S13", "Scam", "Mixed",
     "Binance Pakistan: Invest Rs. 20,000 in Bitcoin aur earn karein Rs. 5000 daily. Guaranteed profit. WhatsApp group join karein: bit.ly/pakcrypto"),
    ("S14", "Scam", "English",
     "EXCLUSIVE: Pre-IPO shares of Careem Pakistan available at Rs. 50/share. Minimum investment Rs. 100,000. Expected listing price Rs. 500. Contact 021-111-222-333."),

    # SIM/telecom scams (new patterns)
    ("S15", "Scam", "Roman Urdu",
     "PTA: Aap ka number unregistered SIM list mein ha. 48 ghante mein biometric verification na krwane par number permanently band ho jaye ga. Call 051-5700800."),
    ("S16", "Scam", "Urdu",
     "زونگ: آپ کا نمبر لکی ڈرا میں 500,000 روپے کا فاتح ہے۔ انعام حاصل کرنے کے لیے 3,000 روپے ریچارج کریں اور رسید بھیجیں۔"),

    # Fake delivery / courier
    ("S17", "Scam", "Mixed",
     "Leopards Courier: Aap ka parcel from China customs mein hold hai. Rs. 4,500 duty pay karein via JazzCash to 0300-7778899 for immediate release."),
    ("S18", "Scam", "English",
     "Amazon.pk: Your package delivery failed 3 times. Pay Rs. 500 rescheduling fee at amazon.pk/redelivery within 24 hours or package will be returned."),

    # Impersonation (new variants)
    ("S19", "Scam", "Roman Urdu",
     "Aslam o alaikum, yeh aap ki bhanji Sana hai. Mera phone toot gaya hai naye number se msg kr rahi hoon. Urgent Rs. 8,000 chahiye medicine k liye. JazzCash pe bhejen."),
    ("S20", "Scam", "Mixed",
     "Dear Sir, this is your bank manager Mr. Tariq from HBL Gulberg. Aap ka Rs. 8 Lakh loan approve ho gaya hai. Rs. 15,000 processing fee account mein jama karwaen."),

    # QR code / digital scams
    ("S21", "Scam", "English",
     "State Bank: Scan this QR code to receive your Rs. 25,000 COVID relief payment. Enter your debit card PIN when prompted to verify identity."),
    ("S22", "Scam", "Roman Urdu",
     "JazzCash offer: Yeh QR code scan kren aur foran Rs. 3,000 cashback payen. Apna PIN enter kren verification k liye."),

    # Charity / donation scams
    ("S23", "Scam", "Urdu",
     "عید الاضحی قربانی مہم: صرف 25,000 روپے میں بکرا قربانی۔ رقم اس اکاؤنٹ میں بھیجیں: 0012-345-6789۔ رسید واٹس ایپ پر بھیجی جائے گی۔"),
    ("S24", "Scam", "Roman Urdu",
     "Flood Relief Fund: Sindh mein logon ki madad kren. Apna zakat Rs. 10,000 is Easypaisa number 0345-1234567 par bhejen. JazakAllah."),
    ("S25", "Scam", "Mixed",
     "URGENT: Pakistan flood victims ko help chahiye. Donate Rs. 5,000 or more via bank transfer to account PK36MEZN0012345678. Receipt will be emailed."),

    # === SAFE MESSAGES (25 messages, diverse types) ===

    # Legitimate banking
    ("R1", "Safe", "English",
     "HBL: Transaction alert. Rs. 12,500 debited from your account at Imtiaz Store, Gulberg on 28-Aug-2026 at 2:15 PM. Available balance: Rs. 95,340."),
    ("R2", "Safe", "Roman Urdu",
     "Meezan Bank: Aap ki monthly Zakat deduction of Rs. 1,250 ho gayi hai as per SBP guidelines. Remaining balance: Rs. 88,750."),
    ("R3", "Safe", "Urdu",
     "بینک الفلاح: آپ کا ماہانہ بیان تیار ہے۔ کل جمع: 125,000 روپے۔ کل اخراجات: 89,000 روپے۔ موجودہ بیلنس: 236,000 روپے۔"),

    # Government legitimate communications
    ("R4", "Safe", "Roman Urdu",
     "NADRA: Aap ka CNIC renewal ka application receive ho gaya hai. Processing time 15 working days. Track status at id.nadra.gov.pk. Koi fee nahi chahiye."),
    ("R5", "Safe", "English",
     "FBR: Your income tax return for FY 2025-26 has been processed. Refund of Rs. 35,000 will be credited to your bank account within 30 days. NTN: 8876543-2."),
    ("R6", "Safe", "Urdu",
     "پنجاب حکومت: مفت آٹا تقسیم پروگرام کل سے شروع ہو رہا ہے۔ قریبی یوٹیلٹی اسٹور پر شناختی کارڈ لے کر جائیں۔"),

    # Personal/family
    ("R7", "Safe", "Roman Urdu",
     "Ammi, main office se nikal gaya hoon. Traffic bohat hai, 45 min mein ghar pohanch jaoonga. Khana mat garam karo, aa kr khata hoon."),
    ("R8", "Safe", "Urdu",
     "بھائی، کل امی کی سالگرہ ہے۔ کیک کا آرڈر دے دیا ہے۔ شام 7 بجے سب مل کر منائیں گے۔"),
    ("R9", "Safe", "Mixed",
     "Yaar, aaj cricket match dekhne chalte hain. Pakistan vs Australia 7 PM pe. Meri jagah pe aa jao, BBQ bhi karenge."),

    # Service notifications
    ("R10", "Safe", "English",
     "Your K-Electric bill for August 2026 is Rs. 8,450. Due date: 15-Sep-2026. Pay via HBL app or any bank branch. Consumer no: 12345678."),
    ("R11", "Safe", "Roman Urdu",
     "PTCL: Aap ka broadband bill Rs. 3,200 generate ho gaya hai. Due date 10-Sep-2026. Online pay kren ptcl.com.pk/pay ya kisi bhi bank se."),
    ("R12", "Safe", "Urdu",
     "سوئی گیس: آپ کا اگست کا بل 4,500 روپے ہے۔ آخری تاریخ 20 ستمبر۔ لیٹ فیس سے بچنے کے لیے بروقت ادائیگی کریں۔"),

    # E-commerce / delivery
    ("R13", "Safe", "Mixed",
     "Daraz: Your order #789123 (Samsung Galaxy Buds) has been shipped via TCS. Tracking: TCS-2026-445566. Expected delivery: 30-Aug-2026."),
    ("R14", "Safe", "English",
     "Foodpanda: Your order from McDonald's Gulberg is being prepared. Estimated delivery: 25 minutes. Track your rider in the app."),

    # Telecom legitimate
    ("R15", "Safe", "Roman Urdu",
     "Jazz: Aap ne Rs. 1,500 ka Super Card package activate kia hai. 30GB data, 3000 Jazz min, 300 off-net min. Validity: 30 days."),
    ("R16", "Safe", "English",
     "Zong: Your postpaid bill for August 2026 is Rs. 2,100. Due date: 5-Sep-2026. Pay via MyZong app or JazzCash. Account: 0312-9876543."),
    ("R17", "Safe", "Urdu",
     "ٹیلی نار: آپ کا بیلنس 1,250 روپے ہے۔ آج کا استعمال: 50 ایم بی ڈیٹا، 15 منٹ کال۔"),

    # Educational
    ("R18", "Safe", "Roman Urdu",
     "LUMS: Fall 2026 semester starts on Sep 1. Course registration is now open on the portal. Classes begin Sep 4. Fee deadline: Aug 31."),
    ("R19", "Safe", "English",
     "NUST H-12: Mid-term examinations will be held from Oct 15-22, 2026. Date sheets available on CMS. Report to exam hall 15 minutes early."),

    # Healthcare
    ("R20", "Safe", "Urdu",
     "آغا خان ہسپتال: آپ کا اپائنٹمنٹ ڈاکٹر احمد کے ساتھ 5 ستمبر کو صبح 10 بجے مقرر ہے۔ براہ کرم 15 منٹ پہلے تشریف لائیں۔"),
    ("R21", "Safe", "Roman Urdu",
     "Shaukat Khanum: Aap ki lab report tayyar hai. CBC results normal hain. Report portal ya reception se collect kren. Koi charges nahi."),

    # Social / invitations
    ("R22", "Safe", "Mixed",
     "Assalam o Alaikum! Hamare ghar Eid dinner hai Saturday ko 8 PM. Aap sab ko invite hai. Address: House 45, Street 12, DHA Phase 5. Please confirm."),
    ("R23", "Safe", "Roman Urdu",
     "Bhai, kal Subhanullah ki namaz 5:45 AM pe hai masjid mein. Fajr 5:30 AM. Jaldi aa jana pehli saf mein jagah mil jaye gi."),

    # Work / professional
    ("R24", "Safe", "English",
     "Systems Ltd: Your August 2026 salary slip is available on the HR portal. Gross: Rs. 185,000. Net after tax: Rs. 152,300. Check email for details."),
    ("R25", "Safe", "Mixed",
     "Team reminder: Kal 11 AM pe client meeting hai Zoom pe. Meeting ID: 887-654-321. Agenda slides share folder mein upload kar dein aaj raat tak."),
]

# Run blind test
print(f"\n{'=' * 85}")
print(f"  TRULY BLIND FINAL TEST: {len(BLIND_TEST)} fresh messages (NEVER seen by model)")
print(f"{'=' * 85}\n")

correct = 0
total = len(BLIND_TEST)
fn_list = []  # missed scams
fp_list = []  # wrongly flagged safe

for msg_id, true_label, lang, msg in BLIND_TEST:
    result = predict_message(msg)
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

    status = "OK" if is_correct else "** FAIL **"
    p_str = f"P={prob:.3f}" if prob else "P=N/A"
    print(f"  [{status:10s}] {msg_id:<4s} [{lang:<10s}] Expected={true_label:<4s} Got={predicted:<4s} {p_str}")

acc = correct / total * 100
scam_msgs = [m for m in BLIND_TEST if m[1] == "Scam"]
safe_msgs = [m for m in BLIND_TEST if m[1] == "Safe"]
scam_caught = sum(1 for m in scam_msgs if predict_message(m[3])["label"] == "Scam")
safe_passed = sum(1 for m in safe_msgs if predict_message(m[3])["label"] == "Safe")

print(f"\n{'=' * 85}")
print(f"  FINAL BLIND RESULTS")
print(f"{'=' * 85}")
print(f"  Total:     {correct}/{total} correct ({acc:.1f}%)")
print(f"  Scams:     {scam_caught}/{len(scam_msgs)} caught ({scam_caught/len(scam_msgs)*100:.1f}% recall)")
print(f"  Safe:      {safe_passed}/{len(safe_msgs)} passed ({safe_passed/len(safe_msgs)*100:.1f}% specificity)")
print(f"  FN (missed scams):  {len(fn_list)}")
print(f"  FP (wrongly flagged): {len(fp_list)}")

if fn_list:
    print(f"\n  MISSED SCAMS ({len(fn_list)}):")
    for mid, lang, msg, prob in fn_list:
        print(f"    {mid} [{lang}] P={prob:.3f}: \"{msg[:90]}...\"")

if fp_list:
    print(f"\n  FALSE POSITIVES ({len(fp_list)}):")
    for mid, lang, msg, prob in fp_list:
        print(f"    {mid} [{lang}] P={prob:.3f}: \"{msg[:90]}...\"")

print(f"\n{'=' * 85}")
print(f"  VERDICT")
print(f"{'=' * 85}")
print(f"  This is the HONEST generalization score.")
print(f"  No training decisions were made using these messages.")
print(f"  Score: {acc:.1f}% — {'STRONG' if acc >= 94 else 'ACCEPTABLE' if acc >= 90 else 'NEEDS WORK'}")
print(f"  Use THIS number in the hackathon pitch.")
