from typing import Protocol, Dict, Any

class CognitionPort(Protocol):
    """
    Interface for AI/LLM operations (Thinking, Narrative Generation).
    """
    async def think(self, context: str, prompt: str) -> str:
        """
        Generate raw text response from the AI.
        """
        ...
    
    async def decide_action(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate structured decision (JSON) based on game state.
        """
        ...
