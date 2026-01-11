# Feature: Flow Control & Behavior Engineering
# As a System Architect
# I want to dynamically adjust difficulty and prompts
# So that the user remains in the "Flow Channel" and forms habits.

## 1. PID Controller (Dynamic Difficulty Adjustment)

### Scenario: User is Frustrated (Too Hard)
**Given** the user's current difficulty tier is "A" (Hard)
**And** the user has Failed the last 3 quests
**When** the FlowController calculates the next difficulty
**Then** the output tier should be "B" or "C" (Lower)
**And** the PID Error term should be negative

### Scenario: User is Bored (Too Easy) 
**Given** the user's current difficulty tier is "C"
**And** the user has Completed the last 5 quests within 10 minutes
**When** the FlowController calculates the next difficulty
**Then** the output tier should be "B" (Higher)
**And** the PID Error term should be positive

### Scenario: Flow State Maintenance (Perfect Match)
**Given** the user has a 50% win rate (Balanced)
**When** the FlowController calculates the next difficulty
**Then** the output tier should remain unchanged
**And** the PID Integral term should be stable

## 2. Fogg Behavior Model ($B=MAP$)

### Scenario: Low Motivation, High Friction (No Behavior)
**Given** the time is "03:00 AM" (Low Motivation Context)
**And** the proposed task is "Run 5km" (High Friction)
**When** the Fogg Calculator evaluates Trigger Probability
**Then** the result should be FALSE (Below Action Line)

### Scenario: High Motivation, Spark Trigger
**Given** the user just leveled up (High Motivation)
**And** the proposed task is "Claim Reward" (Low Friction)
**When** the Fogg Calculator evaluates Trigger Probability
**Then** the result should be TRUE
**And** the system should send a Prompt immediately

## 3. EOMM (Engagement Optimized Matchmaking)

### Scenario: High Churn Risk (Save the User)
**Given** the User State `churn_risk` is "HIGH"
**When** the FlowController generates a Quest
**Then** the Quest Difficulty should be forced to "E" (Easiest)
**And** the Loot Probability should be boosted (Pity Timer active)

## 4. Multi-Objective Recommendation (Contextual Bandits)

### Scenario: Diversity Enforcement (DPP)
**Given** the user's last 3 quests were "STR" (Strength) related
**When** the Brain generates a new quest list
**Then** the list must include at least one non-STR tag (e.g., "INT" or "VIT")
**And** the diversity penalty for "STR" should be high

### Scenario: Exploration vs Exploitation
**Given** the user has a high completion rate for "Code" tasks (Exploit)
**But** the system has not suggested "Meditation" in 7 days (Explore)
**When** ranking potential tasks
**Then** "Meditation" should receive an "Exploration Boost" to appear in the top 3

## 5. Notification Scheduling (RL)

### Scenario: Optimal Prompt Timing
**Given** the user's historical active time is 08:00-09:00 (High Prob)
**And** current time is 08:30
**When** the Fogg Calculator checks `P` (Prompt)
**Then** the Trigger Score should be maximized
**And** a notification should be scheduled immediately

## 6. RPE (Reward Prediction Error)

### Scenario: Unexpected Reward (Positive RPE)
**Given** the user expects a standard "C-Tier" reward (Value ~ 10)
**When** the LootService rolls a "S-Tier" item (Value ~ 100)
**Then** the `RPE` (100 - 10) is Positive High
**And** the generic narrative should emphasize "Surprise" and "Luck"

### Scenario: Boring Reward (Zero RPE)
**Given** the user always gets 10 Gold for this task
**When** the user completes it again and gets 10 Gold
**Then** `RPE` is Zero
**And** the system should flag this loop as "Habituation Risk" (Needs Variance)

## 7. Stress Pacing (The "AI Director")

### Scenario: Forced Relaxation (Sine Wave)
**Given** the user has been in "High Intensity" (Tier A quests) for 30 minutes
**And** the "Stress Accumulator" is above 80%
**When** the FlowController plans the next batch
**Then** it must force a "Relax Phase" (Tier D quests or downtime)
**Even if** the user's performance is perfect (Prevent Exhaustion/Numbness)

## 8. Hyperbolic Discounting (Immediate Gratification)

### Scenario: Instant Feedback Latency
**Given** the user inputs a "Complete" action
**When** the system processes the reward
**Then** a "Visceral Signal" (Sound/Animation trigger) must be sent within 200ms
**Before** the expensive LLM narrative is generated (Optimization of $D \to 0$)

## 9. Hook Investment Loop

### Scenario: Investment Increases Trigger Relevance
**Given** the user has invested effort (Defined 10 customized habits)
**When** the system constructs a Prompt ($P$)
**Then** the Prompt must reference specific user-defined terms (High Context)
**And** the "Cognitive Load" estimate should be lowered (increasing $A$)
