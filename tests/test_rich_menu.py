import pytest
from unittest.mock import MagicMock, patch, mock_open
from application.services.rich_menu_service import RichMenuService


@pytest.fixture
def mock_service():
    with patch("application.services.rich_menu_service.settings") as mock_settings:
        mock_settings.LINE_CHANNEL_ACCESS_TOKEN = "fake_token"
        service = RichMenuService()
        service.api = MagicMock()
        service.blob_api = MagicMock()
        return service


def test_get_menu_id_by_name(mock_service):
    # Setup Mock Response
    mock_menu = MagicMock()
    mock_menu.name = "LIFGAME_MAIN"
    mock_menu.rich_menu_id = "rich_menu_123"

    mock_response = MagicMock()
    mock_response.rich_menus = [mock_menu]
    mock_service.api.get_rich_menu_list.return_value = mock_response

    # Test Found
    assert mock_service.get_menu_id_by_name("LIFGAME_MAIN") == "rich_menu_123"

    # Test Not Found
    assert mock_service.get_menu_id_by_name("LIFGAME_OTHER") is None


def test_create_menu_idempotent(mock_service):
    # Scenario: Menu already exists
    mock_service.get_menu_id_by_name = MagicMock(return_value="existing_id_456")

    mid = mock_service.create_menu("LIFGAME_MAIN", [])

    assert mid == "existing_id_456"
    mock_service.api.create_rich_menu.assert_not_called()


def test_create_menu_new(mock_service):
    # Scenario: Menu does not exist
    mock_service.get_menu_id_by_name = MagicMock(return_value=None)
    mock_service.api.create_rich_menu.return_value.rich_menu_id = "new_id_789"

    with (
        patch("builtins.open", mock_open(read_data=b"image_data")),
        patch("os.path.exists", return_value=True),
    ):
        mid = mock_service.create_menu("LIFGAME_MAIN", [], "path/to/img.jpg")

        assert mid == "new_id_789"
        mock_service.api.create_rich_menu.assert_called_once()
        mock_service.blob_api.set_rich_menu_image.assert_called_once()
