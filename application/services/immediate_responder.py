"""
Immediate Responder Service - Hyperbolic Discounting Implementation

Per Feature 4 of Behavioral Engineering specs:
- Sends visceral signal within 200ms of user input
- Before LLM processing begins
- Provides instant gratification and confirmation
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ImmediateResponder:
    """
    Handles immediate response generation for specific intents.
    Goal: Reduce perceived latency by sending acknowledgment < 200ms.
    """

    # Intent -> Immediate Response mapping
    INTENT_RESPONSES = {
        "CREATE_GOAL": "🎯 收到目標指令！啟動規劃協議...",
        "START_CHALLENGE": "⚔️ 挑戰確認！準備戰鬥...",
        "GREETING": None,  # Greetings are fast enough
        "UNKNOWN": None,  # No immediate response for unknown
    }

    def classify_intent_fast(self, text: str) -> str:
        """
        Fast rule-based intent classification (no AI).
        Target: < 5ms execution time.
        """
        text_lower = text.lower().strip()

        # CREATE_GOAL patterns
        goal_patterns = [
            r"我想",
            r"想要",
            r"目標",
            r"new goal",
            r"i want",
        ]
        for pattern in goal_patterns:
            if re.search(pattern, text_lower):
                return "CREATE_GOAL"

        # START_CHALLENGE patterns
        challenge_patterns = [
            r"挑戰",
            r"試試",
            r"開始",
            r"start",
            r"challenge",
        ]
        for pattern in challenge_patterns:
            if re.search(pattern, text_lower):
                return "START_CHALLENGE"

        # GREETING patterns
        greeting_patterns = [r"你好", r"嗨", r"hello", r"hi", r"早安", r"晚安"]
        for pattern in greeting_patterns:
            if re.search(pattern, text_lower):
                return "GREETING"

        return "UNKNOWN"

    def get_immediate_response(self, intent: str) -> Optional[str]:
        """Get the immediate response text for an intent."""
        return self.INTENT_RESPONSES.get(intent)

    def should_send_immediate(self, intent: str) -> bool:
        """Check if this intent warrants an immediate response."""
        return self.INTENT_RESPONSES.get(intent) is not None


# Singleton instance
immediate_responder = ImmediateResponder()
