"""
Streamlit Frontend — CGAN Colorizer
====================================
Run with : streamlit run app.py
"""

import io
import base64
import requests
import streamlit as st
from PIL import Image, ImageDraw

API = "http://localhost:8000"

st.set_page_config(
    page_title="CGAN Colorizer",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────────────────────
# 🔷 MODERN DESIGN - LARGE BUTTONS + ELEGANT TYPOGRAPHY
# ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

* {
    font-family: 'Space Grotesk', sans-serif;
}

.stApp {
    background: radial-gradient(ellipse at 20% 30%, #0a0a1a, #02020a);
    background-attachment: fixed;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(8, 8, 18, 0.8) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* ─── LARGE BUTTONS ─── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
    color: white;
    border: none;
    border-radius: 60px;
    padding: 0.9rem 2rem !important;
    font-weight: 600;
    font-size: 1rem !important;
    letter-spacing: -0.2px;
    transition: all 0.25s ease;
    box-shadow: 0 8px 20px rgba(124, 58, 237, 0.3);
    width: 100%;
    cursor: pointer;
}

.stButton > button:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(124, 58, 237, 0.4);
}

.stButton > button:active {
    transform: translateY(1px);
}

/* Large download buttons */
.stDownloadButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
    padding: 0.8rem 1.8rem !important;
    font-size: 0.95rem !important;
    border-radius: 60px;
}

/* File uploader - larger */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.02);
    border: 2px dashed rgba(124, 58, 237, 0.4);
    border-radius: 28px;
    padding: 3rem 2rem;
    transition: 0.25s;
}

[data-testid="stFileUploader"]:hover {
    border-color: #8b5cf6;
    background: rgba(124, 58, 237, 0.05);
}

/* Metrics cards */
[data-testid="metric-container"] {
    background: rgba(20, 20, 40, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 1.2rem;
}

/* Tabs styling */
[data-baseweb="tab-list"] {
    gap: 12px;
    background: transparent;
    margin-bottom: 2rem;
}

[data-baseweb="tab"] {
    background: rgba(30,30,55,0.4) !important;
    border-radius: 60px !important;
    padding: 0.6rem 2rem !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    color: #aaa !important;
    font-weight: 500;
    font-size: 1rem;
}

[aria-selected="true"] {
    background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
    color: white !important;
    border: none !important;
}

/* Elegant titles */
h1 {
    background: linear-gradient(135deg, #ffffff, #c084fc, #a855f7);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 3.2rem !important;
    letter-spacing: -0.03em;
    text-align: center;
    margin-bottom: 0.5rem;
}

h2 {
    background: linear-gradient(135deg, #e0e0ff, #c084fc);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 600;
    font-size: 1.8rem;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(30,30,55,0.4) !important;
    border-radius: 20px !important;
    font-weight: 500;
    padding: 1rem !important;
}

/* Slider */
[data-testid="stSlider"] {
    background: rgba(30,30,55,0.5);
    border-radius: 60px;
    padding: 0.8rem 1rem;
}

/* Info/Success/Warning */
.stAlert {
    background: rgba(20,20,40,0.7) !important;
    backdrop-filter: blur(12px);
    border-radius: 20px !important;
    border: 1px solid rgba(255,255,255,0.1);
}

/* Caption */
.stCaption {
    color: #9ca3af !important;
    font-size: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64)))

def pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def api_get(path: str):
    try:
        r = requests.get(f"{API}{path}", timeout=6)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_post_file(path: str, file_bytes: bytes, filename: str):
    try:
        r = requests.post(f"{API}{path}", files={"file": (filename, file_bytes, "image/jpeg")}, timeout=70)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_delete(path: str):
    try:
        requests.delete(f"{API}{path}", timeout=5)
        return True, None
    except Exception as e:
        return False, str(e)

# ────────────────────────────────────────────────────────────────
# SIDEBAR - Minimal & clean
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 1.5rem 0;'>
        <div style='font-size: 4rem;'>✨</div>
        <h2 style='margin: 0.5rem 0 0 0;'>CGAN</h2>
        <p style='color: #8b8b9e; font-size: 0.75rem; margin-top: -0.2rem;'>colorization</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    health, _ = api_get("/health")
    if health and health.get("model_loaded"):
        st.markdown("""
        <div style='background: rgba(34,197,94,0.08); border-radius: 40px; padding: 0.8rem; text-align: center; border: 0.5px solid rgba(34,197,94,0.3);'>
            <span style='font-size: 0.8rem;'>● system ready</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: rgba(239,68,68,0.08); border-radius: 40px; padding: 0.8rem; text-align: center; border: 0.5px solid rgba(239,68,68,0.3);'>
            <span style='font-size: 0.8rem;'>● offline</span>
        </div>
        """, unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────
# MAIN TABS
# ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["colorize", "history", "statistics"])

# ════════════════════════════════════════════════════════════════
# TAB 1 - COLORIZE
# ════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div style='text-align: center; margin: 1rem 0 2rem 0;'>
        <h1>AI-Powered Black & White to Color Transformation</h1>
        <p style='color: #9ca3af; font-size: 1rem;'>transform your photos with AI</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        label_visibility="collapsed",
    )

    if uploaded:
        original_pil = Image.open(uploaded).convert("RGB")
        w, h = original_pil.size

        # Two large columns
        col_left, col_right = st.columns([1, 2])
        with col_left:
            run = st.button("🎨 GENERATE COLOR", use_container_width=True, type="primary")
        with col_right:
            st.caption(f"📐 {w} × {h} px  ·  {uploaded.name}")

        if run:
            with st.spinner("processing image..."):
                result, err = api_post_file("/colorize", uploaded.getvalue(), uploaded.name)
            
            if err:
                st.error(f"error: {err}")
            else:
                output_pil = b64_to_pil(result["output_b64"])
                duration = result["duration_ms"]

                st.success(f"✓ colorized in {duration:.0f} ms")
                
                # Large comparison slider
                st.markdown("#### — interactive comparison —")
                
                slider_val = st.slider(
                    "",
                    0, 100, 50,
                    label_visibility="collapsed",
                    key="compare"
                )

                # Build comparison image
                target_w = 900
                ratio = target_w / w
                disp_h = int(h * ratio)
                
                orig_resized = original_pil.resize((target_w, disp_h))
                out_resized = output_pil.resize((target_w, disp_h))

                split_x = int(target_w * slider_val / 100)
                composite = Image.new("RGB", (target_w, disp_h))
                composite.paste(orig_resized.crop((0, 0, split_x, disp_h)), (0, 0))
                composite.paste(out_resized.crop((split_x, 0, target_w, disp_h)), (split_x, 0))

                draw = ImageDraw.Draw(composite)
                for offset in [-2, 0, 2]:
                    draw.line([(split_x + offset, 0), (split_x + offset, disp_h)], fill=(255,255,255,180), width=2)
                
                center_x, center_y = split_x, disp_h // 2
                draw.ellipse([center_x-22, center_y-22, center_x+22, center_y+22], fill="white")
                draw.ellipse([center_x-16, center_y-16, center_x+16, center_y+16], fill="#7c3aed")

                st.image(composite, use_container_width=True)
                
                # Labels
                lcol, mcol, rcol = st.columns(3)
                lcol.markdown("<p style='text-align: center; color: #9ca3af;'>◀ original</p>", unsafe_allow_html=True)
                mcol.markdown(f"<p style='text-align: center; color: #9ca3af;'>slider: {slider_val}%</p>", unsafe_allow_html=True)
                rcol.markdown("<p style='text-align: center; color: #9ca3af;'>colorized ▶</p>", unsafe_allow_html=True)

                st.divider()
                
                # Large download button
                col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
                with col_d2:
                    st.download_button(
                        "⬇ DOWNLOAD COLORIZED IMAGE",
                        data=pil_to_bytes(output_pil),
                        file_name=f"colorized_{uploaded.name.rsplit('.', 1)[0]}.png",
                        mime="image/png",
                        use_container_width=True,
                    )
    else:
        # Empty state - visually appealing
        st.markdown("""
        <div style='text-align: center; padding: 4rem 2rem;'>
            <div style='font-size: 5rem; opacity: 0.4;'>🖼</div>
            <h3 style='margin-top: 1rem; color: #d1d5db;'>drop your image here</h3>
            <p style='color: #6b7280; margin-top: 0.5rem;'>JPEG · PNG · WEBP · BMP</p>
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# TAB 2 - HISTORY
# ════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>history</h2>", unsafe_allow_html=True)
    
    col_ref, col_clr = st.columns(2)
    with col_ref:
        if st.button("⟳ refresh", use_container_width=True):
            st.rerun()
    with col_clr:
        if st.button("🗑 clear all", use_container_width=True):
            api_delete("/history")
            st.rerun()

    st.divider()

    history, err = api_get("/history?limit=25")
    
    if err:
        st.error(err)
    elif not history:
        st.info("no colorizations yet — start with the colorize tab")
    else:
        for item in history:
            with st.expander(f"📷 {item['filename']}  ·  {item['created_at'][:19]}  ·  {item['duration_ms']:.0f} ms"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.image(b64_to_pil(item["input_b64"]), caption="original", use_container_width=True)
                with col_b:
                    out_img = b64_to_pil(item["output_b64"])
                    st.image(out_img, caption="colorized", use_container_width=True)
                
                dcol, xcol = st.columns(2)
                with dcol:
                    st.download_button(
                        "download",
                        data=pil_to_bytes(out_img),
                        file_name=f"result_{item['id']}.png",
                        key=f"d_{item['id']}"
                    )
                with xcol:
                    if st.button("delete", key=f"del_{item['id']}"):
                        api_delete(f"/history/{item['id']}")
                        st.rerun()

# ════════════════════════════════════════════════════════════════
# TAB 3 - STATISTICS
# ════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>statistics</h2>", unsafe_allow_html=True)
    
    stats, err = api_get("/stats")
    
    if err:
        st.error(err)
    elif not stats or stats.get("total", 0) == 0:
        st.info("no data available — colorize an image first")
    else:
        total = stats.get("total", 0)
        avg_ms = stats.get("avg_ms", 0) or 0
        min_ms = stats.get("min_ms", 0) or 0
        max_ms = stats.get("max_ms", 0) or 0
        days = stats.get("active_days", 0)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("total images", total)
        m2.metric("average", f"{avg_ms:.0f} ms")
        m3.metric("fastest", f"{min_ms:.0f} ms")
        m4.metric("slowest", f"{max_ms:.0f} ms")
        m5.metric("active days", days)

        if total > 0:
            st.divider()
            st.markdown("#### performance trend")
            
            history, _ = api_get("/history?limit=100")
            if history:
                import pandas as pd
                df = pd.DataFrame(history)[["created_at", "duration_ms"]].sort_values("created_at")
                df.columns = ["timestamp", "ms"]
                st.line_chart(df.set_index("timestamp")["ms"], use_container_width=True)
                
                st.markdown("#### detailed log")
                st.dataframe(df, use_container_width=True, hide_index=True)