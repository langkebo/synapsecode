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
Matrix Synapse 联邦API处理器

这个模块处理联邦相关的操作，包括服务器发现、事件同步、房间加入等。
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class FederationHandler:
    """
    联邦处理器
    
    处理与其他Matrix服务器的联邦通信。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.store = hs.get_datastore()
        self.clock = hs.get_clock()
        self.config = hs.config
        self.federation_client = hs.get_federation_client()
        self.event_auth = hs.get_event_auth()
        
    async def send_event_to_server(self, destination: str, event: Dict[str, Any]) -> bool:
        """
        向远程服务器发送事件
        
        Args:
            destination: 目标服务器
            event: 要发送的事件
            
        Returns:
            发送成功返回True，否则返回False
        """
        logger.info(f"Sending event {event.get('event_id')} to {destination}")
        
        try:
            result = await self.federation_client.send_event(
                destination, event
            )
            logger.info(f"Event sent successfully to {destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to send event to {destination}: {e}")
            return False
            
    async def get_event_from_server(self, destination: str, event_id: str) -> Optional[Dict[str, Any]]:
        """
        从远程服务器获取事件
        
        Args:
            destination: 目标服务器
            event_id: 事件ID
            
        Returns:
            事件数据，如果获取失败则返回None
        """
        logger.debug(f"Getting event {event_id} from {destination}")
        
        try:
            event = await self.federation_client.get_event(
                destination, event_id
            )
            
            # 验证事件
            if await self._validate_event(event):
                return event
            else:
                logger.warning(f"Event {event_id} from {destination} failed validation")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get event {event_id} from {destination}: {e}")
            return None
            
    async def _validate_event(self, event: Dict[str, Any]) -> bool:
        """
        验证事件的有效性
        
        Args:
            event: 要验证的事件
            
        Returns:
            事件有效返回True，否则返回False
        """
        try:
            # 检查必需字段
            required_fields = ["event_id", "type", "room_id", "sender", "origin_server_ts"]
            for field in required_fields:
                if field not in event:
                    logger.warning(f"Event missing required field: {field}")
                    return False
                    
            # 验证事件签名和授权
            auth_result = await self.event_auth.check_auth_rules_for_event(event)
            if not auth_result:
                logger.warning(f"Event {event['event_id']} failed auth check")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating event: {e}")
            return False
            
    async def join_room_via_federation(self, room_id: str, user_id: str,
                                      remote_servers: List[str]) -> Dict[str, Any]:
        """
        通过联邦加入远程房间
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            remote_servers: 远程服务器列表
            
        Returns:
            加入结果
        """
        logger.info(f"Joining room {room_id} via federation for user {user_id}")
        
        for server in remote_servers:
            try:
                # 尝试从服务器获取房间信息
                room_info = await self.federation_client.get_room_state(
                    server, room_id
                )
                
                if room_info:
                    # 创建加入事件
                    join_event = await self._create_join_event(
                        room_id, user_id, server
                    )
                    
                    # 发送加入请求
                    join_result = await self.federation_client.send_join(
                        server, room_id, join_event
                    )
                    
                    if join_result:
                        # 存储房间状态和事件
                        await self._store_room_state(room_id, join_result["state"])
                        await self.store.store_event(join_event)
                        
                        logger.info(f"Successfully joined room {room_id} via {server}")
                        return {"room_id": room_id, "server": server}
                        
            except Exception as e:
                logger.warning(f"Failed to join room via {server}: {e}")
                continue
                
        raise RuntimeError(f"Failed to join room {room_id} via any server")
        
    async def _create_join_event(self, room_id: str, user_id: str, 
                                via_server: str) -> Dict[str, Any]:
        """
        创建加入事件
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            via_server: 通过的服务器
            
        Returns:
            加入事件
        """
        # 获取房间的加入模板
        join_template = await self.federation_client.make_join(
            via_server, room_id, user_id
        )
        
        # 填充事件内容
        join_event = join_template["event"]
        join_event["content"] = {"membership": "join"}
        join_event["origin"] = self.hs.hostname
        join_event["origin_server_ts"] = self.clock.time_msec()
        
        # 签名事件
        await self._sign_event(join_event)
        
        return join_event
        
    async def _sign_event(self, event: Dict[str, Any]):
        """
        对事件进行签名
        
        Args:
            event: 要签名的事件
        """
        # 这里应该实现实际的事件签名逻辑
        # 简化实现
        event["signatures"] = {
            self.hs.hostname: {
                f"ed25519:{self.hs.signing_key_id}": "signature_placeholder"
            }
        }
        
    async def _store_room_state(self, room_id: str, state_events: List[Dict[str, Any]]):
        """
        存储房间状态
        
        Args:
            room_id: 房间ID
            state_events: 状态事件列表
        """
        logger.debug(f"Storing state for room {room_id}")
        
        for event in state_events:
            # 验证事件
            if await self._validate_event(event):
                await self.store.store_event(event)
            else:
                logger.warning(f"Skipping invalid state event: {event.get('event_id')}")
                
    async def invite_user_to_room(self, room_id: str, inviter_id: str,
                                 invitee_id: str) -> Dict[str, Any]:
        """
        邀请远程用户加入房间
        
        Args:
            room_id: 房间ID
            inviter_id: 邀请者ID
            invitee_id: 被邀请者ID
            
        Returns:
            邀请结果
        """
        logger.info(f"Inviting {invitee_id} to room {room_id}")
        
        # 解析被邀请者的服务器
        invitee_server = invitee_id.split(":")[1]
        
        # 创建邀请事件
        invite_event = await self._create_invite_event(
            room_id, inviter_id, invitee_id
        )
        
        try:
            # 发送邀请到远程服务器
            invite_result = await self.federation_client.send_invite(
                invitee_server, room_id, invite_event
            )
            
            if invite_result:
                # 存储邀请事件
                await self.store.store_event(invite_event)
                logger.info(f"Invitation sent successfully to {invitee_id}")
                return {"event_id": invite_event["event_id"]}
            else:
                raise RuntimeError("Failed to send invitation")
                
        except Exception as e:
            logger.error(f"Failed to invite {invitee_id}: {e}")
            raise
            
    async def _create_invite_event(self, room_id: str, inviter_id: str,
                                  invitee_id: str) -> Dict[str, Any]:
        """
        创建邀请事件
        
        Args:
            room_id: 房间ID
            inviter_id: 邀请者ID
            invitee_id: 被邀请者ID
            
        Returns:
            邀请事件
        """
        event = {
            "type": "m.room.member",
            "room_id": room_id,
            "sender": inviter_id,
            "state_key": invitee_id,
            "content": {"membership": "invite"},
            "origin": self.hs.hostname,
            "origin_server_ts": self.clock.time_msec(),
            "event_id": f"${self._generate_event_id()}:{self.hs.hostname}"
        }
        
        # 签名事件
        await self._sign_event(event)
        
        return event
        
    def _generate_event_id(self) -> str:
        """
        生成事件ID的本地部分
        
        Returns:
            事件ID本地部分
        """
        import secrets
        return secrets.token_urlsafe(32)
        
    async def get_room_state_from_server(self, destination: str, 
                                       room_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        从远程服务器获取房间状态
        
        Args:
            destination: 目标服务器
            room_id: 房间ID
            
        Returns:
            房间状态事件列表，如果获取失败则返回None
        """
        logger.debug(f"Getting room state for {room_id} from {destination}")
        
        try:
            state_events = await self.federation_client.get_room_state(
                destination, room_id
            )
            
            # 验证所有状态事件
            validated_events = []
            for event in state_events:
                if await self._validate_event(event):
                    validated_events.append(event)
                else:
                    logger.warning(f"Invalid state event from {destination}: {event.get('event_id')}")
                    
            return validated_events
            
        except Exception as e:
            logger.error(f"Failed to get room state from {destination}: {e}")
            return None
            
    async def backfill_events(self, destination: str, room_id: str,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        从远程服务器回填历史事件
        
        Args:
            destination: 目标服务器
            room_id: 房间ID
            limit: 事件数量限制
            
        Returns:
            历史事件列表
        """
        logger.info(f"Backfilling events for room {room_id} from {destination}")
        
        try:
            events = await self.federation_client.backfill(
                destination, room_id, limit
            )
            
            # 验证和存储事件
            stored_events = []
            for event in events:
                if await self._validate_event(event):
                    await self.store.store_event(event)
                    stored_events.append(event)
                else:
                    logger.warning(f"Invalid backfilled event: {event.get('event_id')}")
                    
            logger.info(f"Backfilled {len(stored_events)} events for room {room_id}")
            return stored_events
            
        except Exception as e:
            logger.error(f"Failed to backfill events from {destination}: {e}")
            return []
            
    async def handle_incoming_event(self, origin: str, 
                                   event: Dict[str, Any]) -> bool:
        """
        处理来自远程服务器的事件
        
        Args:
            origin: 事件来源服务器
            event: 接收到的事件
            
        Returns:
            处理成功返回True，否则返回False
        """
        logger.debug(f"Handling incoming event {event.get('event_id')} from {origin}")
        
        try:
            # 验证事件来源
            if event.get("origin") != origin:
                logger.warning(f"Event origin mismatch: {event.get('origin')} != {origin}")
                return False
                
            # 验证事件
            if not await self._validate_event(event):
                logger.warning(f"Invalid incoming event from {origin}")
                return False
                
            # 检查是否已经处理过这个事件
            existing_event = await self.store.get_event_by_id(event["event_id"])
            if existing_event:
                logger.debug(f"Event {event['event_id']} already processed")
                return True
                
            # 存储事件
            await self.store.store_event(event)
            
            logger.debug(f"Successfully processed incoming event {event['event_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle incoming event from {origin}: {e}")
            return False  # pyright: ignore[reportUnreachable]