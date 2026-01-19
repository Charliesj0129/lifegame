import asyncio
import logging
import sys
from app.core.database import AsyncSessionLocal
from app.main import handle_status
from app.models.user import User

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_status():
    logger.info("--- Starting Debug Status ---")
    async with AsyncSessionLocal() as session:
        # ensuring user exists
        user_id = "debug_user_001"
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, name="Debug Hero", gold=100, xp=50)
            session.add(user)
            await session.commit()
            logger.info(f"Created debug user: {user_id}")

        try:
            logger.info(f"Invoking handle_status for {user_id}...")
            result = await handle_status(session, user_id, "狀態")
            logger.info(f"Result: {result.text}")
            if result.intent == "status_critical_error" or result.intent == "status_render_error":
                logger.error("!!! STATUS FAILED !!!")
                sys.exit(1)
            elif result.intent == "status":
                logger.info(">>> STATUS SUCCESS <<<")
                import json

                flex = result.metadata.get("flex_message")
                if flex:
                    try:
                        # Convert to dict if it's a model object
                        flex_dict = flex
                        if hasattr(flex, "to_dict"):
                            flex_dict = flex.to_dict()
                        elif hasattr(flex, "as_json_dict"):
                            flex_dict = flex.as_json_dict()

                        # Test Serialization (Critical for LINE API)
                        json_str = json.dumps(flex_dict, default=str, indent=2, ensure_ascii=False)
                        logger.info("Flex Message JSON:\n" + json_str)

                        # Basic Schema Check
                        container_type = (
                            flex_dict.get("type") if isinstance(flex_dict, dict) else getattr(flex, "type", "unknown")
                        )
                        if container_type != "bubble" and container_type != "carousel":
                            logger.warning(f"Flex type suspicious: {container_type}")

                    except Exception as json_err:
                        logger.error(f"FLEX SERIALIZATION FAILED: {json_err}", exc_info=True)
                else:
                    logger.warning("No flex_message in metadata")

                # --- INTEGRATION TEST: Line Client Conversion ---
                try:
                    logger.info("--- Testing LineClient Conversion ---")
                    # Mock result for LineClient
                    # We need to initialize LineClient (it uses global get_messaging_api)
                    # For test, we might skip the actual API call but test the _to_line_messages

                    from adapters.perception.line_client import line_client

                    messages = line_client._to_line_messages(result)
                    logger.info(f"LineClient Conversion Success. Message Count: {len(messages)}")

                    for i, msg in enumerate(messages):
                        logger.info(f"Msg [{i}] Type: {type(msg)}")
                        # Verify we can dict-ify it (SDK validation check)
                        if hasattr(msg, "as_json_dict"):
                            logger.info(
                                f"Msg [{i}] Valid JSON: {json.dumps(msg.as_json_dict(), ensure_ascii=False)[:50]}..."
                            )
                        else:
                            logger.warning(f"Msg [{i}] does not have as_json_dict (might be raw dict?)")

                except Exception as client_err:
                    logger.error(f"LINE CLIENT CONVERSION FAILED: {client_err}", exc_info=True)

            else:
                logger.error(f"Intent mismatch: {result.intent}")
        except Exception:
            logger.exception("CRITICAL UNHANDLED EXCEPTION")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_status())
