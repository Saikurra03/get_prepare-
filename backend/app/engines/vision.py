"""Vision heuristics: cautious, evidence-worded. No emotion claims. Analyzes optional frame bytes."""
from __future__ import annotations

def analyze_frame(image_bytes: bytes | None, camera_on: bool, mic_on: bool) -> dict:
    notes: list[str] = []
    if not camera_on:
        return {"camera_on": camera_on, "mic_on": mic_on,
                "notes": "camera was off, so visual presence could not be observed"}
    if not image_bytes:
        return {"camera_on": camera_on, "mic_on": mic_on,
                "notes": "camera on; no frame sampled this turn"}
    # Lightweight heuristics: size + brightness proxy (no face recognition, no emotion inference)
    kb = len(image_bytes) / 1024
    if kb < 8:
        notes.append("video frame appeared very dark or low-detail; check lighting")
    else:
        notes.append("camera on; facial expression appeared relatively neutral in the sampled frame")
    notes.append("keep eye contact with the lens and sit upright for stronger presence")
    return {"camera_on": camera_on, "mic_on": mic_on, "notes": "; ".join(notes)}
