"""
YOLOv8 People Counter Integration

This module loads a YOLOv8 model and counts people in a video.
Requires ultralytics package: pip install ultralytics
"""
import time
import os
from pathlib import Path
import cv2
import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel
from torch.nn.modules.container import Sequential
from torch.serialization import add_safe_globals

# PyTorch 2.7+ defaults to weights_only=True in torch.load which breaks legacy YOLOv8 weights.
# 1) Allowlist known Ultralytics classes.
add_safe_globals([DetectionModel, Sequential])
# 2) Force torch.load to fall back to weights_only=False unless explicitly overridden.
_torch_load = torch.load
def _safe_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _torch_load(*args, **kwargs)
torch.load = _safe_load

_DEFAULT_YOLO_PATH = Path(__file__).parent.parent.parent / "models" / "yolov8n.pt"
MODEL_PATH = Path(os.getenv("YOLO_WEIGHTS", str(_DEFAULT_YOLO_PATH)))
if not MODEL_PATH.exists():
    fallback = _DEFAULT_YOLO_PATH.parent / "people_detector_yolov8n.pt"
    if fallback.exists():
        MODEL_PATH = fallback

# Global model cache
_yolo_model = None

def load_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO(str(MODEL_PATH))
    return _yolo_model

def detect_people_count(video_path: str) -> dict:
    model = load_yolo_model()
    cap = cv2.VideoCapture(video_path)
    people_count = 0
    frame_count = 0
    start = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, verbose=False)
        # Count people (class 0 in COCO)
        n_people = sum(int(cls == 0) for cls in results[0].boxes.cls.cpu().numpy())
        people_count += n_people
        frame_count += 1
        if frame_count >= 16:
            break
    cap.release()
    avg_count = int(round(people_count / frame_count)) if frame_count else 0
    latency = int((time.time() - start) * 1000)
    return {
        "count": avg_count,
        "confidence": 0.95,  # Placeholder, can be improved
        "model": "yolov8n.pt",
        "latency_ms": latency,
        "timestamp": time.time()
    }
