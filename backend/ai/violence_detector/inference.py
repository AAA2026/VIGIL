"""TorchScript violence inference for the V6 model bundle."""

from __future__ import annotations

__all__ = ["run_inference"]

import json
import os
import time
from pathlib import Path
from typing import Dict, Iterable

import cv2
import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = PROJECT_ROOT / "backend" / "models"

DEFAULT_MODEL_PATH = MODEL_DIR / "violence_detector_v6_ts.pt"
DEFAULT_CONFIG_PATH = MODEL_DIR / "violence_detector_v6_config.json"
DEFAULT_THRESHOLD = 0.315
DEFAULT_PROFILE = "balanced"

# CPU default keeps backend stable on Windows dev machines.
DEVICE = torch.device(os.getenv("VIOLENCE_DEVICE", "cpu"))

_MODEL_CACHE: Dict[str, torch.jit.ScriptModule] = {}
_CONFIG_CACHE: Dict[str, Dict] = {}


def _resolve_model_name(model_name: str) -> str:
    normalized = (model_name or "").strip().lower()
    aliases = {
        "mobilenet": "v6",
        "mobilenet_clip": "v6",
        "v6": "v6",
        "violence_v6": "v6",
        "x3d": "v6",  # Keep compatibility with old callers.
    }
    if normalized not in aliases:
        raise ValueError(f"Unknown model: {model_name}")
    return aliases[normalized]


def _load_json(path: Path) -> Dict:
    key = str(path.resolve())
    if key not in _CONFIG_CACHE:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _CONFIG_CACHE[key] = json.load(f)
        else:
            _CONFIG_CACHE[key] = {}
    return _CONFIG_CACHE[key]


def _model_paths() -> tuple[Path, Path]:
    model_path = Path(os.getenv("VIOLENCE_MODEL_TS", str(DEFAULT_MODEL_PATH)))
    config_path = Path(os.getenv("VIOLENCE_EXPORT_CONFIG", str(DEFAULT_CONFIG_PATH)))
    return model_path, config_path


def _load_model(model_name: str) -> torch.jit.ScriptModule:
    canonical = _resolve_model_name(model_name)
    if canonical in _MODEL_CACHE:
        return _MODEL_CACHE[canonical]

    model_path, _ = _model_paths()
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = torch.jit.load(str(model_path), map_location=DEVICE)
    model.eval()
    _MODEL_CACHE[canonical] = model
    return model


def _sample_indices(total_frames: int, clip_len: int) -> np.ndarray:
    if total_frames <= 0:
        return np.zeros(clip_len, dtype=int)
    if total_frames == 1:
        return np.zeros(clip_len, dtype=int)
    return np.linspace(0, total_frames - 1, clip_len, dtype=int)


def _extract_frames(video_path: str, clip_len: int, frame_size: int) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = _sample_indices(total_frames, clip_len)

    frames: list[np.ndarray] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (frame_size, frame_size), interpolation=cv2.INTER_LINEAR)
        frames.append(frame)

    cap.release()

    if not frames:
        raise ValueError(f"No frames extracted from {video_path}")

    # Pad using the last valid frame to match required clip length.
    while len(frames) < clip_len:
        frames.append(frames[-1].copy())

    return np.stack(frames[:clip_len], axis=0)


def _preprocess(frames: np.ndarray) -> torch.Tensor:
    # Input expected: [1, T, C, H, W]
    tensor = frames.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    tensor = (tensor - mean) / std
    tensor = np.transpose(tensor, (0, 3, 1, 2))  # T, C, H, W
    tensor = np.expand_dims(tensor, axis=0)  # 1, T, C, H, W
    return torch.from_numpy(tensor).to(DEVICE)


def _iter_tensors(payload: object) -> Iterable[torch.Tensor]:
    if torch.is_tensor(payload):
        yield payload
    elif isinstance(payload, dict):
        for value in payload.values():
            yield from _iter_tensors(value)
    elif isinstance(payload, (list, tuple)):
        for value in payload:
            yield from _iter_tensors(value)


def _to_probability(value: float) -> float:
    if 0.0 <= value <= 1.0:
        return float(value)
    # Interpret as logit.
    return float(torch.sigmoid(torch.tensor(value)).item())


def _extract_violence_probability(raw_output: object) -> float:
    tensor = next(iter(_iter_tensors(raw_output)), None)
    if tensor is None:
        raise RuntimeError("Model output did not contain a tensor")

    data = tensor.detach().float().cpu()

    if data.shape and data.shape[-1] == 2:
        # Binary logits/probs where index 1 is violence.
        probs = torch.softmax(data, dim=-1)[..., 1]
        return float(probs.mean().item())

    if data.shape and data.shape[-1] == 1:
        return _to_probability(float(data.mean().item()))

    if data.numel() == 1:
        return _to_probability(float(data.item()))

    # Fallback: mean of all outputs treated as a logit/probability scalar.
    return _to_probability(float(data.mean().item()))


def _threshold_from_config(config: Dict) -> float:
    profile = os.getenv("TH_PROFILE", DEFAULT_PROFILE)
    profiles = config.get("threshold_profiles", {}) if isinstance(config, dict) else {}
    if isinstance(profiles, dict) and profile in profiles:
        return float(profiles[profile])
    if "deploy_threshold" in config:
        return float(config["deploy_threshold"])
    return DEFAULT_THRESHOLD


def run_inference(video_path: str, model_name: str = "mobilenet") -> Dict:
    """Run violence detection inference for a single video clip."""
    started = time.time()
    model_path, config_path = _model_paths()
    config = _load_json(config_path)
    clip_len = int(config.get("clip_len", 12))
    frame_size = int(config.get("frame_size", 160))
    threshold = _threshold_from_config(config)

    try:
        frames = _extract_frames(video_path, clip_len=clip_len, frame_size=frame_size)
        inputs = _preprocess(frames)
        model = _load_model(model_name)

        with torch.no_grad():
            raw_output = model(inputs)

        violence_prob = _extract_violence_probability(raw_output)
        event = "violence" if violence_prob >= threshold else "normal"
        confidence = violence_prob if event == "violence" else (1.0 - violence_prob)

        return {
            "event": event,
            "confidence": round(float(confidence), 3),
            "score": round(float(violence_prob), 3),
            "threshold": round(float(threshold), 3),
            "model": f"violence_v6_ts:{model_path.name}",
            "latency_ms": int((time.time() - started) * 1000),
            "timestamp": time.time(),
        }
    except Exception as exc:
        return {
            "event": "error",
            "confidence": 0.0,
            "score": 0.0,
            "threshold": round(float(threshold), 3),
            "model": f"violence_v6_ts:{model_path.name}",
            "latency_ms": int((time.time() - started) * 1000),
            "timestamp": time.time(),
            "error": str(exc),
        }


if __name__ == "__main__":
    test_video = "demo.mp4"
    if Path(test_video).exists():
        print(run_inference(test_video))
    else:
        print(f"Test video not found: {test_video}")
