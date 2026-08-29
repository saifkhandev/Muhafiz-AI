"""
V4 Final Holdout Validation — 100 fresh messages, NEVER used in any prior set.
50 scam + 50 safe, maximum difficulty.
This is the FINAL proof that V4 generalizes to unseen data.
"""
import sys, os, warnings, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message, load_model

# ═══════════════════════════════════════════════════════════════════════
# 50 SCAM MESSAGES — completely new patterns, never seen before
# ═══════════════════════════════════════════════════════════════════════
SCAM = [
    # Novel BISP variants
    ("S01", "Scam", "Ehsaas Tahafuz: Aap ki family ko Rs. 35,000 health grant milegi. Rs. 750 registration fee JazzCash 0345-667788 pe bhejen."),
    ("S02", "Scam", "BISP 8171: Aap ka survey complete nahi hua. Rs. 18,000 band ho jayenge. 8171 pe CNIC bhejen abhi."),
    ("S03", "Scam", "بینظیر انکم سپورٹ: آپ کی 13000 روپے کی قسط تیار ہے۔ 350 روپے پراسیسنگ فیس ایزی پیسہ پر بھیجیں۔"),

    # Novel delivery scams
    ("S04", "Scam", "CallCourier: Aap ka parcel Islamabad airport pe ruka hai. Rs. 4,200 customs duty pay kren callcourier-pk.com/parcel-8821"),
    ("S05", "Scam", "MnP Express: Shipment #MN-44521 returned to sender. Rs. 1,200 re-dispatch fee bhejen warna parcel destroy ho jaye ga."),
    ("S06", "Scam", "Trax Logistics: Aap k parcel mein prohibited item mila. Rs. 8,500 fine ada kren warna police report darj hogi. Ref: TRX-9928."),

    # Novel job scams
    ("S07", "Scam", "Careem is hiring 200 drivers in Karachi. Monthly income Rs. 120,000 guaranteed. Vehicle deposit Rs. 25,000. Apply: careem-drivers.pk"),
    ("S08", "Scam", "Remote TikTok moderator needed. Rs. 3,500/day. Joining fee Rs. 2,000 via Easypaisa. WhatsApp: 0312-TIKTOK1."),
    ("S09", "Scam", "Qatar World Cup hospitality jobs: Rs. 200,000/month. Agent fee Rs. 80,000. Visa guaranteed. Apply within 48 hours."),

    # Novel prize scams
    ("S10", "Scam", "Jazz World Cup Prediction: Aap ne Rs. 750,000 jeeta hai! Claim krne k liye Rs. 12,000 tax JazzCash pe bhejen. Code: JWC-2026."),
    ("S11", "Scam", "Tapal Tea: Bottle cap se 2nd prize Rs. 100,000 nikla! Delivery fee Rs. 3,500 bhejen. Contact: 0321-TAPAL1."),
    ("S12", "Scam", "مبارک ہو! آپ کو عمرہ قرعہ اندازی میں منتخب کیا گیا ہے۔ 15000 روپے رجسٹریشن فیس جمع کروائیں۔"),

    # Novel bank/financial scams
    ("S13", "Scam", "Raast Payment: Rs. 85,000 aap k account mein credit hone wale hain. Verify krne k liye apna 4-digit PIN 111-RAAST par btaen."),
    ("S14", "Scam", "MCB Islamic: Aap ka Musharakah account suspend ho gaya hai. Rs. 2,000 bhej kr reactivate kren. Account: PK36MCB0000123456."),
    ("S15", "Scam", "Zarai Taraqiati Bank: Kissan loan Rs. 300,000 approved. Processing fee Rs. 15,000 via JazzCash. Apply before 15-Sep."),
    ("S16", "Scam", "آسکری بینک: آپ کے اکاؤنٹ میں 75000 روپے آئے ہیں۔ OTP کوڈ شیئر کریں وصول کرنے کے لیے۔"),

    # Novel telecom scams
    ("S17", "Scam", "Jazz 5G SIM: Aap ka number 5G k liye upgrade ho sakta hai. Rs. 1,500 bhej kr new SIM ghar mangwaen. Offer expires today."),
    ("S18", "Scam", "Zong Super Card Pro: Unlimited everything. Rs. 2,999/month. Activation: Rs. 500 bhejen 0312-ZONG123 par."),
    ("S19", "Scam", "PTA: Aap ka phone IMEI non-compliant hai. Rs. 8,000 DIRBS fee ada kren warna SIM block. Pay at ptcl.com.pk/dirbs-pay"),

    # Novel government impersonation
    ("S20", "Scam", "FBR Audit: Aap ki tax return mein discrepancy mili hai. Rs. 35,000 penalty pay kren warna prosecution hoga. Ref: FBR-AUD-2026-8832."),
    ("S21", "Scam", "NADRA Family Verification: Aap k deceased father ki property transfer k liye Rs. 5,000 verification fee chahiye. Apply: nadra-fam.gov.pk"),
    ("S22", "Scam", "Excise Punjab: Aap ki gari ka token tax 3 saal se unpaid hai. Rs. 12,000 + Rs. 4,000 penalty. Pay at excise.punjab.gov.pk/token"),

    # Novel phishing
    ("S23", "Scam", "WhatsApp: Aap ka number 47 logon ne spam report kia hai. Account verify kren warna 72 hours mein permanently delete. Verify: wa-verify-9921.pk"),
    ("S24", "Scam", "Gmail: 3 unauthorized login attempts from Moscow. Account lock hone wala hai. Secure kren: google-secure-verify.pk/recover"),
    ("S25", "Scam", "Daraz Pro Seller: Aap ka store 48 hours mein close ho jaye ga. Verify bank details: daraz-seller-portal.pk/verify-8872"),

    # Novel investment/forex
    ("S26", "Scam", "Halal Crypto Fund: Shariah-compliant crypto trading. Rs. 25,000 invest kren, 30% monthly return. Mufti-approved. Join WhatsApp."),
    ("S27", "Scam", "PSX Penny Stocks: Rs. 10,000 se shuru kren. Daily Rs. 2,000 profit guaranteed. SECP registered broker. WhatsApp: 0300-STOCK1."),
    ("S28", "Scam", "Gold Savings Plan: Daily Rs. 500 invest kren. 1 saal mein 1 tola gold guaranteed. Registration fee Rs. 2,000."),

    # Novel impersonation
    ("S29", "Scam", "Assalam o Alaikum bhai, main Dubai mein hun. Meri wife ka accident ho gaya hai. Hospital deposit Rs. 50,000 chahiye urgently. Western Union se bhejo."),
    ("S30", "Scam", "CEO here. Board meeting cancelled. Before that, urgently transfer Rs. 200,000 to vendor account PK99HBL00004455. Will explain later."),

    # Novel tech support
    ("S31", "Scam", "Norton Antivirus: Aap ka subscription expire ho gaya hai. Rs. 4,500 renew kren warna computer unprotected hai. Call: 0800-NORTON1."),
    ("S32", "Scam", "Google Chrome: Critical security update required. Download at chrome-update-secure.pk to prevent data theft."),

    # Novel real estate
    ("S33", "Scam", "DHA City Karachi: Phase 2 plot Rs. 45 lakh mein available. Booking Rs. 200,000. Transfer to PK99MEZN000055667. Agent: 0300-DHA123."),
    ("S34", "Scam", "Bahria Enclave: 5 marla plot on installments. Monthly Rs. 35,000. Down payment Rs. 500,000. Visit bahriaenclave-book.com"),

    # Novel charity
    ("S35", "Scam", "Flood Relief Fund 2026: Donate Rs. 5,000 to help Sindhi families. JazzCash: 0300-FLOOD26. Government-approved NGO."),
    ("S36", "Scam", "Edhi Foundation: Aap ki zakat Rs. 12,000 accept ho gayi hai. Processing fee Rs. 500 bhejen. Account: PK36EDHI000012345."),

    # Novel short/deceptive
    ("S37", "Scam", "CNIC expired. Rs. 2000 bhejo."),
    ("S38", "Scam", "Rs. 500,000 approved. Fee Rs. 10,000 first. Call now."),
    ("S39", "Scam", "آپ کا اکاؤنٹ ہیک ہو گیا ہے۔ بازیابی کے لیے 3000 روپے بھیجیں۔"),

    # Novel mixed-language
    ("S40", "Scam", "Dear Customer, aap ki HBL debit card cloned ho gayi hai overseas mein. Rs. 35,000 unauthorized transaction. Call 0300-HBL-HELP for refund processing."),
    ("S41", "Scam", "IMPORTANT: Aap k CNIC pe 5 SIMs registered hain jo illegal activity mein use ho rahi hain. PTA fine Rs. 15,000. Pay at pta-sims.gov.pk"),

    # Novel Urdu scams
    ("S42", "Scam", "پاکستان پوسٹ: آپ کا بین الاقوامی پارسل کسٹم میں ہے۔ 5000 روپے ڈیوٹی ادا کریں۔"),
    ("S43", "Scam", "ایف آئی اے: آپ کے نام پر منی لانڈرنگ کیس درج ہے۔ 25000 روپے ضمانت ادا کریں ورنہ گرفتاری۔"),

    # Novel wallet scams
    ("S44", "Scam", "SadaPay: Aap ka card compromised ho gaya hai international transaction mein. Rs. 45,000 deducted. Reverse krne k liye card CVV share kren."),
    ("S45", "Scam", "NayaPay: Rs. 20,000 cashback mega draw! Rs. 500 entry fee bhejen. Draw on 15-Sep. JazzCash: 0345-NAYAPAY."),

    # Novel loan scam
    ("S46", "Scam", "Akhuwat Foundation: Interest-free loan Rs. 200,000 approved. Documentation fee Rs. 5,000. Visit nearest center with CNIC + Rs. 5,000."),
    ("S47", "Scam", "Kashf Microfinance: Women's business loan Rs. 100,000. Processing fee Rs. 3,000 via Easypaisa. Apply: kashf-women.pk"),

    # Novel SIM/mobile
    ("S48", "Scam", "Jazz: Aap ka number 2 saal se inactive hai. Rs. 500 bhej kr number save kren warna auction ho jaye ga."),
    ("S49", "Scam", "Ufone: International roaming bill Rs. 45,000 unpaid. Pay immediately or legal action. Contact: 0333-UAN-UFONE."),
    ("S50", "Scam", "Telenor Microfinance Bank: Aap ki savings account mein suspicious login hui hai. PIN reset kren: telenorbank-secure.pk/reset"),
]

# ═══════════════════════════════════════════════════════════════════════
# 50 SAFE MESSAGES — legitimate but keyword-heavy, designed to trigger FPs
# ═══════════════════════════════════════════════════════════════════════
SAFE = [
    # Legitimate bank notifications with money amounts
    ("R01", "Safe", "HBL: Your monthly mortgage installment of Rs. 42,000 deducted on 01-Sep-2026. Remaining tenure: 12 years 4 months."),
    ("R02", "Safe", "Meezan Bank: Your car financing EMI Rs. 28,500 auto-deducted. Next due date: 01-Oct-2026. Account: XXXX7721."),
    ("R03", "Safe", "UBL: Remittance of Rs. 150,000 received from Muhammad Khan (UAE) via Roshan Digital Account. Credited to your account."),
    ("R04", "Safe", "MCB: Your mutual fund redemption of Rs. 500,000 processed. Amount credited to account XXXX3344. Tax deducted: Rs. 7,500."),
    ("R05", "Safe", "بینک الحبیب: آپ کی تنخواہ 85000 روپے جمع ہو گئی ہے۔ بیلنس: 125000 روپے۔"),

    # Legitimate government messages
    ("R06", "Safe", "NADRA: Aap ka CNIC renewal application receive ho gaya hai. Processing time: 15 working days. Collect from Clifton center."),
    ("R07", "Safe", "FBR: Aap ka NTN 8876543-2 active taxpayer list mein shamil hai. Verify at fbr.gov.pk/atl. No action required."),
    ("R08", "Safe", "BISP: Aap ki Rs. 13,000 ki payment 15-Sep-2026 ko HBL branch se disburse ho gayi. CNIC dikha kr collect kren. Koi fee NAHI."),
    ("R09", "Safe", "Ehsaas: Monthly wazifa Rs. 14,000 approved for your family. Collect from nearest BISP tehsil office with valid CNIC."),
    ("R10", "Safe", "پی ٹی اے: آپ کا فون IMEI 356789012345678 رجسٹرڈ ہے۔ کوئی ایکشن ضروری نہیں۔"),

    # Legitimate personal money conversations
    ("R11", "Safe", "Ammi, maine easypaisa se Rs. 8,000 bhej diye hain aap ko. Check kren. Ghar ka bill pay kr dena."),
    ("R12", "Safe", "Bhai meri salary kal aa jaye gi. Rs. 15,000 wapis bhej dunga promise. Thora tight month hai."),
    ("R13", "Safe", "Yaar Rs. 3,500 ka electricity bill aa gaya hai. Bohat zyada hai. K-Electric ko complaint kren?"),
    ("R14", "Safe", "Baji ne Rs. 25,000 bhej diye hain Eidi ke. Bohat shukriya un ka. Kal milne aa rahi hain."),
    ("R15", "Safe", "Abbu ki pension Rs. 45,000 aa gayi hai bank mein. Main ATM se nikalwa dunga shaam ko."),

    # Legitimate business/professional
    ("R16", "Safe", "HR Notice: Your annual increment of 12% effective from 01-Sep-2026. Revised salary: Rs. 134,400/month. Letter in your email."),
    ("R17", "Safe", "Invoice paid: Client XYZ Corp transferred Rs. 450,000 for project milestone 3. Bank confirmation received."),
    ("R18", "Safe", "Payroll: September salary will be disbursed on 28th due to Eid holidays. No action needed from employees."),
    ("R19", "Safe", "Vendor alert: Raw material order #PO-2026-889 confirmed. Total: Rs. 225,000. Delivery expected 10-Sep."),
    ("R20", "Safe", "Freelancer.com: Client released milestone payment of $750. Converted to Rs. 209,250. Available in your bank in 3-5 days."),

    # Legitimate delivery/e-commerce
    ("R21", "Safe", "Daraz: Aap ka order #DRZ-88721 successfully delivered. Product: Samsung Earbuds. Rate the seller in the app."),
    ("R22", "Safe", "TCS: Parcel #TCS-9912345 out for delivery today. Rider: Imran Ahmed. Expected by 4 PM. Track at tcs.com.pk"),
    ("R23", "Safe", "Foodpanda: Your order from Bun Kebab Wala has been delivered. Total: Rs. 680. Enjoy your meal!"),
    ("R24", "Safe", "PostEx: COD collection of Rs. 12,500 from customer in Lahore. Transfer to your bank account in 48 hours."),

    # Legitimate healthcare
    ("R25", "Safe", "Aga Khan: Appointment with Dr. Fatima confirmed for 10-Sep at 2:30 PM. Bring previous lab reports. Fee: Rs. 3,500 at counter."),
    ("R26", "Safe", "Shaukat Khanum: Aap ka blood test report ready hai. All values normal. Download from patient portal."),
    ("R27", "Safe", "Pharmacy: Aap ki insulin pens delivered via Bykea. Store at 2-8°C. Total: Rs. 4,200. Receipt in bag."),

    # Legitimate utility/bills
    ("R28", "Safe", "K-Electric: Aap ka August bill Rs. 15,200 generate ho gaya hai. Due date: 20-Sep. Online payment available."),
    ("R29", "Safe", "SNGPL: Gas bill Rs. 4,800 for August. Pay at any bank or via JazzCash bill payment feature."),
    ("R30", "Safe", "StormFiber: September bill Rs. 3,999 auto-deducted from your bank account. Connection active."),

    # Legitimate education
    ("R31", "Safe", "FAST-NUCES: Aap ka Fall 2026 semester fee Rs. 95,000 receive ho gaya. Receipt student portal pe available hai."),
    ("R32", "Safe", "LUMS: Convocation ceremony on 15-Oct-2026. Register by 30-Sep at lums.edu.pk. Degree collection from registrar."),
    ("R33", "Safe", "Board result: Aap ki beti ne matric mein 1050/1100 marks liye hain. Bohat mubarak! Position holder."),

    # Legitimate social/platform notifications
    ("R34", "Safe", "LinkedIn: You appeared in 23 searches this week. 3 recruiters viewed your profile. Consider updating your headline."),
    ("R35", "Safe", "GitHub: Your repository 'scam-detection' received 15 stars and 3 forks. Keep building!"),
    ("R36", "Safe", "YouTube: Your channel analytics — 500 views this week, 12 new subscribers. Top video: 'AI Tutorial Urdu'."),

    # Legitimate financial
    ("R37", "Safe", "PSX: KSE-100 index at 82,350 (+650). Your portfolio value: Rs. 2,450,000. Unrealized gain: Rs. 350,000."),
    ("R38", "Safe", "Meezan Gold Fund: Aap ki investment Rs. 200,000 ab Rs. 235,000 ki ho gayi hai. NAV: Rs. 117.50/unit."),
    ("R39", "Safe", "State Life: Your insurance policy premium of Rs. 24,000 auto-deducted. Policy active. Next due: March 2027."),
    ("R40", "Safe", "National Savings: Aap ki Defence Savings Certificate Rs. 100,000 matured. Profit: Rs. 22,500. Collect at any branch."),

    # Tricky safe — contains "prize", "urgent", "verify" etc. but legitimate
    ("R41", "Safe", "NUST: URGENT — Course registration deadline is tomorrow at 11:59 PM. Verify your enrolled courses on portal.nust.edu.pk."),
    ("R42", "Safe", "HR: Congratulations! You have been selected for the Employee of the Quarter award. Prize: Rs. 25,000 bonus in next payroll."),
    ("R43", "Safe", "HBL: Your annual credit card fee of Rs. 5,000 will be charged on 15-Sep. To waive, spend Rs. 500,000 before that date."),
    ("R44", "Safe", "Insurance: Your car claim of Rs. 185,000 has been APPROVED. Visit EFU office with CNIC to collect cheque."),
    ("R45", "Safe", "Property alert: Zameen.com — Aap ki saved area 'DHA Phase 6' mein 5 naye plots listed hain. Price range: 80 lakh to 1.5 crore."),

    # Legitimate Urdu safe messages
    ("R46", "Safe", "نیو کراچی: بجلی کی فراہمی کل صبح 8 بجے بحال ہو جائے گی کے الیکٹرک۔"),
    ("R47", "Safe", "شوکت خانم: آپ کی زکوٰۃ 50000 روپے موصول ہو گئی ہے۔ رسید ای میل کر دی گئی ہے۔"),
    ("R48", "Safe", "اسٹیٹ بینک: شرح سود 22% برقرار۔ اگلا جائزہ اکتوبر 2026 میں ہوگا۔"),

    # Legitimate travel/booking
    ("R49", "Safe", "PIA: Aap ki flight PK-305 Islamabad to Karachi 5-Sep ko on-time hai. Boarding: 6:45 AM. E-ticket emailed."),
    ("R50", "Safe", "Booking.com: Aap ka hotel 'Avari Towers Karachi' confirm ho gaya hai. Check-in: 10-Sep. Total: Rs. 28,000 (prepaid)."),
]

# ═══════════════════════════════════════════════════════════════════════
# RUN EVALUATION
# ═══════════════════════════════════════════════════════════════════════
print("=" * 80)
print("  V4 FINAL HOLDOUT VALIDATION — 100 Fresh Messages")
print("  These messages were NEVER used in training, validation, or any prior test.")
print("=" * 80)

artifacts, le, threshold, metadata = load_model()
print(f"\n  Model: {metadata['best_model_name']}, Version: {metadata.get('version', 'N/A')}")
print(f"  Threshold: {threshold:.2f}, Training: {metadata.get('training_size', 'N/A')} messages")

all_msgs = [(i, l, m) for i, l, m in SCAM] + [(i, l, m) for i, l, m in SAFE]
total = len(all_msgs)
tp = fp = tn = fn = 0
fn_list = []
fp_list = []

print(f"\n  Running {total} predictions...")
t0 = time.time()

for msg_id, true_label, msg in all_msgs:
    result = predict_message(msg, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)
    predicted = result["label"]
    prob = result["scam_probability"]
    correct = predicted == true_label

    if true_label == "Scam" and predicted == "Scam": tp += 1
    elif true_label == "Safe" and predicted == "Scam":
        fp += 1
        fp_list.append((msg_id, msg, prob))
    elif true_label == "Safe" and predicted == "Safe": tn += 1
    elif true_label == "Scam" and predicted == "Safe":
        fn += 1
        fn_list.append((msg_id, msg, prob))

    status = "OK" if correct else "** FAIL **"
    print(f"  [{status:10s}] {msg_id:<5s} Exp={true_label:<4s} Got={predicted:<4s} P={prob:.3f}")

elapsed = time.time() - t0
print(f"\n  Done in {elapsed:.1f}s ({total/elapsed:.0f} msg/s)")

# ── Results ──────────────────────────────────────────────────────────────
accuracy = (tp + tn) / total * 100
precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 100
recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 100
specificity = tn / (tn + fp) * 100 if (tn + fp) > 0 else 100
fpr = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0

print(f"\n{'=' * 80}")
print(f"  V4 HOLDOUT RESULTS")
print(f"{'=' * 80}")
print(f"  Accuracy:    {accuracy:.1f}% ({tp+tn}/{total})")
print(f"  Precision:   {precision:.1f}%")
print(f"  Recall:      {recall:.1f}%")
print(f"  Specificity: {specificity:.1f}%")
print(f"  FPR:         {fpr:.1f}%")
print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")

print(f"\n  CONFUSION MATRIX:")
print(f"  ┌──────────────────┬───────────┬───────────┐")
print(f"  │                  │ Pred Scam │ Pred Safe │")
print(f"  ├──────────────────┼───────────┼───────────┤")
print(f"  │ Actual Scam (50) │ TP = {tp:<3d}   │ FN = {fn:<3d}   │")
print(f"  │ Actual Safe (50) │ FP = {fp:<3d}   │ TN = {tn:<3d}   │")
print(f"  └──────────────────┴───────────┴───────────┘")

if fp_list:
    print(f"\n  FALSE POSITIVES ({fp}):")
    for mid, msg, prob in fp_list:
        print(f"    {mid} P={prob:.3f}: \"{msg[:90]}{'...' if len(msg)>90 else ''}\"")
else:
    print(f"\n  ZERO FALSE POSITIVES!")

if fn_list:
    print(f"\n  FALSE NEGATIVES ({fn}):")
    for mid, msg, prob in fn_list:
        print(f"    {mid} P={prob:.3f}: \"{msg[:90]}{'...' if len(msg)>90 else ''}\"")
else:
    print(f"\n  ZERO FALSE NEGATIVES!")

assessment = "STRONG" if accuracy >= 95 else "ACCEPTABLE" if accuracy >= 90 else "NEEDS WORK"
print(f"\n  ASSESSMENT: {assessment}")
print(f"  This is V4's honest generalization score on completely unseen data.")
print(f"{'=' * 80}")

# Save results
import json
results = {
    "test": "V4_holdout_100",
    "total": total,
    "accuracy": round(accuracy, 2),
    "precision": round(precision, 2),
    "recall": round(recall, 2),
    "specificity": round(specificity, 2),
    "fpr": round(fpr, 2),
    "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    "threshold": round(threshold, 2),
    "model_version": metadata.get("version", "V4"),
    "fp_messages": [(mid, msg[:200], round(prob, 4)) for mid, msg, prob in fp_list],
    "fn_messages": [(mid, msg[:200], round(prob, 4)) for mid, msg, prob in fn_list],
}
out_path = os.path.join(PROJECT_ROOT, "reports", "v4_holdout_100_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"  Results saved to: {out_path}")
