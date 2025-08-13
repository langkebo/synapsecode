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
Matrix Synapse 房间API

这个模块实现了Matrix协议的房间相关API端点。
"""

import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class RoomAPI:
    """
    房间API处理器
    
    实现Matrix协议的房间创建、管理、成员操作等API端点。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.auth_handler = hs.get_auth_handler()
        self.room_handler = hs.get_room_handler()
        self.message_handler = hs.get_message_handler()
        self.clock = hs.get_clock()
        
    async def handle_create_room(self, access_token: str, 
                               request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理创建房间请求
        
        POST /_matrix/client/r0/createRoom
        
        Args:
            access_token: 访问令牌
            request_data: 请求数据
            
        Returns:
            创建房间响应
        """
        logger.info("Processing create room request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 解析房间创建参数
            room_alias_name = request_data.get('room_alias_name')
            name = request_data.get('name')
            topic = request_data.get('topic')
            invite = request_data.get('invite', [])
            preset = request_data.get('preset', 'private_chat')
            is_direct = request_data.get('is_direct', False)
            visibility = request_data.get('visibility', 'private')
            
            # 创建房间
            room_info = await self.room_handler.create_room(
                creator_id=user_id,
                room_alias_name=room_alias_name,
                name=name,
                topic=topic,
                invite_list=invite,
                preset=preset,
                is_direct=is_direct,
                visibility=visibility
            )
            
            logger.info(f"Room created successfully: {room_info['room_id']}")
            
            return {
                'room_id': room_info['room_id'],
                'room_alias': room_info.get('room_alias')
            }, 200
            
        except ValueError as e:
            logger.warning(f"Create room failed: {e}")
            return {
                'errcode': 'M_INVALID_PARAM',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Create room error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_join_room(self, access_token: str, room_id: str,
                             request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理加入房间请求
        
        POST /_matrix/client/r0/rooms/{roomId}/join
        POST /_matrix/client/r0/join/{roomIdOrAlias}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID或别名
            request_data: 请求数据
            
        Returns:
            加入房间响应
        """
        logger.info(f"Processing join room request: {room_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 加入房间
            result = await self.room_handler.join_room(
                user_id=user_id,
                room_id=room_id
            )
            
            if result['success']:
                logger.info(f"User {user_id} joined room {room_id} successfully")
                return {
                    'room_id': result['room_id']
                }, 200
            else:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': result.get('error', 'Failed to join room')
                }, 403
                
        except ValueError as e:
            logger.warning(f"Join room failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Join room error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_leave_room(self, access_token: str, room_id: str,
                              request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理离开房间请求
        
        POST /_matrix/client/r0/rooms/{roomId}/leave
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            request_data: 请求数据
            
        Returns:
            离开房间响应
        """
        logger.info(f"Processing leave room request: {room_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 离开房间
            success = await self.room_handler.leave_room(
                user_id=user_id,
                room_id=room_id
            )
            
            if success:
                logger.info(f"User {user_id} left room {room_id} successfully")
                return {}, 200
            else:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Failed to leave room'
                }, 403
                
        except ValueError as e:
            logger.warning(f"Leave room failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Leave room error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_invite_user(self, access_token: str, room_id: str,
                               request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理邀请用户请求
        
        POST /_matrix/client/r0/rooms/{roomId}/invite
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            request_data: 请求数据
            
        Returns:
            邀请用户响应
        """
        logger.info(f"Processing invite user request: {room_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            invitee_id = request_data.get('user_id')
            
            if not invitee_id:
                return {
                    'errcode': 'M_MISSING_PARAM',
                    'error': 'Missing user_id'
                }, 400
                
            # 邀请用户
            success = await self.room_handler.invite_user(
                inviter_id=user_id,
                invitee_id=invitee_id,
                room_id=room_id
            )
            
            if success:
                logger.info(f"User {invitee_id} invited to room {room_id} by {user_id}")
                return {}, 200
            else:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Failed to invite user'
                }, 403
                
        except ValueError as e:
            logger.warning(f"Invite user failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Invite user error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_room_state(self, access_token: str, room_id: str,
                                  event_type: Optional[str] = None,
                                  state_key: Optional[str] = None) -> Dict[str, Any]:
        """
        处理获取房间状态请求
        
        GET /_matrix/client/r0/rooms/{roomId}/state
        GET /_matrix/client/r0/rooms/{roomId}/state/{eventType}
        GET /_matrix/client/r0/rooms/{roomId}/state/{eventType}/{stateKey}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_type: 事件类型（可选）
            state_key: 状态键（可选）
            
        Returns:
            房间状态响应
        """
        logger.debug(f"Processing get room state request: {room_id}")
        
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
                
            # 获取房间状态
            state = await self.room_handler.get_room_state(
                room_id=room_id,
                event_type=event_type,
                state_key=state_key
            )
            
            if state is None:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'State not found'
                }, 404
                
            return state, 200
            
        except ValueError as e:
            logger.warning(f"Get room state failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Get room state error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_room_members(self, access_token: str, room_id: str,
                                    at: Optional[str] = None,
                                    membership: Optional[str] = None,
                                    not_membership: Optional[str] = None) -> Dict[str, Any]:
        """
        处理获取房间成员请求
        
        GET /_matrix/client/r0/rooms/{roomId}/members
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            at: 时间点（可选）
            membership: 成员状态过滤（可选）
            not_membership: 排除成员状态（可选）
            
        Returns:
            房间成员响应
        """
        logger.debug(f"Processing get room members request: {room_id}")
        
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
                
            # 获取房间成员
            members = await self.room_handler.get_room_members(
                room_id=room_id,
                membership=membership,
                not_membership=not_membership
            )
            
            return {
                'chunk': members
            }, 200
            
        except ValueError as e:
            logger.warning(f"Get room members failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Get room members error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_joined_rooms(self, access_token: str) -> Dict[str, Any]:
        """
        处理获取已加入房间请求
        
        GET /_matrix/client/r0/joined_rooms
        
        Args:
            access_token: 访问令牌
            
        Returns:
            已加入房间响应
        """
        logger.debug("Processing get joined rooms request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 获取用户已加入的房间
            joined_rooms = await self.room_handler.get_user_joined_rooms(user_id)
            
            return {
                'joined_rooms': joined_rooms
            }, 200
            
        except Exception as e:
            logger.error(f"Get joined rooms error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_set_room_state(self, access_token: str, room_id: str,
                                  event_type: str, state_key: str,
                                  request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理设置房间状态请求
        
        PUT /_matrix/client/r0/rooms/{roomId}/state/{eventType}/{stateKey}
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            event_type: 事件类型
            state_key: 状态键
            request_data: 请求数据
            
        Returns:
            设置房间状态响应
        """
        logger.info(f"Processing set room state request: {room_id}/{event_type}/{state_key}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查用户权限
            has_permission = await self.room_handler.check_user_power_level(
                user_id=user_id,
                room_id=room_id,
                required_level=50  # 默认状态事件需要50级权限
            )
            
            if not has_permission:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Insufficient power level'
                }, 403
                
            # 设置房间状态
            event_id = await self.room_handler.send_state_event(
                sender_id=user_id,
                room_id=room_id,
                event_type=event_type,
                state_key=state_key,
                content=request_data
            )
            
            logger.info(f"Room state set successfully: {event_id}")
            
            return {
                'event_id': event_id
            }, 200
            
        except ValueError as e:
            logger.warning(f"Set room state failed: {e}")
            return {
                'errcode': 'M_INVALID_PARAM',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Set room state error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_kick_user(self, access_token: str, room_id: str,
                             request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理踢出用户请求
        
        POST /_matrix/client/r0/rooms/{roomId}/kick
        
        Args:
            access_token: 访问令牌
            room_id: 房间ID
            request_data: 请求数据
            
        Returns:
            踢出用户响应
        """
        logger.info(f"Processing kick user request: {room_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            target_user_id = request_data.get('user_id')
            reason = request_data.get('reason')
            
            if not target_user_id:
                return {
                    'errcode': 'M_MISSING_PARAM',
                    'error': 'Missing user_id'
                }, 400
                
            # 检查用户权限
            has_permission = await self.room_handler.check_user_power_level(
                user_id=user_id,
                room_id=room_id,
                required_level=50  # 踢人需要50级权限
            )
            
            if not has_permission:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Insufficient power level'
                }, 403
                
            # 踢出用户
            success = await self.room_handler.kick_user(
                kicker_id=user_id,
                target_user_id=target_user_id,
                room_id=room_id,
                reason=reason
            )
            
            if success:
                logger.info(f"User {target_user_id} kicked from room {room_id} by {user_id}")
                return {}, 200
            else:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Failed to kick user'
                }, 403
                
        except ValueError as e:
            logger.warning(f"Kick user failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Kick user error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500