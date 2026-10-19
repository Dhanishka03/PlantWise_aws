# PlantWise – Requirements

## Overview
PlantWise is a conversational plant-care advisor for beginners. The user describes what they
observe — soil moisture, leaf condition, sunlight exposure — and the agent recommends the most
appropriate next action: water the plant, improve its sunlight, or inspect it further.

---

## User Stories

### US-01 – Diagnose by observation
WHEN a user describes their plant's soil moisture, leaf condition and sunlight exposure,
THE agent SHALL ask Strands Decider 2B which care action is most appropriate
BEFORE generating its recommendation.

Acceptance: the agent's reply names one of `water`, `sunlight`, or `inspect` and explains why.

### US-02 – Retrieve a care tip
WHEN the decider returns a recommended action with confidence ≥ 0.55,
THE agent SHALL call `get_plant_care_tip(action)` and include the tip in its reply,
paired with Amazon Bedrock for the conversational response.

### US-03 – Low-confidence handling
WHEN the decider's top-choice confidence is < 0.55,
THE agent SHALL ask the user one clarifying follow-up question (e.g. "Can you describe the
leaves in more detail?") and NOT recommend an action until it receives the answer.

### US-04 – Log observation
WHEN the user provides a plant name along with observations,
THE agent SHALL call `log_observation(plant_name, observations, action)` to persist a record
for future reference.

### US-05 – Retrieve care history
WHEN a user asks how their named plant has been doing or what was recommended before,
THE agent SHALL call `get_care_history(plant_name)` and summarise past observations and actions.

### US-06 – Multiple plants
WHEN a user discusses more than one plant in a session,
THE agent SHALL handle each as a separate observation and keep records per plant name.

### US-07 – Decision transparency
WHEN Strands Decider 2B returns its answer, the agent SHALL include the decision record
(action, confidence, decider_ms) in the `decisions` list of the chat response so the demo
panel can display it.

### US-08 – Amazon Bedrock
THE generative replies SHALL be produced by an Amazon Bedrock model (Amazon Nova Pro by
default), routed through the Strands Agents SDK, never via direct boto3 calls.
