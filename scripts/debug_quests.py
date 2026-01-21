import asyncio
import logging

from app.core.container import container
from app.core.database import AsyncSessionLocal
from app.main import handle_quests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    user_id = "U0bad6ce00eec7d3ac817ba349ff3b6fd"  # Charlie's mock ID

    logger.info("--- Testing handle_quests ---")
    async with AsyncSessionLocal() as session:
        # 1. Ensure user exists
        await container.user_service.get_or_create_user(session, user_id)

        # 2. Call handler
        result = await handle_quests(session, user_id, "任務")

        print("\n=== RESULT ===")
        print(f"Text: {result.text}")
        print(f"Intent: {result.intent}")
        print(f"Metadata Keys: {result.metadata.keys() if result.metadata else 'None'}")

        if result.metadata and "flex_message" in result.metadata:
            import json

            flex = result.metadata["flex_message"]
            # Check if it's a valid object or dict
            print(f"Flex Message Type: {type(flex)}")
            try:
                # Attempt to serialize to check validity
                if hasattr(flex, "to_dict"):
                    print(json.dumps(flex.to_dict(), indent=2, ensure_ascii=False))
                elif hasattr(flex, "as_json_dict"):
                    print(json.dumps(flex.as_json_dict(), indent=2, ensure_ascii=False))
                else:
                    print(json.dumps(flex, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"Flex Serialization Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
