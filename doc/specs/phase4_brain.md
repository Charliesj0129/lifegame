# Feature: The Brain (Agentic Orchestration)
# As a User
# I want an intelligent "Game Master" that remembers my context and adjusts to my mood
# So that I feel "Understood" and "Hooked".

## 1. The Addiction Loop Integration

### Scenario: Contextualized Response (Memory)
**Given** the user's short-term history includes "Failed to run 5km"
**And** the Graph Memory has "User -> [HAS_GOAL] -> Marathon"
**When** the Brain receives "I'm tired"
**Then** the System Prompt must include these context bits
**And** the AI Response should reference the "Marathon" goal compassionately

### Scenario: Flow-Directed Tone (AI Director)
**Given** the FlowController outputs `FlowState(tier="E", tone="Encourage", loot_mult=2.0)`
**When** the Brain generates a response
**Then** the response narrative must be "Encouraging" (Instructions)
**And** the generated Quest must be Tier "E" (Easy)
**And** the Loot Drop probability must strictly follow the multiplier

## 2. Decision Making (Agent Plan)

### Scenario: Parsing Action Plans
**Given** the user says "I completed the pushups"
**When** the Brain thinks
**Then** it should output a structured JSON plan:
    ```json
    {
      "narrative": "Great job! Muscles are growing.",
      "stat_update": {"STR": 10, "XP": 50},
      "tool_calls": ["update_quest_status"]
    }
    ```
**And** the `UserService` should execute these updates

### Scenario: Handling Unknown Intents
**Given** the user says "What is the meaning of life?"
**When** the Brain thinks
**Then** it should detect this is "ChitChat" (Not a game action)
**And** respond with a persona-based answer
**Without** triggering Stat Updates or Loot

## 3. Latency & Fallback

### Scenario: AI Time-Out
**Given** the AI Engine takes > 5 seconds to respond
**When** the Brain is processing
**Then** it should implement a "Thinking..." signal (or use Line Loading)
**Or** fallback to a heuristic response if critical failure occurs
