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
Matrix Synapse 消息API

这个模块实现了Matrix协议的消息相关API端点。
"""

import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MessageAPI:
    """
    消息API处理器
    
    实现Matrix协议的消息发送、获取、编辑等API端点。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.auth_handler = hs.get_auth_handler()
        self.room_handler = hs.get_room_handler()
        self.message_handler = hs.get_message_handler()
        self.clock = hs.get_clock()
        
    async def handle_send_message(self, access_token: str, room_id: str,
                                event_type: str, txn_id: str,
                                request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发送消息请求
        
        PUT /_matrix/client/r0/rooms/{roomId}/send/{eventType}/{txnId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_type: 事件类型
            txn_id: 事务ID
            request_data: 请求数据
            
        Returns:
            发送消息响应
        """
        logger.info(f"Processing send message request: {room_id}/{event_type}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 检查是否为重复事务
            existing_event = await self.message_handler.get_event_by_txn_id(
                user_id, txn_id
            )
            if existing_event:
                return {
                    'event_id': existing_event['event_id']
                }, 200
                
            # 发送消息
            event_id = await self.message_handler.send_message(
                sender_id=user_id,
                room_id=room_id,
                event_type=event_type,
                content=request_data,
                txn_id=txn_id
            )
            
            logger.info(f"Message sent successfully: {event_id}")
            
            return {
                'event_id': event_id
            }, 200
            
        except ValueError as e:
            logger.warning(f"Send message failed: {e}")
            return {
                'errcode': 'M_INVALID_PARAM',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_messages(self, access_token: str, room_id: str,
                                from_token: Optional[str] = None,
                                to_token: Optional[str] = None,
                                direction: str = 'b',
                                limit: int = 10,
                                filter_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理获取消息请求
        
        GET /_matrix/client/r0/rooms/{roomId}/messages
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            from_token: 起始令牌
            to_token: 结束令牌
            direction: 方向（'b'向后，'f'向前）
            limit: 限制数量
            filter_dict: 过滤条件
            
        Returns:
            获取消息响应
        """
        logger.debug(f"Processing get messages request: {room_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 获取消息
            messages_data = await self.message_handler.get_room_messages(
                room_id=room_id,
                from_token=from_token,
                to_token=to_token,
                direction=direction,
                limit=limit,
                filter_dict=filter_dict
            )
            
            return {
                'start': messages_data['start'],
                'end': messages_data['end'],
                'chunk': messages_data['events'],
                'state': messages_data.get('state', [])
            }, 200
            
        except ValueError as e:
            logger.warning(f"Get messages failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Get messages error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_event(self, access_token: str, room_id: str,
                             event_id: str) -> Dict[str, Any]:
        """
        处理获取单个事件请求
        
        GET /_matrix/client/r0/rooms/{roomId}/event/{eventId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_id: 事件ID
            
        Returns:
            获取事件响应
        """
        logger.debug(f"Processing get event request: {room_id}/{event_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 获取事件
            event = await self.message_handler.get_event(event_id, room_id)
            
            if not event:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Event not found'
                }, 404
                
            return event, 200
            
        except ValueError as e:
            logger.warning(f"Get event failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Get event error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_event_context(self, access_token: str, room_id: str,
                                     event_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        处理获取事件上下文请求
        
        GET /_matrix/client/r0/rooms/{roomId}/context/{eventId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_id: 事件ID
            limit: 限制数量
            
        Returns:
            获取事件上下文响应
        """
        logger.debug(f"Processing get event context request: {room_id}/{event_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 获取事件上下文
            context = await self.message_handler.get_event_context(
                room_id=room_id,
                event_id=event_id,
                limit=limit
            )
            
            if not context:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Event not found'
                }, 404
                
            return {
                'start': context['start'],
                'end': context['end'],
                'events_before': context['events_before'],
                'event': context['event'],
                'events_after': context['events_after'],
                'state': context['state']
            }, 200
            
        except ValueError as e:
            logger.warning(f"Get event context failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Get event context error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_redact_event(self, access_token: str, room_id: str,
                                event_id: str, txn_id: str,
                                request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理删除事件请求
        
        PUT /_matrix/client/r0/rooms/{roomId}/redact/{eventId}/{txnId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_id: 事件ID
            txn_id: 事务ID
            request_data: 请求数据
            
        Returns:
            删除事件响应
        """
        logger.info(f"Processing redact event request: {room_id}/{event_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 检查是否为重复事务
            existing_event = await self.message_handler.get_event_by_txn_id(
                user_id, txn_id
            )
            if existing_event:
                return {
                    'event_id': existing_event['event_id']
                }, 200
                
            # 获取原始事件
            original_event = await self.message_handler.get_event(event_id, room_id)
            if not original_event:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Event not found'
                }, 404
                
            # 检查权限（用户可以删除自己的消息或管理员可以删除任何消息）
            can_redact = (
                original_event['sender'] == user_id or
                await self.room_handler.check_user_power_level(
                    user_id=user_id,
                    room_id=room_id,
                    required_level=50
                )
            )
            
            if not can_redact:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Insufficient permission to redact event'
                }, 403
                
            # 删除事件
            reason = request_data.get('reason') if request_data else None
            redaction_event_id = await self.message_handler.redact_event(
                redacter_id=user_id,
                room_id=room_id,
                event_id=event_id,
                reason=reason,
                txn_id=txn_id
            )
            
            logger.info(f"Event redacted successfully: {redaction_event_id}")
            
            return {
                'event_id': redaction_event_id
            }, 200
            
        except ValueError as e:
            logger.warning(f"Redact event failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Redact event error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_send_reaction(self, access_token: str, room_id: str,
                                 event_id: str, reaction: str,
                                 txn_id: str) -> Dict[str, Any]:
        """
        处理发送反应请求
        
        PUT /_matrix/client/r0/rooms/{roomId}/send/m.reaction/{txnId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_id: 目标事件ID
            reaction: 反应内容
            txn_id: 事务ID
            
        Returns:
            发送反应响应
        """
        logger.info(f"Processing send reaction request: {room_id}/{event_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 检查目标事件是否存在
            target_event = await self.message_handler.get_event(event_id, room_id)
            if not target_event:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Target event not found'
                }, 404
                
            # 发送反应
            reaction_event_id = await self.message_handler.send_reaction(
                sender_id=user_id,
                room_id=room_id,
                target_event_id=event_id,
                reaction=reaction,
                txn_id=txn_id
            )
            
            logger.info(f"Reaction sent successfully: {reaction_event_id}")
            
            return {
                'event_id': reaction_event_id
            }, 200
            
        except ValueError as e:
            logger.warning(f"Send reaction failed: {e}")
            return {
                'errcode': 'M_INVALID_PARAM',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Send reaction error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_edit_message(self, access_token: str, room_id: str,
                                event_id: str, new_content: Dict[str, Any],
                                txn_id: str) -> Dict[str, Any]:
        """
        处理编辑消息请求
        
        PUT /_matrix/client/r0/rooms/{roomId}/send/m.room.message/{txnId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_id: 原始事件ID
            new_content: 新内容
            txn_id: 事务ID
            
        Returns:
            编辑消息响应
        """
        logger.info(f"Processing edit message request: {room_id}/{event_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 检查原始事件是否存在且属于该用户
            original_event = await self.message_handler.get_event(event_id, room_id)
            if not original_event:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Original event not found'
                }, 404
                
            if original_event['sender'] != user_id:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Can only edit own messages'
                }, 403
                
            # 编辑消息
            edit_event_id = await self.message_handler.edit_message(
                sender_id=user_id,
                room_id=room_id,
                original_event_id=event_id,
                new_content=new_content,
                txn_id=txn_id
            )
            
            logger.info(f"Message edited successfully: {edit_event_id}")
            
            return {
                'event_id': edit_event_id
            }, 200
            
        except ValueError as e:
            logger.warning(f"Edit message failed: {e}")
            return {
                'errcode': 'M_INVALID_PARAM',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Edit message error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_typing(self, access_token: str, room_id: str,
                          request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理输入状态请求
        
        PUT /_matrix/client/r0/rooms/{roomId}/typing/{userId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            request_data: 请求数据
            
        Returns:
            输入状态响应
        """
        logger.debug(f"Processing typing request: {room_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 设置输入状态
            typing = request_data.get('typing', False)
            timeout = request_data.get('timeout', 30000)  # 默认30秒
            
            await self.message_handler.set_typing_state(
                user_id=user_id,
                room_id=room_id,
                typing=typing,
                timeout=timeout
            )
            
            return {}, 200
            
        except Exception as e:
            logger.error(f"Typing error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_receipt(self, access_token: str, room_id: str,
                           event_id: str, receipt_type: str = 'm.read') -> Dict[str, Any]:
        """
        处理已读回执请求
        
        POST /_matrix/client/r0/rooms/{roomId}/receipt/{receiptType}/{eventId}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_id: 事件ID
            receipt_type: 回执类型
            
        Returns:
            已读回执响应
        """
        logger.debug(f"Processing receipt request: {room_id}/{event_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户是否在房间中
            is_member = await self.room_handler.is_user_in_room(user_id, room_id)
            if not is_member:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User not in room'
                }, 403
                
            # 设置已读回执
            await self.message_handler.set_receipt(
                user_id=user_id,
                room_id=room_id,
                event_id=event_id,
                receipt_type=receipt_type
            )
            
            return {}, 200
            
        except Exception as e:
            logger.error(f"Receipt error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500