"""
rigorous_real_world_test.py
Test V3 model with diverse real-world Pakistani messages a user might actually receive.
Covers edge cases, ambiguous messages, and adversarial inputs.
"""
import sys, os, io, warnings
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message

# Real-world test cases organized by category
TEST_CASES = [
    # ── OBVIOUS SCAMS (should be Scam) ──
    ("SCAM-1: BISP prize", "Moaziz sarif, apka BISP ki taraf se 25000 PKR ka inaam nikla hai. Taseeq k liye 0312998877 par pin code bhejen.", "Scam"),
    ("SCAM-2: JazzCash OTP", "JazzCash: Aap ka account mein Rs. 15,000 credit hue hain. Withdraw k liye OTP 884412 share kren.", "Scam"),
    ("SCAM-3: SIM block threat", "PTA Notice: Aap ka SIM 24 ghante mein block ho jaye ga. Verification k liye CNIC aur bank details bhejen.", "Scam"),
    ("SCAM-4: Lottery winner", "Congratulations! You have won Rs. 500,000 in the Pakistan Day Lucky Draw. Pay Rs. 5,000 processing fee to claim.", "Scam"),
    ("SCAM-5: Fake job offer", "URGENT: 500 jobs in Dubai. Salary AED 5000. No experience needed. Pay Rs. 25,000 visa fee to apply. Contact 0300-1234567.", "Scam"),
    ("SCAM-6: Urdu phishing", "آپ کا بینک اکاؤنٹ بلاک ہو رہا ہے۔ فوری طور پر اپنا پاسورڈ اور او ٹی پی درج کریں۔", "Scam"),
    ("SCAM-7: Forex scam", "OctaFX: Invest Rs. 10,000 and earn $100 daily. Guaranteed returns. No risk. Register now.", "Scam"),
    ("SCAM-8: Easypaisa wrong number", "Bhai ghalti se apke easypaisa number par 15000 rs aa gaye hain. Please wapis bhej dain 03457766554.", "Scam"),
    ("SCAM-9: HBL branch manager loan", "Dear Sir, yeh HBL Branch Manager hai. Aap ka Rs. 500,000 loan pre-approved hai. Rs. 12,000 processing fee jama kren.", "Scam"),
    ("SCAM-10: TCS customs fee", "TCS: Aap ka international parcel customs mein ruka hai. Rs. 3,500 clearance fee jama kren account 0012-8877665 mein.", "Scam"),

    # ── OBVIOUS SAFE (should be Safe) ──
    ("SAFE-1: Bank salary credit", "HBL: Your account has been credited with Rs. 85,000 as salary from Systems Ltd. Available balance: Rs. 142,350.", "Safe"),
    ("SAFE-2: JazzCash receipt", "JazzCash: Rs. 2,500 sent to 0312-9876543. Transaction ID: JC-2026-88776. New balance: Rs. 8,450.", "Safe"),
    ("SAFE-3: OTP from bank", "Your HBL One Time Password (OTP) is 487234. Valid for 5 minutes. Do NOT share with anyone.", "Safe"),
    ("SAFE-4: Friend message", "Yaar kal dinner pe aana, 8 baje. Main biryani bana raha hoon. Ghar ka address bhej deta hoon.", "Safe"),
    ("SAFE-5: Office meeting", "Team meeting rescheduled to 3 PM tomorrow in Conference Room B. Please bring your quarterly reports.", "Safe"),
    ("SAFE-6: Urdu personal", "امی، میں نے کھانا کھا لیا ہے۔ آپ فکر نہ کریں۔ کل گھر آؤں گا۔", "Safe"),
    ("SAFE-7: Careem receipt", "Your Careem ride from DHA to Gulberg has been completed. Fare: Rs. 650. Thank you!", "Safe"),
    ("SAFE-8: NUST admission", "Congratulations! You have been selected for the NUST MS program. Confirm enrollment at admissions.nust.edu.pk.", "Safe"),
    ("SAFE-9: PSX portfolio", "PSX Daily: KSE-100 closed at 78,450 (+2.3%). Your portfolio value: Rs. 245,000.", "Safe"),
    ("SAFE-10: Zong recharge", "Your Zong recharge of Rs. 500 was successful. New balance: Rs. 523. Valid for 30 days.", "Safe"),

    # ── EDGE CASES (tricky - model must be smart) ──
    ("EDGE-1: Bank deduction tax", "Aap k HBL account se Rs. 50,000 ki deduction hui hai tax ki madd mein.", "Safe"),
    ("EDGE-2: Meezan deposit", "Dear Customer, Apke Meezan Bank account me 50,000 PKR deposit hue hain. Available Balance: 50,000 PKR.", "Safe"),
    ("EDGE-3: Google internship", "Congratulations! You've been selected for Google Summer of Code 2026. Stipend: $3000. Apply at summerofcode.withgoogle.com.", "Safe"),
    ("EDGE-4: Password expiry", "Security Notice: Your HBL password was last changed 90 days ago. Please update for better security at hbl.com.", "Safe"),
    ("EDGE-5: BISP Ehsaas stipend", "Ehsaas Programme: Aap ki mahana payment Rs. 14,000 aap ke designated bank account mein jama ho gayi hai.", "Safe"),
    ("EDGE-6: Govt job real", "Federal Public Service Commission: Your CSS 2026 interview is scheduled for Oct 15 at FPSC Headquarters, Islamabad.", "Safe"),
    ("EDGE-7: Subtle scam - cousin", "Assalam o alaikum, main aap ka cousin Imran hoon. Naye number se message kr raha hoon. Emergency hai, Rs. 15,000 foran bhejen.", "Scam"),
    ("EDGE-8: Subtle scam - boss", "Hi this is your CEO Ahmed. I'm in a meeting right now. Need you to urgently wire Rs. 500,000 to a vendor. I'll explain later.", "Scam"),
    ("EDGE-9: FBR legit notice", "FBR: Your income tax return for FY 2024-25 has been acknowledged. NTN: 1234567-8. No action required.", "Safe"),
    ("EDGE-10: Daraz delivery", "Your Daraz order #445566 (Wireless Earbuds) has been delivered. Enjoy your purchase! Return within 7 days if needed.", "Safe"),

    # ── ROMAN URDU SPECIFIC (critical for this project) ──
    ("RU-1: Easypaisa payment", "Aap k easypaisa se Rs. 1,500 ki payment ho gayi hai. Merchant: Daraz. Balance: Rs. 3,450.", "Safe"),
    ("RU-2: BISP inaam scam", "Moaziz sarif, apka Benazir Income Support ki taraf se 10,000 PKR ka inaam nikla hai. Taseeq k liye 0345678901 par call kren.", "Scam"),
    ("RU-3: Job interview fee", "Sarkari naukri: Aap ki application shortlist ho gayi hai. 5000 Rs interview fee jama karwaen.", "Scam"),
    ("RU-4: Family chat", "Ammi ne kaha hai k aaj jaldi ghar aana. Chachi bhi aa rahi hain. Khana ready hoga 7 baje.", "Safe"),
    ("RU-5: Telenor balance", "Telenor: Aap ka balance Rs. 125 hai. Validity: 15 din. Recharge karwaen.", "Safe"),
    ("RU-6: Inaami car", "Mubarak ho! Aap Pakistan Day Lucky Draw mein Honda Civic 2026 k winner hain! 0800-24842 par call kren.", "Scam"),

    # ── URDU SPECIFIC ──
    ("UR-1: Bank statement", "آپ کا ماہانہ اسٹیٹمنٹ: کل کریڈٹس 95,000 روپے۔ کل ڈیبٹس 67,000 روپے۔ بیلنس 128,000 روپے۔", "Safe"),
    ("UR-2: PayPal phishing", "آپ کا پے پال اکاؤنٹ محدود ہو گیا ہے۔ بینک کارڈ کی تفصیلات سے دوبارہ بحال کریں۔", "Scam"),
    ("UR-3: Education", "نوٹس: کل اسکول کی چھٹیاں شروع ہو رہی ہیں۔ پہلی جماعت سے دسویں جماعت تک تمام طلبا کے لیے۔", "Safe"),
    ("UR-4: Prize scam", "رمضان لکی ڈرا: آپ کو ہونڈا سوک گاڑی کا انعام ملا ہے۔ 0800-12345 پر کال کریں۔", "Scam"),

    # ── MIXED LANGUAGE ──
    ("MX-1: Netflix renewal legit", "Your Netflix subscription 1-Sep-2026 ko renew hoga. Amount: Rs. 1500. Payment method: Visa card.", "Safe"),
    ("MX-2: Scam mixed", "Congratulations! Aap ne Rs. 100,000 ka inaam jeeta hai! Claim karne ke liye 0300-1234567 par call karein aur Rs. 2,000 fee bhejein.", "Scam"),
    ("MX-3: Foodpanda order", "Foodpanda: Aap ka order Salt'n Pepper se deliver ho gaya. Total Rs. 2,350. App mein rate kren.", "Safe"),
]

# Run all tests
print("=" * 80)
print("  RIGOROUS REAL-WORLD TESTING: V3 Model (B_combined_C5)")
print("=" * 80)

correct = 0
incorrect = 0
scam_correct = 0
scam_total = 0
safe_correct = 0
safe_total = 0
edge_correct = 0
edge_total = 0
failures = []

for name, msg, expected in TEST_CASES:
    result = predict_message(msg)
    predicted = result["label"]
    prob = result["scam_probability"]
    
    is_correct = predicted == expected
    if is_correct:
        correct += 1
    else:
        incorrect += 1
        failures.append((name, msg, expected, predicted, prob))
    
    if "SCAM" in name:
        scam_total += 1
        if is_correct: scam_correct += 1
    elif "SAFE" in name:
        safe_total += 1
        if is_correct: safe_correct += 1
    elif "EDGE" in name:
        edge_total += 1
        if is_correct: edge_correct += 1
    elif name.startswith("RU-"):
        edge_total += 1
        if is_correct: edge_correct += 1
    elif name.startswith("UR-"):
        edge_total += 1
        if is_correct: edge_correct += 1
    elif name.startswith("MX-"):
        edge_total += 1
        if is_correct: edge_correct += 1
    
    status = "OK" if is_correct else "FAIL"
    tag = f"P={prob:.3f}" if prob is not None else "P=N/A"
    print(f"  [{status:4s}] {name:<25s} Expected={expected:<4s} Got={predicted:<4s} {tag}")

total = len(TEST_CASES)
print(f"\n{'=' * 80}")
print(f"  RESULTS: {correct}/{total} correct ({correct/total*100:.1f}%)")
print(f"{'=' * 80}")
print(f"  Obvious Scams:    {scam_correct}/{scam_total} ({scam_correct/scam_total*100:.1f}%)")
print(f"  Obvious Safe:     {safe_correct}/{safe_total} ({safe_correct/safe_total*100:.1f}%)")
print(f"  Edge Cases + Lang: {edge_correct}/{edge_total} ({edge_correct/edge_total*100:.1f}%)")

if failures:
    print(f"\n  FAILURES ({len(failures)}):")
    for name, msg, exp, pred, prob in failures:
        print(f"    {name}: Expected={exp} Got={pred} P={prob:.3f}")
        print(f"      \"{msg[:80]}...\"")

print(f"\n  VERDICT: {'PASS' if correct/total >= 0.95 else 'NEEDS WORK'}")
print(f"  Model is {'READY' if correct/total >= 0.95 else 'NOT READY'} for hackathon demo")
