"""Quick test of the retrained model prediction interface."""
import sys, os, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.predict import predict_message

tests = [
    # English
    ("Congratulations! You won Rs. 50000 lottery. Send OTP to claim.", "Scam"),
    ("Your HBL account has been credited with Rs. 50000 from salary.", "Safe"),
    ("URGENT: Your account will be suspended. Call now to verify your identity.", "Scam"),
    ("Meeting rescheduled to 3 PM tomorrow. Please confirm attendance.", "Safe"),
    # Roman Urdu (abbreviated - like external dataset)
    ("Mubarak ho! BISP main apka 12500 ka inam lga ha. OTP bhejain.", "Scam"),
    ("Aap k HBL acount se Rs. 50000 ki deduction hui ha tax ki madd mein.", "Safe"),
    ("Aap ka account block hone wala hai. Foran OTP share karein.", "Scam"),
    ("Aap k JazzCash me Rs. 5000 aaye hain. Balance check karein.", "Safe"),
    # Roman Urdu scam without "Mubarak ho"
    ("Bhai apke number par ghalti se mere 5000 rs aa gaye hain easypaisa me wapis bhej do", "Scam"),
    # Urdu
    ("آپ کا اکاؤنٹ بلاک ہو رہا ہے۔ فوری طور پر رابطہ کریں۔", "Scam"),
    ("آپ کے اکاؤنٹ سے Rs. 5000 کی کٹوتی ہوئی ہے۔ یہ ٹیکس کی وجہ سے ہے۔", "Safe"),
]

print(f"{'Expected':8s} {'Got':8s} {'P':>7s} {'Match':7s} Message")
print("-" * 80)
correct = 0
for msg, expected in tests:
    r = predict_message(msg)
    match = "OK" if r['label'] == expected else "MISS"
    if match == "OK": correct += 1
    print(f"{expected:8s} {r['label']:8s} {r['scam_probability']:>7.4f} {match:7s} {msg[:50]}...")

print(f"\n{correct}/{len(tests)} correct")
