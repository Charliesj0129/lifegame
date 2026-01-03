---
version: 1.0
xp_curve:
  formula: "Fast Start"
  base_xp_level_1_10: "100 * level"
  base_xp_level_11_plus: "Base * (Level ^ 2.5)"
attributes:
  STR: "Strength (Physical Power)"
  VIT: "Vitality (Health & Energy)"
  INT: "Intelligence (Logic & Output)"
  WIS: "Wisdom (Learning & Focus)"
  CHA: "Charisma (Social)"
vitals:
  EP: "Energy Points (Physical)"
  WP: "Willpower (Mental)"
currencies:
  xp: "Experience"
  gold: "Redeemable Points"
  alpha: "Rare Token"
difficulty_tiers:
  F: { name: "Trivial", multiplier: 0.5 }
  E: { name: "Easy", multiplier: 1.0 }
  D: { name: "Normal", multiplier: 2.0 }
  C: { name: "Hard", multiplier: 5.0 }
  B: { name: "Very Hard", multiplier: 10.0 }
  A: { name: "Epic", multiplier: 50.0 }
game_loop:
  daily_cap_xp: 5000
  drop_rate_base: 0.20
  photo_bonus_multiplier: 1.5
---

# Rules of the World

## 1. Core Loop
Action -> Attribute Mapping (STR/INT...) -> Validation -> XP/Gold -> Feedback

## 2. Progression System

### Attributes (The "Real Life" Stats)
Instead of generic XP, actions feed specific attributes.
1.  **STR (Strength)**: Physical power. (Gym, Pushups, Heavy labor)
2.  **VIT (Vitality)**: Health & Energy. (Sleep, Diet, Cardio, Meditation)
3.  **INT (Intelligence)**: Deep work & Logic. (Coding, Math, Engineering)
4.  **WIS (Wisdom)**: Knowledge & Awareness. (Reading, Learning, Reflection)
5.  **CHA (Charisma)**: Social & Influence. (Meetings, Dates, Speaking)

### Vitals (Daily Resource)
Actions have a **Cost**.
- **EP (Energy Points)**: Physical energy. Max = VIT * 10. Recover via Sleep/Food.
- **WP (Willpower)**: Mental focus. Max = WIS * 10. Recover via Meditation/Fun.

### Currencies
1.  **Level**: Overall character level (Sum of all Attribute levels / 5).
2.  **Gold (G)**: Redeemable for real-life rewards (O2O).
3.  **Alpha (α)**: Rare token for special unlocks.

### XP Curve (Fast Start)
Design: Levels 1-10 are fast (daily level up) to build habit. Lv 10+ is logarithmic.

| Level | Total XP | Note |
|-------|----------|------|
| 1     | 0        | Start |
| 2     | 100      | Day 1 possible |
| 5     | 1500     | ~Week 1 |
| 10    | 5500     | Milestone |

### Difficulty Classification
| Tier | Multiplier | Examples |
|------|------------|----------|
| **F** (Trivial) | 0.5x XP | Brushing teeth, drinking water |
| **E** (Easy) | 1.0x XP | 15m chores, standard routine |
| **D** (Normal) | 2.0x XP | 1 hour work, 30m gym |
| **C** (Hard) | 5.0x XP | Deep work (4hr), Heavy lift |
| **B** (Very Hard)| 10.0x XP| Complex project finish, PR Day |
| **A** (Epic) | 50.0x XP | Monthly/Quarterly Goal achieved |

## 3. Loot System (Hybrid)
**Base Drop Rate**: 20% on actions.
**Bonus**: +50% drop rate if Photo Proof provided.

### Categories
1.  **Real Rewards**: Coupons, "Cheat Day" pass, Coffee fund.
2.  **Buffs**: "Early Bird" (XP boost), "Focus Potion" (Next INT task +20% XP).

### Rarity Table
| Rarity | Chance | Color |
|--------|--------|-------|
| Common | 60%    | Gray  |
| Uncommon| 30%   | Green |
| Rare   | 8%     | Blue  |
| Epic   | 1.9%   | Purple|
| Legendary| 0.1% | Orange|

## 4. Anti-Cheese Strategy (Relaxed)
- **Honor System**: Focus on positive reinforcement.
- **AI Feedback**: If user claims "Ran 100km in 1 hour", Narrative Agent provides snarky/humorous response ("Did you attach the GPS to a cheetah?") but can still grant partial pity XP or cap it.
- **Photo Bonus**: 1.5x XP for verifying via image (later phase).
