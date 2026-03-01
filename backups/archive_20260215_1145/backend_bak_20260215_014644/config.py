
# Camera type groupings for simulator and backend logic
VIOLENCE_CAMERAS = [
    "CAM-042", "CAM-128", "CAM-089", "CAM-156"
]
CRASH_CAMERAS = [
    "CAM-283", "CAM-074", "CAM-195", "CAM-267"
]
PEOPLE_COUNT_CAMERAS = VIOLENCE_CAMERAS  # Or specify a different list if needed
# Global configuration for thresholds and model paths

# Externalized thresholds for tunability
# HIGH ACCURACY MODE: Only trigger on very confident detections
VIOLENCE_THRESHOLD = 0.70  # Higher confidence to reduce false positives
ACCIDENT_THRESHOLD = 0.30  # Increased sensitivity for more crash detections
SMOOTHING_WINDOW = 5

# Default cameras (aligned with dashboard mock metadata)
DEFAULT_CAMERAS = [
    "CAM-042", "CAM-128", "CAM-089", "CAM-156",
    "CAM-283", "CAM-074", "CAM-195", "CAM-267",
    "CAM-341", "CAM-412", "CAM-523", "CAM-604"
]





# Model identification
MODEL_NAME = "Vigil-MobileNetClip-v1"


from pathlib import Path

# Base project directory (workspace root)
BASE_DIR = Path(__file__).parent.parent

MODEL_PATHS = {
    "mobilenet_clip": str((BASE_DIR / "backend" / "models" / "mobilenet_clip_best_ts.pt").resolve()),  # Violence
    "crash_lstm": str((BASE_DIR / "backend" / "models" / "mobilenetv2_lstm_finetuned.pt").resolve()),  # Crash
    "people_counter": str((BASE_DIR / "backend" / "models" / "yolov8n.pt").resolve()),                 # People counting
    "x3d_s": str((BASE_DIR / "backend" / "models" / "x3d_s_best.pth").resolve()),
}

DATA_PATHS = {
    # Default demo video path (optional). Consumers should accept either absolute paths or relative names.
    "demo_video": str((BASE_DIR / "data" / "videos" / "demo.mp4").resolve())
}
