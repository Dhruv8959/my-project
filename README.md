# 🧱 Cement Bag Counter (CPU Edition)

Detect and count cement bags in a video using YOLOv8.  
Runs entirely on **CPU** — no GPU required.  
Outputs a **CSV report** with per-frame bag counts + an annotated video.

---

## 📁 Project Structure

```
cement_bag_counter/
├── detector.py        # YOLO detection (forced CPU)
├── tracker.py         # Centroid tracker (unique bag IDs)
├── video_processor.py # Core pipeline: detect → track → export CSV
├── main.py            # FastAPI server (upload video via HTTP)
├── run_local.py       # CLI script (no server needed)
├── requirements.txt
└── best.pt            # ← Place your trained YOLO model here
```

---

## ⚙️ Installation

```bash
# 1. Clone / unzip this project
cd cement_bag_counter

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies (CPU-safe build)
pip install -r requirements.txt

# 4. Place your trained model
cp /path/to/your/best.pt .
```

> **Note:** `ultralytics` will automatically install the CPU-only build of  
> PyTorch if no CUDA GPU is detected. No manual torch installation needed.

---

## 🚀 Usage

### Option A — Command Line (simplest)

```bash
python run_local.py --video path/to/video.mp4
```

Optional flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `best.pt` | Path to YOLO weights |
| `--output_dir` | `outputs/` | Folder for CSV + annotated video |
| `--frame_skip` | `2` | Process every Nth frame (higher = faster) |
| `--confidence` | `0.4` | Min detection confidence (0.1–0.95) |

**Example:**
```bash
python run_local.py --video factory.mp4 --frame_skip 3 --confidence 0.45
```

---

### Option B — FastAPI Server

```bash
uvicorn main:app --reload --host 172.22.16.1 --port 8000
```

Then open **http://172.22.16.1:8000/docs** for the interactive Swagger UI.

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/` | Upload video → count bags |
| `GET`  | `/download/csv/{job_id}` | Download CSV report |
| `GET`  | `/download/video/{job_id}` | Download annotated video |

**Example with curl:**
```bash
curl -X POST "http://172.22.16.1:8000/upload/?frame_skip=2&confidence=0.4" \
     -F "file=@factory.mp4"
```

---

## 📊 CSV Output Format

The output CSV (`outputs/<videoname>_bag_count.csv`) contains:

| Column | Description |
|--------|-------------|
| `frame_id` | Frame number (0-indexed) |
| `timestamp_sec` | Time in video (seconds) |
| `bags_in_frame` | Bags detected in this frame |
| `unique_bags_total` | Cumulative unique bags counted so far |

**Example:**
```
frame_id,timestamp_sec,bags_in_frame,unique_bags_total
0,0.0,0,0
1,0.04,2,2
2,0.08,2,2
3,0.12,3,3
...
```

---

## 🎯 Model Notes

- The project expects a YOLO model trained to detect `cement_bag` class.
- If your model has only **one class** (regardless of name), it will work automatically.
- Recommended: Train with [Ultralytics YOLOv8](https://docs.ultralytics.com/).

---

## ⚡ CPU Performance Tips

| Tip | Effect |
|-----|--------|
| Increase `--frame_skip` to 3–5 | 2–4× faster processing |
| Use `yolov8n.pt` (nano) as base | Lightest model for CPU |
| Reduce video resolution beforehand | Speeds up frame processing |

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| `FileNotFoundError: best.pt` | Place your model file in the project folder |
| `No module named 'ultralytics'` | Run `pip install -r requirements.txt` |
| Bags not detected | Lower `--confidence` to 0.25–0.35 |
| Double-counting bags | Increase `max_distance` in `tracker.py` |
