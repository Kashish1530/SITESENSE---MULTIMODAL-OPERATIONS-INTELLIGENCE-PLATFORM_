"""
app_streamlit.py — SiteSense Operations Intelligence (Enterprise UI Edition)
Member 2: Video Analytics, Spatial Intelligence & Violation Lifecycle Management

Refined UI Architecture:
  Header: Executive KPI Banner & System Status
  Tab 1: 🎥 Live Vision Ops (Stream, Real-Time HUD, Live Telemetry)
  Tab 2: 📸 Forensic Evidence Gallery (Clean Multi-Column Grid, No Endless Scrolling)
  Tab 3: 🔥 Post-Shift Heatmap & PDF Compliance Report
  Tab 4: 🚨 Violation Lifecycle & Resolution Desk (Before-and-After Proof Comparison)
  Tab 5: 📊 Compliance Analytics & Weekly Trends
"""

import streamlit as st
import cv2
import json
import os
import glob
import shutil
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

import sys
sys.path.append(os.path.abspath("src"))
from tracker import ByteTrackEngine
from zone_engine import ZoneEngine
from event_generator import SpatialEventFormatter
from annotator import VisualAnnotator
from heatmap_generator import HeatmapGenerator
from report_generator import generate_pdf_report
from zone_validator import (
    ZoneConfigValidator, CANONICAL_CLASSES,
    VALID_SEVERITIES, VALID_ZONE_TYPES, get_zone_config_json_schema
)
from violation_db import (
    init_db, insert_violation, resolve_violation,
    get_active_violations, get_resolved_violations,
    get_weekly_summary, get_violation_by_id, get_all_violations_count
)

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SiteSense | Operations Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database
init_db()

# ── Modern Styling CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global Font & Spacing */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Header Card */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white;
        padding: 1.25rem 1.75rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* KPI Metric Cards */
    .kpi-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* Severity Badges */
    .badge-critical {
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #f87171;
    }
    .badge-high {
        background-color: #fef3c7;
        color: #92400e;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #fcd34d;
    }
    .badge-resolved {
        background-color: #d1fae5;
        color: #065f46;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #6ee7b7;
    }
    
    /* Evidence Grid Cards */
    .evidence-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    
    /* Custom Streamlit Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# Audio Chime JavaScript (Debounced WebAudio)
AUDIO_ALERT_JS = """
<script>
function playAlertBeep() {
    try {
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var osc = context.createOscillator();
        var gain = context.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, context.currentTime);
        gain.gain.setValueAtTime(0.15, context.currentTime);
        osc.connect(gain);
        gain.connect(context.destination);
        osc.start();
        osc.stop(context.currentTime + 0.35);
    } catch(e) {}
}
playAlertBeep();
</script>
"""

# ── Sidebar Configuration ─────────────────────────────────────────────────────
st.sidebar.markdown("### ⚙️ Control & Configuration")

with st.sidebar.container(border=True):
    st.markdown("**📹 Video Input Feed**")
    video_dir = "data/sample_videos"
    available_videos = sorted(glob.glob(f"{video_dir}/*.mp4"))
    video_names = [os.path.basename(v) for v in available_videos]
    
    selected_video_name = st.selectbox(
        "Select Feed:",
        video_names,
        index=video_names.index("warehouse1.mp4") if "warehouse1.mp4" in video_names else 0,
        label_visibility="collapsed"
    )
    selected_video_path = os.path.join(video_dir, selected_video_name)

    is_construction = "construction" in selected_video_name.lower()
    zone_config_path = st.selectbox(
        "Zone Layout:",
        ["config/zones_warehouse.json", "config/zones_construction.json"],
        index=1 if is_construction else 0
    )

with st.sidebar.container(border=True):
    st.markdown("**🧠 AI Vision Engine**")
    model_options = []
    if os.path.exists("models/best_3.pt"):
        model_options.append("models/best_3.pt (YOLOv11 - Latest Trained 16-Classes)")
    if os.path.exists("models/best.pt"):
        model_options.append("models/best.pt (YOLOv11 - Trained 16-Classes)")
    for extra_pt in glob.glob("models/*.pt"):
        norm_p = extra_pt.replace("\\", "/")
        if norm_p not in ["models/best_3.pt", "models/best.pt"]:
            model_options.append(f"{norm_p} (Custom Model)")
    if os.path.exists("yolov8n.pt"):
        model_options.append("yolov8n.pt (Baseline COCO)")

    selected_model_str = st.selectbox("Detection Model:", model_options, index=0)
    model_path = selected_model_str.split(" ")[0]

    conf_threshold = st.slider("Confidence Threshold:", 0.15, 0.80, 0.25, 0.05)
    enable_audio = st.checkbox("🔊 Real-Time Audio Chime", value=True)

start_analysis = st.sidebar.button("▶️ Run Vision Pipeline", type="primary", use_container_width=True)

# Sidebar Database Stats
st.sidebar.markdown("---")
with st.sidebar.container(border=True):
    st.markdown("**📊 Central Violation Store**")
    db_stats = get_all_violations_count()
    sb1, sb2 = st.columns(2)
    sb1.metric("Active", db_stats["active"])
    sb2.metric("Resolved", db_stats["resolved"])
    st.caption(f"Total Audit Records: **{db_stats['total']}**")

# ── Executive Top Header & KPI Bar ───────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div>
        <h2 style="margin: 0; padding: 0; color: white;">🏭 SiteSense Operations Intelligence</h2>
        <span style="font-size: 0.85rem; color: #94a3b8;">
            Multimodal Spatial Intelligence & Violation Lifecycle Management • Member 2
        </span>
    </div>
    <div style="text-align: right;">
        <span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">
            ● VISION ENGINE ACTIVE
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Top KPI Stat Cards
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    with st.container(border=True):
        st.markdown("<small style='color: #64748b; font-weight: 600;'>CURRENT FEED</small>", unsafe_allow_html=True)
        top_kpi_feed = st.empty()
        top_kpi_feed.markdown(f"**`{selected_video_name}`**")

with kpi_col2:
    with st.container(border=True):
        st.markdown("<small style='color: #64748b; font-weight: 600;'>ACTIVE TRACKS</small>", unsafe_allow_html=True)
        top_kpi_tracks = st.empty()
        top_kpi_tracks.markdown("### 0")

with kpi_col3:
    with st.container(border=True):
        st.markdown("<small style='color: #64748b; font-weight: 600;'>ACTIVE SPATIAL ALERTS</small>", unsafe_allow_html=True)
        top_kpi_alerts = st.empty()
        top_kpi_alerts.markdown("<h3 style='color: #10b981;'>0</h3>", unsafe_allow_html=True)

with kpi_col4:
    with st.container(border=True):
        st.markdown("<small style='color: #64748b; font-weight: 600;'>PEDESTRIAN DOOR FLOW</small>", unsafe_allow_html=True)
        top_kpi_flow = st.empty()
        top_kpi_flow.markdown("### IN: 0 | OUT: 0")

# ── Session State Persistence ────────────────────────────────────────────────
if "last_results" not in st.session_state:
    st.session_state["last_results"] = None

# ── Main Tabbed Navigation ────────────────────────────────────────────────────
tab_live, tab_evidence, tab_analytics, tab_lifecycle, tab_trends, tab_zone_editor = st.tabs([
    "🎥 Live Vision Ops",
    "📸 Captured Evidence Gallery",
    "📈 Heatmap & Audit Report",
    "🚨 Violation Lifecycle Desk",
    "📊 Weekly Compliance Trends",
    "📐 Visual Zone Configuration Editor (Admin Screen 12)"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: LIVE VISION OPS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_live:
    col_stream, col_telemetry = st.columns([2.3, 1.1])

    with col_stream:
        with st.container(border=True):
            st.markdown(f"**Live Feed Monitor**: `{selected_video_name}`")
            video_placeholder = st.empty()
            # Placeholder for initial load
            if st.session_state["last_results"] is None:
                video_placeholder.info("Click '▶️ Run Vision Pipeline' from the sidebar to start live processing.")

    with col_telemetry:
        with st.container(border=True):
            st.markdown("**🚨 Real-Time Spatial Alert Stream**")
            alerts_container = st.empty()
            alerts_container.success("✅ All monitored zones clear.")
            audio_placeholder = st.empty()

        with st.container(border=True):
            st.markdown("**📐 Active Zone Configuration**")
            st.markdown(f"- **Config**: `{os.path.basename(zone_config_path)}`")
            st.markdown(f"- **Model**: `{os.path.basename(model_path)}`")
            st.markdown(f"- **Confidence**: `{conf_threshold}`")

    # Lower section: Live Incident Log
    with st.container(border=True):
        st.markdown("**📜 Incident Log Stream**")
        log_table = st.empty()
        log_table.caption("No active incidents logged yet.")

# ── Execution Loop (Triggered by Sidebar Button) ───────────────────────────────
if start_analysis:
    cap = cv2.VideoCapture(selected_video_path)
    if not cap.isOpened():
        st.error(f"Cannot open video feed: {selected_video_path}")
    else:
        fps          = cap.get(cv2.CAP_PROP_FPS) or 24.0
        width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        tracker     = ByteTrackEngine(model_weights=model_path)
        tracker.model.overrides["conf"] = conf_threshold
        zone_engine = ZoneEngine(zone_config_path)
        heatmap_gen = HeatmapGenerator(width=width, height=height)

        frame_idx            = 0
        emitted_events       = []
        captured_evidence_files = []
        first_frame          = None
        last_audio_played_ts = -10.0
        last_saved_track_frame = {}
        inserted_violation_ids = {}

        progress_bar = st.progress(0, text="Processing video frames...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if first_frame is None:
                first_frame = frame.copy()

            timestamp = frame_idx / fps

            # 1. ByteTrack
            tracked_objects = tracker.process_frame(frame)

            # 2. Cumulative Heatmap update
            heatmap_gen.update(tracked_objects)

            # 3. Zone & Dwell Evaluation
            violations, crossings = zone_engine.evaluate_tracks(tracked_objects, timestamp)

            active_zone_ids = set()
            for viol in violations:
                active_zone_ids.add(viol["zone_id"])
                event = SpatialEventFormatter.format_event(
                    viol,
                    site_id="SITE_DEMO",
                    camera_id=zone_engine.config.get("camera_id", "CAM_01")
                )
                emitted_events.append(event)

            # 4. Annotations Drawing
            annotated_frame = frame.copy()
            annotated_frame = VisualAnnotator.draw_zones(annotated_frame, zone_engine.zones, active_zone_ids)
            annotated_frame = VisualAnnotator.draw_counting_lines(annotated_frame, zone_engine.counting_lines)
            annotated_frame = VisualAnnotator.draw_tracked_objects(annotated_frame, tracked_objects, violations)
            annotated_frame = VisualAnnotator.draw_hud(
                annotated_frame, frame_idx, timestamp, violations,
                len(tracked_objects), zone_engine.counting_lines
            )

            # 5. Evidence Capture & Auto-DB Persistence
            for viol in violations:
                if viol["severity"] in ["HIGH", "CRITICAL"]:
                    track_key = (viol["zone_id"], viol["track_id"])
                    last_saved = last_saved_track_frame.get(track_key, -999)

                    ev_path = None
                    if frame_idx - last_saved >= 20:
                        ev_path = os.path.abspath(
                            f"outputs/evidence_frames/{viol['zone_id']}_{viol['track_id']}_{frame_idx}.jpg"
                        )
                        cv2.imwrite(ev_path, annotated_frame)
                        captured_evidence_files.append(ev_path)
                        last_saved_track_frame[track_key] = frame_idx

                    # Persist to SQLite
                    if track_key not in inserted_violation_ids:
                        event_for_db = SpatialEventFormatter.format_event(
                            viol,
                            site_id="SITE_DEMO",
                            camera_id=zone_engine.config.get("camera_id", "CAM_01")
                        )
                        db_id = insert_violation(
                            event_for_db,
                            evidence_path=ev_path,
                            video_name=selected_video_name
                        )
                        inserted_violation_ids[track_key] = db_id

                    # Audio Alert Chime (Debounced 3s)
                    if enable_audio and (timestamp - last_audio_played_ts > 3.0):
                        with audio_placeholder:
                            st.components.v1.html(AUDIO_ALERT_JS, height=0)
                        last_audio_played_ts = timestamp

            # Render Live Video Frame
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, use_container_width=True)

            # Update KPI Header Cards
            top_kpi_tracks.markdown(f"### {len(tracked_objects)}")
            if violations:
                top_kpi_alerts.markdown(f"<h3 style='color: #ef4444;'>{len(violations)} ALERTS</h3>", unsafe_allow_html=True)
            else:
                top_kpi_alerts.markdown("<h3 style='color: #10b981;'>0</h3>", unsafe_allow_html=True)

            flow_str = "IN: 0 | OUT: 0"
            flow_stats = {"entries": 0, "exits": 0}
            if zone_engine.counting_lines:
                for cl in zone_engine.counting_lines.values():
                    flow_stats["entries"] += cl.entries
                    flow_stats["exits"]   += cl.exits
                flow_str = f"IN: {flow_stats['entries']} | OUT: {flow_stats['exits']}"
            top_kpi_flow.markdown(f"### {flow_str}")

            # Telemetry Alert Panel
            if violations:
                alert_html = ""
                for v in violations[:3]:
                    c_name = VisualAnnotator.CLASS_NAMES.get(v["class_id"], "object")
                    badge = "badge-critical" if v["severity"] == "CRITICAL" else "badge-high"
                    alert_html += f"""
                    <div style='background: white; border-left: 4px solid #ef4444; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
                        <span class='{badge}'>{v['severity']}</span>
                        <strong style='margin-left: 6px;'>{v['zone_name']}</strong><br/>
                        <small style='color: #475569;'><b>{c_name.capitalize()}</b> blocking zone for <b>{v['dwell_time_seconds']}s</b></small>
                    </div>
                    """
                alerts_container.markdown(alert_html, unsafe_allow_html=True)
            else:
                alerts_container.success("✅ All monitored zones clear.")

            progress_bar.progress(min(1.0, frame_idx / max(1, total_frames)))
            frame_idx += 1

        cap.release()
        progress_bar.progress(1.0, text="Analysis Complete!")
        st.toast("🎉 Video Analysis Completed! Violations logged to database.", icon="✅")

        st.session_state["last_results"] = {
            "selected_video_name": selected_video_name,
            "frame_idx":           frame_idx,
            "emitted_events":      emitted_events,
            "flow_stats":          flow_stats,
            "captured_evidence_files": captured_evidence_files,
            "first_frame":         first_frame,
            "heatmap_matrix":      heatmap_gen.heatmap
        }

# ── Render Persistent Results for Tab 1 ───────────────────────────────────────
if st.session_state["last_results"] is not None:
    res = st.session_state["last_results"]

    if res["emitted_events"]:
        unique_events = []
        seen = set()
        for e in res["emitted_events"]:
            sig = (e["event_type"], e["target"]["track_id"], e["zone_name"])
            if sig not in seen:
                seen.add(sig)
                unique_events.append({
                    "Event ID":           e["event_id"],
                    "Severity":           e["severity"],
                    "Violation Type":     e["event_type"],
                    "Monitored Zone":     e["zone_name"],
                    "Object & Track ID":  f"{e['target']['class_name']} (ID {e['target']['track_id']})",
                    "Dwell Time":         f"{e['temporal']['dwell_time_seconds']}s",
                    "Recommended Action": e["recommended_action"]
                })
        log_table.dataframe(pd.DataFrame(unique_events), use_container_width=True)
    else:
        log_table.info("No spatial incidents detected during the playback.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: CAPTURED EVIDENCE GALLERY (Clean Responsive Grid)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_evidence:
    st.markdown("### 📸 Forensic Evidence Gallery")
    st.caption("Annotated snapshots captured whenever an obstacle or hazard exceeded the dwell threshold.")

    if st.session_state["last_results"] is not None:
        ev_files = [p for p in st.session_state["last_results"]["captured_evidence_files"] if os.path.exists(p)]
        
        if ev_files:
            # Display neatly in a 2-column or 3-column grid
            cols_per_row = 3
            for i in range(0, len(ev_files), cols_per_row):
                row_cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(ev_files):
                        file_p = ev_files[idx]
                        bname = os.path.basename(file_p)
                        with row_cols[j]:
                            with st.container(border=True):
                                st.image(file_p, use_container_width=True)
                                st.markdown(f"**Evidence #{idx+1}**: `{bname}`")
                                st.caption("Captured with Bounding Box, Zone Polygon & Dwell HUD overlay.")
        else:
            st.info("No critical incident evidence frames were captured in the last run.")
    else:
        st.info("Run a video analysis from the sidebar to populate evidence frames.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: HEATMAP & OFFICIAL AUDIT REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    st.markdown("### 📈 Post-Shift Operations Intelligence")
    st.caption("Long-term spatial traffic density heatmap and automated executive compliance report.")

    if st.session_state["last_results"] is not None:
        res = st.session_state["last_results"]
        ev_files = [p for p in res["captured_evidence_files"] if os.path.exists(p)]

        col_heat, col_rep = st.columns([1.3, 1.0])

        with col_heat:
            with st.container(border=True):
                st.markdown("**🔥 Cumulative Movement & Congestion Heatmap**")
                if res["first_frame"] is not None:
                    hgen = HeatmapGenerator(
                        width=res["first_frame"].shape[1],
                        height=res["first_frame"].shape[0]
                    )
                    hgen.heatmap = res["heatmap_matrix"]
                    heatmap_img  = hgen.generate(background_frame=res["first_frame"])
                    heatmap_rgb  = cv2.cvtColor(heatmap_img, cv2.COLOR_BGR2RGB)
                    st.image(heatmap_rgb, caption="High-intensity red zones indicate frequent dwell and bottlenecks.", use_container_width=True)

        with col_rep:
            with st.container(border=True):
                st.markdown("**📄 Official Compliance Audit Report**")
                st.markdown("""
                Automatically synthesizes:
                - Shift Operations KPI Summary
                - Spatial Incident Log with Exact Timestamps
                - Embedded High-Resolution Annotated Evidence Snapshots
                """)

                report_pdf_path = f"outputs/SiteSense_Inspection_Report_{Path(res['selected_video_name']).stem}.pdf"
                generate_pdf_report(
                    site_id="SITE_DEMO_01",
                    video_name=res["selected_video_name"],
                    total_frames=res["frame_idx"],
                    events=res["emitted_events"],
                    flow_stats=res["flow_stats"],
                    evidence_images=ev_files,
                    output_pdf_path=report_pdf_path
                )

                with open(report_pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()

                st.download_button(
                    label="📥 Download Official Signed PDF Report",
                    data=pdf_bytes,
                    file_name=os.path.basename(report_pdf_path),
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                st.caption(f"File: `{os.path.basename(report_pdf_path)}` ({len(pdf_bytes)//1024} KB)")
    else:
        st.info("Run a video analysis from the sidebar to generate the heatmap and audit report.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: VIOLATION LIFECYCLE & RESOLUTION DESK
# ═══════════════════════════════════════════════════════════════════════════════
with tab_lifecycle:
    st.markdown("### 🚨 Violation Lifecycle & Supervisor Resolution Desk")
    st.caption("Audit trail from detection to physical resolution with verifiable proof photos.")

    desk_view = st.radio("Select View:", ["🔴 Active Violations (Action Required)", "✅ Resolved Violations (Audit Records)"], horizontal=True)

    if "Active" in desk_view:
        active_rows = get_active_violations()

        if not active_rows:
            st.success("🎉 All clear! There are currently no active unresolved violations.")
        else:
            st.warning(f"**{len(active_rows)} Active Violation(s) requiring immediate resolution:**")

            for r in active_rows:
                with st.container(border=True):
                    c_img, c_detail, c_form = st.columns([1.1, 1.2, 1.5])

                    with c_img:
                        ev_path = r.get("evidence_frame_path", "")
                        if ev_path and os.path.exists(ev_path):
                            st.image(ev_path, caption=f"Evidence: Track #{r['track_id']}", use_container_width=True)
                        else:
                            st.caption("No image captured.")

                    with c_detail:
                        badge = "badge-critical" if r["severity"] == "CRITICAL" else "badge-high"
                        st.markdown(f"<span class='{badge}'>{r['severity']}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Zone:** {r['zone_name']}")
                        st.markdown(f"**Object:** `{r['class_name']}` (Track #{r['track_id']})")
                        st.markdown(f"**Dwell:** `{r['dwell_time']:.1f}s`")
                        st.markdown(f"**Source Video:** `{r['video_name']}`")
                        st.caption(f"Detected: {r['created_at'][:19].replace('T', ' ')} UTC")

                    with c_form:
                        st.markdown("**✅ Mark as Resolved**")
                        r_by = st.text_input("Supervisor ID / Name:", value="site_supervisor", key=f"rby_{r['id']}")
                        r_note = st.text_input("Resolution Note:", placeholder="e.g. Pallet removed from exit pathway", key=f"rnt_{r['id']}")
                        proof_pic = st.file_uploader("Upload Clear Area Proof:", type=["jpg", "png", "jpeg"], key=f"up_{r['id']}")

                        if st.button("Confirm Resolution & Discard Alert", key=f"res_btn_{r['id']}", type="primary"):
                            photo_save_path = None
                            if proof_pic is not None:
                                os.makedirs("outputs/resolution_proofs", exist_ok=True)
                                photo_save_path = os.path.abspath(f"outputs/resolution_proofs/RESOLVED_{r['id'][:8]}_{proof_pic.name}")
                                with open(photo_save_path, "wb") as f_out:
                                    f_out.write(proof_pic.getbuffer())

                            ok = resolve_violation(
                                violation_id=r["id"],
                                resolved_by=r_by,
                                resolution_photo_path=photo_save_path,
                                resolution_note=r_note
                            )
                            if ok:
                                st.toast(f"Violation {r['id'][:8]} resolved successfully!", icon="✅")
                                st.rerun()

    else:
        resolved_rows = get_resolved_violations()

        if not resolved_rows:
            st.info("No resolved violations found yet.")
        else:
            st.success(f"**{len(resolved_rows)} Resolved Audit Record(s) Archived:**")

            for r in resolved_rows:
                with st.container(border=True):
                    st.markdown(f"<span class='badge-resolved'>RESOLVED</span> **{r['zone_name']}** — Object: `{r['class_name']}`", unsafe_allow_html=True)
                    
                    c_before, c_after, c_meta = st.columns([1.2, 1.2, 1.0])

                    with c_before:
                        st.markdown("**1. Violation Evidence (Before)**")
                        ev_path = r.get("evidence_frame_path", "")
                        if ev_path and os.path.exists(ev_path):
                            st.image(ev_path, use_container_width=True)
                        else:
                            st.caption("No violation image available.")

                    with c_after:
                        st.markdown("**2. Proof of Resolution (After)**")
                        proof_path = r.get("resolution_photo_path", "")
                        if proof_path and os.path.exists(proof_path):
                            st.image(proof_path, use_container_width=True)
                        else:
                            st.caption("No resolution proof photo uploaded.")

                    with c_meta:
                        st.markdown("**Audit Details**")
                        st.markdown(f"- **Resolved By**: `{r.get('resolved_by', 'N/A')}`")
                        st.markdown(f"- **Note**: {r.get('resolution_note', '—')}")
                        st.markdown(f"- **Week**: Week {r.get('week_number')}")
                        st.caption(f"Resolved: {str(r.get('resolved_at', ''))[:19].replace('T', ' ')} UTC")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: WEEKLY COMPLIANCE TRENDS & AGENT QUERY PANEL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_trends:
    st.markdown("### 📊 Weekly Compliance Trends & Agent Query Panel")
    st.caption("Longitudinal tracking of site compliance, resolution speed, and GenAI query interface.")

    weekly_data = get_weekly_summary()

    if weekly_data:
        df_week = pd.DataFrame(weekly_data)
        df_week.columns = ["Week Number", "Total Violations", "Active (Unresolved)", "Resolved"]

        m1, m2, m3, m4 = st.columns(4)
        tot_all = df_week["Total Violations"].sum()
        tot_act = df_week["Active (Unresolved)"].sum()
        tot_res = df_week["Resolved"].sum()
        res_rate = (tot_res / tot_all * 100) if tot_all > 0 else 0.0

        m1.metric("Total Incidents", int(tot_all))
        m2.metric("Active (Open)", int(tot_act))
        m3.metric("Resolved (Closed)", int(tot_res))
        m4.metric("Resolution Velocity", f"{res_rate:.1f}%")

        col_chart, col_tbl = st.columns([1.5, 1.0])
        with col_chart:
            with st.container(border=True):
                st.markdown("**Active vs Resolved Incidents by Week**")
                chart_df = df_week.set_index("Week Number")[["Active (Unresolved)", "Resolved"]]
                st.bar_chart(chart_df)

        with col_tbl:
            with st.container(border=True):
                st.markdown("**Weekly Data Summary**")
                st.dataframe(df_week, use_container_width=True)

        st.markdown("---")
        with st.container(border=True):
            st.markdown("**🔍 GenAI Agent Query Simulator**")
            st.caption("Simulate queries made by Member 4's LangChain / CrewAI agents via `/vision/violations/*` API.")
            
            q_mode = st.radio("Query:", ["Show Active Violations", "Show Resolved Violations"], horizontal=True)
            if q_mode == "Show Active Violations":
                q_rows = get_active_violations()
                st.write(f"Query returned **{len(q_rows)}** active record(s):")
                st.json(q_rows[:3])
            else:
                q_rows = get_resolved_violations()
                st.write(f"Query returned **{len(q_rows)}** resolved record(s):")
                st.json(q_rows[:3])

    else:
        st.info("No compliance data in database yet. Run a video analysis to initialize weekly metrics.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: VISUAL ZONE CONFIGURATION EDITOR (ADMIN SCREEN 12 - M6.9)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_zone_editor:
    st.markdown("### 📐 Visual Zone Configuration Editor (Admin Screen 12)")
    st.caption(
        "Interactive Spatial Polygon & Virtual Tripwire Designer. Define restricted perimeters, "
        "assign prohibited object classes, and configure dwell time thresholds directly over camera frames. "
        "Dynamic updates are validated and hot-reloaded with zero server downtime."
    )

    # Zone Editor State Initialization
    if "editor_points" not in st.session_state:
        st.session_state["editor_points"] = [[480, 340], [920, 340], [920, 700], [480, 700]]
    if "active_zone_key" not in st.session_state:
        st.session_state["active_zone_key"] = "emergency_exit"

    col_setup, col_preview = st.columns([1.15, 1.35])

    # ── Left Column: Controls & Configuration ────────────────────────────────
    with col_setup:
        with st.container(border=True):
            st.markdown("**1️⃣ Reference Camera Frame Selection**")
            frame_source = st.radio(
                "Source:",
                ["Extract from Sample Video", "Upload Camera Snapshot"],
                horizontal=True,
                label_visibility="collapsed"
            )

            ref_frame = None
            frame_w, frame_h = 1280, 720

            if frame_source == "Extract from Sample Video":
                editor_video_name = st.selectbox("Select Video Feed:", video_names, index=0, key="ed_vid_select")
                ed_vid_path = os.path.join(video_dir, editor_video_name)
                
                # Extract first frame or scrubbed frame
                cap_ref = cv2.VideoCapture(ed_vid_path)
                total_f = int(cap_ref.get(cv2.CAP_PROP_FRAME_COUNT) or 100)
                frame_scrub = st.slider("Scrub Video Frame:", 0, max(0, total_f - 1), 0, step=10, key="ed_frame_scrub")
                
                cap_ref.set(cv2.CAP_PROP_POS_FRAMES, frame_scrub)
                ret_f, extracted_f = cap_ref.read()
                cap_ref.release()

                if ret_f and extracted_f is not None:
                    ref_frame = extracted_f
                    frame_h, frame_w = ref_frame.shape[:2]
                else:
                    st.error("Failed to read video frame.")
            else:
                uploaded_snap = st.file_uploader("Upload Frame (.jpg / .png):", type=["jpg", "jpeg", "png"], key="ed_snap_upload")
                if uploaded_snap is not None:
                    file_bytes = np.asarray(bytearray(uploaded_snap.read()), dtype=np.uint8)
                    ref_frame = cv2.imdecode(file_bytes, 1)
                    if ref_frame is not None:
                        frame_h, frame_w = ref_frame.shape[:2]
                else:
                    # Fallback to default frame
                    def_path = os.path.join(video_dir, video_names[0]) if video_names else None
                    if def_path and os.path.exists(def_path):
                        c = cv2.VideoCapture(def_path)
                        _, ref_frame = c.read()
                        c.release()
                        if ref_frame is not None:
                            frame_h, frame_w = ref_frame.shape[:2]

            st.caption(f"Camera Frame Resolution: **{frame_w} × {frame_h} px**")

        # Configuration Target & Base Template
        with st.container(border=True):
            st.markdown("**2️⃣ Target Facility & Base Template**")
            col_site, col_templ = st.columns(2)
            with col_site:
                site_id_input = st.text_input("Site ID:", value="warehouse", help="Config will be saved as config/zones_{site_id}.json").strip().lower()
            with col_templ:
                avail_templates = sorted(glob.glob("config/zones_*.json") + glob.glob("config/camera_*.json"))
                chosen_template = st.selectbox("Load Base Template:", ["-- New Custom Zone --"] + avail_templates)

            if chosen_template != "-- New Custom Zone --" and st.button("📥 Load Template Zones", use_container_width=True):
                try:
                    with open(chosen_template, "r") as tf:
                        loaded_data = json.load(tf)
                        t_zones = loaded_data.get("zones", {})
                        if t_zones:
                            first_k = list(t_zones.keys())[0]
                            st.session_state["editor_points"] = t_zones[first_k].get("coordinates", [])
                            st.session_state["active_zone_key"] = first_k
                            st.success(f"Loaded {len(t_zones)} zones from {chosen_template}!")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error loading template: {e}")

        # Zone Properties Configuration
        with st.container(border=True):
            st.markdown("**3️⃣ Zone Parameters & Alert Rules**")
            z_col1, z_col2 = st.columns(2)
            with z_col1:
                zone_key_in = st.text_input("Zone Config Key:", value=st.session_state["active_zone_key"]).strip()
                zone_id_in = st.text_input("Zone Unique ID:", value=f"ZONE_{zone_key_in.upper()}").strip()
                zone_type_in = st.selectbox("Zone Category:", list(VALID_ZONE_TYPES), index=0)
            with z_col2:
                zone_name_in = st.text_input("Zone Display Name:", value=zone_key_in.replace("_", " ").title()).strip()
                alert_sev_in = st.selectbox("Alert Severity:", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], index=0)
                dwell_thresh_in = st.slider("Blockage / Dwell Time Threshold (s):", 0.0, 20.0, 3.0, 0.5)

            # Prohibited classes multi-select
            all_class_names = [CANONICAL_CLASSES[i] for i in sorted(CANONICAL_CLASSES.keys())]
            def_classes = ["pallet", "forklift", "obstacle"] if "exit" in zone_key_in.lower() else ["forklift", "spill"]
            prohibited_selected = st.multiselect(
                "Prohibited Classes (Trigger Violation on Entry/Blockage):",
                all_class_names,
                default=[c for c in def_classes if c in all_class_names]
            )
            prohibited_ids = [k for k, v in CANONICAL_CLASSES.items() if v in prohibited_selected]

            zone_desc_in = st.text_input(
                "Compliance Rule / Policy SOP Note:",
                value="Evacuation and transit route must remain 100% unobstructed at all times."
            )

        # Polygon Points & Presets
        with st.container(border=True):
            st.markdown("**4️⃣ Polygon Coordinates & Presets**")
            
            # Quick preset buttons
            st.markdown("Quick Geometry Presets:")
            pr_c1, pr_c2, pr_c3, pr_c4 = st.columns(4)
            if pr_c1.button("🚪 Center Door", use_container_width=True):
                st.session_state["editor_points"] = [
                    [int(frame_w * 0.38), int(frame_h * 0.45)],
                    [int(frame_w * 0.72), int(frame_h * 0.45)],
                    [int(frame_w * 0.72), int(frame_h * 0.95)],
                    [int(frame_w * 0.38), int(frame_h * 0.95)]
                ]
                st.rerun()
            if pr_c2.button("🚶 Left Aisle", use_container_width=True):
                st.session_state["editor_points"] = [
                    [int(frame_w * 0.15), int(frame_h * 0.40)],
                    [int(frame_w * 0.38), int(frame_h * 0.40)],
                    [int(frame_w * 0.38), int(frame_h * 0.95)],
                    [int(frame_w * 0.15), int(frame_h * 0.95)]
                ]
                st.rerun()
            if pr_c3.button("🧯 Fire Ext. Bay", use_container_width=True):
                st.session_state["editor_points"] = [
                    [int(frame_w * 0.74), int(frame_h * 0.35)],
                    [int(frame_w * 0.95), int(frame_h * 0.35)],
                    [int(frame_w * 0.95), int(frame_h * 0.70)],
                    [int(frame_w * 0.74), int(frame_h * 0.70)]
                ]
                st.rerun()
            if pr_c4.button("📦 Dock Perimeter", use_container_width=True):
                st.session_state["editor_points"] = [
                    [int(frame_w * 0.20), int(frame_h * 0.25)],
                    [int(frame_w * 0.85), int(frame_h * 0.25)],
                    [int(frame_w * 0.85), int(frame_h * 0.80)],
                    [int(frame_w * 0.20), int(frame_h * 0.80)]
                ]
                st.rerun()

            # Point adjustment controls
            col_add_x, col_add_y, col_add_btn = st.columns([1.2, 1.2, 1.0])
            with col_add_x:
                add_px = st.number_input("Point X:", min_value=0, max_value=frame_w, value=int(frame_w / 2), step=20)
            with col_add_y:
                add_py = st.number_input("Point Y:", min_value=0, max_value=frame_h, value=int(frame_h / 2), step=20)
            with col_add_btn:
                st.write("")
                st.write("")
                if st.button("➕ Add Vertex", use_container_width=True):
                    st.session_state["editor_points"].append([int(add_px), int(add_py)])
                    st.rerun()

            # Manual JSON coordinate editor
            pts_str = json.dumps(st.session_state["editor_points"])
            edited_pts_str = st.text_area(
                "Polygon Coordinates [[x1,y1], [x2,y2], ...]:",
                value=pts_str,
                height=80,
                help="Enter valid JSON list of coordinate pairs."
            )
            try:
                parsed_pts = json.loads(edited_pts_str)
                if isinstance(parsed_pts, list) and all(isinstance(p, list) and len(p) == 2 for p in parsed_pts):
                    st.session_state["editor_points"] = parsed_pts
            except Exception:
                pass

            col_pt_undo, col_pt_clr = st.columns(2)
            if col_pt_undo.button("↩️ Undo Last Vertex", use_container_width=True):
                if st.session_state["editor_points"]:
                    st.session_state["editor_points"].pop()
                    st.rerun()
            if col_pt_clr.button("🗑️ Clear Vertices", use_container_width=True):
                st.session_state["editor_points"] = []
                st.rerun()

        # Virtual Counting Line Section
        with st.expander("Virtual Directional Tripwire / Counting Line (Optional)", expanded=False):
            enable_line = st.checkbox("Include Counting Line in Config", value=True)
            line_id_in = st.text_input("Line ID:", value="LINE_MAIN_FLOW")
            line_name_in = st.text_input("Line Name:", value="Main Entrance Flow")
            lc_col1, lc_col2 = st.columns(2)
            with lc_col1:
                lx1 = st.number_input("Line Start X:", 0, frame_w, int(frame_w * 0.45), step=20)
                ly1 = st.number_input("Line Start Y:", 0, frame_h, int(frame_h * 0.50), step=20)
            with lc_col2:
                lx2 = st.number_input("Line End X:", 0, frame_w, int(frame_w * 0.70), step=20)
                ly2 = st.number_input("Line End Y:", 0, frame_h, int(frame_h * 0.85), step=20)

        # Save Button & Action
        st.markdown("---")
        if st.button("💾 Validate & Save Zone Configuration", type="primary", use_container_width=True):
            # Construct complete payload
            candidate_payload = {
                "camera_id": f"CAM_{site_id_input.upper()}_01",
                "site_id": f"SITE_{site_id_input.upper()}",
                "site_name": f"{site_id_input.title()} Facility Operations",
                "site_type": "warehouse" if "warehouse" in site_id_input else "construction",
                "resolution": [frame_w, frame_h],
                "zones": {
                    zone_key_in: {
                        "zone_id": zone_id_in,
                        "zone_name": zone_name_in,
                        "zone_type": zone_type_in,
                        "alert_severity": alert_sev_in,
                        "coordinates": st.session_state["editor_points"],
                        "prohibited_classes": prohibited_ids,
                        "blockage_threshold_seconds": float(dwell_thresh_in),
                        "description": zone_desc_in
                    }
                },
                "counting_lines": {}
            }

            if enable_line:
                candidate_payload["counting_lines"][line_id_in.lower()] = {
                    "line_id": line_id_in,
                    "name": line_name_in,
                    "coordinates": [[int(lx1), int(ly1)], [int(lx2), int(ly2)]],
                    "count_classes": [0],
                    "description": "Virtual pedestrian and equipment counter"
                }

            # Strictly validate with ZoneConfigValidator
            is_valid, validation_errors, validated_config = ZoneConfigValidator.validate(candidate_payload)

            if not is_valid:
                st.error("❌ Zone Configuration Validation Failed:")
                for err in validation_errors:
                    st.markdown(f"- ⚠️ {err}")
            else:
                os.makedirs("config", exist_ok=True)
                save_target = f"config/zones_{site_id_input}.json"
                with open(save_target, "w") as f_save:
                    json.dump(validated_config, f_save, indent=2)

                # Hot-reload in memory if ZoneEngine instance exists
                try:
                    active_zone_engine = ZoneEngine(save_target)
                    st.session_state["zone_engine_instance"] = active_zone_engine
                except Exception:
                    pass

                st.success(f"✅ Configuration successfully validated and saved to `{save_target}`!")
                st.balloons()

    # ── Right Column: Live Visual Canvas & Real-Time Rendering ───────────────
    with col_preview:
        with st.container(border=True):
            st.markdown("**🖥️ Live Visual Polygon Overlay & Geometry Inspector**")

            if ref_frame is not None:
                vis_canvas = ref_frame.copy()
                curr_pts = st.session_state["editor_points"]

                # Severity Color Mapping (BGR)
                sev_bgr = {
                    "CRITICAL": (0, 0, 230),     # Bright Red
                    "HIGH":     (0, 140, 255),   # Vivid Orange
                    "MEDIUM":   (0, 215, 255),   # Safety Yellow
                    "LOW":      (255, 128, 0),   # Cyan / Blue
                    "INFO":     (200, 200, 0)
                }.get(alert_sev_in, (0, 0, 255))

                # Draw polygon if >= 3 points
                if len(curr_pts) >= 3:
                    pts_arr = np.array(curr_pts, dtype=np.int32)
                    
                    # Semi-transparent polygon fill
                    overlay = vis_canvas.copy()
                    cv2.fillPoly(overlay, [pts_arr], sev_bgr)
                    cv2.addWeighted(overlay, 0.35, vis_canvas, 0.65, 0, vis_canvas)

                    # Boundary line
                    cv2.polylines(vis_canvas, [pts_arr], isClosed=True, color=sev_bgr, thickness=3, lineType=cv2.LINE_AA)

                    # Compute Centroid for Zone Label
                    M = cv2.moments(pts_arr)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = curr_pts[0]

                    # Zone Badge Overlay
                    badge_text = f"{zone_name_in} [{alert_sev_in} | >{dwell_thresh_in:.1f}s]"
                    (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                    cv2.rectangle(vis_canvas, (cx - int(tw/2) - 6, cy - th - 8), (cx + int(tw/2) + 6, cy + 8), (20, 20, 25), -1)
                    cv2.rectangle(vis_canvas, (cx - int(tw/2) - 6, cy - th - 8), (cx + int(tw/2) + 6, cy + 8), sev_bgr, 2)
                    cv2.putText(vis_canvas, badge_text, (cx - int(tw/2), cy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

                # Draw vertex points and order markers
                for idx, pt in enumerate(curr_pts):
                    cv2.circle(vis_canvas, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(vis_canvas, (int(pt[0]), int(pt[1])), 6, sev_bgr, -1, cv2.LINE_AA)
                    cv2.putText(
                        vis_canvas, f"{idx+1}", (int(pt[0]) + 10, int(pt[1]) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA
                    )

                # Draw connecting lines if 1 or 2 points
                if len(curr_pts) == 2:
                    cv2.line(vis_canvas, tuple(curr_pts[0]), tuple(curr_pts[1]), sev_bgr, 2, cv2.LINE_AA)

                # Draw virtual counting line if enabled
                if 'enable_line' in locals() and enable_line:
                    p1 = (int(lx1), int(ly1))
                    p2 = (int(lx2), int(ly2))
                    cv2.line(vis_canvas, p1, p2, (0, 255, 0), 3, cv2.LINE_AA)
                    # Direction indicator
                    mid_x = int((p1[0] + p2[0]) / 2)
                    mid_y = int((p1[1] + p2[1]) / 2)
                    cv2.arrowedLine(vis_canvas, (mid_x - 15, mid_y - 20), (mid_x + 15, mid_y + 20), (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(vis_canvas, f"{line_name_in} (COUNTING)", (p1[0], p1[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

                # Convert BGR to RGB for Streamlit rendering
                vis_rgb = cv2.cvtColor(vis_canvas, cv2.COLOR_BGR2RGB)
                st.image(vis_rgb, use_container_width=True)

                # Geometric Status Indicator
                pts_count = len(curr_pts)
                if pts_count >= 3:
                    try:
                        poly_geom = Polygon(curr_pts)
                        if poly_geom.is_valid and poly_geom.area > 0:
                            st.success(f"✅ **Valid Spatial Polygon**: {pts_count} vertices | Enclosed Area: **{poly_geom.area:,.0f} px²** | Severity: **{alert_sev_in}**")
                        else:
                            st.warning(f"⚠️ **Geometry Warning**: Polygon is self-intersecting or degenerate.")
                    except Exception as ge:
                        st.error(f"Geometric calculation error: {ge}")
                else:
                    st.info(f"ℹ️ Place at least **{3 - pts_count} more point(s)** to close the spatial polygon.")

            else:
                st.info("Load or extract a reference camera frame above to preview polygon rendering.")

        # Interactive Click Coordinate Helper
        with st.container(border=True):
            st.markdown("**🎯 Interactive Pixel Coordinate Picker Guide**")
            st.caption(
                "Hover or inspect locations on the preview frame to find exact pixel boundaries for high-risk zones, "
                "emergency fire exits, pedestrian lanes, or machinery clearances."
            )
            g1, g2, g3 = st.columns(3)
            g1.metric("Current Vertices", len(st.session_state["editor_points"]))
            g2.metric("Frame Width", f"{frame_w} px")
            g3.metric("Frame Height", f"{frame_h} px")

        # JSON Configuration Output & Contract Viewer
        with st.expander("📄 Real-Time JSON Configuration Contract Preview (Member 6 / Member 3)", expanded=False):
            curr_dict = {
                "camera_id": f"CAM_{site_id_input.upper()}_01",
                "site_id": f"SITE_{site_id_input.upper()}",
                "site_name": f"{site_id_input.title()} Facility Operations",
                "site_type": "warehouse" if "warehouse" in site_id_input else "construction",
                "resolution": [frame_w, frame_h],
                "zones": {
                    zone_key_in: {
                        "zone_id": zone_id_in,
                        "zone_name": zone_name_in,
                        "zone_type": zone_type_in,
                        "alert_severity": alert_sev_in,
                        "coordinates": st.session_state["editor_points"],
                        "prohibited_classes": prohibited_ids,
                        "blockage_threshold_seconds": float(dwell_thresh_in),
                        "description": zone_desc_in
                    }
                }
            }
            if 'enable_line' in locals() and enable_line:
                curr_dict["counting_lines"] = {
                    line_id_in.lower(): {
                        "line_id": line_id_in,
                        "name": line_name_in,
                        "coordinates": [[int(lx1), int(ly1)], [int(lx2), int(ly2)]],
                        "count_classes": [0],
                        "description": "Virtual pedestrian and equipment counter"
                    }
                }
            st.json(curr_dict)
            st.download_button(
                "⬇️ Download Config JSON",
                data=json.dumps(curr_dict, indent=2),
                file_name=f"zones_{site_id_input}.json",
                mime="application/json",
                use_container_width=True
            )

