"""Quick diagnostic: does the model catch BISP scams that DON'T match the trained template?"""
import sys, os, io, warnings
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message, load_model

artifacts, le, threshold, metadata = load_model()

tests = [
    # (description, message, expected_label)
    ("Template match (trained pattern)",
     "Moaziz sarif, apka BISP ki taraf se 8000 PKR ka inaam nikla hai. Taseeq k liye 0399123456 par call kren.",
     "Scam"),

    ("Different phrasing (RU)",
     "BISP se aap ka payment ready hai. CNIC number bhej kr collect kren. Helpline: 0300-1234567.",
     "Scam"),

    ("Registration scam (RU)",
     "Ehsaas Program mein registration ka aakhri moqa. Rs. 500 fee ada kren warna naam kat jaye ga. 0312-9988776 par rabta kren.",
     "Scam"),

    ("Cash pickup fee scam (RU)",
     "Aap ka BISP cash Rs. 12000 teyar hai. Qareebi HBL branch se len. Processing fee Rs. 300 pehle jama kren.",
     "Scam"),

    ("Short SMS style (RU)",
     "BISP: Rs.25000 milenge! 8989 pe SMS bhejen abhi.",
     "Scam"),

    ("Urdu different phrasing",
     "بینظیر انکم سپورٹ پروگرام: آپ کی امداد تیار ہے۔ 500 روپے بھیج کر حاصل کریں۔",
     "Scam"),

    ("Roman Urdu casual",
     "Bhen apka ehsas ka paisa aa gaya ha. 15000 rs. Easypaisa se nikalwaen. Code bhejen.",
     "Scam"),

    ("English variant (scam)",
     "Benazir Income Support: Your quarterly payment of Rs. 9,000 is ready. Pay Rs. 500 processing fee to receive at nearest BISP office.",
     "Scam"),

    ("LEGITIMATE BISP message",
     "BISP: Aap ki Rs. 12,000 ki quarterly payment 1-Sep-2026 ko disburse ho gayi hai. Qareebi HBL branch se CNIC dikha kr hasil kren. Koi fee nahi chahiye.",
     "Safe"),

    ("LEGITIMATE Ehsaas notification",
     "Ehsaas Program: Aap ki family ko monthly Rs. 14,000 ka wazifa approve ho gaya hai. Qareebi BISP center se CNIC ke saath tashreef layen. Koi advance payment nahi.",
     "Safe"),
]

print(f"\n{'=' * 75}")
print(f"  BISP TEMPLATE DIVERSITY DIAGNOSTIC")
print(f"  Testing: can the model catch BISP scams BEYOND the trained template?")
print(f"{'=' * 75}\n")

correct = 0
total = len(tests)

for desc, msg, expected in tests:
    r = predict_message(msg, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)
    got = r["label"]
    prob = r["scam_probability"]
    ok = (got == expected)
    if ok:
        correct += 1
    status = "OK" if ok else "** FAIL **"
    marker = "SCAM" if expected == "Scam" else "SAFE"
    print(f"  [{status:10s}] {desc:<35s} Exp={marker:<4s} Got={got:<5s} P={prob:.3f}")
    if not ok:
        print(f"             \"{msg[:70]}...\"")

print(f"\n  Result: {correct}/{total} correct")
print(f"  Scams caught: {sum(1 for d,m,e in tests if e=='Scam' and predict_message(m, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)['label']=='Scam')}/{sum(1 for d,m,e in tests if e=='Scam')}")
print(f"  Safe passed:  {sum(1 for d,m,e in tests if e=='Safe' and predict_message(m, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)['label']=='Safe')}/{sum(1 for d,m,e in tests if e=='Safe')}")

if correct == total:
    print(f"\n  VERDICT: Model handles diverse BISP phrasings well.")
elif correct >= total - 2:
    print(f"\n  VERDICT: Mostly OK but some non-template phrasings slip through.")
    print(f"  ACTION: Add 10-15 diverse BISP training examples tomorrow before demo.")
else:
    print(f"\n  VERDICT: Model is overfit to trained BISP templates.")
    print(f"  ACTION: URGENT — must retrain with diverse BISP phrasings.")
