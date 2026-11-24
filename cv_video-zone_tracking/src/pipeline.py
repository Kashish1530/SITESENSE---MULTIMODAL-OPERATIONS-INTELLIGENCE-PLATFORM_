"""
pipeline.py
Main execution script for Member 2.
Complies with SiteSense Capstone Specification (Features 2.3, 2.4, 2.6).
Outputs:
1. Annotated Video (*_annotated.mp4)
2. Evidence Frame Screenshots (outputs/evidence_frames/)
3. Standardized Spatial Event JSON Log (outputs/events/)
4. Interactive GUI display (with standard playback speed & controls)
"""
import cv2
import json
import os
import argparse
import csv
from pathlib import Path
from tracker import ByteTrackEngine
from zone_engine import ZoneEngine
from event_generator import SpatialEventFormatter
from annotator import VisualAnnotator
from violation_db import insert_violation
from video_reader import VideoReader
from tracking_metrics import TrackingMetricsTracker

class AnalyticsResult(list):
    """
    List of emitted spatial events with attached executive summary metadata.
    Fully compatible with standard list iteration (for e in result).
    """
    def __init__(self, events, summary=None):
        super().__init__(events)
        self.summary = summary or {}

def run_site_analytics(
    video_path: str,
    zones_config_path: str = "config/zones_warehouse.json",
    model_weights: str = "models/best.pt",
    site_id: str = "SITE_07",
    output_dir: str = "outputs",
    show_display: bool = True,
    save_annotated_video: bool = True,
    max_frames: int = None
):
    Path(f"{output_dir}/events").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/evidence_frames").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/annotated_videos").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/tracking").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/zone_events").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/reports").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/metadata").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/evaluation").mkdir(parents=True, exist_ok=True)

    # Deliverable 1: VideoReader with EOS, Dropped Frame detection & Metadata
    reader = VideoReader(video_path, max_frames=max_frames)
    fps = reader.fps
    width = reader.width
    height = reader.height
    total_frames = reader.total_frames

    video_writer = None
    annotated_video_path = None
    if save_annotated_video:
        video_stem = Path(video_path).stem
        annotated_video_path = f"{output_dir}/annotated_videos/{video_stem}_annotated.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(annotated_video_path, fourcc, fps, (width, height))

    tracker = ByteTrackEngine(model_weights=model_weights)
    zone_engine = ZoneEngine(zones_config_path)
    camera_id = zone_engine.config.get("camera_id", "CAM_01")
    metrics_tracker = TrackingMetricsTracker(site_id=site_id, camera_id=camera_id)

    all_emitted_events = []
    active_event_ids_logged = set()
    is_paused = False

    print(f"\n=======================================================")
    print(f"[*] Starting Video Spatial Analysis")
    print(f"[*] Site ID: {site_id} | Camera: {camera_id}")
    print(f"[*] Input Video: {video_path} ({width}x{height} @ {fps:.1f} FPS, {total_frames} frames)")
    print(f"[*] Model Weights: {model_weights}")
    print(f"[*] Zones Config: {zones_config_path}")
    print(f"[*] CONTROLS: Space = Pause/Resume | Q / ESC = Exit")
    print(f"=======================================================\n")

    window_name = "SiteSense Operations Intelligence - CV Stream"
    if show_display:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

    frame_delay_ms = max(1, int(1000.0 / fps))

    try:
        for frame_idx, timestamp, frame in reader.frames():
            if is_paused:
                if show_display:
                    key = cv2.waitKey(100) & 0xFF
                    if key == ord(' ') or key == ord('p'):
                        is_paused = False
                        print("[>] Resuming video playback...")
                    elif key == ord('q') or key == 27:
                        print("\n[!] User closed window.")
                        break
                continue

            frame_start_t = metrics_tracker.record_frame_start()

            # 1. ByteTrack Object Tracking (Feature 2.3)
            tracked_objects = tracker.process_frame(frame)
            metrics_tracker.record_frame_end(frame_start_t)
            metrics_tracker.add_tracking_detections(frame_idx, timestamp, tracked_objects, VisualAnnotator.CLASS_NAMES)

            # 2. Zone Evaluation, Dwell Time, & Line Crossing (Feature 2.4)
            violations, crossings = zone_engine.evaluate_tracks(tracked_objects, timestamp)
            metrics_tracker.add_zone_events(violations, timestamp)

            for cr in crossings:
                print(f"[FLOW] Line {cr['line_name']} crossed by Track {cr['track_id']} ({cr['direction']}) -> Total IN: {cr['entries']} | Total OUT: {cr['exits']}")

            # 3. Emit & Log Events
            active_violating_zone_ids = set()
            for viol in violations:
                active_violating_zone_ids.add(viol["zone_id"])
                event = SpatialEventFormatter.format_event(
                    viol, site_id=site_id, camera_id=camera_id
                )
                
                event_sig = f"{viol['track_id']}_{viol['zone_id']}"
                if event_sig not in active_event_ids_logged:
                    active_event_ids_logged.add(event_sig)
                    print(f"-> [{viol['severity']} ALERT @ {timestamp:.1f}s] {event['event_type']} in {viol['zone_name']} "
                          f"by Track {viol['track_id']} (Dwell: {viol['dwell_time_seconds']}s)")

                all_emitted_events.append(event)
                
            # 4. Annotations
            frame = VisualAnnotator.draw_zones(frame, zone_engine.zones, active_violating_zone_ids)
            frame = VisualAnnotator.draw_counting_lines(frame, zone_engine.counting_lines)
            frame = VisualAnnotator.draw_tracked_objects(frame, tracked_objects, violations)
            frame = VisualAnnotator.draw_hud(frame, frame_idx, timestamp, violations, len(tracked_objects), zone_engine.counting_lines)

            # Save Annotated Evidence Frame & DB Record for High/Critical Violations
            for viol in violations:
                if viol["severity"] in ["HIGH", "CRITICAL"]:
                    ev_filename = f"{output_dir}/evidence_frames/{event['event_id']}_{frame_idx}.jpg"
                    if not os.path.exists(ev_filename):
                        cv2.imwrite(ev_filename, frame)
                        event["evidence_frame_path"] = ev_filename
                        # Persist to SQLite Violation DB (deduplicated)
                        try:
                            insert_violation(event, evidence_path=os.path.abspath(ev_filename), video_name=Path(video_path).name)
                        except Exception as db_err:
                            pass

            # 5. Write to Output Video
            if video_writer is not None:
                video_writer.write(frame)

            # 6. Interactive Display
            if show_display:
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(frame_delay_ms) & 0xFF
                if key == ord('q') or key == 27:
                    print("\n[!] User interrupted playback.")
                    break
                elif key == ord(' ') or key == ord('p'):
                    is_paused = True
                    print("[||] PAUSED! Press SPACEBAR to Resume...")

    finally:
        reader.release()
        if video_writer is not None:
            video_writer.release()
            print(f"[+] Saved Full Annotated Video -> {annotated_video_path}")
        if show_display:
            cv2.destroyAllWindows()

    frame_idx = reader.current_frame_idx

    # Export Standardized Outputs (Deliverables for Member 3 & Agentic AI)
    tracking_csv = f"{output_dir}/tracking/tracking_results.csv"
    zone_events_csv = f"{output_dir}/zone_events/zone_events.csv"
    zone_summary_json = f"{output_dir}/reports/zone_summary.json"
    metadata_csv = f"{output_dir}/metadata/video_metadata.csv"
    summary_metrics_csv = f"{output_dir}/evaluation/tracking_summary.csv"

    unique_person_count = tracker.get_unique_person_count()
    unique_counts_by_class = tracker.get_unique_counts_by_class()
    total_unique_objects = tracker.get_total_unique_objects()

    metrics_tracker.export_output_a_tracking_results(tracking_csv)
    metrics_tracker.export_output_b_zone_events(zone_events_csv)
    metrics_tracker.export_output_c_zone_summary(zone_summary_json, unique_person_count, zone_engine, zone_engine.counting_lines)
    reader.export_metadata_csv(metadata_csv)

    metrics_summary = metrics_tracker.compute_summary_metrics(
        unique_person_count=unique_person_count,
        unique_counts_by_class=unique_counts_by_class,
        total_frames=frame_idx,
        dropped_frames=reader.dropped_frames_count
    )

    with open(summary_metrics_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics_summary.keys()))
        writer.writeheader()
        writer.writerow(metrics_summary)

    log_file = f"{output_dir}/events/site_{site_id}_events.json"
    with open(log_file, "w") as f:
        json.dump(all_emitted_events, f, indent=2)

    summary_file = f"{output_dir}/events/site_{site_id}_summary.json"
    with open(summary_file, "w") as f:
        json.dump(metrics_summary, f, indent=2)

    print(f"\n[+] Analysis Complete!")
    print(f"[+] Total Frames Processed: {frame_idx} (Dropped: {reader.dropped_frames_count})")
    print(f"[+] Average Processing Speed: {metrics_summary['average_fps']} FPS (Latency: {metrics_summary['average_latency_ms']} ms/frame)")
    print(f"[+] Unique Persons Tracked (Persistent IDs): {unique_person_count}")
    print(f"[+] Total Distinct Tracked Objects: {total_unique_objects}")
    print(f"[+] Total Events Emitted: {len(all_emitted_events)}")
    print(f"[+] Exported Output A (Tracking Results): {tracking_csv}")
    print(f"[+] Exported Output B (Zone Events): {zone_events_csv}")
    print(f"[+] Exported Output C (Zone Summary): {zone_summary_json}")
    print(f"[+] Exported Performance Summary: {summary_metrics_csv}")
    return AnalyticsResult(all_emitted_events, summary=metrics_summary)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SiteSense Video Spatial Analytics Pipeline")
    parser.add_argument("--video", default="data/sample_videos/warehouse1.mp4", help="Video file path")
    parser.add_argument("--zones", default="config/zones_warehouse.json", help="Zones config JSON")
    default_model = "models/best_3.pt" if os.path.exists("models/best_3.pt") else "models/best.pt"
    parser.add_argument("--model", default=default_model, help="YOLO model path")
    parser.add_argument("--site_id", default="SITE_WAREHOUSE_01", help="Site identifier")
    parser.add_argument("--headless", action="store_true", help="Run without UI window")
    parser.add_argument("--no_save_video", action="store_true", help="Do not save output video")
    parser.add_argument("--max_frames", type=int, default=None, help="Max frames to process")
    args = parser.parse_args()

    if os.path.exists(args.video):
        run_site_analytics(
            video_path=args.video,
            zones_config_path=args.zones,
            model_weights=args.model,
            site_id=args.site_id,
            show_display=(not args.headless),
            save_annotated_video=(not args.no_save_video),
            max_frames=args.max_frames
        )
    else:
        print(f"Notice: '{args.video}' nahi mila. Koi bhi valid MP4 file data/sample_videos/ mein daal ke run karo.")
