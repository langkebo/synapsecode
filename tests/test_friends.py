# Copyright 2024 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import time

from synapse.api.errors import SynapseError, NotFoundError, AuthError
from synapse.config.friends import FriendsConfig
from synapse.handlers.friends import FriendsHandler
from synapse.storage.databases.main.friends import FriendsWorkerStore
from synapse.types import Requester, UserID
from synapse.util import Clock


class TestFriendsConfig(unittest.TestCase):
    """Test FriendsConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = FriendsConfig()
        
        # Test default values
        self.assertTrue(config.enabled)
        self.assertEqual(config.max_requests_per_hour, 10)
        self.assertEqual(config.rate_limit_window, 3600)
        self.assertTrue(config.enable_requests)
        self.assertTrue(config.require_mutual_consent)
        self.assertFalse(config.auto_accept_requests)
        self.assertEqual(config.request_message_max_length, 500)
        self.assertEqual(config.request_expiry_hours, 168)
        self.assertEqual(config.max_friends_per_user, 1000)
        self.assertFalse(config.enable_friend_suggestions)
        self.assertTrue(config.show_online_status)
        self.assertTrue(config.enable_blocking)
        self.assertEqual(config.max_blocked_users, 500)
        self.assertFalse(config.block_mutual_friends)
        self.assertTrue(config.allow_friend_discovery)
        self.assertTrue(config.show_friends_in_profile)
        self.assertTrue(config.enable_friend_requests_from_strangers)
        self.assertTrue(config.enable_user_search)
        self.assertEqual(config.search_result_limit, 20)
        self.assertEqual(config.search_min_chars, 2)
        self.assertTrue(config.enable_email_notifications)
        self.assertTrue(config.enable_push_notifications)
        self.assertTrue(config.notify_on_friend_request)
        self.assertTrue(config.notify_on_request_accepted)
        self.assertFalse(config.notify_on_friend_removed)

    def test_invalid_config_values(self):
        """Test invalid configuration values"""
        config = FriendsConfig()
        
        # Test invalid max_requests_per_hour
        with self.assertRaises(ValueError):
            config.max_requests_per_hour = 0
            
        # Test invalid rate_limit_window
        with self.assertRaises(ValueError):
            config.rate_limit_window = 30
            
        # Test invalid max_friends_per_user
        with self.assertRaises(ValueError):
            config.max_friends_per_user = 0
            
        # Test invalid max_blocked_users
        with self.assertRaises(ValueError):
            config.max_blocked_users = 0
            
        # Test invalid request_message_max_length
        with self.assertRaises(ValueError):
            config.request_message_max_length = -1
            
        # Test invalid request_expiry_hours
        with self.assertRaises(ValueError):
            config.request_expiry_hours = 0

    def test_read_config(self):
        """Test reading configuration from dict"""
        config_dict = {
            "friends": {
                "enabled": False,
                "rate_limiting": {
                    "max_requests_per_hour": 5,
                    "rate_limit_window": 1800
                },
                "requests": {
                    "enabled": False,
                    "message_max_length": 200
                },
                "friends_list": {
                    "max_friends_per_user": 500
                }
            }
        }
        
        config = FriendsConfig()
        config.read_config(config_dict)
        
        self.assertFalse(config.enabled)
        self.assertEqual(config.max_requests_per_hour, 5)
        self.assertEqual(config.rate_limit_window, 1800)
        self.assertFalse(config.enable_requests)
        self.assertEqual(config.request_message_max_length, 200)
        self.assertEqual(config.max_friends_per_user, 500)


class TestFriendsWorkerStore(unittest.TestCase):
    """Test FriendsWorkerStore class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_database = MagicMock()
        self.mock_db_conn = MagicMock()
        self.mock_hs = MagicMock()
        
        self.store = FriendsWorkerStore(
            database=self.mock_database,
            db_conn=self.mock_db_conn,
            hs=self.mock_hs
        )

    def test_get_friendship_success(self):
        """Test successful friendship retrieval"""
        async def mock_run_interaction(name, callback):
            return {
                "user1_id": "@user1:example.com",
                "user2_id": "@user2:example.com",
                "status": "active",
                "created_ts": 1640995200000
            }
        
        self.store.db_pool.runInteraction = mock_run_interaction
        
        result = asyncio.run(self.store.get_friendship("@user1:example.com", "@user2:example.com"))
        
        self.assertEqual(result["user1_id"], "@user1:example.com")
        self.assertEqual(result["user2_id"], "@user2:example.com")
        self.assertEqual(result["status"], "active")

    def test_get_friendship_empty_user_ids(self):
        """Test friendship retrieval with empty user IDs"""
        result = asyncio.run(self.store.get_friendship("", "@user2:example.com"))
        self.assertIsNone(result)
        
        result = asyncio.run(self.store.get_friendship("@user1:example.com", ""))
        self.assertIsNone(result)

    def test_create_friendship_success(self):
        """Test successful friendship creation"""
        async def mock_run_interaction(name, callback):
            return None
        
        self.store.db_pool.runInteraction = mock_run_interaction
        
        # Should not raise exception
        asyncio.run(self.store.create_friendship("@user1:example.com", "@user2:example.com", 1640995200000))

    def test_create_friendship_same_user(self):
        """Test friendship creation with same user"""
        with self.assertRaises(Exception):
            asyncio.run(self.store.create_friendship("@user1:example.com", "@user1:example.com", 1640995200000))

    def test_is_user_blocked_success(self):
        """Test successful user block check"""
        async def mock_run_interaction(name, callback):
            return True
        
        self.store.db_pool.runInteraction = mock_run_interaction
        
        result = asyncio.run(self.store.is_user_blocked("@user1:example.com", "@user2:example.com"))
        self.assertTrue(result)

    def test_generate_request_id(self):
        """Test request ID generation"""
        request_id = self.store._generate_request_id()
        self.assertIsInstance(request_id, str)
        self.assertTrue(len(request_id) > 0)


class TestFriendsHandler(unittest.TestCase):
    """Test FriendsHandler class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_hs = MagicMock()
        self.mock_store = MagicMock()
        self.mock_clock = MagicMock()
        self.mock_auth = MagicMock()
        self.mock_user_directory_handler = MagicMock()
        self.mock_profile_handler = MagicMock()
        
        self.mock_hs.get_datastores.return_value.main = self.mock_store
        self.mock_hs.get_clock.return_value = self.mock_clock
        self.mock_hs.get_auth.return_value = self.mock_auth
        self.mock_hs.get_user_directory_handler.return_value = self.mock_user_directory_handler
        self.mock_hs.get_profile_handler.return_value = self.mock_profile_handler
        self.mock_hs.is_mine_server_name.return_value = True
        
        self.handler = FriendsHandler(self.mock_hs)

    def test_init(self):
        """Test handler initialization"""
        self.assertEqual(self.handler.store, self.mock_store)
        self.assertEqual(self.handler.clock, self.mock_clock)
        self.assertEqual(self.handler.hs, self.mock_hs)
        self.assertEqual(self.handler.auth, self.mock_auth)
        self.assertEqual(self.handler._max_requests_per_hour, 10)
        self.assertEqual(self.handler._rate_limit_window, 3600)

    def test_validate_user_id_valid(self):
        """Test valid user ID validation"""
        # Should not raise exception
        self.handler._validate_user_id("@user:example.com")

    def test_validate_user_id_invalid(self):
        """Test invalid user ID validation"""
        with self.assertRaises(SynapseError):
            self.handler._validate_user_id("")
            
        with self.assertRaises(SynapseError):
            self.handler._validate_user_id(None)
            
        with self.assertRaises(SynapseError):
            self.handler._validate_user_id("x" * 256)

    def test_check_rate_limit_under_limit(self):
        """Test rate limiting when under limit"""
        self.mock_clock.time_msec.return_value = 1640995200000
        
        # Should not raise exception
        self.handler._check_rate_limit("@user:example.com")

    def test_check_rate_limit_over_limit(self):
        """Test rate limiting when over limit"""
        self.mock_clock.time_msec.return_value = 1640995200000
        
        # Fill up rate limit cache
        for i in range(10):
            self.handler._check_rate_limit("@user:example.com")
        
        # Should raise exception on 11th attempt
        with self.assertRaises(SynapseError):
            self.handler._check_rate_limit("@user:example.com")

    def test_send_friend_request_success(self):
        """Test successful friend request sending"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@sender:example.com"
        
        self.mock_store.is_user_blocked.return_value = False
        self.mock_store.get_friendship.return_value = None
        self.mock_store.get_friend_request.return_value = None
        self.mock_store.create_friend_request.return_value = "request123"
        self.mock_clock.time_msec.return_value = 1640995200000
        
        result = asyncio.run(self.handler.send_friend_request(
            mock_requester, "@target:example.com", "Hello!"
        ))
        
        self.assertEqual(result["request_id"], "request123")
        self.assertEqual(result["status"], "pending")

    def test_send_friend_request_to_self(self):
        """Test friend request to self"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@user:example.com"
        
        with self.assertRaises(SynapseError):
            asyncio.run(self.handler.send_friend_request(
                mock_requester, "@user:example.com", "Hello!"
            ))

    def test_send_friend_request_blocked(self):
        """Test friend request to blocked user"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@sender:example.com"
        
        self.mock_store.is_user_blocked.return_value = True
        
        with self.assertRaises(SynapseError):
            asyncio.run(self.handler.send_friend_request(
                mock_requester, "@target:example.com", "Hello!"
            ))

    def test_respond_to_friend_request_accept(self):
        """Test accepting friend request"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@target:example.com"
        
        self.mock_store.get_friend_request_by_id.return_value = {
            "request_id": "request123",
            "sender_user_id": "@sender:example.com",
            "target_user_id": "@target:example.com",
            "status": "pending",
            "created_ts": 1640995200000,
            "updated_ts": 1640995200000
        }
        self.mock_clock.time_msec.return_value = 1640995200000
        
        result = asyncio.run(self.handler.respond_to_friend_request(
            mock_requester, "request123", True
        ))
        
        self.assertEqual(result["request_id"], "request123")
        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["accepted"])

    def test_respond_to_friend_request_not_found(self):
        """Test responding to non-existent friend request"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@target:example.com"
        
        self.mock_store.get_friend_request_by_id.return_value = None
        
        with self.assertRaises(NotFoundError):
            asyncio.run(self.handler.respond_to_friend_request(
                mock_requester, "request123", True
            ))

    def test_respond_to_friend_request_unauthorized(self):
        """Test responding to friend request not sent to user"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@unauthorized:example.com"
        
        self.mock_store.get_friend_request_by_id.return_value = {
            "request_id": "request123",
            "sender_user_id": "@sender:example.com",
            "target_user_id": "@target:example.com",
            "status": "pending",
            "created_ts": 1640995200000,
            "updated_ts": 1640995200000
        }
        
        with self.assertRaises(AuthError):
            asyncio.run(self.handler.respond_to_friend_request(
                mock_requester, "request123", True
            ))

    def test_get_friends_list_success(self):
        """Test successful friends list retrieval"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@user:example.com"
        
        self.mock_store.get_user_friendships.return_value = [
            {
                "friend_id": "@friend1:example.com",
                "status": "active",
                "created_ts": 1640995200000
            },
            {
                "friend_id": "@friend2:example.com",
                "status": "active",
                "created_ts": 1640995200000
            }
        ]
        
        self.mock_profile_handler.get_profile.side_effect = [
            {"displayname": "Friend One", "avatar_url": "mxc://example.com/avatar1"},
            {"displayname": "Friend Two", "avatar_url": "mxc://example.com/avatar2"}
        ]
        
        result = asyncio.run(self.handler.get_friends_list(mock_requester))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["user_id"], "@friend1:example.com")
        self.assertEqual(result[0]["displayname"], "Friend One")
        self.assertEqual(result[1]["user_id"], "@friend2:example.com")
        self.assertEqual(result[1]["displayname"], "Friend Two")

    def test_remove_friend_success(self):
        """Test successful friend removal"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@user:example.com"
        
        self.mock_store.get_friendship.return_value = {
            "user1_id": "@user:example.com",
            "user2_id": "@friend:example.com",
            "status": "active",
            "created_ts": 1640995200000
        }
        
        result = asyncio.run(self.handler.remove_friend(
            mock_requester, "@friend:example.com"
        ))
        
        self.assertTrue(result["removed"])
        self.assertEqual(result["user_id"], "@friend:example.com")

    def test_remove_friend_not_found(self):
        """Test removing non-existent friend"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@user:example.com"
        
        self.mock_store.get_friendship.return_value = None
        
        with self.assertRaises(NotFoundError):
            asyncio.run(self.handler.remove_friend(
                mock_requester, "@friend:example.com"
            ))

    def test_block_user_success(self):
        """Test successful user blocking"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@user:example.com"
        
        self.mock_store.get_friendship.return_value = None
        
        result = asyncio.run(self.handler.block_user(
            mock_requester, "@target:example.com"
        ))
        
        self.assertTrue(result["blocked"])
        self.assertEqual(result["user_id"], "@target:example.com")

    def test_block_user_self(self):
        """Test blocking self"""
        mock_requester = MagicMock()
        mock_requester.user.to_string.return_value = "@user:example.com"
        
        with self.assertRaises(SynapseError):
            asyncio.run(self.handler.block_user(
                mock_requester, "@user:example.com"
            ))


if __name__ == '__main__':
    unittest.main()