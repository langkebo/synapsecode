# Copyright 2024 OpenMarket Ltd
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

import logging
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any

from synapse.api.errors import (
    AuthError,
    Codes,
    NotFoundError,
    SynapseError,
)
from synapse.types import JsonDict, Requester, UserID
from synapse.util.caches.descriptors import cached
from synapse.util.stringutils import random_string

if TYPE_CHECKING:
    from synapse.server import HomeServer

logger = logging.getLogger(__name__)

# 好友请求状态常量
FRIEND_REQUEST_PENDING = "pending"
FRIEND_REQUEST_ACCEPTED = "accepted"
FRIEND_REQUEST_REJECTED = "rejected"

# 好友关系状态常量
FRIEND_STATUS_ACTIVE = "active"
FRIEND_STATUS_BLOCKED = "blocked"


class FriendsHandler:
    """处理好友关系管理的业务逻辑
    
    包括好友请求、好友列表、好友搜索等功能
    """

    def __init__(self, hs: "HomeServer"):
        self.store = hs.get_datastores().main
        self.clock = hs.get_clock()
        self.hs = hs
        self.auth = hs.get_auth()
        self.user_directory_handler = hs.get_user_directory_handler()
        self.profile_handler = hs.get_profile_handler()
        self._is_mine_server_name = hs.is_mine_server_name
        
        # 速率限制：每个用户每小时最多发送10个好友请求
        self._rate_limit_cache: Dict[str, List[float]] = {}
        self._max_requests_per_hour = 10
        self._rate_limit_window = 3600  # 1小时
        
    def _check_rate_limit(self, user_id: str) -> None:
        """检查用户是否超过速率限制"""
        current_time = time.time()
        
        if user_id not in self._rate_limit_cache:
            self._rate_limit_cache[user_id] = []
            
        # 清理过期的请求记录
        self._rate_limit_cache[user_id] = [
            timestamp for timestamp in self._rate_limit_cache[user_id]
            if current_time - timestamp < self._rate_limit_window
        ]
        
        # 检查是否超过限制
        if len(self._rate_limit_cache[user_id]) >= self._max_requests_per_hour:
            raise SynapseError(
                429, 
                f"Rate limit exceeded. Maximum {self._max_requests_per_hour} friend requests per hour.",
                Codes.LIMIT_EXCEEDED
            )
            
        # 记录当前请求
        self._rate_limit_cache[user_id].append(current_time)
        
    def _validate_user_id(self, user_id: str) -> None:
        """验证用户ID格式"""
        if not user_id or not isinstance(user_id, str):
            raise SynapseError(400, "Invalid user ID", Codes.INVALID_PARAM)
        if len(user_id) > 255:  # 防止过长的用户ID
            raise SynapseError(400, "User ID too long", Codes.INVALID_PARAM)
        if user_id.startswith('@') and ':' not in user_id:
            raise SynapseError(400, "Invalid user ID format", Codes.INVALID_PARAM)

    async def send_friend_request(
        self, requester: Requester, target_user_id: str, message: Optional[str] = None
    ) -> JsonDict:
        """发送好友请求
        
        Args:
            requester: 发送请求的用户
            target_user_id: 目标用户ID
            message: 可选的请求消息
            
        Returns:
            包含请求ID和状态的字典
            
        Raises:
            SynapseError: 如果用户已经是好友或已有待处理请求
        """
        sender_user_id = requester.user.to_string()
        logger.info(f"User {sender_user_id} sending friend request to {target_user_id}")
        
        try:
            # 验证输入
            self._validate_user_id(sender_user_id)
            self._validate_user_id(target_user_id)
            
            # 检查速率限制
            self._check_rate_limit(sender_user_id)
            
            # 验证目标用户ID格式
            if not UserID.is_valid(target_user_id):
                logger.warning(f"Invalid target user ID format: {target_user_id}")
                raise SynapseError(400, "Invalid user ID", Codes.INVALID_PARAM)
                
            target_user = UserID.from_string(target_user_id)
            
            # 不能向自己发送好友请求
            if sender_user_id == target_user_id:
                logger.warning(f"User {sender_user_id} attempted to send friend request to self")
                raise SynapseError(400, "Cannot send friend request to yourself", Codes.INVALID_PARAM)
                
            # 检查是否被屏蔽
            is_blocked = await self.store.is_user_blocked(target_user_id, sender_user_id)
            if is_blocked:
                logger.warning(f"User {sender_user_id} is blocked by {target_user_id}")
                raise SynapseError(403, "Cannot send friend request to this user", Codes.FORBIDDEN)
                
            # 检查是否已经是好友
            existing_friendship = await self.store.get_friendship(
                sender_user_id, target_user_id
            )
            if existing_friendship:
                logger.warning(f"Users {sender_user_id} and {target_user_id} are already friends")
                raise SynapseError(400, "Users are already friends", Codes.INVALID_PARAM)
                
            # 检查是否已有待处理的请求
            existing_request = await self.store.get_friend_request(
                sender_user_id, target_user_id
            )
            if existing_request and existing_request["status"] == FRIEND_REQUEST_PENDING:
                logger.warning(f"Pending friend request already exists from {sender_user_id} to {target_user_id}")
                raise SynapseError(400, "Friend request already pending", Codes.INVALID_PARAM)
                
            # 创建好友请求
            request_id = await self.store.create_friend_request(
                sender_user_id=sender_user_id,
                target_user_id=target_user_id,
                message=message,
                created_ts=self.clock.time_msec(),
            )
            
            logger.info(f"Friend request {request_id} created successfully from {sender_user_id} to {target_user_id}")
            
            return {
                "request_id": request_id,
                "status": FRIEND_REQUEST_PENDING,
                "created_ts": self.clock.time_msec(),
            }
        except SynapseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in send_friend_request: {e}")
            raise SynapseError(500, "Internal server error", Codes.UNKNOWN)

    async def respond_to_friend_request(
        self, requester: Requester, request_id: str, accept: bool
    ) -> JsonDict:
        """响应好友请求
        
        Args:
            requester: 响应请求的用户
            request_id: 好友请求ID
            accept: 是否接受请求
            
        Returns:
            包含响应状态的字典
            
        Raises:
            NotFoundError: 如果请求不存在
            AuthError: 如果用户无权响应此请求
        """
        user_id = requester.user.to_string()
        action = "accepting" if accept else "rejecting"
        logger.info(f"User {user_id} {action} friend request {request_id}")
        
        try:
            # 获取好友请求
            friend_request = await self.store.get_friend_request_by_id(request_id)
            if not friend_request:
                logger.warning(f"Friend request {request_id} not found")
                raise NotFoundError("Friend request not found")
                
            # 验证用户权限（只有目标用户可以响应请求）
            if friend_request["target_user_id"] != user_id:
                logger.warning(f"User {user_id} attempted to respond to request {request_id} not sent to them")
                raise AuthError(403, "You can only respond to requests sent to you")
                
            # 检查请求状态
            if friend_request["status"] != FRIEND_REQUEST_PENDING:
                logger.warning(f"Friend request {request_id} is no longer pending (status: {friend_request['status']})")
                raise SynapseError(400, "Friend request is no longer pending", Codes.INVALID_PARAM)
                
            # 更新请求状态
            new_status = FRIEND_REQUEST_ACCEPTED if accept else FRIEND_REQUEST_REJECTED
            await self.store.update_friend_request_status(
                request_id, new_status, self.clock.time_msec()
            )
            
            # 如果接受请求，创建好友关系
            if accept:
                await self.store.create_friendship(
                    user1_id=friend_request["sender_user_id"],
                    user2_id=friend_request["target_user_id"],
                    created_ts=self.clock.time_msec(),
                )
                # 清除缓存
                self.get_friends_list.invalidate((requester,))
                logger.info(f"Friendship created between {friend_request['sender_user_id']} and {friend_request['target_user_id']}")
            else:
                logger.info(f"Friend request {request_id} rejected by {user_id}")
                
            return {
                "request_id": request_id,
                "status": new_status,
                "accepted": accept,
            }
        except (NotFoundError, AuthError, SynapseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in respond_to_friend_request: {e}")
            raise SynapseError(500, "Internal server error", Codes.UNKNOWN)

    async def get_friend_requests(
        self, requester: Requester, direction: str = "received"
    ) -> List[JsonDict]:
        """获取好友请求列表
        
        Args:
            requester: 请求用户
            direction: "sent" 或 "received"
            
        Returns:
            好友请求列表
        """
        user_id = requester.user.to_string()
        
        if direction == "sent":
            requests = await self.store.get_friend_requests_sent_by_user(user_id)
        elif direction == "received":
            requests = await self.store.get_friend_requests_received_by_user(user_id)
        else:
            raise SynapseError(400, "Invalid direction parameter", Codes.INVALID_PARAM)
            
        # 为每个请求添加用户信息
        enriched_requests = []
        for request in requests:
            # 获取对方用户的基本信息
            other_user_id = (
                request["target_user_id"] if direction == "sent" 
                else request["sender_user_id"]
            )
            try:
                profile = await self.profile_handler.get_profile(other_user_id)
                request["user_profile"] = profile
            except Exception:
                # 如果获取用户信息失败，使用默认值
                request["user_profile"] = {
                    "displayname": None,
                    "avatar_url": None,
                }
            enriched_requests.append(request)
            
        return enriched_requests

    @cached()
    async def get_friends_list(self, requester: Requester) -> List[JsonDict]:
        """获取好友列表
        
        Args:
            requester: 请求用户
            
        Returns:
            好友列表，包含用户信息
        """
        user_id = requester.user.to_string()
        
        # 获取好友关系
        friendships = await self.store.get_user_friendships(user_id)
        
        # 为每个好友添加详细信息
        friends_list = []
        for friendship in friendships:
            friend_user_id = (
                friendship["user2_id"] if friendship["user1_id"] == user_id
                else friendship["user1_id"]
            )
            
            try:
                # 获取好友的个人资料
                profile = await self.profile_handler.get_profile(friend_user_id)
                friend_info = {
                    "user_id": friend_user_id,
                    "displayname": profile.get("displayname"),
                    "avatar_url": profile.get("avatar_url"),
                    "friendship_created_ts": friendship["created_ts"],
                    "status": friendship["status"],
                }
                friends_list.append(friend_info)
            except Exception as e:
                logger.warning(f"Failed to get profile for friend {friend_user_id}: {e}")
                # 即使获取资料失败，也要包含基本信息
                friend_info = {
                    "user_id": friend_user_id,
                    "displayname": None,
                    "avatar_url": None,
                    "friendship_created_ts": friendship["created_ts"],
                    "status": friendship["status"],
                }
                friends_list.append(friend_info)
                
        return friends_list

    async def remove_friend(
        self, requester: Requester, friend_user_id: str
    ) -> JsonDict:
        """删除好友关系
        
        Args:
            requester: 请求用户
            friend_user_id: 要删除的好友用户ID
            
        Returns:
            操作结果
            
        Raises:
            NotFoundError: 如果好友关系不存在
        """
        user_id = requester.user.to_string()
        
        # 验证好友用户ID格式
        if not UserID.is_valid(friend_user_id):
            raise SynapseError(400, "Invalid user ID", Codes.INVALID_PARAM)
            
        # 检查好友关系是否存在
        friendship = await self.store.get_friendship(user_id, friend_user_id)
        if not friendship:
            raise NotFoundError("Friendship not found")
            
        # 删除好友关系
        await self.store.remove_friendship(user_id, friend_user_id)
        
        # 清除缓存
        self.get_friends_list.invalidate((requester,))
        
        return {
            "removed": True,
            "user_id": friend_user_id,
        }

    async def search_users(
        self, requester: Requester, search_term: str, limit: int = 10
    ) -> List[JsonDict]:
        """搜索用户（用于添加好友）
        
        Args:
            requester: 请求用户
            search_term: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            用户搜索结果列表
        """
        user_id = requester.user.to_string()
        
        # 使用用户目录搜索
        search_results = await self.user_directory_handler.search_users(
            user_id, search_term, limit
        )
        
        # 为搜索结果添加好友状态信息
        enriched_results = []
        for user in search_results.get("results", []):
            result_user_id = user["user_id"]
            
            # 检查是否已经是好友
            friendship = await self.store.get_friendship(user_id, result_user_id)
            is_friend = friendship is not None
            
            # 检查是否有待处理的好友请求
            pending_request = await self.store.get_friend_request(user_id, result_user_id)
            has_pending_request = (
                pending_request is not None and 
                pending_request["status"] == FRIEND_REQUEST_PENDING
            )
            
            user["is_friend"] = is_friend
            user["has_pending_request"] = has_pending_request
            enriched_results.append(user)
            
        return enriched_results

    async def block_user(
        self, requester: Requester, target_user_id: str
    ) -> JsonDict:
        """屏蔽用户
        
        Args:
            requester: 请求用户
            target_user_id: 要屏蔽的用户ID
            
        Returns:
            操作结果
        """
        user_id = requester.user.to_string()
        
        # 验证目标用户ID格式
        if not UserID.is_valid(target_user_id):
            raise SynapseError(400, "Invalid user ID", Codes.INVALID_PARAM)
            
        # 不能屏蔽自己
        if user_id == target_user_id:
            raise SynapseError(400, "Cannot block yourself", Codes.INVALID_PARAM)
            
        # 如果存在好友关系，先删除
        friendship = await self.store.get_friendship(user_id, target_user_id)
        if friendship:
            await self.store.remove_friendship(user_id, target_user_id)
            
        # 创建屏蔽关系
        await self.store.create_user_block(
            blocker_user_id=user_id,
            blocked_user_id=target_user_id,
            created_ts=self.clock.time_msec(),
        )
        
        return {
            "blocked": True,
            "user_id": target_user_id,
        }

    async def unblock_user(
        self, requester: Requester, target_user_id: str
    ) -> JsonDict:
        """取消屏蔽用户
        
        Args:
            requester: 请求用户
            target_user_id: 要取消屏蔽的用户ID
            
        Returns:
            操作结果
        """
        user_id = requester.user.to_string()
        
        # 验证目标用户ID格式
        if not UserID.is_valid(target_user_id):
            raise SynapseError(400, "Invalid user ID", Codes.INVALID_PARAM)
            
        # 删除屏蔽关系
        removed = await self.store.remove_user_block(user_id, target_user_id)
        
        if not removed:
            raise NotFoundError("Block relationship not found")
            
        return {
            "unblocked": True,
            "user_id": target_user_id,
        }

    async def get_blocked_users(
        self, requester: Requester
    ) -> List[JsonDict]:
        """获取被屏蔽的用户列表
        
        Args:
            requester: 请求用户
            
        Returns:
            被屏蔽用户列表
        """
        user_id = requester.user.to_string()
        
        # 获取屏蔽关系
        blocks = await self.store.get_user_blocks(user_id)
        
        # 为每个被屏蔽用户添加基本信息
        blocked_users = []
        for block in blocks:
            blocked_user_id = block["blocked_user_id"]
            
            try:
                profile = await self.profile_handler.get_profile(blocked_user_id)
                user_info = {
                    "user_id": blocked_user_id,
                    "displayname": profile.get("displayname"),
                    "avatar_url": profile.get("avatar_url"),
                    "blocked_ts": block["created_ts"],
                }
                blocked_users.append(user_info)
            except Exception as e:
                logger.warning(f"Failed to get profile for blocked user {blocked_user_id}: {e}")
                user_info = {
                    "user_id": blocked_user_id,
                    "displayname": None,
                    "avatar_url": None,
                    "blocked_ts": block["created_ts"],
                }
                blocked_users.append(user_info)
                
        return blocked_users