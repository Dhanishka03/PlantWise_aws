"""PlantWise tools: plant care tips, observation logging and history lookup.

Each tool has a one-line docstring — the model reads it to decide whether to call it.
Data is stored in agent/data/observations.json so the demo runs anywhere without a database.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from strands import tool

# ---------------------------------------------------------------------------
# Care tips (static knowledge, beginner-friendly)
# ---------------------------------------------------------------------------

_CARE_TIPS: dict[str, str] = {
    "water": (
        "Time to water! Pour water slowly at the base of the plant until it drains from the "
        "bottom holes — this ensures the roots get a deep drink. Then wait until the top inch "
        "of soil feels dry before watering again. Avoid letting the plant sit in standing water."
    ),
    "sunlight": (
        "Your plant needs a light adjustment. Move it to a spot with brighter indirect light "
        "(near a window but not in direct harsh sun). If leaves are pale or stretching toward "
        "the light, it needs more. If tips are bleached or scorched, move it slightly further "
        "from the window. Most houseplants thrive in bright, indirect light."
    ),
    "inspect": (
        "Take a closer look at your plant. Check the undersides of leaves for tiny bugs or "
        "webbing (pests). Look at the soil surface for mold or a sour smell (overwatering). "
        "Gently tip the pot to check for dark, mushy roots (root rot). If the soil is soggy "
        "and leaves are yellow, reduce watering. If you see bugs, isolate the plant and treat "
        "with neem oil or insecticidal soap."
    ),
}


@tool
def get_plant_care_tip(action: str) -> dict[str, str]:
    """Return a beginner-friendly care tip for a recommended action: water, sunlight, or inspect."""
    action = action.lower().strip()
    tip = _CARE_TIPS.get(action)
    if tip:
        return {"action": action, "tip": tip}
    return {"action": action, "tip": "No specific tip found. Observe your plant daily and adjust care gradually."}


# ---------------------------------------------------------------------------
# Observation log (persisted to agent/data/observations.json)
# ---------------------------------------------------------------------------

_DATA_PATH = Path(__file__).parent / "data" / "observations.json"


def _load_obs() -> list[dict[str, Any]]:
    if _DATA_PATH.exists():
        try:
            return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_obs(records: list[dict[str, Any]]) -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DATA_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


@tool
def log_observation(plant_name: str, observations: str, action: str) -> dict[str, Any]:
    """Save a plant observation and recommended action to history for future reference."""
    records = _load_obs()
    entry: dict[str, Any] = {
        "plant_name": plant_name.strip(),
        "observations": observations.strip(),
        "recommended_action": action.strip(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    records.append(entry)
    _save_obs(records)
    return {"saved": True, "plant_name": plant_name, "action": action, "total_records": len(records)}


@tool
def get_care_history(plant_name: str) -> dict[str, Any]:
    """Retrieve past observations and recommended actions for a named plant."""
    records = _load_obs()
    name = plant_name.strip().lower()
    matches = [r for r in records if r.get("plant_name", "").lower() == name]
    if not matches:
        return {"plant_name": plant_name, "history": [], "message": "No history found for this plant."}
    return {"plant_name": plant_name, "history": matches[-10:], "total_entries": len(matches)}


TOOLS = [get_plant_care_tip, log_observation, get_care_history]
