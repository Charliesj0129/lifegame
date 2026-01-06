import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta
from app.services.rival_service import rival_service
from app.models.user import User
from app.models.quest import Rival

@pytest.mark.asyncio
async def test_rival_inactive_penalty():
    # Mock Session
    session = AsyncMock() # Use AsyncMock for async methods like execute/commit
    
    user = User(id="test_user", xp=1000, gold=1000, level=5)
    # 3 Days Inactive
    user.last_active_date = datetime.now() - timedelta(days=4)
    
    rival = Rival(id="VIPER", level=1, xp=0)
    
    # Mock DB Query Results
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = rival
    session.execute.return_value = mock_result

    # Run Encounter
    narrative = await rival_service.process_encounter(session, user)
    
    # Assertions
    # Theft: 3 days * 5% = 15%. 1000 * 0.15 = 150 stolen. 
    assert user.xp == 850 
    assert rival.xp == 300
    assert "入侵警報" in narrative

@pytest.mark.asyncio
async def test_rival_sabotage():
    session = AsyncMock()
    
    user = User(id="test_user", xp=1000, level=1)
    user.last_active_date = datetime.now() - timedelta(days=2) # 1 missed day
    
    rival = Rival(id="VIPER", level=10, xp=5000)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = rival
    session.execute.return_value = mock_result
    
    # Run
    narrative = await rival_service.process_encounter(session, user)
    
    # Assertions
    assert "病毒植入" in narrative
    assert session.add.call_count >= 1
