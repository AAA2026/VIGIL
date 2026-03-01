"""Thread-safe camera state and video rotation utilities."""

from __future__ import annotations

import logging
import random
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import CRASH_CAMERAS, VIOLENCE_CAMERAS

_VIDEO_ROOT = Path(__file__).resolve().parents[2] / "Videos"
_VIDEO_PATTERNS = ("*.mp4", "*.MP4", "*.avi", "*.AVI")


class SafeDict:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


camera_states = SafeDict()
incidents = SafeDict()

_system_state = SafeDict()
_system_state.set("offline_mode", False)


def get_offline_mode_state() -> bool:
    return bool(_system_state.get("offline_mode", False))


def set_offline_mode_state(enabled: bool) -> None:
    _system_state.set("offline_mode", bool(enabled))
    logging.info("System offline mode set to: %s", bool(enabled))


def _video_files(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    files: list[Path] = []
    for pattern in _VIDEO_PATTERNS:
        files.extend([f for f in folder.glob(pattern) if f.is_file()])
    return files


def _folder_for_camera(camera_id: str) -> Path:
    if camera_id in VIOLENCE_CAMERAS:
        return _VIDEO_ROOT / "violence"
    if camera_id in CRASH_CAMERAS:
        return _VIDEO_ROOT / "crash"

    neutral_candidates = [_VIDEO_ROOT / "no_violence", _VIDEO_ROOT / "no_crash"]
    random.shuffle(neutral_candidates)
    for folder in neutral_candidates:
        if _video_files(folder):
            return folder

    return _VIDEO_ROOT / "no_violence"


def rotate_camera_video(camera_id: str, allow_violence: bool = True, allow_crash: bool = True) -> str:
    # allow_violence/allow_crash are preserved for API compatibility.
    del allow_violence, allow_crash
    folder = _folder_for_camera(camera_id)
    files = _video_files(folder)
    if files:
        chosen = random.choice(files)
        return f"{folder.name}/{chosen.name}"

    for fallback_name in ("violence", "crash", "no_violence", "no_crash"):
        fallback_folder = _VIDEO_ROOT / fallback_name
        fallback_files = _video_files(fallback_folder)
        if fallback_files:
            chosen = random.choice(fallback_files)
            return f"{fallback_folder.name}/{chosen.name}"

    logging.warning("No valid video found for camera %s", camera_id)
    return ""


def get_video_path(camera_id: str) -> str:
    return rotate_camera_video(camera_id)


def get_video_absolute_path(camera_id: str) -> str:
    state = camera_states.get(camera_id, {})
    current_rel = state.get("video")
    if current_rel:
        candidate = (_VIDEO_ROOT / current_rel).resolve()
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    rel = rotate_camera_video(camera_id)
    if not rel:
        return ""
    return str((_VIDEO_ROOT / rel).resolve())


def update_camera_inference(camera_id: str, inference_result: Dict[str, Any]) -> None:
    state = camera_states.get(camera_id, {})
    state.setdefault("camera_id", camera_id)
    state.update(inference_result or {})
    camera_states.set(camera_id, state)


def get_all_camera_states() -> list[Dict[str, Any]]:
    return list(camera_states.all().values())
