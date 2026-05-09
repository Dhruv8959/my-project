from ultralytics import YOLO
import torch


class CementBagDetector:
    def __init__(self, model_path="best.pt", confidence=0.4):
        """
        Initialize YOLO detector, forced to CPU for compatibility.
        Args:
            model_path: Path to trained YOLO .pt model
            confidence: Minimum confidence threshold for detections
        """
        # Force CPU — no CUDA required
        self.device = "cpu"
        self.confidence = confidence
        self.target_class = "cement_bag"

        print(f"[INFO] Loading model: {model_path} on {self.device}")
        self.model = YOLO(model_path)
        self.model.to(self.device)
        print("[INFO] Model loaded successfully.")

    def detect(self, frame):
        """
        Run detection on a single frame.
        Returns list of dicts: {bbox, confidence, label}
        """
        results = self.model(
            frame,
            device=self.device,
            conf=self.confidence,
            verbose=False
        )[0]

        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]

            # Accept 'cement_bag' or fallback to class 0 if model has only one class
            if label == self.target_class or (len(self.model.names) == 1 and cls_id == 0):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": round(conf, 3),
                    "label": label
                })

        return detections
