import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Add path
sys.path.append(os.getcwd())

from app.services.rich_menu_service import RichMenuService

class TestRichMenuService(unittest.TestCase):
    def setUp(self):
        # Patch settings to ensure we try to init API
        self.settings_patcher = patch('app.services.rich_menu_service.settings')
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.LINE_CHANNEL_ACCESS_TOKEN = "test_token"
        
        # Patch API Clients
        self.api_client_patcher = patch('app.services.rich_menu_service.ApiClient')
        self.mock_api_client_cls = self.api_client_patcher.start()
        
        self.msg_api_patcher = patch('app.services.rich_menu_service.MessagingApi')
        self.mock_msg_api_cls = self.msg_api_patcher.start()
        self.mock_msg_api = self.mock_msg_api_cls.return_value
        
        self.blob_api_patcher = patch('app.services.rich_menu_service.MessagingApiBlob')
        self.mock_blob_api_cls = self.blob_api_patcher.start()
        self.mock_blob_api = self.mock_blob_api_cls.return_value
        
        self.service = RichMenuService()

    def tearDown(self):
        self.settings_patcher.stop()
        self.api_client_patcher.stop()
        self.msg_api_patcher.stop()
        self.blob_api_patcher.stop()

    def test_create_menu(self):
        print("\n--- Testing Create Menu ---")
        # Mock Return
        mock_resp = MagicMock()
        mock_resp.rich_menu_id = "rich_menu_123"
        self.mock_msg_api.create_rich_menu.return_value = mock_resp
        
        # Test
        with patch("builtins.open", mock_open(read_data=b"image_data")),\
             patch("os.path.exists", return_value=True):
            rid = self.service.create_menu("TEST_MENU", [], "dummy_path.png")
            
        print(f"Created ID: {rid}")
        
        # Verify
        self.mock_msg_api.create_rich_menu.assert_called_once()
        self.mock_blob_api.set_rich_menu_image.assert_called_once()
        assert rid == "rich_menu_123"
        print("✅ Create & Upload Verified.")

    def test_link_user(self):
        print("\n--- Testing Link User ---")
        # Mock mappings load
        with patch.object(self.service, '_load_mappings', return_value={"MORNING": "rm_morning_001"}):
            self.service.link_user("U12345", "MORNING")
            
        self.mock_msg_api.link_rich_menu_to_user.assert_called_with("U12345", "rm_morning_001")
        print("✅ Link User Verified.")

if __name__ == '__main__':
    unittest.main()
