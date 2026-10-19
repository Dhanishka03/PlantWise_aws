# PlantWise – beginner plant-care advisor

**a beginner plant-care advisor that reads your observations and tells you exactly**

An agent on AWS that hands one decision to **Strands Decider 2B** and the conversation to **Amazon Bedrock**. Decision pattern: `#policy`. Tags: `#strands-decider-2b` `#policy`.

- Video: (add the YouTube/Vimeo link)
- Article: (add the AWS Builder Center link)
- Deployed: run `./kit deploy`

## The project

- **Pitch:** a beginner plant-care advisor that reads your observations and tells you exactly
  what your plant needs — water, better light, or a closer look.
- **Who it is for:** beginner plant owners who aren't sure when or how to act on what they see.
- **Features:**
  - describe soil moisture, leaf condition and sunlight in plain words — no plant expertise needed;
  - Strands Decider 2B classifies the situation into water / sunlight / inspect before the LLM replies;
  - beginner-friendly care tips tailored to the recommended action;
  - logs every observation so you can track a plant over time;
  - asks a clarifying question when confidence is low, instead of guessing;
  - deployed on Amazon Bedrock AgentCore Runtime.
- **The decision handed to Strands Decider 2B:** which care action fits these observations —
  water, improve sunlight, or inspect further? (`#policy`)
- **Why a decision model:** the same three-way classification runs on every message; it must be
  fast, cheap, and return a confidence the code can branch on for low-confidence handling.
- **Amazon Bedrock:** the conversational replies and tool use (Amazon Nova Pro by default).



## How it is built

Strands Agents with Amazon Bedrock for the generative part, the tools in `agent/tools.py`, deployed to Amazon Bedrock AgentCore Runtime, and one decision handed to Strands Decider 2B at a clear seam in the agent's path.

Every Amazon Bedrock model id is set in `.env` (`BEDROCK_MODEL_ID`, and `BEDROCK_SMALL/MEDIUM/LARGE_MODEL_ID` for routing), Amazon Nova by default.



## Reusable decision pattern: plant-care policy classification  (#policy)

The pattern lives in [`agent/decision.py`](agent/decision.py), labelled `REUSABLE DECISION PATTERN`. It contains the typed questions and their options, the wiring that puts the decision in the agent's path, and a note on how to reuse it:

```text
REUSABLE DECISION PATTERN: plant-care policy classification  (#policy)

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
```

Typed questions:

```python
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
```

## Measured

Decider: strands-decider-2b-hobson-v19 (ugmdu). 12 labelled cases, 24 decisions.

| | Strands Decider 2B | qwen3.5-4b |
|---|---|---|
| Accuracy | 83.3% | 86.4% |
| Latency p50 per decision | 6163 ms | 19560 ms |
| Latency p95 | 18095 ms | 43948 ms |
| Cost per 1,000 decisions | $0.0350 | $0.0000 |
| Answered alone at confidence >= 0.7 | 71% | 100% |
| Accuracy when confident | 88.2% | 86.4% |

At the median the decider was 3.2x faster than the LLM.

Reproduce with `./kit bench` (cases in `agent/eval_cases.jsonl`; charts in `submission/bench/`).

## Run it

```bash
./kit setup        # checks your machine and AWS, sets up Strands Decider 2B (local model or hosted API)
./kit demo         # web UI at http://localhost:8501
./kit bench        # the decision vs an Amazon Bedrock LLM
./kit deploy       # Amazon Bedrock AgentCore Runtime
```

Requirements: Python 3.10+, AWS credentials with Amazon Bedrock access, and for deploying, Node 20+ with the AgentCore CLI (`./kit agentcore-cli`).

## Credits

Built with the AWS User Group Madurai Strands Decider hackathon kit (https://github.com/awsugmdu). The kit's reusable library (`decider_kit/`, the demo UI, the video and article tooling, and the Kiro steering, skills and hooks) is the user group's; the agent in `agent/` is mine. Strands Decider: https://github.com/strands-labs/strands-decider (Apache-2.0).

Licence: Apache-2.0 (see LICENSE).
