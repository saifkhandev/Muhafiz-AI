from src.predict import load_model, predict_message

artifacts, le, threshold, metadata = load_model()

test_cases = [
    # OBVIOUS SCAMS
    ("Your account has been blocked. Click here to verify immediately.", "Scam"),
    ("Congratulations! You have won Rs 500,000. Send fee Rs 5000 to claim your prize.", "Scam"),
    ("Your ATM card is blocked. Call this number and share your OTP to unblock.", "Scam"),
    ("BISP program se aap ko Rs 25000 milay hain. Fee Rs 500 bhejein.", "Scam"),
    ("Aap ka account suspend hone wala hai. OTP share karein verification k liye.", "Scam"),
    ("FBR tax notice: Pay Rs 10,000 immediately or legal action will be taken.", "Scam"),
    ("JazzCash account verification k liye apna PIN aur OTP bataein.", "Scam"),
    ("Your electricity bill is unpaid. Pay now or your connection will be disconnected.", "Scam"),
    ("I am stuck in an emergency, please send me Rs 5000 immediately.", "Scam"),
    ("Your package is stuck at customs. Pay clearance fee Rs 2000.", "Scam"),
    ("Dubai job offer with free visa. Send processing fee Rs 15,000.", "Scam"),
    ("Your loan is approved. Pay advance fee Rs 2000 to receive amount.", "Scam"),
    ("Blackmail: I have your private photos. Send Rs 50,000 or I will share them.", "Scam"),
    ("I love you, please send me money for my sick mother.", "Scam"),
    ("Click this link to verify your bank account details.", "Scam"),
    ("URGENT: Your mobile number has won a prize. Call now to claim.", "Scam"),
    # SAFE MESSAGES
    ("Your OTP is 123456. Do not share it with anyone.", "Safe"),
    ("Your account balance is Rs 5,000. Transaction ID: ABC123.", "Safe"),
    ("Interview scheduled for tomorrow at 10 AM. Bring your CV.", "Safe"),
    ("Bhai kal milte hain cafe mein.", "Safe"),
    ("Your salary has been credited to your account.", "Safe"),
    ("Meeting rescheduled to 3 PM. Please confirm availability.", "Safe"),
    ("Thank you for shopping with us. Your order #12345 has been delivered.", "Safe"),
    ("Easypaisa se Rs 1000 transfer kiye hain. Reference: 987654.", "Safe"),
    ("Mpin set kar lijiye apne JazzCash account ke liye.", "Safe"),
    ("Your electricity bill of Rs 3500 is due on 15th March.", "Safe"),
]

print(f'Threshold: {threshold}')
print('=' * 80)
scam_correct = 0
safe_correct = 0
scam_total = 0
safe_total = 0

for msg, expected in test_cases:
    result = predict_message(msg, artifacts, le, threshold, metadata)
    pred = result['label']
    prob = result['scam_probability']
    guardrail = result.get('guardrail')
    status = 'OK ' if pred == expected else 'BAD'
    g = f' [{guardrail}]' if guardrail else ''
    print(f'{status} {expected:5} -> {pred:5} ({prob:.3f}){g}')
    print(f'    {msg[:80]}...')
    if expected == 'Scam':
        scam_total += 1
        if pred == expected:
            scam_correct += 1
    else:
        safe_total += 1
        if pred == expected:
            safe_correct += 1

print('=' * 80)
print(f'Scam recall: {scam_correct}/{scam_total} = {scam_correct/scam_total:.2%}')
print(f'Safe precision: {safe_correct}/{safe_total} = {safe_correct/safe_total:.2%}')
