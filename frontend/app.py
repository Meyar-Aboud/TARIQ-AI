import streamlit as st
from PIL import Image
import requests
import pandas as pd
import pydeck as pdk
import os
from streamlit_geolocation import streamlit_geolocation

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")

# 1. Page Configuration
st.set_page_config(
    page_title="TARIQ AI",
    page_icon="🚧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Custom CSS Injection (Glassmorphism & Gradients)
st.markdown("""
<style>
    /* Hero Header Styling */
    .hero-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 2.2rem;
        border-radius: 20px;
        box-shadow: 0 15px 30px -5px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1.5rem;
    }
    
    .hero-title {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        background: linear-gradient(to right, #60a5fa, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        color: #cbd5e1;
        margin-top: 0.4rem;
        font-weight: 300;
    }

    /* Container Glass Effects */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background: rgba(30, 41, 59, 0.4) !important;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
    }

    /* Custom Button Styling */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4) !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.7) !important;
    }

    /* Styled Workflow Steps */
    .step-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 8px;
    }
    
    .step-num {
        background: #6366f1;
        color: white;
        border-radius: 50%;
        width: 26px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. Hero Banner
st.markdown("""
<div class="hero-banner">
    <div style="display: flex; align-items: center; gap: 18px;">
        <span style="font-size: 3.2rem;">🚧</span>
        <div>
            <h1 class="hero-title">TARIQ AI</h1>
            <p class="hero-subtitle">TARIQ AI • Automated Road Hazard Analysis & Municipal Dispatch Portal</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. Tab Navigation
tab_report, tab_map = st.tabs(["🚧 Pothole Report", "🗺️ Maps Analytics"])

# ==================== PAGE 1: POTHOLE REPORT ====================
with tab_report:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        with st.container(border=True):
            st.subheader("📋 Instructions")
            st.markdown("""
            <div class="step-card">
                <div class="step-num">1</div>
                <div>Upload a clear image of the road surface pothole.</div>
            </div>
            <div class="step-card">
                <div class="step-num">2</div>
                <div>AI detects potholes and calculates the severity score.</div>
            </div>
            <div class="step-card">
                <div class="step-num">3</div>
                <div>Report is automatically dispatched to local county maintenance.</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("📸 Evidence Upload")
            uploaded = st.file_uploader(
                "Upload image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    with col_right:
        with st.container(border=True):
            st.subheader("🔍 Analysis Dashboard")

            if uploaded is None:
                st.info(
                    "👈 Please upload a road image on the left to begin analysis.")
            else:
                left, right = st.columns(2)

                with left:
                    st.caption("📷 Original Upload")
                    st.image(uploaded, caption="image preview",
                             use_container_width=True)

                analyze_clicked = st.button("Analyse")

                if analyze_clicked:
                    with st.spinner("Analyzing image and generating report..."):
                        bytess = uploaded.getvalue()
                        files = {
                            "file": (uploaded.name, bytess, uploaded.type)}
                        url_upload = f"{BACKEND_URL}/upload_image"

                        # Browser location, sent as a fallback in case the
                        # image itself has no EXIF GPS data.
                        loc = streamlit_geolocation()
                        data = {}
                        if loc and loc.get("latitude") and loc.get("longitude"):
                            data["client_lat"] = loc["latitude"]
                            data["client_lon"] = loc["longitude"]

                        r = requests.post(url_upload, files=files, data=data)

                        if r.status_code == 200:
                            st.success("Analysis completed")
                            response = r.json()

                            # --- 1. IF NO POTHOLES DETECTED (SEVERITY 0) ---
                            if response.get("severity") == 0:
                                with right:
                                    st.caption("📷 Result Preview")
                                    st.image(
                                        uploaded,
                                        caption="No potholes detected",
                                        use_container_width=True,
                                    )
                                st.info(
                                    "✅ Road looks clear! No potholes were detected in this image.")

                            # --- 2. ELSE: POTHOLES FOUND (SEVERITY > 0) ---
                            else:
                                st.metric(
                                    label="Calculated Severity Score",
                                    value=f"{response.get('severity')}/10",
                                )

                                # Only fetch bounding box overlay if a real report ID exists
                                report_id = response.get("report_id")
                                url_collected = f"{BACKEND_URL}/collected/{report_id}"
                                img_res = requests.get(url_collected)

                                if img_res.status_code == 200:
                                    with right:
                                        st.caption("🖼️ Detection Overlay")
                                        st.image(
                                            img_res.content,
                                            caption="Processed Image",
                                            use_container_width=True,
                                        )
                                else:
                                    st.error(
                                        "Failed to load processed image from backend")

                        else:
                            st.error("Fetching error, please try again.")

# ==================== PAGE 2: MAPS ANALYTICS ====================
with tab_map:
    st.subheader("🗺️ Geospatial Pothole Map")

    try:
        r = requests.get(f"{BACKEND_URL}/reports")

        if r.status_code == 200:
            potholes_data = r.json()
            df_potholes = pd.DataFrame(potholes_data)

            # -----------------------------------------------------------------------------
            # 1. INTERACTIVE PYDECK MAP
            # -----------------------------------------------------------------------------
            with st.container(border=True):
                if not df_potholes.empty:
                    layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=df_potholes,
                        id="pothole-pins",
                        get_position=["lon", "lat"],
                        get_color="[239, 68, 68, 220]",
                        get_radius=150,
                        pickable=True,
                    )

                    view_state = pdk.ViewState(
                        latitude=36.7538, longitude=3.0588, zoom=10, pitch=0
                    )

                    event = st.pydeck_chart(
                        pdk.Deck(
                            layers=[layer],
                            initial_view_state=view_state,
                            tooltip={
                                "html": "<b>ID:</b> {id}<br><b>Severity:</b> {severity}/10<br><b>Date:</b> {date_taken}",
                                "style": {
                                    "backgroundColor": "#1e293b",
                                    "color": "white",
                                },
                            },
                        ),
                        on_select="rerun",
                        selection_mode="single-object",
                    )
                else:
                    st.info("No pothole data available to display on the map.")
                    event = None

            # -----------------------------------------------------------------------------
            # 2. DYNAMIC CLICK DETAILS DISPLAY
            # -----------------------------------------------------------------------------
            with st.container(border=True):
                st.subheader("🔍 Selected Report Details")

                if (
                    event
                    and event.selection
                    and "pothole-pins" in event.selection["objects"]
                ):
                    selected_objects = event.selection["objects"]["pothole-pins"]

                    if selected_objects:
                        clicked_item = selected_objects[0]

                        col_img, col_info = st.columns([1, 2], gap="medium")

                        with col_img:
                            # image_url from the backend is now a relative API route
                            # (e.g. "/collected/{id}") since images are served from the
                            # database instead of static files, so it needs the backend
                            # host prefixed to be a valid, fetchable URL.
                            image_url = clicked_item.get("image_url")
                            full_image_url = f"{BACKEND_URL}{image_url}" if image_url else None

                            if full_image_url:
                                st.image(
                                    full_image_url,
                                    caption=f"Evidence Photo • ID: {clicked_item.get('id')}",
                                    use_container_width=True,
                                )
                            else:
                                st.info("No image available for this report.")

                        with col_info:
                            st.markdown(
                                f"### Report ID: `{clicked_item.get('id')}`")

                            col_metric1, col_metric2 = st.columns(2)
                            col_metric1.metric(
                                "Severity Score", f"{clicked_item.get('severity')}/10"
                            )
                            col_metric2.metric(
                                "Coordinates",
                                f"{clicked_item.get('lat')}, {clicked_item.get('lon')}",
                            )

                            st.markdown(
                                f"**📅 Date Taken:** `{clicked_item.get('date_taken')}`"
                            )
                            st.markdown(
                                "**📍 Location Source:** Automatic EXIF GPS Verification"
                            )
                    else:
                        st.info(
                            "👆 Click on any red dot on the map above to view detailed report analysis."
                        )
                else:
                    st.info(
                        "👆 Click on any red dot on the map above to view detailed report analysis."
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # -----------------------------------------------------------------------------
            # 3. BOTTOM STATISTICS SECTION
            # -----------------------------------------------------------------------------
            col_count, col_severity = st.columns(2, gap="large")

            total_count = len(df_potholes) if not df_potholes.empty else 0
            avg_severity = (
                round(df_potholes["severity"].mean(), 2)
                if not df_potholes.empty
                else "—"
            )

            with col_count:
                with st.container(border=True):
                    st.subheader("📊 Pothole Count")
                    st.markdown(
                        f"""
                    * **In Selected Region:** {total_count}
                    * **Total Active Reports:** {total_count}
                    """
                    )

            with col_severity:
                with st.container(border=True):
                    st.subheader("📈 Mean Severity")
                    st.metric(
                        label="Calculated Mean Severity Score", value=avg_severity
                    )
        else:
            st.error(
                f"Failed to fetch reports from backend (HTTP Status: {r.status_code})")

    except Exception as e:
        st.error(f"Could not connect to backend server: {e}")
