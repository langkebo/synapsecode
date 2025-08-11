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

import attr
from typing import Optional

from synapse.config._base import Config


@attr.s(auto_attribs=True, frozen=True, slots=True)
class FriendsConfig(Config):
    """Configuration for friends functionality"""
    
    section = "friends"
    
    def read_config(self, config, **kwargs):
        friends_config = config.get("friends", {})
        
        # Enable/disable friends functionality
        self.enabled = friends_config.get("enabled", True)
        
        # Rate limiting configuration
        rate_limit_config = friends_config.get("rate_limiting", {})
        self.max_requests_per_hour = rate_limit_config.get("max_requests_per_hour", 10)
        self.rate_limit_window = rate_limit_config.get("rate_limit_window", 3600)  # 1 hour
        
        # Friend request configuration
        request_config = friends_config.get("requests", {})
        self.enable_requests = request_config.get("enabled", True)
        self.require_mutual_consent = request_config.get("require_mutual_consent", True)
        self.auto_accept_requests = request_config.get("auto_accept", False)
        self.request_message_max_length = request_config.get("message_max_length", 500)
        self.request_expiry_hours = request_config.get("expiry_hours", 168)  # 7 days
        
        # Friends list configuration
        list_config = friends_config.get("friends_list", {})
        self.max_friends_per_user = list_config.get("max_friends_per_user", 1000)
        self.enable_friend_suggestions = list_config.get("enable_suggestions", False)
        self.show_online_status = list_config.get("show_online_status", True)
        
        # Blocking configuration
        blocking_config = friends_config.get("blocking", {})
        self.enable_blocking = blocking_config.get("enabled", True)
        self.max_blocked_users = blocking_config.get("max_blocked_users", 500)
        self.block_mutual_friends = blocking_config.get("block_mutual_friends", False)
        
        # Privacy configuration
        privacy_config = friends_config.get("privacy", {})
        self.allow_friend_discovery = privacy_config.get("allow_friend_discovery", True)
        self.show_friends_in_profile = privacy_config.get("show_friends_in_profile", True)
        self.enable_friend_requests_from_strangers = privacy_config.get(
            "enable_requests_from_strangers", True
        )
        
        # Search configuration
        search_config = friends_config.get("search", {})
        self.enable_user_search = search_config.get("enabled", True)
        self.search_result_limit = search_config.get("result_limit", 20)
        self.search_min_chars = search_config.get("min_characters", 2)
        
        # Notifications configuration
        notifications_config = friends_config.get("notifications", {})
        self.enable_email_notifications = notifications_config.get("email_enabled", True)
        self.enable_push_notifications = notifications_config.get("push_enabled", True)
        self.notify_on_friend_request = notifications_config.get("on_friend_request", True)
        self.notify_on_request_accepted = notifications_config.get("on_request_accepted", True)
        self.notify_on_friend_removed = notifications_config.get("on_friend_removed", False)
        
        # Validation
        if self.max_requests_per_hour < 1:
            raise ValueError("max_requests_per_hour must be at least 1")
        if self.rate_limit_window < 60:
            raise ValueError("rate_limit_window must be at least 60 seconds")
        if self.max_friends_per_user < 1:
            raise ValueError("max_friends_per_user must be at least 1")
        if self.max_blocked_users < 1:
            raise ValueError("max_blocked_users must be at least 1")
        if self.request_message_max_length < 0:
            raise ValueError("request_message_max_length must be non-negative")
        if self.request_expiry_hours < 1:
            raise ValueError("request_expiry_hours must be at least 1 hour")