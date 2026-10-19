# PlantWise: Teaching a Plant-Care Agent When to Act with Strands Decider 2B

By PlantWise Builder

Most beginner plant owners face the same problem: the leaves look wrong, but what does that mean? Water it? Move it closer to a window? Call a plant doctor? An LLM can talk about plants all day, but it makes confident guesses even when the observations are genuinely ambiguous. I wanted an agent that knows when it knows -- and asks a question when it does not.

PlantWise is a beginner plant-care advisor that reads your observations and classifies the situation -- water, improve sunlight, or inspect -- using Strands Decider 2B before Amazon Bedrock writes the reply. On the held-out test split, the decider answered in 6 seconds at the median compared to 20 seconds for the LLM doing the same classification, a 3.2x speedup, with calibrated confidence so the agent can ask a follow-up question instead of guessing.

## The project

PlantWise is for people who just bought their first houseplant and aren't sure what the drooping leaves are telling them. You describe what you see in plain language -- "my pothos has bone-dry soil and the leaves are drooping" -- and the agent tells you what to do and why.

Features:
- describe soil moisture, leaf condition and sunlight in plain words with no plant expertise needed;
- Strands Decider 2B classifies the situation into water / sunlight / inspect before the LLM replies;
- beginner-friendly care tips from the get_plant_care_tip tool tailored to the recommended action;
- logs every observation so you can track a plant over time with get_care_history;
- asks a clarifying question when confidence is below 0.55, instead of guessing;
- deployed on Amazon Bedrock AgentCore Runtime.

Here is a short exchange from the demo:

User: "My pothos has bone-dry soil and the leaves are drooping. It sits in a dark corner."
PlantWise: "Your pothos is thirsty. Bone-dry soil and drooping leaves are classic dehydration signs. Give it a thorough watering until water drains from the bottom, then let it dry out partially before the next watering. Moving it slightly closer to indirect light would help it recover faster too."

User: "My fern's soil is moist but some leaves have brown tips and a few are dropping."
PlantWise: "Those symptoms are a bit mixed -- moist soil rules out thirst, and the brown tips could be hard water, low humidity, or a pest starting up. I'd take a closer look at the undersides of the leaves for tiny bugs and consider a humidity tray. Can you tell me more about where the brown tips are and whether you see any sticky residue?"

The second turn shows the decider doing its job: it read moist soil plus ambiguous symptoms and chose "inspect" with enough confidence to commit, rather than prescribing water or light when neither is clearly the fix.

## How I built it

The stack is Strands Agents for the agent loop, three tools (get_plant_care_tip, log_observation, get_care_history) backed by a JSON data file, Amazon Bedrock Nova Pro for the conversational replies, and Strands Decider 2B running on the AWS User Group Madurai hosted API for the policy classification. The agent is deployed on Amazon Bedrock AgentCore Runtime.

Strands Decider 2B sits between the user message and the LLM. Before the Strands Agent runs, PlantCarePolicy.evaluate() extracts observation fields from the message (soil moisture, leaf condition, sunlight), builds a state block, and calls the decider. The verdict is injected into the system prompt so Nova Pro knows what was decided and can explain it naturally.

I used the AWS User Group Madurai Strands Decider hackathon kit and Kiro (spec-driven build) to scaffold the agent, decision pattern, eval cases, benchmark and deployment in a single session.

< FIGURE 1 of 5: upload submission/article/img/architecture.png here >
Alt text: Architecture: the user, the agent with its tools and decision, Amazon Bedrock and Strands Decider 2B

## The decision I handed to Strands Decider 2B

Every message to PlantWise carries the same three-way classification problem: given what the user sees, is this a watering problem, a light problem, or something that needs investigation? That runs on every single turn, so it needs to be fast and cheap. And critically, I need a calibrated confidence number -- not just an answer, but a measure of how sure the model is -- so the agent can fall back to a clarifying question instead of prescribing the wrong fix.

An LLM does this in about 20 seconds and costs per token. The decider does it in one forward pass, returns probabilities for each option, and costs $0.035 per 1,000 decisions.

```python
QUESTIONS = {
    "care_action": Decider.choice(
        "What is the most appropriate next care step given these plant observations?",
        {
            "water":    "the soil is dry or the plant shows dehydration signs such as wilting, drooping, or dry crispy leaf tips -- watering is clearly the fix",
            "sunlight": "the plant is in a low-light spot or getting too much direct sun, shown by yellowing leaves, leggy pale etiolated growth, leaf drop in dark conditions, or sun-scorched patches -- moving it to better light is the fix",
            "inspect":  "the soil moisture and light are both adequate but symptoms persist, or signs point to pests, disease, root rot, nutrient deficiency, or overwatering -- investigation is needed before acting",
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

The wiring is a single call before the Strands Agent runs:

```python
verdict = self.policy.evaluate(state)
# verdict.action: "water" | "sunlight" | "inspect" | "clarify"
# verdict.confidence: 0..1
# verdict.urgent: bool
```

If action is "clarify" (confidence below 0.55), the system prompt tells Nova Pro to ask one focused question instead of recommending anything. If urgent is True, the system prompt flags it so the reply mentions urgency. Otherwise the verdict is injected as the primary recommendation and Nova Pro explains it in beginner-friendly terms.

## Measured

I tuned the question descriptions on 12 cases and measured on a held-out 12-case test split. The decider was compared to the same hosted qwen3.5-4b LLM answering the same typed questions through a Strands Agent with structured output. Both ran on the AWS User Group Madurai hosted API.

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

The honest weak spots: the decider's overall accuracy (83.3%) is slightly below the LLM (86.4%) because the "sunlight vs inspect" distinction is hard when the only signal is low light plus a symptom that could go either way, like brown tips on a cactus. One case still falls below the 0.55 confidence threshold on the test split and triggers the clarify path instead. That is the right behavior -- when the model is not sure, asking the user is better than guessing.

The cost comparison here favors the LLM because qwen3.5-4b on the hosted API is free for hackathon participants, while the hosted decider API charges $0.035 per 1,000 decisions. With a real Bedrock LLM (Nova Pro at roughly $0.80 per 1M input tokens), the decider wins on cost too -- a 100-token classification through Nova Pro costs about $0.08 per 1,000 calls, more than twice the decider's rate.

< FIGURE 2 of 5: upload submission/article/img/bench-accuracy.png here >
Alt text: Accuracy of Strands Decider 2B and the Bedrock LLM on the labelled cases

< FIGURE 3 of 5: upload submission/article/img/bench-latency.png here >
Alt text: Median latency per decision for both

< FIGURE 4 of 5: upload submission/article/img/bench-cost.png here >
Alt text: Cost per 1,000 decisions for both

< FIGURE 5 of 5: upload submission/article/img/bench-confidence.png here >
Alt text: Accuracy against the share of decisions answered without a human, as the confidence threshold moves

## The reusable decision pattern

The pattern lives in agent/decision.py and is tagged #policy. It is a three-way classification with an urgency flag and a low-confidence fallback. To reuse it:

1. Copy agent/decision.py into your project.
2. Replace the three options in QUESTIONS["care_action"] with your own categories, each with a one-line description of what that option means.
3. Adjust CONFIDENCE_THRESHOLD (default 0.55) for your domain's tolerance -- lower if you want the agent to commit more often, higher if you want it to ask more questions.
4. Call PlantCarePolicy (or rename it) from your agent before the LLM runs, and inject the verdict into the system prompt.

The pattern works for any domain where you need to route a natural-language input to one of a small number of actions before generating a response -- customer support triage, medical symptom routing, content moderation -- anywhere the classification needs to be fast, cheap and honest about uncertainty.

## What I learned and what is next

The biggest learning was that question descriptions carry most of the signal. The first version of the sunlight option just said "yellowing leaves or leggy growth" -- the decider kept confusing it with inspect on cases where moist soil made watering clearly wrong. Adding "the plant is in a low-light spot" to the description lifted sunlight accuracy from 67% to 92% on the tune split.

The confidence threshold also took some tuning. At 0.7 the agent asked a clarifying question on 29% of turns, which felt excessive. At 0.55 it clarifies on about 10-15% of turns, which matches what I'd want from a human plant advisor.

Next steps would be adding image support -- Strands Decider 2B can read photos -- so users can send a picture of the drooping leaf and get a decision grounded in what they see, not just what they type.

---

Code: https://github.com/PLACEHOLDER/plantwise (update after ./kit publish) . Video: https://youtube.com/PLACEHOLDER (update after upload) . Tags: #strands-decider-2b #policy

Built with the AWS User Group Madurai Strands Decider hackathon kit
