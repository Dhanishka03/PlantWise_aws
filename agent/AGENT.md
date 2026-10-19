# PlantWise

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
