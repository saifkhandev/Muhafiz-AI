"""Step 1: Audit the current 868-message training dataset."""
import sys, os, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from collections import Counter
from difflib import SequenceMatcher

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PK_FILE = os.path.join(DATA_DIR, "scam_messages_dataset.xlsx")
PK_SHEET = "Scam Detection Dataset"

def main():
    df = pd.read_excel(PK_FILE, sheet_name=PK_SHEET)
    
    print("=" * 70)
    print("  STEP 1: TRAINING DATA AUDIT")
    print("=" * 70)
    
    # Basic stats
    print(f"\n[1] TOTAL SAMPLES: {len(df)}")
    print(f"    Columns: {list(df.columns)}")
    
    # Label distribution
    labels = df["Label"].value_counts()
    print(f"\n[2] SCAM/SAFE DISTRIBUTION:")
    for lbl, cnt in labels.items():
        print(f"    {lbl}: {cnt} ({cnt/len(df)*100:.1f}%)")
    
    # Language distribution
    langs = df["Language Type"].value_counts()
    print(f"\n[3] LANGUAGE DISTRIBUTION:")
    for lang, cnt in langs.items():
        print(f"    {lang}: {cnt} ({cnt/len(df)*100:.1f}%)")
    
    # Scam category distribution
    cats = df["Scam Category"].value_counts()
    print(f"\n[4] SCAM CATEGORY DISTRIBUTION:")
    for cat, cnt in cats.items():
        print(f"    {cat}: {cnt} ({cnt/len(df)*100:.1f}%)")
    
    # Exact duplicates
    dup_full = df.duplicated().sum()
    dup_msg = df["Message Content"].duplicated().sum()
    print(f"\n[5] DUPLICATES:")
    print(f"    Full row duplicates: {dup_full}")
    print(f"    Duplicate messages: {dup_msg}")
    
    # Near-duplicates (within same source) - optimized with sampling
    print(f"\n[6] NEAR-DUPLICATE DETECTION (>=85% similarity, sampled)...")
    msgs = df["Message Content"].astype(str).tolist()
    near_dupes = []
    n = len(msgs)
    # Use shingle-based approach for speed instead of SequenceMatcher
    def char_shingles(text, k=4):
        t = text.lower().strip()
        return set(t[i:i+k] for i in range(max(len(t)-k+1, 1)))
    def jaccard(s1, s2):
        if not s1 or not s2: return 0.0
        inter = len(s1 & s2)
        union = len(s1 | s2)
        return inter / union if union > 0 else 0.0
    shingles = [char_shingles(msgs[i]) for i in range(n)]
    for i in range(n):
        for j in range(i+1, min(i+100, n)):  # Only check nearby pairs for speed
            li, lj = len(msgs[i]), len(msgs[j])
            if li == 0 or lj == 0: continue
            ratio = min(li, lj) / max(li, lj)
            if ratio < 0.6: continue
            sim = jaccard(shingles[i], shingles[j])
            if sim >= 0.75:  # Jaccard is stricter than SequenceMatcher
                near_dupes.append({
                    "i": i, "j": j, "sim": round(sim, 4),
                    "lbl_i": df.iloc[i]["Label"], "lbl_j": df.iloc[j]["Label"],
                    "msg_i": msgs[i][:60], "msg_j": msgs[j][:60],
                })
    
    print(f"    Near-duplicate pairs (>=85%): {len(near_dupes)}")
    for nd in near_dupes[:10]:
        conflict = "CONFLICT" if nd["lbl_i"] != nd["lbl_j"] else "same"
        print(f"      sim={nd['sim']:.2f} [{conflict}] {nd['msg_i']}...")
    
    # Conflicting labels
    conflicts = [nd for nd in near_dupes if nd["lbl_i"] != nd["lbl_j"]]
    print(f"\n[7] CONFLICTING LABELS (near-duplicates with different labels): {len(conflicts)}")
    
    # Message length distribution
    lengths = df["Message Content"].astype(str).str.len()
    print(f"\n[8] MESSAGE LENGTH DISTRIBUTION:")
    print(f"    Mean: {lengths.mean():.1f}")
    print(f"    Median: {lengths.median():.0f}")
    print(f"    Std: {lengths.std():.1f}")
    print(f"    Min: {lengths.min()}")
    print(f"    Max: {lengths.max()}")
    for q in [25, 50, 75, 90, 95]:
        print(f"    P{q}: {lengths.quantile(q/100):.0f}")
    
    # Roman Urdu deep dive
    print(f"\n[9] ROMAN URDU DEEP DIVE:")
    ru_mask = df["Language Type"] == "Roman Urdu"
    ru_df = df[ru_mask]
    print(f"    Total Roman Urdu: {len(ru_df)}")
    ru_scam = ru_df[ru_df["Label"] == "Scam"]
    ru_safe = ru_df[ru_df["Label"] == "Safe"]
    print(f"    Scam: {len(ru_scam)}")
    print(f"    Safe: {len(ru_safe)}")
    
    # Template analysis - look for repeated patterns in Roman Urdu
    print(f"\n[10] ROMAN URDU TEMPLATE ANALYSIS:")
    ru_scam_msgs = ru_scam["Message Content"].astype(str).tolist()
    
    # Count common prefixes
    prefix_counts = Counter()
    for msg in ru_scam_msgs:
        words = msg.split()
        for n_words in [2, 3, 4]:
            prefix = " ".join(words[:n_words]).lower()
            prefix_counts[prefix] += 1
    
    print(f"    Top 15 prefixes in Roman Urdu scam messages:")
    for prefix, count in prefix_counts.most_common(15):
        if count >= 2:
            print(f"      '{prefix}' appears {count} times")
    
    # Template-like structures
    templates = [
        "Mubarak ho", "mubarak ho",
        "Moaziz sarif", "moaziz sarif",
        "inaam", "inam", "prize",
        "account block", "account band",
        "OTP", "otp", "PIN", "pin",
        "Easypaisa", "JazzCash", "easypaisa", "jazzcash",
        "BISP", "Ehsaas", "bisp", "ehsaas",
    ]
    print(f"\n    Template keyword frequency in Roman Urdu scam:")
    for t in templates:
        count = sum(1 for msg in ru_scam_msgs if t.lower() in msg.lower())
        if count > 0:
            print(f"      '{t}': {count} messages ({count/len(ru_scam_msgs)*100:.1f}%)")
    
    # Roman Urdu safe messages analysis
    print(f"\n[11] ROMAN URDU SAFE MESSAGE ANALYSIS:")
    ru_safe_msgs = ru_safe["Message Content"].astype(str).tolist()
    safe_patterns = [
        "OTP", "otp", "PIN", "pin",
        "account", "bank",
        "transaction", "debit",
        "successfully", "confirmed",
        "share", "never",
    ]
    print(f"    Safe messages with scam-like keywords:")
    for p in safe_patterns:
        count = sum(1 for msg in ru_safe_msgs if p.lower() in msg.lower())
        if count > 0:
            print(f"      '{p}': {count} safe messages")
    
    # Cross-language breakdown by scam category
    print(f"\n[12] SCAM CATEGORY x LANGUAGE BREAKDOWN:")
    cross = pd.crosstab(df["Scam Category"], df["Language Type"])
    print(cross.to_string())
    
    # Abbreviated spelling check
    print(f"\n[13] SPELLING VARIATION IN ROMAN URDU:")
    abbrevs = {
        "lga": "laga", "krne": "karne", "k lie": "ke liye",
        "krin": "karein", "krna": "karna", "bhejain": "bhejein",
        "kare": "karein", "hain": "hai", "nahi": "naheen",
        "acount": "account", "acount": "account",
    }
    for short, full in abbrevs.items():
        short_count = sum(1 for msg in ru_scam_msgs if short.lower() in msg.lower())
        full_count = sum(1 for msg in ru_scam_msgs if full.lower() in msg.lower())
        if short_count > 0 or full_count > 0:
            print(f"      '{short}' (abbrev): {short_count}, '{full}' (full): {full_count}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"  AUDIT SUMMARY")
    print(f"{'='*70}")
    print(f"  Total messages: {len(df)}")
    print(f"  Scam: {labels.get('Scam', 0)} / Safe: {labels.get('Safe', 0)}")
    print(f"  Languages: {dict(langs)}")
    print(f"  Roman Urdu: {len(ru_df)} (Scam={len(ru_scam)}, Safe={len(ru_safe)})")
    print(f"  Duplicates: {dup_full} full, {dup_msg} message-only")
    print(f"  Near-duplicates (>=85%): {len(near_dupes)}")
    print(f"  Conflicting labels: {len(conflicts)}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
