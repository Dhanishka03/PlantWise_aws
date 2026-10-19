"""REUSABLE DECISION PATTERN: plant-care policy classification  (#policy)

What it does
    Before the plant-care agent recommends an action, Strands Decider 2B reads the user's
    natural-language observations (soil moisture, leaf condition, sunlight) and classifies the
    situation into one of three care actions:
      - water:    dry soil or dehydration signs
      - sunlight: light-related symptoms (yellowing, leggy growth, scorch)
      - inspect:  ambiguous, mixed, or non-light/water problems

    It also checks whether the situation is urgent (severe wilting, rapid leaf drop).

    When confidence is below 0.55, the wiring returns a special "clarify" verdict so the
    agent asks a follow-up question rather than guessing.

Typed questions and options
    care_action (choice):
      water    – dry soil or dehydration signs (wilting, dry crispy tips)
      sunlight – light-related symptoms (yellowing, leggy growth, sun-scorch)
      inspect  – ambiguous, mixed, or non-light/water problems
    urgent (noul):
      true  – severe distress that needs attention today
      false – mild or gradual symptoms

Wiring
    `PlantCarePolicy` is called in `HackathonAgent.chat()` before the Strands Agent runs:

        verdict = self.policy.evaluate(observation_text)
        # verdict has .action ("water"|"sunlight"|"inspect"|"clarify"),
        #              .confidence, .urgent, .decider_ms

    The verdict is injected into the system prompt context so the LLM knows what the decider
    decided. The log record is appended to `decisions` in the chat response.

How to reuse it
    Copy this file, replace the three care actions in QUESTIONS["care_action"] with your own
    categories (each with a one-line description), and adjust the 0.55 threshold in
    PlantCarePolicy.evaluate() for your domain's tolerance for uncertainty.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from decider_kit import Decider
from decider_kit.client import DeciderError

PATTERN_TAG = "#policy"

QUESTIONS = {
    "care_action": Decider.choice(
        "What is the most appropriate next care step given these plant observations?",
        {
            "water":    "the soil is dry or the plant shows dehydration signs such as wilting, drooping, or dry crispy leaf tips — watering is clearly the fix",
            "sunlight": "the plant is in a low-light spot or getting too much direct sun, shown by yellowing leaves, leggy pale etiolated growth, leaf drop in dark conditions, or sun-scorched patches — moving it to better light is the fix",
            "inspect":  "the soil moisture and light are both adequate but symptoms persist, or signs point to pests, disease, root rot, nutrient deficiency, or overwatering — investigation is needed before acting",
        }
    ),
    "urgent": Decider.noul(
        "Does the plant show urgent distress that needs attention today?",
        {
            "true":  "severe wilting, rapid leaf drop, or extensive browning that will worsen within a day",
            "false": "mild or gradual symptoms that can wait a few days",
        }
    ),
}

CONFIDENCE_THRESHOLD = 0.55  # below this: ask the user for more detail


@dataclass
class PlantVerdict:
    action: str          # "water" | "sunlight" | "inspect" | "clarify"
    confidence: float
    urgent: bool
    p_urgent: float
    decider_ms: int
    raw: dict[str, Any]


class PlantCarePolicy:
    """Evaluate a plant observation and decide the care action using Strands Decider 2B."""

    def __init__(self, decider: Decider):
        self.decider = decider
        self.log: list[dict[str, Any]] = []

    def evaluate(self, observation_text: str, retries: int = 3) -> PlantVerdict:
        """Run the decision. Returns a PlantVerdict; appends one record to self.log.

        Retries up to `retries` times on transient 503 errors (server busy) with
        exponential backoff (2 s, 4 s, 8 s).
        """
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                a = self.decider.ask(observation_text, QUESTIONS)
                break
            except DeciderError as e:
                if "503" in str(e) and attempt < retries - 1:
                    last_err = e
                    time.sleep(2 ** (attempt + 1))  # 2, 4, 8 s
                else:
                    raise
        else:
            raise last_err  # type: ignore[misc]
        action_ans = a["care_action"]
        urgent_ans = a["urgent"]

        action = action_ans.label or "inspect"
        confidence = action_ans.confidence or 0.0
        p_urgent = urgent_ans.p_yes or 0.0

        if confidence < CONFIDENCE_THRESHOLD:
            action = "clarify"

        rec: dict[str, Any] = {
            "pattern": PATTERN_TAG,
            "action": action,
            "confidence": round(confidence, 3),
            "urgent": p_urgent >= 0.65,
            "p_urgent": round(p_urgent, 3),
            "decider_ms": round(self.decider.last_latency_ms or 0),
            # per-option probabilities for the demo panel
            "probabilities": {opt: round(action_ans.probs.get(opt, 0.0), 3) for opt in ("water", "sunlight", "inspect")}
            if hasattr(action_ans, "probs") and action_ans.probs else {},
            "verdict": action,
        }
        self.log.append(rec)
        return PlantVerdict(
            action=action,
            confidence=confidence,
            urgent=rec["urgent"],
            p_urgent=p_urgent,
            decider_ms=rec["decider_ms"],
            raw=rec,
        )

    @staticmethod
    def build_state(plant_name: str, moisture: str, leaves: str, sunlight: str, notes: str) -> str:
        """Build the state text the decider reads. Use the same layout in eval_cases.jsonl."""
        return (
            "--- PLANT OBSERVATION ---\n"
            f"Plant name: {plant_name or 'unknown'}\n"
            f"Soil moisture: {moisture or 'unknown'}\n"
            f"Leaf condition: {leaves or 'unknown'}\n"
            f"Sunlight exposure: {sunlight or 'unknown'}\n"
            f"Additional notes: {notes or 'none'}"
        )
