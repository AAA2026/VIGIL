
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
# Aligned with the V6 export profile in backend/models/violence_detector_v6_config.json
VIOLENCE_THRESHOLD = 0.315
ACCIDENT_THRESHOLD = 0.30  # Increased sensitivity for more crash detections
SMOOTHING_WINDOW = 5

# Default cameras (aligned with dashboard mock metadata)
DEFAULT_CAMERAS = [
    "CAM-042", "CAM-128", "CAM-089", "CAM-156",
    "CAM-283", "CAM-074", "CAM-195", "CAM-267",
    "CAM-341", "CAM-412", "CAM-523", "CAM-604"
]





# Model identification
MODEL_NAME = "Vigil-Violence-V6-TorchScript"


MODEL_PATHS = {
    "violence_ts": "backend/models/violence_detector_v6_ts.pt",
    "violence_config": "backend/models/violence_detector_v6_config.json",
    "crash_lstm": "backend/ai/crash_detector/mobilenetv2_lstm_finetuned.pt",
    "people_counter": "backend/models/yolov8n.pt",
    # Backward-compatible alias for older callers.
    "mobilenet_clip": "backend/models/violence_detector_v6_ts.pt",
}

DATA_PATHS = {
    "demo_video": "demo.mp4"
}
