import cv2
import pandas as pd
import os
import time
from detector import CementBagDetector
from tracker import CentroidTracker


def draw_detections(frame, detections, objects):
    """Draw bounding boxes and IDs on frame."""
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        conf = det["confidence"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"Bag {conf:.2f}", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    for oid, (cx, cy) in objects.items():
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
        cv2.putText(frame, f"ID:{oid}", (cx + 5, cy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

    return frame


def process_video(video_path, output_dir=".", frame_skip=2,
                  confidence=0.4, progress_callback=None, job_id=None):

    """
    Process video file to detect and count cement bags.

    Args:
        video_path:        Path to input video
        output_dir:        Where to save CSV and annotated video
        frame_skip:        Process every Nth frame (speeds up on CPU)
        confidence:        Detection confidence threshold
        progress_callback: Optional fn(current_frame, total_frames)

    Returns:
        dict with total_unique_bags, csv_path, annotated_video_path, summary
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps       = cap.get(cv2.CAP_PROP_FPS) or 25
    width     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[INFO] Video: {width}x{height} @ {fps:.1f}fps, {total_frames} frames")
    print(f"[INFO] Processing every {frame_skip} frame(s) | conf={confidence}")

    detector = CementBagDetector(confidence=confidence)
    tracker  = CentroidTracker(max_distance=80, max_disappeared=15)

    # Annotated output video
    base_name = job_id if job_id else os.path.splitext(os.path.basename(video_path))[0]
    out_video_path = os.path.join(output_dir, f"{base_name}_annotated.mp4")
    csv_path       = os.path.join(output_dir, f"{base_name}_bag_count.csv")


    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(out_video_path, fourcc, fps, (640, 480))

    frame_id  = 0
    rows      = []
    start_t   = time.time()

    while frame_id < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))
        
        detections = detector.detect(frame)
        objects    = tracker.update(detections)


        bags_in_frame   = len(detections)
        unique_so_far   = tracker.unique_count
        timestamp_sec   = round(frame_id / fps, 3)

        rows.append({
            "frame_id":         frame_id,
            "timestamp_sec":    timestamp_sec,
            "bags_in_frame":    bags_in_frame,
            "unique_bags_total": unique_so_far
        })

        # Annotate frame
        frame = draw_detections(frame, detections, objects)
        cv2.putText(frame, f"Unique Bags: {unique_so_far}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
        cv2.putText(frame, f"Frame: {frame_id}", (10, 54),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        out.write(frame)

        if progress_callback:
            progress_callback(frame_id, total_frames)

        frame_id += frame_skip

    cap.release()
    out.release()

    elapsed = round(time.time() - start_t, 1)
    print(f"[INFO] Done in {elapsed}s — {frame_id} frames processed.")

    # Save CSV
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    print(f"[INFO] CSV saved: {csv_path}")

    summary = {
        "total_unique_bags": tracker.unique_count,
        "total_frames":      frame_id,
        "duration_sec":      round(frame_id / fps, 2),
        "processing_time_sec": elapsed,
        "csv_path":          csv_path,
        "annotated_video_path": out_video_path
    }
    return summary
