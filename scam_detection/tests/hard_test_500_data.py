"""
Comprehensive 500+ adversarial test set for Muhafizz AI.
250 Scam + 250 Safe, equal distribution, all edge cases.
"""
import sys, os, warnings, time, json
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import (accuracy_score, f1_score, fbeta_score, precision_score,
                             recall_score, confusion_matrix, classification_report)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message, load_model

# ═══════════════════════════════════════════════════════════════════════
# SCAM MESSAGES (250) — diverse, disguised, edge cases
# ═══════════════════════════════════════════════════════════════════════

scam_messages = []

# ── CAT 1: BISP/Ehsaas diverse (30) ──
scam_messages += [("BISP/Ehsaas", "Scam", m) for m in [
    "Bhen apka ehsas ka paisa aa gaya ha. 15000 rs. Easypaisa se nikalwaen. Code bhejen 0321876543.",
    "Bhai BISP wale hain. Aap ka 12000 payment ready hai. CNIC or account number bhejen.",
    "Aap ka BISP cash Rs. 12000 teyar hai. Processing fee Rs. 300 pehle jama kren 0312-555443.",
    "Ehsaas Program mein registration ka aakhri moqa. Rs. 500 fee ada kren warna naam kat jaye ga.",
    "BISP: Rs.25000 milenge! 8989 pe SMS bhejen abhi.",
    "Ehsaas scheme k tehat aap k liye 18000 rupay manzor ho gaye hain. Verification fee 250 rs JazzCash pe bhejen.",
    "Benazir income support program: Aap ki quarterly qist Rs. 9000 teyar hai. OTP code share kren.",
    "BISP payment update: Aap ka account mein Rs. 14000 credit hone wale hain. 200 rs processing fee bhejen.",
    "Ehsaas kafalat: Rs. 7000 mil rahe hain. Registration k liye apna CNIC aur mobile OTP bhejen.",
    "BISP se aap ka payment ready hai. CNIC number bhej kr collect kren. Helpline: 0300-1234567.",
    "احساس کفالت: آپ کو 18000 روپے مل رہے ہیں۔ رجسٹریشن کے لیے CNIC اور OTP بھیجیں۔",
    "بینظیر انکم سپورٹ پروگرام: آپ کی امداد تیار ہے۔ 500 روپے بھیج کر حاصل کریں۔",
    "BISP: Your quarterly payment of Rs. 9,000 is ready. Pay Rs. 500 processing fee to collect.",
    "Ehsaas Programme: Rs. 25,000 emergency relief approved. Send CNIC and bank details. Contact: 0312-9988776.",
    "BISP Notification: Rs. 12,500 cash grant pending. Transfer Rs. 300 verification fee to JazzCash 0345-778899.",
    "Moaziz sarif, BISP ki taraf se 8000 PKR ka inaam nikla hai. Taseeq k liye 0399123456 par call kren.",
    "Ehsaas program: Rs. 3000 monthly wazifa approved. Registration fee Rs. 150 pay kren.",
    "BISP wale bol rahe hain k aap eligible hain. Rs. 20000 milenge. Account details bhejen.",
    "Ehsaas cash program: Aap ki family ko Rs. 10000 milenge. Pehle Rs. 400 fee ada kren.",
    "BISP: Aap ki payment reject ho rahi hai. Rs. 250 bhej kr reactivate kren warna band ho jaye ga.",
    "Ehsaas update: Aap ka naam list mein aa gaya hai. Rs. 15000 collect krne k liye OTP bhejen.",
    "BISP agent: Main BISP se bol raha hun. Aap ko Rs. 25000 dene hain. Bank PIN share kren.",
    "Ehsaas Nigehban: Senior citizens ko Rs. 8000 extra milenge. Form bharne k liye fee Rs. 200.",
    "BISP helpline: Aap ki qist delay ho rahi hai. Rs. 500 bhej kr fast-track kren.",
    "Ehsaas survey: Aap selected hain. Rs. 5000 inaam. WhatsApp pe CNIC photo bhejen.",
    "BISP emergency fund: Rs. 50000 approved for flood victims. Processing fee Rs. 1000.",
    "Ehsaas education: Bacho ki taleem k liye Rs. 12000. Registration k liye call kren 0333-111222.",
    "BISP mobile unit: Aap k ilaqe mein aa rahi hai. Rs. 250 advance bhej kr appointment len.",
    "Ehsaas health card: Rs. 3000 ka health insurance. Rs. 100 activation fee JazzCash pe.",
    "BISP: Aap ki beti ki shadi k liye Rs. 50000 grant. Documents k saath Rs. 500 fee bhejen.",
]]

# ── CAT 2: Delivery/Logistics scams (25) ──
scam_messages += [("Delivery", "Scam", m) for m in [
    "Your TCS parcel #8834521 is held at customs. Pay Rs. 1500 duty to release. Link: tcs-express.pk/customs",
    "Leopards Courier: Your package requires address verification. Click leopards-verify.pk/update",
    "Pakistan Post: Shipment #PK9923847 returned. Re-ship fee Rs. 500. Pay at post-track.pk/resend",
    "Daraz order #7734521 delivery failed. Update address: daraz-verify.pk/address",
    "FedEx: Your parcel from UAE is stuck. Customs duty Rs. 3500. Pay via JazzCash to 0312-9988776.",
    "DHL Express: International shipment held. Pay Rs. 5000 clearance fee at dhl-pak-clearance.com",
    "Your Amazon package is ready. Pay Rs. 299 delivery charge first. UPI: amazon-delivery@pay",
    "Courier alert: Your parcel contains prohibited items. Pay Rs. 2000 fine or police action.",
    "BlueEx: Delivery attempted 3 times. Storage fee Rs. 150/day. Pay now or parcel returned.",
    "Your AliExpress order cleared customs. Additional duty Rs. 800. Pay at aliexpress-pak-duty.com",
    "Post office: Registered letter from NADRA waiting. Collection fee Rs. 100. Pay online.",
    "Your Foodpanda order was cancelled. Refund processing. Share bank details for Rs. 2500 refund.",
    "Careem package: Driver found Rs. 5000 in your bag. Send Rs. 500 to claim. JazzCash: 0345-111222.",
    "InDrive delivery: Your parcel is with driver. Tip Rs. 200 for priority delivery.",
    "Swiggy: Your order is delayed. Compensation Rs. 500. Share UPI PIN to receive.",
    "TCS: Aap ka parcel China se aa gaya hai. Customs duty Rs. 2500 bhejen warna wapis.",
    "Courier: Aap k naam parcel aaya hai. Rs. 800 delivery charge pehle bhejen.",
    "ڈی ایچ ایل: آپ کا پارسل کسٹم میں رک گیا۔ 3000 روپے ڈیوٹی ادا کریں۔",
    "Leopards: Aap ka parcel damage ho gaya hai. Insurance claim Rs. 5000. Processing fee Rs. 300.",
    "Post office: Aap k liye registered parcel aaya hai USA se. Rs. 1500 customs duty bhejen.",
    "Your parcel tracking #PK998234 shows delivery failed. Re-delivery fee Rs. 250.",
    "Pakistan Post: International parcel arrived. Pay Rs. 2000 duty at post-clearance.pk",
    "Daraz return: Rs. 3500 refund approved. Share JazzCash account number and PIN.",
    "TCS Express: Your parcel is overweight. Extra charge Rs. 1200. Pay at tcs-extra.pk",
    "BlueEx delivery: Your address is wrong. Correction fee Rs. 500 or parcel returned to sender.",
]]

# ── CAT 3: Job scams (25) ──
scam_messages += [("Job", "Scam", m) for m in [
    "URGENT HIRING: Data entry operator needed. Salary Rs. 80,000/month. Security deposit Rs. 5000.",
    "Work from home: Earn Rs. 5000/day liking YouTube videos. Registration fee Rs. 1500.",
    "PTCL hiring customer service. Salary Rs. 45,000. Interview fee Rs. 2000. Apply: ptcl-jobs.pk",
    "Jazz is hiring 500 agents. Monthly salary Rs. 60,000. Processing fee Rs. 3000 via easypaisa.",
    "Remote job: Typing work. Rs. 3000/page. Joining fee Rs. 2500. WhatsApp: 0312-555777.",
    "Overseas job in Dubai: Salary AED 8000. Visa processing fee Rs. 50,000. Limited seats!",
    "Amazon product reviewer needed. Earn Rs. 2000/review. Security deposit Rs. 3000.",
    "Government job: NADRA clerk position. Salary Rs. 55,000. Application fee Rs. 5000.",
    "Freelance opportunity: Rs. 100,000/month guaranteed. Training fee Rs. 10,000. Limited slots.",
    "Uber driver partner: Earn Rs. 8000/day. Vehicle registration fee Rs. 15,000.",
    "Teaching job: O/A Level tutor needed. Rs. 70,000/month. Joining fee Rs. 5000.",
    "Call center hiring: Night shift agents. Rs. 40,000/month. Uniform fee Rs. 2000.",
    "YouTube earning: Rs. 50,000/month. Course fee Rs. 8000. Guaranteed income.",
    "Crypto trading job: Rs. 200,000/month. Initial investment Rs. 25,000 required.",
    "Nokri chahiye? Ghar beth kr Rs. 3000 rozana kamaen. Registration Rs. 1500 JazzCash pe bhejen.",
    "Job offer: Rs. 75,000 salary. Pehle Rs. 4000 training fee bhejen.",
    "نوکری: گھر بیٹھے 50000 روپے ماہانہ۔ رجسٹریشن فیس 3000 روپے۔",
    "OLX job: Rs. 45,000/month data entry. Security deposit Rs. 2500.",
    "Fiverr earning course: Rs. 100,000/month guaranteed. Course fee Rs. 15,000.",
    "Saudi Arabia job: Rs. 150,000/month. Agent fee Rs. 75,000. Visa guaranteed.",
    "Part-time: 2 hours/day, Rs. 3000/hour. Joining fee Rs. 5000. WhatsApp for details.",
    "Bank job: HBL cashier position. Rs. 50,000/month. Application fee Rs. 8000.",
    "Freelance writing: Rs. 500/article. Membership fee Rs. 2000 to access assignments.",
    "Delivery rider: Rs. 60,000/month. Bike deposit Rs. 10,000. Apply now.",
    "Import/Export business: Rs. 500,000/month profit. Investment Rs. 50,000 to start.",
]]

# ── CAT 4: Prize/Lottery scams (25) ──
scam_messages += [("Prize", "Scam", m) for m in [
    "Mubarak ho! Aap ne Jeeto Pakistan mein Rs. 500,000 jeete hain. Claim fee Rs. 5000 bhejen.",
    "Congratulations! You won Rs. 1,000,000 in the PTA lucky draw. Tax Rs. 50,000 required.",
    "Coca-Cola reward: Aap ne Rs. 250,000 jeeta hai. Processing fee Rs. 3000 bhejen.",
    "Nestle promotion: Rs. 100,000 prize confirmed. Delivery charge Rs. 2500.",
    "LUX Style Awards: You've been nominated. Voting fee Rs. 1500. Vote now!",
    "Jazz Jackpot: Rs. 500,000 ka inaam! Rs. 2000 SMS fee bhejen.",
    "Zong Lucky Draw: Aap ka number Rs. 250,000 k liye select hua hai. Rs. 1500 bhejen.",
    "PTV Sports: Cricket prediction winner! Rs. 75,000 prize. Claim fee Rs. 3000.",
    "Pepsi cap prize: Rs. 50,000 confirmed. Courier charge Rs. 2000.",
    "Telenor reward: Rs. 200,000 inaam nikla hai. Rs. 5000 tax ada kren.",
    "Ufone lucky subscriber: Rs. 150,000 prize. Verification fee Rs. 2500.",
    "Samsung promotion: Free Galaxy S24 Ultra. Shipping fee Rs. 3000.",
    "Apple iPhone giveaway: You're selected! Customs duty Rs. 5000 for delivery.",
    "Inaam Ghar: Rs. 75,000 jeet gaye! Processing fee Rs. 2000 bhejen.",
    "مبارک ہو! آپ نے 500000 روپے کا انعام جیتا ہے۔ 5000 روپے فیس بھیجیں۔",
    "Lucky draw winner! Rs. 300,000 prize. Transfer Rs. 5000 to claim.",
    "NayaPay reward: Rs. 25,000 cashback approved. Processing fee Rs. 500.",
    "JazzCash lucky user: Rs. 100,000 inaam! Rs. 2000 verification fee.",
    "Easypaisa jackpot: Rs. 500,000 winner! Tax Rs. 10,000 pay kren.",
    "State Bond winner: Rs. 1,000,000 prize. Government fee Rs. 25,000.",
    "Ramadan lucky draw: Rs. 200,000 prize. Claim within 24 hours. Fee Rs. 5000.",
    "Eid Mubarak prize: Rs. 50,000 confirmed. Delivery fee Rs. 1500.",
    "Independence Day lottery: Rs. 750,000 winner! Tax Rs. 15,000.",
    "New Year lucky number: Rs. 400,000 prize. Processing fee Rs. 8000.",
    "Surprise gift: Rs. 150,000 prize from unknown sender. Courier fee Rs. 3000.",
]]

# ── CAT 5: Wallet/Crypto scams (25) ──
scam_messages += [("Wallet/Crypto", "Scam", m) for m in [
    "JazzCash: Your account is blocked. Send Rs. 500 to unblock via 0312-9988776.",
    "Easypaisa alert: Suspicious activity detected. Verify by sending Rs. 100 to helpline.",
    "Your Binance wallet shows unusual login. Reset password at binance-secure.pk",
    "Crypto investment: Rs. 10,000 mein Rs. 100,000 banayen. Join WhatsApp group.",
    "Bitcoin earning: Rs. 50,000 invest kren, Rs. 500,000 kamayen. 100% guaranteed!",
    "Your SadaPay account needs verification. Share OTP sent to your number.",
    "NayaPay: Rs. 5000 cashback approved. Share account PIN to receive.",
    "Crypto trading signal: Buy now, 500% profit in 24 hours. Join VIP group Rs. 10,000.",
    "Easypaisa merchant: Payment of Rs. 25,000 received. Share PIN to withdraw.",
    "JazzCash loan: Rs. 50,000 instant loan approved. Processing fee Rs. 2500.",
    "Your PayPal account is restricted. Verify at paypal-verify.pk to restore.",
    "Forex trading: Rs. 20,000 se Rs. 200,000 daily. Join now! Limited slots.",
    "Binance P2P: Buyer sent Rs. 50,000. Release crypto or account suspended.",
    "Easypaisa: Aap ka account freeze ho gaya hai. Rs. 1000 bhej kr unfreeze kren.",
    "JazzCash: Rs. 15,000 cashback offer. Pehle Rs. 500 verification fee bhejen.",
    "Your crypto wallet has been compromised. Transfer funds to safe address immediately.",
    "Ethereum mining: Rs. 30,000 invest kren. Rs. 300,000/month passive income.",
    "SadaPay: Rs. 10,000 bonus mile. Card details share kren to claim.",
    "NayaPay security: Unauthorized transaction of Rs. 8000. Call 0312-555888 to reverse.",
    "JazzCash: Aap ko Rs. 20,000 milne wale hain. OTP share kren.",
    "Binance airdrop: Free BNB tokens worth Rs. 5000. Connect wallet to claim.",
    "Crypto pump signal: Next 100x coin. Entry fee Rs. 5000 for insider group.",
    "Easypaisa refund: Rs. 3500 overpayment detected. Share CNIC to process refund.",
    "JazzCash: Account upgrade to Gold. Fee Rs. 2000. Higher limits.",
    "Your wallet balance of Rs. 45,000 will expire. Transfer to bank within 1 hour.",
]]

# ── CAT 6: Bank/Financial scams (25) ──
scam_messages += [("Bank", "Scam", m) for m in [
    "HBL Alert: Your debit card is blocked. Unblock by sharing last 4 digits and CVV.",
    "Meezan Bank: Suspicious transaction of Rs. 45,000. Call 0312-888999 to verify.",
    "UBL: Your account will be frozen in 24 hours. Update KYC at ubl-update.pk",
    "Allied Bank: Loan pre-approved Rs. 500,000. Processing fee Rs. 5000.",
    "Bank Alfalah: Credit card limit enhanced to Rs. 500,000. Activation fee Rs. 3000.",
    "MCB: Your cheque of Rs. 250,000 is bounced. Penalty Rs. 5000. Pay immediately.",
    "Faysal Bank: Fixed deposit matured. Rs. 1,000,000 ready. Tax Rs. 50,000 required.",
    "Standard Chartered: Premium banking offer. Rs. 10,000 joining fee for 5% interest.",
    "Askari Bank: Your account has been credited with Rs. 75,000. Share OTP to confirm.",
    "Bank Habib: Home loan approved Rs. 5,000,000. Documentation fee Rs. 25,000.",
    "Sindh Bank: Government subsidy Rs. 50,000 credited. Processing fee Rs. 2500.",
    "Your credit card has been charged Rs. 15,000 for annual fee. Call to dispute.",
    "HBL mobile banking: Password expired. Reset at hbl-mobile-reset.pk",
    "Meezan Islamic: Profit rate increased to 18%. Transfer funds to new account.",
    "UBL: Aap k account se Rs. 35,000 kat gaye hain. Reverse krne k liye call kren.",
    "Bank account verification: Share CNIC, account number, and PIN for annual verification.",
    "Your fixed deposit of Rs. 2,000,000 matured. Penalty Rs. 10,000 if not renewed.",
    "MCB: International transaction of $500 detected. Block card by sharing CVV.",
    "Allied Bank: Your ATM card is ready. Delivery fee Rs. 500. Pay via easypaisa.",
    "Faysal Bank: Aap ki loan reject ho gayi hai. Re-apply fee Rs. 3000.",
    "بینک الفلاح: آپ کے اکاؤنٹ سے غیر مجاز منتقلی۔ فوری طور پر کال کریں۔",
    "HBL: Your credit score dropped. Improvement service Rs. 5000. Guaranteed fix.",
    "Meezan: Zakat deduction of Rs. 8000. Claim exemption by sharing account details.",
    "UBL: Wire transfer of Rs. 500,000 pending. SWIFT fee Rs. 5000 required.",
    "Standard Chartered: Your account is flagged for AML review. Share all documents.",
]]

# ── CAT 7: Government impersonation (25) ──
scam_messages += [("Government", "Scam", m) for m in [
    "NADRA: Your CNIC is expiring. Renewal fee Rs. 1500. Apply at nadra-renewal.pk",
    "FBR: Tax refund of Rs. 45,000 approved. Processing fee Rs. 2500 to receive.",
    "Passport Office: Your passport is ready. Courier fee Rs. 800. Pay online.",
    "SECP: Company registration approved. Annual fee Rs. 10,000. Pay at secp-annual.pk",
    "Punjab Police: FIR filed against you. Bail fee Rs. 25,000. Pay to avoid arrest.",
    "Sindh Revenue Board: Property tax overdue Rs. 15,000. Pay at srb-tax.pk",
    "Excise Department: Vehicle token tax due. Pay Rs. 3000 at excise-token.pk",
    "PEMRA: Your TV channel license suspended. Renewal fee Rs. 50,000.",
    "PTA: Your phone is not registered. Registration fee Rs. 5000. Pay at pta-register.pk",
    "Election Commission: Voter registration fee Rs. 500. Pay at ecp-voter.pk",
    "CDA: Property possession letter ready. Stamp duty Rs. 25,000.",
    "KDA: Plot allotment confirmed. Development charges Rs. 100,000.",
    "LDA: Housing scheme registration. Booking fee Rs. 50,000. Limited plots!",
    "NADRA: Aap ka CNIC block ho gaya hai. Rs. 2000 bhej kr unblock kren.",
    "FBR: Tax notice issued. Penalty Rs. 10,000 if not paid within 7 days.",
    "نیب: آپ کے خلاف کرپشن کیس درج ہے۔ 50000 روپے جرمانہ ادا کریں۔",
    "Punjab Government: Kissan card approved. Rs. 500 processing fee.",
    "Sindh Government: Health insurance card ready. Activation fee Rs. 300.",
    "Ministry of Education: Scholarship approved Rs. 100,000. Processing fee Rs. 5000.",
    "HEC: PhD scholarship Rs. 500,000. Application fee Rs. 10,000.",
    "NADRA family tree: Verification fee Rs. 3000 for inheritance claim.",
    "FBR audit: Your tax return selected for audit. Settlement fee Rs. 25,000.",
    "Passport: Urgent processing Rs. 5000 for 24-hour delivery.",
    "Civil Secretariat: Government job confirmation. Medical fee Rs. 8000.",
    "Revenue Department: Land mutation fee Rs. 15,000. Pay at revenue-mutation.pk",
]]

# ── CAT 8: Telecom scams (25) ──
scam_messages += [("Telecom", "Scam", m) for m in [
    "Jazz: Aap ne Rs. 5000 ka package subscribe kia hai. Cancel krne k liye Rs. 500 bhejen.",
    "Zong: Free 100GB data offer! Activation fee Rs. 200. Valid today only!",
    "Telenor: SIM upgrade to 5G. Fee Rs. 1500. Otherwise SIM deactivated.",
    "Ufone: International roaming activated. Deposit Rs. 10,000 required.",
    "JazzCash: Rs. 10,000 loan approved on your number. Processing fee Rs. 500.",
    "Zong 4G: Free device offer. Delivery fee Rs. 3000. Limited stock!",
    "Telenor: Your number will be disconnected. Recharge Rs. 500 to keep active.",
    "Jazz: Aap ko 50GB free data mil raha hai. Rs. 100 activation fee bhejen.",
    "PTCL: Broadband bill overdue Rs. 5000. Pay now or connection terminated.",
    "Nayatel: Fiber optic upgrade. Installation fee Rs. 8000. Special discount!",
    "StormFiber: Rs. 3000 monthly plan. Activation fee Rs. 2000. Free router!",
    "Jazz: Rs. 1000 ka balance expire ho raha hai. Rs. 200 bhej kr save kren.",
    "Zong: Super card activated. Rs. 5000/month. Cancel krne k liye call kren.",
    "Telenor: Your postpaid bill is Rs. 15,000. Pay now or legal action.",
    "Ufone: Free iPhone offer. Pay Rs. 5000 shipping and handling.",
    "Jazz: SIM block hone wali hai. Rs. 300 bhej kr activate rakhain.",
    "Telecom authority: Your number is not verified. Fine Rs. 5000 if not done today.",
    "5G tower installation: Rs. 50,000/month rent for your rooftop. Registration Rs. 10,000.",
    "Jazz: Unlimited calling package Rs. 999. Activation fee Rs. 200.",
    "Zong: International call package. Rs. 2000/month. Security deposit Rs. 5000.",
    "PTCL: Smart TV package. Rs. 1500/month. Installation Rs. 3000.",
    "Telenor microfinance: Rs. 100,000 loan. Processing fee Rs. 5000.",
    "Jazz: Aap ka number lucky draw mein select hua. Rs. 500 bhej kr claim kren.",
    "Mobile network: Your number is blacklisted. Removal fee Rs. 3000.",
    "SIM registration: Biometric verification failed. Re-verify fee Rs. 500.",
]]

# ── CAT 9: Phishing/Social Engineering (25) ──
scam_messages += [("Phishing", "Scam", m) for m in [
    "Your Facebook account will be deleted. Verify at facebook-verify.pk",
    "Instagram: Someone tried to login. Secure account at insta-secure.pk",
    "Gmail security alert: Unusual sign-in from Russia. Reset at gmail-reset.pk",
    "WhatsApp: Your account is being hacked. Forward this to 10 contacts to protect.",
    "Netflix: Payment failed. Update card at netflix-update.pk",
    "Amazon: Order #99887766 shipped. Track at amazon-track.pk (fake)",
    "Your Daraz account was hacked. Reset password at daraz-reset.pk",
    "LinkedIn: 5 recruiters viewed your profile. Premium offer Rs. 5000/month.",
    "Snapchat: Your account is locked. Verify at snapchat-verify.pk",
    "Twitter/X: Your account is suspended. Appeal at twitter-appeal.pk",
    "Google Pay: Rs. 5000 sent to wrong person. Refund at gpay-refund.pk",
    "YouTube: Your channel will be terminated. Verify at youtube-verify.pk",
    "TikTok: Your account violated guidelines. Appeal at tiktok-appeal.pk",
    "OLX: Your listing reported. Verify at olx-verify.pk",
    "Careem: Driver reported you. Account suspended. Verify at careem-verify.pk",
    "Foodpanda: Restaurant reported you. Ban pending. Verify at foodpanda-safe.pk",
    "Spotify: Payment failed. Update at spotify-update.pk",
    "Zoom: Your meeting was compromised. Security update at zoom-secure.pk",
    "Microsoft: Your Office 365 license expired. Renew at microsoft-renew.pk",
    "Apple ID: Your account is locked. Unlock at apple-unlock.pk",
    "Samsung: Your warranty is expiring. Extend at samsung-warranty.pk for Rs. 5000.",
    "HP: Your laptop warranty expired. Renew at hp-renew.pk for Rs. 8000.",
    "Adobe: Your subscription is overdue. Pay at adobe-pay.pk",
    "Dropbox: Storage full. Upgrade at dropbox-upgrade.pk",
    "WhatsApp Business: Your number is banned. Appeal at wa-appeal.pk",
]]

# ── CAT 10: Forex/Investment scams (25) ──
scam_messages += [("Forex/Investment", "Scam", m) for m in [
    "Forex signal: Rs. 10,000 invest kren. Rs. 100,000 profit in 1 week. Guaranteed!",
    "Gold trading: Rs. 50,000 se Rs. 500,000 monthly. Join VIP group.",
    "Mutual fund: 25% monthly return guaranteed. Minimum investment Rs. 25,000.",
    "Real estate: DHA plot booking Rs. 100,000. 200% return in 6 months.",
    "Stock market tips: Rs. 5000/month for insider information. 100% accurate.",
    "Binary options: Rs. 5000 trade, Rs. 50,000 profit. Demo available.",
    "Property investment: Bahria Town plot Rs. 500,000. Double in 1 year.",
    "Diamond investment: Rs. 100,000 buy, Rs. 300,000 sell in 3 months.",
    "Forex robot: Auto-trading software Rs. 15,000. Rs. 50,000/day profit.",
    "Crypto staking: 15% daily return. Minimum Rs. 10,000. Withdraw anytime.",
    "MLM business: Rs. 5000 join kren. Rs. 50,000/month earn kren. 3 logon ko add kren.",
    "Commodity trading: Oil, gold, silver. Rs. 20,000 investment. 300% return.",
    "Ponzi scheme disguised: Rs. 10,000 invest. Rs. 15,000 back in 7 days. Refer friends.",
    "NSE trading: Rs. 5000 account. Rs. 50,000/month. SECP registered (fake).",
    "Forex account management: Give us Rs. 100,000. We trade for you. 50% profit share.",
    "Islamic investment: Halal profit 20% monthly. Shariah compliant (fake).",
    "فاریکس: 10000 روپے لگائیں، 100000 روپے کمائیں۔",
    "Agricultural investment: Rs. 50,000 in farm. Rs. 200,000 harvest profit.",
    "Solar panel business: Rs. 100,000 invest. Rs. 30,000/month passive income.",
    "Car flipping: Rs. 200,000 buy, Rs. 350,000 sell. Guaranteed buyer.",
    "Import business: Rs. 50,000 for Chinese goods. 300% markup.",
    "Dropshipping course: Rs. 10,000. Rs. 100,000/month guaranteed.",
    "Freelance agency: Rs. 25,000 franchise fee. Rs. 200,000/month revenue.",
    "NFT investment: Rs. 5000 buy. Rs. 500,000 sell. Next big thing!",
    "AI trading bot: Rs. 20,000 license. Rs. 50,000/day automated profit.",
]]

print(f"Total scam messages: {len(scam_messages)}")
assert len(scam_messages) == 255, f"Expected 255 scam, got {len(scam_messages)}"
