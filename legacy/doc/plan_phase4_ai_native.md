# 🧠 Phase 4: The Awakening (AI-Native Architecture)

> **Vision**: Shift from "Code-Logic calling AI" to "AI-Agent calling Code-Tools". The System becomes strictly an executor of the AI's will.

## 1. Problem Statement
**Current State**: The bot relies on rigid keywords (`Status`, `Inventory`). If the user types "Show me stats" or "Check bag", the system fails or treats it as a generic log. This feels "dumb" and unresponsive.
**Goal**: Implement an **Intent-Based Router**. The AI receives *all* input, decides the intent, and triggers the appropriate System Tool (Function Calling).

---

## 2. BDD Specifications (Behavior-Driven Development)

### 🏷️ Feature: Natural Language Routing (The Brain)
*As a user, I want to speak naturally to my LifeOS so that I don't have to memorize command keywords.*

**Scenario: User requests status with natural language**
`Given` the user is authenticated
`When` the user sends "How strong am I right now?" or "Show my dashboard"
`Then` the AI Analyzer detects the intent `CMD_SHOW_STATUS`
`And` the system renders the `Status Flex Message`
`And` the AI attaches a contextual comment (e.g., "Looking strong, Samurai.")

**Scenario: User performs compound actions**
`Given` the user has a "Small Potion" in inventory
`When` the user sends "I'm tired, drinking a potion and going to sleep"
`Then` the AI identifies two distinct intents:
    1. `CMD_USE_ITEM(item="potion")`
    2. `LOG_ACTION(text="going to sleep")`
`And` the system executes `inventory_service.use_item` first
`And` the system processes the sleep action for XP recovery second

### 🔍 Feature: Contextual Awareness (Short-Term Memory)
*As a user, I want the bot to remember what we just talked about.*

**Scenario: Follow-up question**
`Given` the user just logged "Ran 5km"
`And` the AI replied "Great run! (VIT +10)"
`When` the user asks "How many more do I need for the next level?"
`Then` the AI understands "more" refers to XP for the *User Level*
`And` the system queries `user_service.get_xp_to_next_level`
`And` the AI replies "You need 450 XP for Level 6."

### 🎭 Feature: Dynamic Persona Switching
*As a user, I want different characters to reply based on the situation.*

**Scenario: Viper Interruption (The Rival)**
`Given` the user has been inactive for 3 days
`When` the user finally types "I'm back"
`Then` the AI defaults not to the "System" persona, but to the **"Viper"** persona
`And` the response is aggressive: "Look who decided to show up. I already took 15% of your gold."
`And` the system logs the Rival Interaction.

---

## 3. Technical Architecture (The "Cortex")

### A. The Intent Router (Prompt Architecture)
We will inject precise system state into the `System Prompt` to ground the AI.

**System Prompt Structure:**
```text
Role: LifeOS Gamification Manager (Cyberpunk 2077 Vibe)
Current User State:
- Level: {user.level}
- Inventory: {user.inventory_list}
- Rival Status: {rival.status} (Active/Dormant)

Available Tools:
1. get_status()
2. use_item(item_name: str)
3. log_action(description: str)
4. set_goal(goal_text: str)
5. query_knowledge_base(query: str) // For "How do I play?"

Instructions:
- Analyze user input.
- Return JSON strictly matching the Tool Call Schema.
- If no tool matches, default to `log_action` or `query_knowledge_base`.
```

### B. Tool Call Schema (Structured Output)
The AI must return machine-parsable JSON.

```json
{
  "thought": "User wants to use an item but didn't specify which one, but context implies 'Health Potion'.",
  "tool_calls": [
    {
      "function": "use_item",
      "arguments": {
        "item_name": "Health Potion"
      }
    }
  ],
  "response_voice": "Mentoring" // or "System", "Rival"
}
```

### C. State Injection (The Context Window)
To minimize token costs while maximizing context, we will inject a "Sliding Window" of the last 3 turns + "Current State Snapshot".

1.  **Fetch User State**: DB call to get Profile, Inventory, Quest Status.
2.  **Fetch History**: Redis/DB call to get last 3 interactions.
3.  **Construct Prompt**: Merge State + History + User Input.
4.  **LLM Inference**: Call Gemini/OpenAI.
5.  **Execute Tool**: Parse JSON -> Run Python Function.
6.  **Final Response**: Send Flex Message or Text.

---

## 4. Implementation Steps

1.  **Refactor `webhook.py`**: Remove hardcoded `if/else` command blocks.
2.  **Create `AIService.router()`**: The new brain.
    -   Implement `assess_intent(text, state)` -> returns JSON.
3.  **Create `ToolRegistry`**: A mapper for `str_name -> python_function`.
4.  **Migrate Logic**:
    -   Move "Status" rendering to `tools.show_status`.
    -   Move "Inventory" rendering to `tools.show_inventory`.
5.  **Test**: Verify "Show me inventory" works as well as "Inventory".

## 5. Success Metrics
-   **Command Failure Rate**: < 1% (User intent misunderstood).
-   **Latency**: Router decision < 2s.
-   **Engagement**: Users perform deeper actions (e.g., specific item usage) due to natural language ease.
