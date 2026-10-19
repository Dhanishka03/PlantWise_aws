# PlantWise – Design

## Pattern tag
`#policy`

## Decision seam
The decision runs **before the agent recommends an action**. In `agent.py`, `chat()` calls
`PlantCarePolicy.evaluate(observation_text)` and adds the result to the `decisions` list before
building the Strands Agent. The result (verdict + confidence) is injected into the system prompt
context so the LLM knows what the decider said.

---

## State text layout

```
--- PLANT OBSERVATION ---
Plant name: {plant_name or "unknown"}
Soil moisture: {dry | moist | wet | unknown}
Leaf condition: {healthy | yellowing | wilting | brown tips | dropping | unknown}
Sunlight exposure: {full sun | partial sun | low light | unknown}
Additional notes: {any extra text the user provided}
```

The state is built from whatever the user typed; fields default to "unknown" when not mentioned.

---

## Typed questions

```python
QUESTIONS = {
    "care_action": Decider.choice(
        "What is the most appropriate next care step given these observations?",
        {
            "water":    "the soil is dry or the plant shows signs of dehydration such as wilting or dry, crispy leaf tips",
            "sunlight": "the plant is getting too little or too much light, shown by yellowing, leggy growth, or sun-scorch",
            "inspect":  "the signs are ambiguous, mixed, or suggest a non-watering/light problem such as pests, disease, root issues, or overwatering",
        }
    ),
    "urgent": Decider.noul(
        "Does the plant show urgent distress that needs attention today?",
        {
            "true":  "severe wilting, rapid leaf drop, or extensive browning that will worsen within a day",
            "false": "mild or gradual symptoms that can be addressed in the next few days",
        }
    ),
}
```

---

## Thresholds and actions

| Condition | Action |
|---|---|
| `care_action.confidence >= 0.55` | Recommend the top action, call `get_plant_care_tip` |
| `care_action.confidence < 0.55`  | Ask one clarifying follow-up, do NOT recommend |
| `urgent.p_yes >= 0.65`           | Prefix the reply with an urgency note |

---

## Tools

| Tool | Purpose |
|---|---|
| `get_plant_care_tip(action)` | Returns a beginner-friendly care tip for water / sunlight / inspect |
| `log_observation(plant_name, observations, action)` | Saves observation + recommended action to `agent/data/observations.json` |
| `get_care_history(plant_name)` | Returns past observations and actions for a named plant |

---

## Eval-case plan

At least 24 cases covering:
- Clear `water` signal: dry soil + wilting (× 4 tune, × 4 test)
- Clear `sunlight` signal: yellowing + low light (× 3 tune, × 3 test)
- Clear `inspect` signal: mixed / ambiguous observations (× 3 tune, × 3 test)
- Low-confidence near-misses: moist soil + mild yellowing (× 2 tune, × 2 test)
- `urgent=yes`: severe wilting (× 2 test)
- `urgent=no`: gradual symptoms (× 2 tune)

Split: ~12 tune, ~12 test.

---

## AgentCore features
Neither Memory nor Gateway is enabled for this agent. Runtime alone is used.
