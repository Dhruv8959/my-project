"""
run_local.py — Run cement bag counting directly from command line.
No server needed. Just point it at a video file.

Usage:
    python run_local.py --video path/to/video.mp4
    python run_local.py --video path/to/video.mp4 --frame_skip 3 --confidence 0.45
"""

import argparse
import os
import sys
from video_processor import process_video


import cv2
from ultralytics import YOLO

# Load model (CPU pe hi chalega by default)
# model = YOLO("best.pt")
def progress_bar(current, total):
    if total <= 0:
        return
    pct   = current / total
    bar   = int(pct * 40)
    line  = f"\r[{'█' * bar}{'░' * (40 - bar)}] {pct*100:.1f}%  frame {current}/{total}"
    sys.stdout.write(line)
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Cement Bag Counter (CPU)")
    parser.add_argument("--video",      required=True, help="Path to input video")
    parser.add_argument("--model",      default="best.pt", help="YOLO model path")
    parser.add_argument("--output_dir", default="outputs",  help="Output directory")
    parser.add_argument("--frame_skip", type=int, default=2,
                        help="Process every Nth frame (default: 2, faster on CPU)")
    parser.add_argument("--confidence", type=float, default=0.1,
                        help="Detection confidence (0.1–1.0, default: 0.1)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"[ERROR] Video not found: {args.video}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"\n🎬  Processing: {args.video}")
    print(f"    Model       : {args.model}")
    print(f"    Frame skip  : {args.frame_skip}")
    print(f"    Confidence  : {args.confidence}")
    print()

    result = process_video(
        video_path=args.video,
        output_dir=args.output_dir,
        frame_skip=args.frame_skip,
        confidence=args.confidence,
        progress_callback=progress_bar
    )

    print()   # newline after progress bar
    print("\n" + "=" * 50)
    print("✅  RESULTS")
    print("=" * 50)
    print(f"  Total unique bags : {result['total_unique_bags']}")
    print(f"  Total frames      : {result['total_frames']}")
    print(f"  Video duration    : {result['duration_sec']} sec")
    print(f"  Processing time   : {result['processing_time_sec']} sec")
    print(f"  CSV report        : {result['csv_path']}")
    print(f"  Annotated video   : {result['annotated_video_path']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
