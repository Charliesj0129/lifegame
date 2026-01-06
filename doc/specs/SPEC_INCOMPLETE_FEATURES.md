# 🧪 BDD Specifications: Incomplete Features

> 本文件涵蓋所有部分完成或尚未實作的功能規格，採用 Gherkin 風格撰寫。

---

## 1. 驗證系統補完 (Verification System Enhancements)

### 🏷️ Feature: Multi-Modal Verification Consistency
*As a user, I want all verification types (text/image/GPS) to behave consistently so that I understand the feedback loop.*

**Scenario: Text verification returns structured result**
```gherkin
Given a quest with verification_type = "text"
And the quest has keywords = ["跑步", "5公里"]
When the user sends "今天跑了 5 公里"
Then the system returns verdict = "APPROVED"
And the response includes:
  | field        | value                    |
  | xp_awarded   | 50                       |
  | gold_awarded | 10                       |
  | message      | "✅ 任務驗證通過！"        |
```

**Scenario: Image verification returns structured result**
```gherkin
Given a quest with verification_type = "image"
And the quest description = "拍照證明你在健身房"
When the user sends an image of a gym
Then the AI Vision API analyzes the image
And the system returns verdict = "APPROVED" | "REJECTED" | "UNCERTAIN"
And the response follows the same template as text verification
```

**Scenario: GPS verification returns structured result**
```gherkin
Given a quest with verification_type = "location"
And the quest has target_lat = 25.0330, target_lng = 121.5654, radius_m = 100
When the user sends a location message at (25.0331, 121.5655)
Then the system calculates haversine distance
And if distance <= 100m, verdict = "APPROVED"
And the response follows the same template as text verification
```

**Scenario: Unified error handling for verification failures**
```gherkin
Given any verification type
When the verification fails (verdict = "REJECTED")
Then the system responds with:
  | field   | value                              |
  | message | "❌ 驗證失敗：{reason}"             |
  | hint    | "💡 {AI-generated suggestion}"     |
And no XP/Gold is awarded
And the quest status remains ACTIVE
```

---

## 2. DDA 排程推播系統 (DDA Scheduler System)

### 🏷️ Feature: Scheduled Quest Push Notifications
*As a user, I want to receive quest reminders at optimal times so that I stay engaged without manual polling.*

**Scenario: Morning push at 08:00**
```gherkin
Given a registered user with timezone = "Asia/Taipei"
And it is 08:00 local time
When the scheduler triggers "Morning" batch
Then quest_service.trigger_push_quests(user_id, "Morning") is called
And the user receives a Flex Message with:
  | section          | content                        |
  | header           | "🌅 早安任務"                   |
  | quest_count      | <= 3                           |
  | dda_hint         | (optional) tier adjustment msg |
And the message includes Quick Reply buttons for reroll/accept
```

**Scenario: Midday push at 12:30**
```gherkin
Given a registered user with active quests
And it is 12:30 local time
When the scheduler triggers "Midday" batch
Then quest_service.trigger_push_quests(user_id, "Midday") is called
And if user has incomplete morning quests:
  | action                          |
  | Include reminder for those too  |
```

**Scenario: Night review at 21:00**
```gherkin
Given a registered user
And it is 21:00 local time
When the scheduler triggers "Night" batch
Then the system calculates daily_outcome
And if all quests complete: send celebration message
And if quests incomplete: send DDA-adjusted summary
And rival_service.advance_daily_briefing() is triggered
```

**Scenario: Scheduler respects user preferences**
```gherkin
Given a user with push_enabled = false
When any scheduled push time arrives
Then no message is sent to that user
And the system logs "Push skipped: user preference"
```

### 🔧 Technical Requirements
```yaml
Scheduler:
  type: APScheduler | Celery Beat | Azure Functions Timer
  jobs:
    - id: morning_push
      cron: "0 8 * * *"
      timezone: per-user
    - id: midday_push
      cron: "30 12 * * *"
    - id: night_review
      cron: "0 21 * * *"
  
Database:
  new_fields:
    User:
      - push_enabled: bool (default: true)
      - push_timezone: str (default: "Asia/Taipei")
      - push_times: JSON (customizable)
```

---

## 3. HP/Hollowed 世界觀系統 (HP/Hollowed World State)

### 🏷️ Feature: Character Health Points (HP)
*As a user, I want a persistent HP system so that my character feels "alive" with consequences.*

**Scenario: New user starts with full HP**
```gherkin
Given a new user registers
When their account is created
Then user.hp = 100
And user.max_hp = 100
And user.hp_status = "HEALTHY"
```

**Scenario: Inactivity drains HP**
```gherkin
Given a user with hp = 80
And the user has been inactive for 2 days
When the daily scheduler runs
Then user.hp -= (10 * inactive_days)  # -20
And user.hp = 60
And if hp < 30: user.hp_status = "CRITICAL"
```

**Scenario: HP reaches zero triggers Hollowed state**
```gherkin
Given a user with hp = 5
And the user misses another day
When hp calculation results in hp <= 0
Then user.hp = 0
And user.hp_status = "HOLLOWED"
And user.is_hollowed = true
And all active quests are PAUSED
And the system sends a "Hollowed Protocol" alert
```

**Scenario: Hollowed user receives rescue dungeon**
```gherkin
Given a user with hp_status = "HOLLOWED"
When the user sends any message
Then the system intercepts normal flow
And offers a "Rescue Mission" dungeon
And the dungeon has simplified stages:
  | stage | description              |
  | 1     | "呼吸：深呼吸 5 次"        |
  | 2     | "補水：喝一杯水"           |
  | 3     | "行動：完成一件小事"       |
And completing ALL stages restores hp = 30
And user.hp_status = "RECOVERING"
```

**Scenario: Completing quests restores HP**
```gherkin
Given a user with hp = 50, hp_status = "CRITICAL"
When the user completes a quest with difficulty = "C"
Then user.hp += 15  # scaled by difficulty
And user.hp = 65
And if hp >= 30: user.hp_status = "HEALTHY"
```

### 🔧 Technical Requirements
```yaml
Database:
  new_fields:
    User:
      - hp: int (default: 100)
      - max_hp: int (default: 100)
      - hp_status: enum [HEALTHY, CRITICAL, HOLLOWED, RECOVERING]
      - is_hollowed: bool (default: false)
      - hollowed_at: datetime (nullable)

Services:
  hp_service.py:
    - calculate_daily_drain(user_id)
    - apply_hp_change(user_id, delta, source)
    - check_hollowed_state(user_id) -> bool
    - trigger_rescue_protocol(user_id)
```

---

## 4. 觀測與日誌簡化 (Observability Improvements)

### 🏷️ Feature: Structured Logging with Toggle
*As a developer, I want clean, structured logs so that debugging is efficient without noise.*

**Scenario: Latency logs controlled by environment**
```gherkin
Given LOG_LATENCY_ENABLED = "0" in environment
When an AI request completes in 1.5s
Then no latency log is written to stdout
And only the standard request log is emitted
```

**Scenario: Latency logs enabled for debugging**
```gherkin
Given LOG_LATENCY_ENABLED = "1" in environment
When an AI request completes
Then a structured log is emitted:
  | field      | value                      |
  | level      | DEBUG                      |
  | event      | "ai_request_latency"       |
  | duration_s | 1.5                        |
  | model      | "gemini-2.0-flash"         |
```

**Scenario: Loading animation is optional**
```gherkin
Given SHOW_LOADING_ANIMATION = "0" in environment
When the user sends a message requiring AI processing
Then no "thinking..." animation is shown
And the final response is sent directly
```

**Scenario: Unified error response format**
```gherkin
Given any unhandled exception occurs
When the error handler catches it
Then the user receives:
  | field   | value                           |
  | message | "⚠️ 系統異常，請稍後再試"         |
  | code    | "{error_hash_for_support}"      |
And the full traceback is logged with the same error_hash
```

---

## 5. CI/CD 品質門檻 (Quality Gates)

### 🏷️ Feature: Automated Test Gates
*As a developer, I want CI to block broken deployments so that production stays stable.*

**Scenario: Core tests must pass before merge**
```gherkin
Given a PR is opened against `main`
When CI runs
Then the following test suites must pass:
  | suite                    | threshold |
  | test_core_mechanics.py   | 100%      |
  | test_quest_system.py     | 100%      |
  | test_verification.py     | 100%      |
  | test_rival_system.py     | 100%      |
And if any fail, the PR is blocked
```

**Scenario: Pre-deploy environment check**
```gherkin
Given a deployment is triggered
When the pre-deploy hook runs
Then the following checks must pass:
  | check                    | method                         |
  | DATABASE_URL set         | env var exists                 |
  | LINE tokens valid        | ping LINE API                  |
  | Migrations applied       | alembic current == head        |
And if any fail, deployment is aborted with detailed error
```

**Scenario: Post-deploy smoke test**
```gherkin
Given a deployment completes
When the smoke test suite runs
Then the following endpoints are verified:
  | endpoint       | expected_status |
  | /health        | 200             |
  | /callback      | 400 (no sig)    |
And if smoke fails, alert is sent to ops channel
```

**Scenario: DB/Rule changes require rollback plan**
```gherkin
Given a PR modifies files in:
  - app/models/*.py
  - doc/PROMPTS*.md
  - app/alembic/versions/*.py
When the PR is created
Then a template comment is required:
  | section              | required |
  | Rollback Procedure   | yes      |
  | Data Migration Notes | yes      |
And the PR cannot be merged without this comment
```

### 🔧 Technical Requirements
```yaml
CI/CD:
  platform: GitHub Actions
  workflows:
    - name: test
      on: [push, pull_request]
      steps:
        - pytest --cov=app --cov-fail-under=80
        - black --check app tests
        - ruff check app
    
    - name: deploy
      on:
        push:
          branches: [main]
      steps:
        - pre_deploy_checks.sh
        - docker build & push
        - az webapp deploy
        - post_deploy_smoke.sh
```

---

## 🗂️ Implementation Priority

| Feature                     | Priority | Effort | Dependencies       |
|-----------------------------|----------|--------|--------------------|
| DDA Scheduler               | P0       | M      | None               |
| HP/Hollowed System          | P1       | L      | None               |
| Verification Consistency    | P1       | S      | None               |
| CI/CD Quality Gates         | P2       | M      | GitHub Actions     |
| Observability Improvements  | P3       | S      | None               |

**Legend**: P0=Critical, P1=High, P2=Medium, P3=Low | S=Small, M=Medium, L=Large
