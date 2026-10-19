0. PlantWise is a beginner plant-care advisor. The user describes what they observe, and Strands Decider decides — water, sunlight, or inspect — before Amazon Bedrock writes the reply.

1. Describe what you see and PlantWise tells you what your plant needs — water, better light, or a closer look. What it does: Plain-language observations — no plant expertise needed. Strands Decider 2B classifies the situation before the LLM replies. Beginner-friendly care tips for every recommended action. Asks a clarifying question when confidence is low, instead of guessing.

2. Dry soil plus wilting — the decider should pick water with high confidence. The decider scored confidence 0.88, p urgent 0.39, so the verdict was water, in 3.8 seconds.

3. Yellowing with low light — the decider should pick sunlight. The decider scored confidence 0.82, p urgent 0.13, so the verdict was sunlight, in 4.1 seconds.

4. Mixed signals — the decider should pick inspect, or ask for more detail if uncertain. The decider scored confidence 0.87, p urgent 0.17, so the verdict was inspect, in 2.9 seconds.

5. The agent retrieves the care history logged from the first turn. The decider scored confidence 0.69, p urgent 0.22, so the verdict was inspect, in 2.8 seconds.

6. On 24 labelled decisions, with the decider on the AWS User Group Madurai hosted API, Strands Decider was 83% accurate at a median of 6163 milliseconds, against 86% and 19560 milliseconds for a hosted open LLM asked the same questions.

7. One forward pass per observation. Typed answers with calibrated confidence. Amazon Bedrock for the conversation. PlantWise — built with the AWS User Group Madurai Strands Decider hackathon kit.