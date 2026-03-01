"""Unified backend AI inference entrypoint."""

from __future__ import annotations

from backend.ai.crash_detector import detect_crash
from backend.ai.people_counter.yolov8 import detect_people_count
from backend.ai.violence_detector import detect_violence


def run_inference(video_path: str, camera_id: str | None = None) -> dict:
    """Route inference by camera role and return a normalized payload."""
    from backend.config import CRASH_CAMERAS, PEOPLE_COUNT_CAMERAS, VIOLENCE_CAMERAS

    if camera_id and camera_id in CRASH_CAMERAS:
        return detect_crash(video_path)

    result = detect_violence(video_path)

    if camera_id and camera_id in VIOLENCE_CAMERAS and camera_id in PEOPLE_COUNT_CAMERAS:
        try:
            people = detect_people_count(video_path)
            result["people_count"] = people.get("count", 0)
            result["people_confidence"] = people.get("confidence", 0.0)
        except Exception as exc:
            result["people_count_error"] = str(exc)

    return result
