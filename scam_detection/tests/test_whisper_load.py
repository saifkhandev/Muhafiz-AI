"""Test loading whisper medium model from local directory."""
import sys, os, warnings, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

local_path = os.path.join(PROJECT_ROOT, "models", "whisper-medium")
print(f"Loading faster-whisper from: {local_path}")
print(f"Files: {os.listdir(local_path)}")

t0 = time.time()
try:
    from faster_whisper import WhisperModel
    model = WhisperModel(local_path, compute_type="int8", device="cpu")
    print(f"SUCCESS! Model loaded in {time.time()-t0:.1f}s")
    print(f"Model type: {type(model).__name__}")
except Exception as e:
    print(f"FAILED: {e}")
    print(f"\nFalling back to tiny model from HF cache...")
    try:
        model = WhisperModel("tiny", compute_type="int8", device="cpu")
        print(f"Tiny model loaded in {time.time()-t0:.1f}s")
    except Exception as e2:
        print(f"Tiny also failed: {e2}")
