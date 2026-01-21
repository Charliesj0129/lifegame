from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from app.models.user import User
from application.services.title_service import title_service


@pytest.mark.asyncio
async def test_title_logic():
    # 1. Novice
    u1 = User(id="u1", level=1, streak_count=0, str=10, int=10)
    t1 = await title_service.get_user_title(None, u1)
    assert "未登錄市民" in t1

    # 2. Street Rat (Level 5) + STR Prefix (25)
    u2 = User(id="u2", level=5, streak_count=0, str=25, int=10, vit=10, wis=10, cha=10)
    t2 = await title_service.get_user_title(None, u2)
    assert "強襲型" in t2
    assert "暗影跑者" in t2

    # 3. Legend (Level 30) + Fire Streak (30)
    u3 = User(id="u3", level=30, streak_count=35, str=10, int=10)
    t3 = await title_service.get_user_title(None, u3)
    assert "都會傳奇" in t3
    assert "不滅之火" in t3
