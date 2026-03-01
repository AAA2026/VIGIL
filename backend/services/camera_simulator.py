"""Background camera simulator for demo/live status endpoints."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

from backend.ai.inference import run_inference
from backend.config import ACCIDENT_THRESHOLD, DEFAULT_CAMERAS, VIOLENCE_THRESHOLD
from backend.services.camera_manager import (
    get_offline_mode_state,
    rotate_camera_video,
    update_camera_inference,
)
from backend.services.incident_storage import add_incident


class CameraSimulator:
    def __init__(self, camera_ids, video_dir, rotation_interval=120, violence_probability=0.10):
        self.camera_ids = list(camera_ids)
        self.video_dir = Path(video_dir)
        self.rotation_interval = float(rotation_interval)
        self.violence_probability = float(violence_probability)

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        self.inference_count = 0
        self.violence_blocked_until: dict[str, float] = {}
        self.crash_blocked_until: dict[str, float] = {}
        self.last_video_rotation: dict[str, float] = {}
        self.processed_incident_videos: set[str] = set()

        self.video_rotation_duration = self.rotation_interval
        self.violence_cooldown = 40
        self.crash_cooldown = 40

        self.camera_states = {cid: self._initial_state(cid) for cid in self.camera_ids}

    def _initial_state(self, camera_id: str) -> dict:
        rel_path = rotate_camera_video(camera_id)
        return {
            "camera_id": camera_id,
            "status": "online",
            "video": rel_path,
            "event": "none",
            "confidence": 0.0,
            "last_update": None,
        }

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _ensure_video(self, camera_id: str) -> str:
        now = time.time()
        state = self.camera_states.setdefault(camera_id, self._initial_state(camera_id))
        current_video = state.get("video")
        last_rot = self.last_video_rotation.get(camera_id, 0.0)

        if not current_video or (now - last_rot) >= self.video_rotation_duration:
            current_video = rotate_camera_video(camera_id)
            state["video"] = current_video
            self.last_video_rotation[camera_id] = now

        return current_video or ""

    def _simulation_loop(self):
        while self.running:
            for camera_id in self.camera_ids:
                if not self.running:
                    break

                try:
                    rel_video_path = self._ensure_video(camera_id)
                    if not rel_video_path:
                        continue

                    video_path = str((self.video_dir / rel_video_path).resolve())
                    result = run_inference(video_path, camera_id=camera_id)

                    result.update(
                        {
                            "camera_id": camera_id,
                            "status": "online",
                            "video": rel_video_path,
                            "last_update": time.time(),
                        }
                    )

                    with self.lock:
                        self.camera_states.setdefault(camera_id, {}).update(result)
                        update_camera_inference(camera_id, result)
                        self.inference_count += 1

                    self._maybe_create_incident(
                        camera_id=camera_id,
                        rel_video_path=rel_video_path,
                        abs_video_path=video_path,
                        result=result,
                    )

                except Exception as exc:
                    print(f"[SIM] Error processing {camera_id}: {exc}")

            time.sleep(self.rotation_interval)

    def _maybe_create_incident(self, camera_id: str, rel_video_path: str, abs_video_path: str, result: dict):
        if get_offline_mode_state():
            return

        event = (result.get("event") or "").lower()
        confidence = float(result.get("confidence", 0.0))
        now = time.time()

        if event == "violence" and confidence >= VIOLENCE_THRESHOLD:
            blocked_until = self.violence_blocked_until.get(camera_id, 0.0)
            if now < blocked_until or abs_video_path in self.processed_incident_videos:
                return

            people = int(result.get("people_count", 0) or 0)
            label = f"Violence incident involving {people} people" if people else "Violence incident detected"
            extra = {"label": label, "timestamp": result.get("timestamp")}
            if people:
                extra["people_count"] = people

            add_incident(
                camera_id=camera_id,
                event_type="violence",
                confidence=confidence,
                video_path=rel_video_path,
                model=result.get("model", "unknown"),
                extra=extra,
            )

            self.processed_incident_videos.add(abs_video_path)
            self.violence_blocked_until[camera_id] = now + self.violence_cooldown
            return

        is_crash_event = event in {"car_crash", "crash", "traffic"}
        if is_crash_event and confidence >= ACCIDENT_THRESHOLD:
            blocked_until = self.crash_blocked_until.get(camera_id, 0.0)
            if now < blocked_until or abs_video_path in self.processed_incident_videos:
                return

            add_incident(
                camera_id=camera_id,
                event_type="crash",
                confidence=confidence,
                video_path=rel_video_path,
                model=result.get("model", "unknown"),
                extra={"label": "Car crash detected", "timestamp": result.get("timestamp")},
            )

            self.processed_incident_videos.add(abs_video_path)
            self.crash_blocked_until[camera_id] = now + self.crash_cooldown

    def get_stats(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "inferences_run": self.inference_count,
                "rotation_interval": self.rotation_interval,
                "violence_probability": self.violence_probability,
                "violence_cooldown_s": self.violence_cooldown,
                "crash_cooldown_s": self.crash_cooldown,
                "cameras_monitored": len(self.camera_ids),
            }

    def clear_processed_video(self, video_path: str, camera_id: str | None = None):
        with self.lock:
            self.processed_incident_videos.discard(video_path)
            if camera_id:
                future_block = time.time() + self.violence_cooldown
                self.violence_blocked_until[camera_id] = future_block
                self.crash_blocked_until[camera_id] = future_block

    def clear_all_processed_videos(self):
        with self.lock:
            self.processed_incident_videos.clear()
            future_block = time.time() + self.violence_cooldown
            for cid in self.camera_ids:
                self.violence_blocked_until[cid] = future_block
                self.crash_blocked_until[cid] = future_block
                self.last_video_rotation[cid] = 0.0


_simulator: Optional[CameraSimulator] = None
_simulator_lock = threading.Lock()


def get_simulator() -> CameraSimulator:
    global _simulator

    if _simulator is None:
        with _simulator_lock:
            if _simulator is None:
                project_root = Path(__file__).resolve().parents[2]
                _simulator = CameraSimulator(
                    camera_ids=DEFAULT_CAMERAS,
                    video_dir=project_root / "Videos",
                    rotation_interval=5,
                    violence_probability=0.15,
                )

    return _simulator


def start_camera_simulator():
    simulator = get_simulator()
    if not simulator.running:
        simulator.start()


def stop_camera_simulator():
    if _simulator and _simulator.running:
        _simulator.stop()
