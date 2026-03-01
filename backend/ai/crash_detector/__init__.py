"""Crash detection service used by the VIGIL backend."""

from __future__ import annotations

import time
from pathlib import Path

import torch
import torch.nn.functional as F
from decord import VideoReader, cpu
from torchvision.transforms.functional import to_pil_image

from backend.config import ACCIDENT_THRESHOLD
from backend.ai.crash_detector.model_architecture import MobileNetV2_LSTM
from backend.ai.crash_detector.sampling import sample_frame_indices
from backend.ai.crash_detector.transforms_setup import get_test_transform

_crash_model = None
_device = "cpu"

MODEL_PATH = Path(__file__).parent / "mobilenetv2_lstm_finetuned.pt"


def load_crash_model(device: str = "cpu"):
    """Load the crash detection model once."""
    global _crash_model, _device

    if _crash_model is not None:
        return _crash_model

    _device = device
    _crash_model = MobileNetV2_LSTM()
    state = torch.load(MODEL_PATH, map_location=device)
    _crash_model.load_state_dict(state)
    _crash_model.to(device)
    _crash_model.eval()
    return _crash_model


def detect_crash(video_path: str, num_frames: int = 16, img_size: int = 224) -> dict:
    """Run crash detection on a video clip."""
    started = time.time()

    if _crash_model is None:
        load_crash_model(_device)

    try:
        test_transform = get_test_transform(img_size)

        vr = VideoReader(video_path, ctx=cpu(0))
        total = len(vr)

        idxs = sample_frame_indices(total, num_frames)
        frames_np = vr.get_batch(idxs).asnumpy()

        frame_tensors = []
        for img in frames_np:
            pil_img = to_pil_image(img)
            frame_tensors.append(test_transform(pil_img))

        video_tensor = torch.stack(frame_tensors, dim=0).unsqueeze(0).to(_device)

        with torch.no_grad():
            out = _crash_model(video_tensor)
            probs = F.softmax(out, dim=1)[0].cpu().numpy()

        accident_prob = float(probs[1])
        normal_prob = float(probs[0])
        is_crash = accident_prob >= ACCIDENT_THRESHOLD
        confidence = accident_prob if is_crash else normal_prob

        return {
            "is_crash": is_crash,
            "event": "car_crash" if is_crash else "normal",
            "confidence": confidence,
            "normal_prob": normal_prob,
            "accident_prob": accident_prob,
            "model": "mobilenet_lstm_crash",
            "latency_ms": int((time.time() - started) * 1000),
            "timestamp": time.time(),
        }

    except Exception as exc:
        return {
            "is_crash": False,
            "event": "normal",
            "confidence": 0.0,
            "normal_prob": 1.0,
            "accident_prob": 0.0,
            "model": "mobilenet_lstm_crash",
            "latency_ms": int((time.time() - started) * 1000),
            "timestamp": time.time(),
            "error": str(exc),
        }
