# Copyright 2014-2016 OpenMarket Ltd
# Copyright 2018-2021 The Matrix.org Foundation C.I.C.
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

"""
Matrix Synapse 房间管理处理器

这个模块处理房间相关的操作，包括创建房间、加入房间、离开房间等。
"""

import logging
import secrets
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class RoomHandler:
    """
    房间管理处理器
    
    处理房间的创建、管理和成员操作。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.store = hs.get_datastore()
        self.clock = hs.get_clock()
        self.config = hs.config
        self.event_builder = hs.get_event_builder()
        
    def _generate_room_id(self) -> str:
        """
        生成房间ID
        
        Returns:
            房间ID字符串
        """
        room_localpart = secrets.token_urlsafe(18)
        return f"!{room_localpart}:{self.hs.hostname}"
        
    async def create_room(self, creator_user_id: str, 
                         config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建新房间
        
        Args:
            creator_user_id: 创建者用户ID
            config: 房间配置
            
        Returns:
            创建的房间信息
        """
        logger.info(f"Creating room for user: {creator_user_id}")
        
        if config is None:
            config = {}
            
        # 生成房间ID
        room_id = self._generate_room_id()
        
        # 设置默认房间配置
        room_config = {
            "room_id": room_id,
            "creator": creator_user_id,
            "creation_ts": self.clock.time_msec(),
            "room_version": config.get("room_version", "9"),
            "preset": config.get("preset", "private_chat"),
            "name": config.get("name"),
            "topic": config.get("topic"),
            "avatar_url": config.get("avatar_url"),
            "is_public": config.get("visibility") == "public",
            "guest_access": config.get("guest_access", "forbidden"),
            "history_visibility": config.get("history_visibility", "shared"),
            "join_rules": config.get("join_rules", "invite")
        }
        
        # 创建房间创建事件
        creation_event = await self._create_room_creation_event(
            room_id, creator_user_id, room_config
        )
        
        # 创建创建者加入事件
        join_event = await self._create_member_event(
            room_id, creator_user_id, creator_user_id, "join"
        )
        
        # 创建权限级别事件
        power_levels_event = await self._create_power_levels_event(
            room_id, creator_user_id, config.get("power_level_content_override")
        )
        
        # 存储房间和事件
        await self.store.create_room(room_config)
        await self.store.store_event(creation_event)
        await self.store.store_event(join_event)
        await self.store.store_event(power_levels_event)
        
        # 如果设置了房间名称，创建名称事件
        if room_config.get("name"):
            name_event = await self._create_name_event(
                room_id, creator_user_id, room_config["name"]
            )
            await self.store.store_event(name_event)
            
        # 如果设置了房间主题，创建主题事件
        if room_config.get("topic"):
            topic_event = await self._create_topic_event(
                room_id, creator_user_id, room_config["topic"]
            )
            await self.store.store_event(topic_event)
            
        logger.info(f"Room {room_id} created successfully")
        return {
            "room_id": room_id,
            "room_alias": config.get("room_alias_name"),
            "preset": room_config["preset"]
        }
        
    async def _create_room_creation_event(self, room_id: str, creator: str, 
                                         config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建房间创建事件
        
        Args:
            room_id: 房间ID
            creator: 创建者
            config: 房间配置
            
        Returns:
            房间创建事件
        """
        content = {
            "creator": creator,
            "room_version": config["room_version"]
        }
        
        if config.get("predecessor"):
            content["predecessor"] = config["predecessor"]
            
        return await self.event_builder.create_event(
            event_type="m.room.create",
            room_id=room_id,
            sender=creator,
            content=content,
            state_key=""
        )
        
    async def _create_member_event(self, room_id: str, sender: str, 
                                  target: str, membership: str,
                                  display_name: Optional[str] = None,
                                  avatar_url: Optional[str] = None) -> Dict[str, Any]:
        """
        创建成员事件
        
        Args:
            room_id: 房间ID
            sender: 发送者
            target: 目标用户
            membership: 成员状态
            display_name: 显示名称
            avatar_url: 头像URL
            
        Returns:
            成员事件
        """
        content = {
            "membership": membership
        }
        
        if display_name:
            content["displayname"] = display_name
        if avatar_url:
            content["avatar_url"] = avatar_url
            
        return await self.event_builder.create_event(
            event_type="m.room.member",
            room_id=room_id,
            sender=sender,
            content=content,
            state_key=target
        )
        
    async def _create_power_levels_event(self, room_id: str, creator: str,
                                        override_content: Optional[Dict] = None) -> Dict[str, Any]:
        """
        创建权限级别事件
        
        Args:
            room_id: 房间ID
            creator: 创建者
            override_content: 覆盖内容
            
        Returns:
            权限级别事件
        """
        content = {
            "ban": 50,
            "events": {
                "m.room.name": 50,
                "m.room.power_levels": 100,
                "m.room.history_visibility": 100,
                "m.room.canonical_alias": 50,
                "m.room.avatar": 50,
                "m.room.tombstone": 100,
                "m.room.server_acl": 100,
                "m.room.encryption": 100
            },
            "events_default": 0,
            "invite": 50,
            "kick": 50,
            "redact": 50,
            "state_default": 50,
            "users": {
                creator: 100
            },
            "users_default": 0,
            "notifications": {
                "room": 50
            }
        }
        
        if override_content:
            content.update(override_content)
            
        return await self.event_builder.create_event(
            event_type="m.room.power_levels",
            room_id=room_id,
            sender=creator,
            content=content,
            state_key=""
        )
        
    async def _create_name_event(self, room_id: str, sender: str, 
                                name: str) -> Dict[str, Any]:
        """
        创建房间名称事件
        
        Args:
            room_id: 房间ID
            sender: 发送者
            name: 房间名称
            
        Returns:
            房间名称事件
        """
        return await self.event_builder.create_event(
            event_type="m.room.name",
            room_id=room_id,
            sender=sender,
            content={"name": name},
            state_key=""
        )
        
    async def _create_topic_event(self, room_id: str, sender: str, 
                                 topic: str) -> Dict[str, Any]:
        """
        创建房间主题事件
        
        Args:
            room_id: 房间ID
            sender: 发送者
            topic: 房间主题
            
        Returns:
            房间主题事件
        """
        return await self.event_builder.create_event(
            event_type="m.room.topic",
            room_id=room_id,
            sender=sender,
            content={"topic": topic},
            state_key=""
        )
        
    async def join_room(self, user_id: str, room_id: str, 
                       remote_room_hosts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        用户加入房间
        
        Args:
            user_id: 用户ID
            room_id: 房间ID
            remote_room_hosts: 远程房间主机列表
            
        Returns:
            加入结果
        """
        logger.info(f"User {user_id} joining room {room_id}")
        
        # 检查房间是否存在
        room = await self.store.get_room_by_id(room_id)
        if not room and not remote_room_hosts:
            raise ValueError(f"Room {room_id} not found")
            
        # 检查用户是否已经在房间中
        current_membership = await self.store.get_room_membership(
            user_id, room_id
        )
        
        if current_membership == "join":
            return {"room_id": room_id}
            
        # 创建加入事件
        join_event = await self._create_member_event(
            room_id, user_id, user_id, "join"
        )
        
        # 存储事件
        await self.store.store_event(join_event)
        
        logger.info(f"User {user_id} joined room {room_id} successfully")
        return {"room_id": room_id}
        
    async def leave_room(self, user_id: str, room_id: str, 
                        reason: Optional[str] = None) -> Dict[str, Any]:
        """
        用户离开房间
        
        Args:
            user_id: 用户ID
            room_id: 房间ID
            reason: 离开原因
            
        Returns:
            离开结果
        """
        logger.info(f"User {user_id} leaving room {room_id}")
        
        # 检查用户是否在房间中
        current_membership = await self.store.get_room_membership(
            user_id, room_id
        )
        
        if current_membership != "join":
            raise ValueError(f"User {user_id} is not in room {room_id}")
            
        # 创建离开事件
        content = {"membership": "leave"}
        if reason:
            content["reason"] = reason
            
        leave_event = await self.event_builder.create_event(
            event_type="m.room.member",
            room_id=room_id,
            sender=user_id,
            content=content,
            state_key=user_id
        )
        
        # 存储事件
        await self.store.store_event(leave_event)
        
        logger.info(f"User {user_id} left room {room_id} successfully")
        return {"room_id": room_id}
        
    async def invite_user(self, inviter_id: str, invitee_id: str, 
                         room_id: str) -> Dict[str, Any]:
        """
        邀请用户加入房间
        
        Args:
            inviter_id: 邀请者ID
            invitee_id: 被邀请者ID
            room_id: 房间ID
            
        Returns:
            邀请结果
        """
        logger.info(f"User {inviter_id} inviting {invitee_id} to room {room_id}")
        
        # 检查邀请者是否有权限邀请
        inviter_membership = await self.store.get_room_membership(
            inviter_id, room_id
        )
        
        if inviter_membership != "join":
            raise ValueError(f"User {inviter_id} cannot invite to room {room_id}")
            
        # 检查被邀请者当前状态
        invitee_membership = await self.store.get_room_membership(
            invitee_id, room_id
        )
        
        if invitee_membership == "join":
            raise ValueError(f"User {invitee_id} is already in room {room_id}")
            
        # 创建邀请事件
        invite_event = await self._create_member_event(
            room_id, inviter_id, invitee_id, "invite"
        )
        
        # 存储事件
        await self.store.store_event(invite_event)
        
        logger.info(f"User {invitee_id} invited to room {room_id} successfully")
        return {"room_id": room_id}
        
    async def get_room_state(self, room_id: str, 
                           user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取房间状态
        
        Args:
            room_id: 房间ID
            user_id: 请求用户ID（用于权限检查）
            
        Returns:
            房间状态事件列表
        """
        logger.debug(f"Getting room state for {room_id}")
        
        # 如果指定了用户，检查用户是否有权限查看房间状态
        if user_id:
            membership = await self.store.get_room_membership(user_id, room_id)
            if membership not in ["join", "invite"]:
                raise ValueError(f"User {user_id} cannot view room {room_id} state")
                
        # 获取房间状态事件
        state_events = await self.store.get_room_state_events(room_id)
        
        return state_events
        
    async def get_room_members(self, room_id: str, 
                             user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取房间成员列表
        
        Args:
            room_id: 房间ID
            user_id: 请求用户ID（用于权限检查）
            
        Returns:
            房间成员列表
        """
        logger.debug(f"Getting room members for {room_id}")
        
        # 如果指定了用户，检查用户是否有权限查看房间成员
        if user_id:
            membership = await self.store.get_room_membership(user_id, room_id)
            if membership not in ["join", "invite"]:
                raise ValueError(f"User {user_id} cannot view room {room_id} members")
                
        # 获取房间成员
        members = await self.store.get_room_members(room_id)
        
        return members  # pyright: ignore[reportUnreachable]