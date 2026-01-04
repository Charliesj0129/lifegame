import asyncio
from unittest.mock import MagicMock
from app.services.flex_renderer import flex_renderer
from app.models.user import User

def test_render():
    user = User(
        id="U12345678",
        name="Charlie",
        level=5,
        xp=150,
        str=10,
        int=10,
        vit=10,
        wis=10,
        cha=10
    )
    
    try:
        msg = flex_renderer.render_status(user)
        print("Render Success!")
        print(msg)
    except Exception as e:
        print(f"Render Failed: {e}")

if __name__ == "__main__":
    test_render()
