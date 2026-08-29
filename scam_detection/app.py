"""Muhafizz AI - Scam Detection Dashboard
Streamlit web app for the Alibaba AI Hackathon Regional Round.
"""
import sys, os, warnings, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import streamlit as st
import numpy as np

# Set page config FIRST (before any other Streamlit calls)
st.set_page_config(
    page_title="Muhafizz AI - Scam Detection",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Project imports ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.predict import predict_message, load_model

# ── Session state for caching models ──
@st.cache_resource
def get_model():
    """Load the text classification model (cached across reruns)."""
    artifacts, le, threshold, metadata = load_model()
    return artifacts, le, threshold, metadata

def predict_text(message):
    """Run text prediction."""
    artifacts, le, threshold, metadata = get_model()
    return predict_message(message, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)

def predict_audio(audio_file):
    """Run audio prediction if Whisper is available."""
    try:
        from src.call_predict import predict_call
        from src.transcribe import load_stt_model

        artifacts, le, threshold, metadata = get_model()

        @st.cache_resource
        def get_stt():
            return load_stt_model()

        stt_model, stt_backend = get_stt()

        # Save uploaded audio to temp file
        temp_dir = os.path.join(PROJECT_ROOT, "temp_audio")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, "upload.wav")
        with open(temp_path, "wb") as f:
            f.write(audio_file.read())

        result = predict_call(
            temp_path,
            artifacts=artifacts, le=le, threshold=threshold, metadata=metadata,
            stt_model=stt_model, stt_backend=stt_backend,
        )
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return result
    except ImportError:
        return None
    except Exception as e:
        return {"error": str(e)}

# ── Custom CSS ──
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .verdict-box {
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin: 1rem 0;
    }
    .verdict-scam {
        background-color: #FFE0E0;
        border: 2px solid #E53E3E;
    }
    .verdict-safe {
        background-color: #E0FFE0;
        border: 2px solid #38A169;
    }
    .verdict-medium {
        background-color: #FFF3E0;
        border: 2px solid #DD6B20;
    }
    .metric-row {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    .metric-item {
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown('<div class="main-header">🛡️ Muhafizz AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time Scam Detection for Pakistan — Text & Audio</div>', unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.header("About")
    st.markdown("""
    **Muhafizz AI** detects scam messages in **English, Roman Urdu, Urdu, and Mixed** languages.
    
    **Model:** TF-IDF + LinearSVC (V4)  
    **Training:** 1,637 messages across 10 scam categories  
    **Accuracy:** 99.6% on 505 adversarial messages  
    **Recall:** 99.6% | **FPR:** 0.4%  
    """)
    st.divider()
    st.markdown("**Languages Supported**")
    st.markdown("- 🇬🇧 English\n- 🇵🇰 Roman Urdu\n- 🇵🇰 Urdu (اردو)\n- 🔄 Mixed")
    st.divider()
    st.markdown("**Alibaba AI Hackathon**  \nKarachi Regional Round 2026")

# ── Main tabs ──
tab1, tab2, tab3 = st.tabs(["💬 Text Message", "🎵 Audio Call", "ℹ️ How It Works"])

# ── TAB 1: Text Classification ──
with tab1:
    st.subheader("Paste a suspicious message")
    message = st.text_area(
        "Enter message text:",
        placeholder="e.g., Moaziz sarif, apka BISP ki taraf se 12500 PKR ka inaam nikla hai...",
        height=120,
    )
    col1, col2 = st.columns([1, 3])
    with col1:
        analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)
    with col2:
        if st.button("📋 Try Example", use_container_width=True):
            message = "Moaziz sarif, apka BISP ki taraf se 12500 PKR ka inaam nikla hai. Taseeq k liye 0312-9988776 par pin code bhejen."

    if analyze_btn and message.strip():
        with st.spinner("Analyzing message..."):
            result = predict_text(message.strip())

        # Verdict display
        label = result["label"]
        prob = result["scam_probability"]
        confidence = result["confidence"]

        if label == "Scam":
            css_class = "verdict-scam"
            emoji = "⚠️"
            verdict_text = "SCAM DETECTED"
        else:
            css_class = "verdict-safe"
            emoji = "✅"
            verdict_text = "SAFE"

        st.markdown(f"""
        <div class="verdict-box {css_class}">
            <div style="font-size: 3rem;">{emoji}</div>
            <div style="font-size: 1.8rem; font-weight: 700;">{verdict_text}</div>
        </div>
        """, unsafe_allow_html=True)

        # Metrics
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Scam Probability", f"{prob:.1%}")
        with col_b:
            st.metric("Confidence", f"{confidence:.1%}")
        with col_c:
            risk = "High" if prob > 0.6 else ("Medium" if prob > 0.35 else "Low")
            st.metric("Risk Level", risk)

        # Probability bar
        st.markdown("**Probability Breakdown:**")
        st.progress(min(prob, 1.0))
        st.caption(f"Scam: {prob:.1%} | Safe: {1-prob:.1%}")

    elif analyze_btn and not message.strip():
        st.warning("Please enter a message to analyze.")

# ── TAB 2: Audio Classification ──
with tab2:
    st.subheader("Upload a suspicious call recording")
    st.markdown("Upload an audio file (.wav, .mp3, .aac, .ogg) to analyze for scam patterns.")

    audio_file = st.file_uploader(
        "Choose an audio file",
        type=["wav", "mp3", "aac", "ogg", "m4a", "flac"],
    )

    if audio_file:
        st.audio(audio_file)

        if st.button("🎵 Analyze Audio", type="primary"):
            with st.spinner("Transcribing and analyzing audio..."):
                result = predict_audio(audio_file)

            if result is None:
                st.warning("Audio analysis requires the Whisper speech-to-text model. Please download it first.")
                st.info("Run: `python -c \"from src.transcribe import load_stt_model; load_stt_model()\"`")
            elif "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                # Display results
                risk = result["overall_risk"]
                score = result["risk_score"]

                if risk == "High":
                    css_class = "verdict-scam"
                    emoji = "⚠️"
                    verdict_text = "HIGH RISK CALL"
                elif risk == "Medium":
                    css_class = "verdict-medium"
                    emoji = "⚡"
                    verdict_text = "MEDIUM RISK CALL"
                else:
                    css_class = "verdict-safe"
                    emoji = "✅"
                    verdict_text = "LOW RISK CALL"

                st.markdown(f"""
                <div class="verdict-box {css_class}">
                    <div style="font-size: 3rem;">{emoji}</div>
                    <div style="font-size: 1.8rem; font-weight: 700;">{verdict_text}</div>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Risk Score", f"{score:.1%}")
                col_b.metric("Scam Segments", f"{result['scam_segment_count']}/{result['total_segments']}")
                col_c.metric("Duration", f"{result['call_duration_seconds']:.1f}s")
                col_d.metric("Language", result['language_detected'])

                # Segment details
                if result.get("segment_predictions"):
                    st.markdown("### Segment Analysis")
                    active = [s for s in result["segment_predictions"] if not s["was_skipped"]]
                    for seg in active:
                        ts = f"[{int(seg['start_time'])//60:02d}:{int(seg['start_time'])%60:02d}]"
                        label = seg["label"]
                        prob = seg["scam_probability"]
                        text = seg["cleaned_text"] or seg["text"]
                        icon = "🔴" if label == "Scam" else "🟢"
                        st.markdown(f"**{ts}** {icon} {label} (P={prob:.2f})")
                        st.caption(f"> {text[:100]}...")

# ── TAB 3: How It Works ──
with tab3:
    st.subheader("How Muhafizz AI Works")

    st.markdown("""
    ### Text Classification Pipeline
    
    ```
    Message → Normalizer → TF-IDF Features → LinearSVC → Verdict
    ```
    
    1. **Normalization**: Lowercase, Unicode normalization, Roman Urdu spelling correction, 
       phone number/URL preservation, USSD code detection
    2. **Feature Extraction**: Combined word (1,2)-gram + character (3,5)-gram TF-IDF vectors
    3. **Classification**: LinearSVC with calibrated probabilities
    4. **Decision**: Threshold-based verdict (Scam if P ≥ 0.23)
    
    ### Audio Call Pipeline
    
    ```
    Audio → Whisper STT → Segments → Classify Each → Aggregate → Verdict
    ```
    
    1. **Audio Loading**: pydub normalizes to 16kHz mono WAV
    2. **Transcription**: faster-whisper (INT8) with VAD filtering
    3. **Segment Processing**: Filler removal, short segment concatenation, text cleanup
    4. **Per-Segment Classification**: Each segment scored independently
    5. **Aggregation**: Weighted scoring (max_prob, temporal weighting, scam ratio)
    
    ### Model Specifications
    
    | Component | Specification |
    |-----------|--------------|
    | Architecture | TF-IDF + LinearSVC (C=5.0) |
    | Training Data | 1,637 messages (879 scam, 758 safe) |
    | Scam Categories | 10 (delivery, govt, job, wallet, prize, telecom, bank, forex, phishing, BISP) |
    | Languages | English, Roman Urdu, Urdu, Mixed |
    | Model Size | ~2 MB |
    | Inference Speed | < 5 ms/message |
    
    ### Performance Metrics
    
    | Test Set | Messages | Accuracy | Recall |
    |----------|----------|----------|--------|
    | Blind Test | 50 | 98.0% | 96.0% |
    | Hard Adversarial | 56 | 98.2% | 100.0% |
    | Comprehensive 505 | 505 | 99.6% | 99.6% |
    | Combined (all) | 617 | 98.7% | — |
    
    ### Limitations (Honest Disclosure)
    
    - Trained on 1,637 messages across 10 scam categories
    - Roman Urdu spelling variation can cause edge cases
    - No transformer comparison completed (TF-IDF+SVM chosen for speed: <10ms/msg)
    - Audio transcription uses medium Whisper model (~1.5 GB, 23-35s processing)
    - Threshold (0.63) optimized for balanced recall + FP reduction
    """)

# ── Footer ──
st.divider()
st.caption("Muhafizz AI v4 — Built for the Alibaba AI Hackathon Karachi Regional Round 2026")
