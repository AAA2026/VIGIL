# VIGIL Camera Manager - cleaned single definitions
import logging
import random
import threading
from pathlib import Path
from backend.config import VIOLENCE_CAMERAS, CRASH_CAMERAS


class SafeDict:
    def __init__(self):
        self._d = {}
        self._lock = threading.Lock()

    def get(self, key, default=None):
        with self._lock:
            return self._d.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._d[key] = value

    def all(self):
        with self._lock:
            return dict(self._d)


camera_states = SafeDict()
incidents = SafeDict()
_system_state = SafeDict()
_system_state.set("offline_mode", False)


def _video_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "videos"


def _pick_video(folder: Path):
    mp4s = [f for f in folder.glob("*.mp4")] + [f for f in folder.glob("*.MP4")]
    avis = [f for f in folder.glob("*.avi")] + [f for f in folder.glob("*.AVI")]
    candidates = mp4s if mp4s else avis
    return random.choice(candidates) if candidates else None


def get_video_path(camera_id: str):
    video_dir = _video_dir()
    if camera_id in VIOLENCE_CAMERAS:
        folder = video_dir / "violence"
    elif camera_id in CRASH_CAMERAS:
        folder = video_dir / "crash"
    else:
        folder = video_dir / "no_violence"
        if not folder.exists() or not _pick_video(folder):
            folder = video_dir / "no_crash"
    if folder.exists():
        choice = _pick_video(folder)
        if choice:
            return f"{folder.name}/{choice.name}"

    # fallback: any available video
    for sub in ["violence", "crash", "no_violence", "no_crash"]:
        folder = video_dir / sub
        if folder.exists():
            choice = _pick_video(folder)
            if choice:
                return f"{folder.name}/{choice.name}"
    logging.warning(f"No valid video found for camera {camera_id}")
    return ""


def rotate_camera_video(camera_id: str, allow_violence: bool = True, allow_crash: bool = True):
    video_dir = _video_dir()
    if camera_id in VIOLENCE_CAMERAS:
        folder = video_dir / "violence"
    elif camera_id in CRASH_CAMERAS:
        folder = video_dir / "crash"
    else:
        # Bias toward no_crash to vary content
        folder = video_dir / ("no_crash" if random.random() < 0.6 else "no_violence")
        if not folder.exists() or not _pick_video(folder):
            folder = video_dir / "no_violence"
    choice = _pick_video(folder) if folder.exists() else None
    return f"{folder.name}/{choice.name}" if choice else ""


def update_camera_inference(camera_id: str, inference_result):
    state = camera_states.get(camera_id, {}) or {}
    state.update(inference_result or {})
    camera_states.set(camera_id, state)


def get_all_camera_states():
    return list(camera_states.all().values())


def get_offline_mode_state() -> bool:
    return _system_state.get("offline_mode", False)


def set_offline_mode_state(enabled: bool):
    _system_state.set("offline_mode", enabled)
    logging.info(f"System offline mode set to: {enabled}")


def get_video_absolute_path(camera_id: str) -> str:
    video_dir = _video_dir()
    if camera_id in VIOLENCE_CAMERAS:
        folder = video_dir / "violence"
    elif camera_id in CRASH_CAMERAS:
        folder = video_dir / "crash"
    else:
        folder = video_dir / "no_violence"
        if not folder.exists() or not _pick_video(folder):
            folder = video_dir / "no_crash"
    choice = _pick_video(folder) if folder.exists() else None
    if choice:
        return f"{folder.name}/{choice.name}"
    for sub in ["violence", "crash", "no_violence", "no_crash"]:
        folder = video_dir / sub
        if folder.exists():
            choice = _pick_video(folder)
            if choice:
                return f"{folder.name}/{choice.name}"
    return ""
