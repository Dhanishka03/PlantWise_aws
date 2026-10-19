"""PlantWise: a beginner plant-care advisor.

Strands Decider 2B classifies soil/leaf/sunlight observations into a care action
(water / sunlight / inspect) before the LLM replies. When confidence is low it asks a
clarifying question instead of guessing.

    from agent.agent import HackathonAgent
    out = HackathonAgent().chat("My pothos has dry soil and drooping leaves.")
    out["reply"], out["decisions"]
"""

from __future__ import annotations

import re
import time
from typing import Any

from strands import Agent

from decider_kit import Decider
from decider_kit.llm import agent_model, default_model_id, strip_thinking

from .decision import PlantCarePolicy, PlantVerdict
from .tools import TOOLS

NAME = "PlantWise – beginner plant-care advisor"

# System prompt injected at agent construction time; the decision context is prepended at chat time.
_BASE_SYSTEM_PROMPT = """You are PlantWise, a friendly plant-care assistant for beginners.
You help users understand what their plants need based on simple observations: soil moisture,
leaf condition and sunlight exposure.

Guidelines:
- Be warm, encouraging and jargon-free.
- When the decider has recommended an action, use it as your primary recommendation and explain
  the reasoning in one or two sentences.
- When the decider says "clarify", ask ONE focused follow-up question to gather the missing detail.
- After recommending an action, always call get_plant_care_tip to fetch the practical tip.
- If the user gives a plant name, call log_observation after recommending an action.
- If the user asks about a plant's history, call get_care_history.
- Never make up plant science facts you are not certain of; say "I'm not sure, but …" if needed.
"""


def _build_system_prompt(verdict: PlantVerdict) -> str:
    """Inject the decider's verdict so the LLM knows what was decided."""
    if verdict.action == "clarify":
        decision_ctx = (
            "The decider is not confident enough to recommend an action yet "
            f"(confidence {verdict.confidence:.0%}). Ask the user one clarifying question "
            "about their plant's appearance or conditions before recommending anything."
        )
    else:
        urgency = " The situation appears urgent — mention this clearly." if verdict.urgent else ""
        decision_ctx = (
            f"The decider recommends: {verdict.action.upper()} "
            f"(confidence {verdict.confidence:.0%}).{urgency} "
            "Use this as your primary recommendation. Call get_plant_care_tip with this action."
        )
    return f"{_BASE_SYSTEM_PROMPT}\n\n[DECIDER VERDICT]\n{decision_ctx}"


def _extract_observation_fields(message: str) -> dict[str, str]:
    """Best-effort extraction of observation fields from free text."""
    moisture, leaves, sunlight, plant_name = "unknown", "unknown", "unknown", "unknown"

    # moisture
    if re.search(r"\b(dry|bone dry|parched|dusty)\b", message, re.I):
        moisture = "dry"
    elif re.search(r"\b(wet|soaked|waterlogged|soggy|drenched)\b", message, re.I):
        moisture = "wet"
    elif re.search(r"\b(moist|damp|humid)\b", message, re.I):
        moisture = "moist"

    # leaves
    if re.search(r"\bwilt(ing|ed)?\b|\bdrooping?\b|\bdroopy\b", message, re.I):
        leaves = "wilting"
    elif re.search(r"\byellow(ing|ed|s)?\b|\byellowy\b", message, re.I):
        leaves = "yellowing"
    elif re.search(r"\bbrown\s*tips?\b|\bbrowning?\b", message, re.I):
        leaves = "brown tips"
    elif re.search(r"\bdropping?\b|\bfall(ing)?\s*off\b", message, re.I):
        leaves = "dropping"
    elif re.search(r"\bhealthy\b|\bgreen\b|\bfine\b|\bgood\b", message, re.I):
        leaves = "healthy"

    # sunlight
    if re.search(r"\b(full sun|bright light|sunny|direct sun)\b", message, re.I):
        sunlight = "full sun"
    elif re.search(r"\b(partial|indirect|filtered|partly)\b", message, re.I):
        sunlight = "partial sun"
    elif re.search(r"\b(low light|dark|dim|no sun|shade|shady)\b", message, re.I):
        sunlight = "low light"

    # plant name — simple heuristic: "my <name>" or "<name> plant/leaves/soil"
    m = re.search(r"\bmy\s+([A-Za-z][a-z]+(?:\s+[a-z]+)?)\s+(?:plant|leaves|soil|has|is)\b", message, re.I)
    if m:
        plant_name = m.group(1).strip()

    return {"moisture": moisture, "leaves": leaves, "sunlight": sunlight, "plant_name": plant_name}


class HackathonAgent:
    """One Strands agent per session, with PlantCarePolicy wired in before the LLM."""

    def __init__(self, decider: Decider | None = None, model_id: str | None = None, eager: bool | None = None):
        self.decider = decider or Decider()
        self.model_id = model_id or default_model_id()
        self.policy = PlantCarePolicy(self.decider)
        self.sessions: dict[str, Agent] = {}
        # eager is accepted for API compatibility but has no effect; PlantWise never needs it
        self.eager = False

    def _get_or_create_agent(self, session_id: str, system_prompt: str) -> Agent:
        """Create a fresh single-turn agent (system prompt carries the verdict each turn)."""
        # We build a new Agent per turn so the system prompt carries the current verdict.
        # History is maintained externally via the Strands Agent's conversation_manager if needed,
        # but for simplicity each turn is stateless — the user's message is self-contained.
        return Agent(
            model=agent_model(self.model_id),
            system_prompt=system_prompt,
            tools=TOOLS,
            callback_handler=None,
        )

    def chat(self, message: str, session_id: str = "default", images: list[Any] | None = None) -> dict[str, Any]:
        """Classify the observation with the decider, then generate a reply with the LLM."""
        # 1. Extract fields and build state text for the decider
        fields = _extract_observation_fields(message)
        state = PlantCarePolicy.build_state(
            plant_name=fields["plant_name"],
            moisture=fields["moisture"],
            leaves=fields["leaves"],
            sunlight=fields["sunlight"],
            notes=message,
        )

        t0 = time.perf_counter()

        # 2. Ask Strands Decider 2B
        verdict: PlantVerdict = self.policy.evaluate(state)

        # 3. Build per-turn system prompt and call the LLM
        system_prompt = _build_system_prompt(verdict)
        agent = self._get_or_create_agent(session_id, system_prompt)
        result = agent(message)
        reply = strip_thinking(str(result))

        return {
            "reply": reply,
            "decisions": list(self.policy.log[-1:]),  # one record per turn
            "model_id": self.model_id,
            "latency_ms": round((time.perf_counter() - t0) * 1000),
            "agent": NAME,
            "eager": self.eager,
        }


if __name__ == "__main__":
    import json
    import sys

    a = HackathonAgent()
    msgs = sys.argv[1:] or [
        "My pothos has bone-dry soil and the leaves are drooping badly. It's in a low-light corner.",
        "My monstera has yellowing leaves and gets very little sunlight.",
        "My fern soil is moist but the leaves have brown tips and some are dropping.",
    ]
    for msg in msgs:
        print(json.dumps(a.chat(msg), indent=2))
