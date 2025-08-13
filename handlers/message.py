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
Matrix Synapse 消息处理器

这个模块处理消息相关的操作，包括发送消息、接收消息、消息历史等。
"""

import logging
import secrets
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    消息处理器
    
    处理房间内的消息发送、接收和历史记录。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.store = hs.get_datastore()
        self.clock = hs.get_clock()
        self.config = hs.config
        self.event_builder = hs.get_event_builder()
        
    def _generate_event_id(self) -> str:
        """
        生成事件ID
        
        Returns:
            事件ID字符串
        """
        event_localpart = secrets.token_urlsafe(32)
        return f"${event_localpart}:{self.hs.hostname}"
        
    async def send_message(self, room_id: str, sender_id: str, 
                          message_type: str, content: Dict[str, Any],
                          txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        发送消息到房间
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            message_type: 消息类型
            content: 消息内容
            txn_id: 事务ID
            
        Returns:
            发送结果，包含事件ID
        """
        logger.info(f"Sending message to room {room_id} from {sender_id}")
        
        # 检查用户是否在房间中
        membership = await self.store.get_room_membership(sender_id, room_id)
        if membership != "join":
            raise ValueError(f"User {sender_id} is not in room {room_id}")
            
        # 如果提供了事务ID，检查是否已经处理过
        if txn_id:
            existing_event = await self.store.get_event_by_txn_id(
                sender_id, room_id, txn_id
            )
            if existing_event:
                return {"event_id": existing_event["event_id"]}
                
        # 生成事件ID
        event_id = self._generate_event_id()
        
        # 创建消息事件
        event = await self.event_builder.create_event(
            event_type=f"m.room.message",
            room_id=room_id,
            sender=sender_id,
            content={
                "msgtype": message_type,
                **content
            },
            event_id=event_id,
            txn_id=txn_id
        )
        
        # 存储事件
        await self.store.store_event(event)
        
        # 如果有事务ID，存储映射关系
        if txn_id:
            await self.store.store_txn_id_mapping(
                sender_id, room_id, txn_id, event_id
            )
            
        logger.info(f"Message sent successfully: {event_id}")
        return {"event_id": event_id}
        
    async def send_text_message(self, room_id: str, sender_id: str, 
                               body: str, txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        发送文本消息
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            body: 消息内容
            txn_id: 事务ID
            
        Returns:
            发送结果
        """
        content = {
            "body": body
        }
        
        return await self.send_message(
            room_id, sender_id, "m.text", content, txn_id
        )
        
    async def send_image_message(self, room_id: str, sender_id: str,
                                body: str, url: str, info: Dict[str, Any],
                                txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        发送图片消息
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            body: 图片描述
            url: 图片URL
            info: 图片信息（尺寸、大小等）
            txn_id: 事务ID
            
        Returns:
            发送结果
        """
        content = {
            "body": body,
            "url": url,
            "info": info
        }
        
        return await self.send_message(
            room_id, sender_id, "m.image", content, txn_id
        )
        
    async def send_file_message(self, room_id: str, sender_id: str,
                               body: str, url: str, info: Dict[str, Any],
                               txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        发送文件消息
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            body: 文件名
            url: 文件URL
            info: 文件信息（大小、类型等）
            txn_id: 事务ID
            
        Returns:
            发送结果
        """
        content = {
            "body": body,
            "url": url,
            "info": info,
            "filename": body
        }
        
        return await self.send_message(
            room_id, sender_id, "m.file", content, txn_id
        )
        
    async def edit_message(self, room_id: str, sender_id: str,
                          original_event_id: str, new_content: Dict[str, Any],
                          txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        编辑消息
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            original_event_id: 原始事件ID
            new_content: 新的消息内容
            txn_id: 事务ID
            
        Returns:
            编辑结果
        """
        logger.info(f"Editing message {original_event_id} in room {room_id}")
        
        # 检查原始事件是否存在且属于发送者
        original_event = await self.store.get_event_by_id(original_event_id)
        if not original_event:
            raise ValueError(f"Event {original_event_id} not found")
            
        if original_event["sender"] != sender_id:
            raise ValueError("Cannot edit message from another user")
            
        # 创建编辑事件
        content = {
            "m.new_content": new_content,
            "m.relates_to": {
                "rel_type": "m.replace",
                "event_id": original_event_id
            },
            **new_content  # 向后兼容
        }
        
        return await self.send_message(
            room_id, sender_id, new_content.get("msgtype", "m.text"), 
            content, txn_id
        )
        
    async def react_to_message(self, room_id: str, sender_id: str,
                              target_event_id: str, reaction: str,
                              txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        对消息添加反应
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            target_event_id: 目标事件ID
            reaction: 反应内容（如emoji）
            txn_id: 事务ID
            
        Returns:
            反应结果
        """
        logger.info(f"Adding reaction to message {target_event_id} in room {room_id}")
        
        # 检查目标事件是否存在
        target_event = await self.store.get_event_by_id(target_event_id)
        if not target_event:
            raise ValueError(f"Event {target_event_id} not found")
            
        # 生成事件ID
        event_id = self._generate_event_id()
        
        # 创建反应事件
        event = await self.event_builder.create_event(
            event_type="m.reaction",
            room_id=room_id,
            sender=sender_id,
            content={
                "m.relates_to": {
                    "rel_type": "m.annotation",
                    "event_id": target_event_id,
                    "key": reaction
                }
            },
            event_id=event_id,
            txn_id=txn_id
        )
        
        # 存储事件
        await self.store.store_event(event)
        
        logger.info(f"Reaction added successfully: {event_id}")
        return {"event_id": event_id}
        
    async def redact_message(self, room_id: str, sender_id: str,
                            target_event_id: str, reason: Optional[str] = None,
                            txn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        删除/编辑消息
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            target_event_id: 目标事件ID
            reason: 删除原因
            txn_id: 事务ID
            
        Returns:
            删除结果
        """
        logger.info(f"Redacting message {target_event_id} in room {room_id}")
        
        # 检查目标事件是否存在
        target_event = await self.store.get_event_by_id(target_event_id)
        if not target_event:
            raise ValueError(f"Event {target_event_id} not found")
            
        # 检查权限（只能删除自己的消息或有管理员权限）
        if target_event["sender"] != sender_id:
            # 检查是否有删除权限
            power_level = await self.store.get_user_power_level(
                sender_id, room_id
            )
            redact_level = await self.store.get_room_redact_level(room_id)
            
            if power_level < redact_level:
                raise ValueError("Insufficient permissions to redact message")
                
        # 生成事件ID
        event_id = self._generate_event_id()
        
        # 创建删除事件
        content = {}
        if reason:
            content["reason"] = reason
            
        event = await self.event_builder.create_event(
            event_type="m.room.redaction",
            room_id=room_id,
            sender=sender_id,
            content=content,
            redacts=target_event_id,
            event_id=event_id,
            txn_id=txn_id
        )
        
        # 存储事件
        await self.store.store_event(event)
        
        # 更新原始事件为已删除状态
        await self.store.redact_event(target_event_id, event_id)
        
        logger.info(f"Message redacted successfully: {event_id}")
        return {"event_id": event_id}
        
    async def get_room_messages(self, room_id: str, user_id: str,
                               from_token: Optional[str] = None,
                               to_token: Optional[str] = None,
                               direction: str = "b",
                               limit: int = 10) -> Dict[str, Any]:
        """
        获取房间消息历史
        
        Args:
            room_id: 房间ID
            user_id: 请求用户ID
            from_token: 起始令牌
            to_token: 结束令牌
            direction: 方向（"b"向后，"f"向前）
            limit: 消息数量限制
            
        Returns:
            消息列表和分页令牌
        """
        logger.debug(f"Getting messages for room {room_id}")
        
        # 检查用户是否有权限查看房间消息
        membership = await self.store.get_room_membership(user_id, room_id)
        if membership not in ["join", "invite", "leave"]:
            raise ValueError(f"User {user_id} cannot view room {room_id} messages")
            
        # 获取消息
        messages = await self.store.get_room_messages(
            room_id=room_id,
            from_token=from_token,
            to_token=to_token,
            direction=direction,
            limit=limit
        )
        
        return {
            "chunk": messages["events"],
            "start": messages["start"],
            "end": messages["end"],
            "prev_batch": messages.get("prev_batch"),
            "next_batch": messages.get("next_batch")
        }
        
    async def get_event_context(self, room_id: str, event_id: str,
                               user_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        获取事件上下文
        
        Args:
            room_id: 房间ID
            event_id: 事件ID
            user_id: 请求用户ID
            limit: 上下文消息数量限制
            
        Returns:
            事件上下文信息
        """
        logger.debug(f"Getting context for event {event_id} in room {room_id}")
        
        # 检查用户是否有权限查看房间
        membership = await self.store.get_room_membership(user_id, room_id)
        if membership not in ["join", "invite", "leave"]:
            raise ValueError(f"User {user_id} cannot view room {room_id}")
            
        # 获取事件上下文
        context = await self.store.get_event_context(
            room_id, event_id, limit
        )
        
        return {
            "event": context["event"],
            "events_before": context["events_before"],
            "events_after": context["events_after"],
            "start": context["start"],
            "end": context["end"],
            "state": context["state"]
        }