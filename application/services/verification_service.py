from __future__ import annotations

import asyncio
import enum
import logging
from typing import Any, Iterable, TypedDict

from sqlalchemy import func, select

from app.core.container import container
from app.models.quest import Quest, QuestStatus
from application.services.ai_engine import ai_engine
from application.services.quest_service import quest_service

logger = logging.getLogger(__name__)

VERDICT_APPROVED = "APPROVED"
VERDICT_REJECTED = "REJECTED"
VERDICT_UNCERTAIN = "UNCERTAIN"


class Verdict(str, enum.Enum):
    APPROVED = VERDICT_APPROVED
    REJECTED = VERDICT_REJECTED
    UNCERTAIN = VERDICT_UNCERTAIN


class VerificationResult(TypedDict):
    """Internal result from individual verify_* methods."""

    verdict: Verdict
    reason: str
    meta: dict


class VerificationResponse(TypedDict):
    """Unified response format for all verification types (BDD Spec compliant)."""

    quest: Quest | None
    verdict: Verdict
    message: str
    xp_awarded: int
    gold_awarded: int
    hint: str | None  # AI-generated suggestion for failures


class VerificationService:
    GOLD_REWARD_BY_DIFF = {
        "S": 50,
        "A": 30,
        "B": 20,
        "C": 10,
        "D": 5,
        "E": 3,
        "F": 1,
    }

    async def get_verifiable_quests(self, session, user_id: str, verification_type: str | None = None) -> list[Quest]:
        stmt = select(Quest).where(
            Quest.user_id == user_id,
            Quest.status.in_([QuestStatus.ACTIVE.value, QuestStatus.PENDING.value]),
            Quest.verification_type.is_not(None),
        )
        if verification_type:
            stmt = stmt.where(func.upper(Quest.verification_type) == verification_type)
        result = await session.execute(stmt)
        scalars = result.scalars()
        if asyncio.iscoroutine(scalars):
            scalars = await scalars
        quests = scalars.all()
        if asyncio.iscoroutine(quests):
            quests = await quests
        if isinstance(quests, list):
            return quests
        if isinstance(quests, tuple):
            return list(quests)
        if quests is None:
            return []
        try:
            return list(quests)
        except TypeError:
            return []

    def _normalize_keywords(self, raw: Any) -> list[str]:
        if not raw:
            return []
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, Iterable):
            return [str(k) for k in raw]
        return []

    def _keyword_match_score(self, text: str, keywords: list[str]) -> int:
        if not text or not keywords:
            return 0
        lowered = text.lower()
        return sum(1 for k in keywords if k and k.lower() in lowered)

    async def auto_match_quest(self, session, user_id: str, payload: Any, verification_type: str) -> Quest | None:
        quests = await self.get_verifiable_quests(session, user_id, verification_type)
        if not quests:
            return None
        if len(quests) == 1:
            return quests[0]

        if verification_type == "TEXT":
            text = str(payload or "")
            scored = []
            for quest in quests:
                keywords = self._normalize_keywords(quest.verification_keywords)
                score = self._keyword_match_score(text, keywords)
                scored.append((score, quest))
            scored.sort(key=lambda item: item[0], reverse=True)
            if scored and scored[0][0] > 0:
                return scored[0][1]
            return None

        # For IMAGE/LOCATION, we pick the first for now (can be refined later)
        return quests[0]

    async def verify_text(self, session, quest: Quest, user_text: str) -> VerificationResult:
        keywords = self._normalize_keywords(quest.verification_keywords)
        # match_score = self._keyword_match_score(user_text, keywords)

        try:
            response = await ai_engine.verify_multimodal(
                mode="TEXT",
                quest_title=quest.title,
                user_text=user_text,
                keywords=keywords,
            )
        except Exception as e:
            logger.warning(f"verify_text fallback: {e}")
            response = {}

        verdict_str = str(response.get("verdict", VERDICT_UNCERTAIN)).upper()
        reason = response.get("reason") or "需要更清楚的完成描述。"
        follow_up = response.get("follow_up")

        # Safe Enum Conversion
        try:
            verdict = Verdict(verdict_str)
        except ValueError:
            verdict = Verdict.UNCERTAIN

        if verdict == Verdict.UNCERTAIN and not follow_up:
            follow_up = "收到回報，但請補充：完成的具體內容或數量是什麼？"

        return {"verdict": verdict, "reason": reason, "meta": {"follow_up": follow_up}}

    async def verify_text_report(self, user_text: str, quest_title: str) -> dict:
        """Legacy helper for tests: verify a text report without quest context."""
        response = await ai_engine.generate_json(
            "你是任務驗證助手。請判斷回報是否完成任務。輸出 JSON: {'verdict':'APPROVED|REJECTED|UNCERTAIN','reason':'str'}",
            f"任務：{quest_title}\n回報：{user_text}",
        )
        verdict = str(response.get("verdict", VERDICT_UNCERTAIN)).upper()
        reason = response.get("reason") or ""
        return {"verdict": verdict, "reason": reason}

    async def verify_image(self, session, quest: Quest, image_data: bytes) -> VerificationResult:
        keywords = self._normalize_keywords(quest.verification_keywords)

        try:
            # We assume mime_type is roughly reliable or handled by engine
            response = await ai_engine.verify_multimodal(
                mode="IMAGE",
                quest_title=quest.title,
                image_bytes=image_data,
                keywords=keywords,
            )
        except Exception as e:
            logger.warning(f"verify_image fallback: {e}")
            response = {}

        verdict_str = str(response.get("verdict", VERDICT_UNCERTAIN)).upper()
        reason = response.get("reason") or "無法確認圖片內容。"
        labels = response.get("detected_labels", [])

        try:
            verdict = Verdict(verdict_str)
        except ValueError:
            verdict = Verdict.UNCERTAIN

        return {"verdict": verdict, "reason": reason, "meta": {"labels": labels}}

    async def verify_image_report(self, image_data: bytes, mime_type: str, quest_title: str) -> dict:
        """Legacy helper for tests: verify an image report without quest context."""
        response = await ai_engine.analyze_image(image_data, mime_type, quest_title)
        return {
            "verdict": response.get("verdict", VERDICT_UNCERTAIN),
            "reason": response.get("reason", ""),
            "tags": response.get("tags", response.get("detected_labels", [])),
        }

    async def verify_location(self, session, quest: Quest, lat: float, lng: float) -> VerificationResult:
        target = quest.location_target or {}
        if not target:
            return {
                "verdict": Verdict.UNCERTAIN,
                "reason": "缺少位置目標設定。",
                "meta": {},
            }

        target_lat = target.get("lat")
        target_lng = target.get("lng")
        radius = target.get("radius_m", 100)

        if target_lat is None or target_lng is None:
            return {
                "verdict": Verdict.UNCERTAIN,
                "reason": "位置資訊不足。",
                "meta": {},
            }

        distance = self._haversine(lat, lng, target_lat, target_lng)
        meta = {"distance_m": int(distance)}

        if distance <= radius:
            return {
                "verdict": Verdict.APPROVED,
                "reason": f"抵達目標範圍（距離 {int(distance)}m）。",
                "meta": meta,
            }

        return {
            "verdict": Verdict.REJECTED,
            "reason": f"尚未抵達目標（距離 {int(distance)}m）。",
            "meta": meta,
        }

    async def _complete_quest(self, session, user_id: str, quest: Quest) -> dict:
        result_data = await quest_service.complete_quest(session, user_id, quest.id)
        if not result_data:
            return {
                "xp": 0,
                "gold": 0,
                "story": "",
                "success": False,
                "message": "⚠️ 任務已完成或不存在。",
            }

        loot = result_data.get("loot")
        xp_awarded = loot.xp if loot else (quest.xp_reward or 0)
        gold_awarded = loot.gold if loot else self.GOLD_REWARD_BY_DIFF.get((quest.difficulty_tier or "E").upper(), 3)
        narrative_flavor = loot.narrative_flavor if loot else "Standard"

        # Feature 4: Epic Feedback (with RPE Flavor)
        from application.services.narrative_service import narrative_service

        # We assume user is already updated by quest_service (it accesses session and user)
        # But for narrative context we might fetch user?
        user = await container.user_service.get_or_create_user(session, user_id)

        story = await narrative_service.generate_outcome_story(
            session=session,
            user_id=user_id,
            action_text=f"Completed Quest: {quest.title}",
            result_data={"xp": xp_awarded, "diff": quest.difficulty_tier, "flavor": narrative_flavor},
            user_context=f"User Lv.{user.level}",
        )

        await session.commit()
        return {
            "xp": xp_awarded,
            "gold": gold_awarded,
            "story": story,
            "success": True,
            "message": f"✅ 任務完成！ ({narrative_flavor})",
        }

    async def _generate_hint(self, quest: Quest, verification_type: str, reason: str) -> str:
        """Generate AI-powered hint for failed verifications."""
        try:
            response = await ai_engine.generate_json(
                system_prompt="你是任務驗證助手。根據驗證失敗原因，給出簡短的改善建議（一句話）。",
                user_prompt=f'任務：{quest.title}\n驗證類型：{verification_type}\n失敗原因：{reason}\n輸出 JSON: {{"hint": "建議內容"}}',
            )
            return response.get("hint", "請確認完成條件並再試一次。")
        except Exception as e:
            logger.warning(f"Hint generation failed: {e}")
            return "請確認完成條件並再試一次。"

    async def process_verification(
        self, session, user_id: str, payload: Any, verification_type: str
    ) -> VerificationResponse:
        """
        Unified verification processor. Returns VerificationResponse (BDD Spec compliant).
        """
        verification_type = verification_type.upper()
        quest = await self.auto_match_quest(session, user_id, payload, verification_type)

        # No matching quest found
        if not quest:
            return VerificationResponse(
                quest=None,
                verdict=Verdict.UNCERTAIN,
                message="此類別無進行中的驗證任務。",
                xp_awarded=0,
                gold_awarded=0,
                hint=None,
            )

        result: VerificationResult = {
            "verdict": Verdict.UNCERTAIN,
            "reason": "無法識別的驗證類型。",
            "meta": {},
        }

        # Dispatch to appropriate verification method
        if verification_type == "TEXT":
            result = await self.verify_text(session, quest, str(payload))
        elif verification_type == "IMAGE":
            result = await self.verify_image(session, quest, payload)
        elif verification_type == "LOCATION":
            if isinstance(payload, (list, tuple)) and len(payload) == 2:
                result = await self.verify_location(session, quest, payload[0], payload[1])

        verdict = result["verdict"]
        reason = result["reason"]

        # APPROVED: Complete quest and return success response
        if verdict == Verdict.APPROVED:
            completion_result = await self._complete_quest(session, user_id, quest)
            xp = completion_result["xp"]
            gold = completion_result["gold"]
            story = completion_result["story"]

            return VerificationResponse(
                quest=quest,
                verdict=verdict,
                message=(
                    "✅ 任務驗證通過！\n"
                    f"任務：{quest.title}\n"
                    f"獲得：{xp} XP / {gold} Gold\n"
                    f"判定：{reason}" + (f"\n\n_{story}_" if story else "")
                ),
                xp_awarded=xp,
                gold_awarded=gold,
                hint=None,
            )

        # REJECTED: Return failure with AI-generated hint
        elif verdict == Verdict.REJECTED:
            hint = await self._generate_hint(quest, verification_type, reason)
            return VerificationResponse(
                quest=quest,
                verdict=verdict,
                message=f"❌ 驗證失敗：{reason}",
                xp_awarded=0,
                gold_awarded=0,
                hint=f"💡 {hint}",
            )

        # UNCERTAIN: Request more information
        else:
            follow_up = result["meta"].get("follow_up", reason)
            return VerificationResponse(
                quest=quest,
                verdict=verdict,
                message=f"🤔 {follow_up}",
                xp_awarded=0,
                gold_awarded=0,
                hint=None,
            )

    def _haversine(self, lat1, lng1, lat2, lng2) -> float:
        from math import asin, cos, radians, sin, sqrt

        r = 6371000  # meters
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * asin(sqrt(a))
        return r * c


verification_service = VerificationService()
