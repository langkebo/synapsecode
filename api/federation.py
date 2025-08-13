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
Matrix Synapse 联邦API

这个模块实现了Matrix协议的联邦相关API端点。
"""

import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class FederationAPI:
    """
    联邦API处理器
    
    实现Matrix协议的服务器间联邦通信API端点。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.federation_handler = hs.get_federation_handler()
        self.auth_handler = hs.get_auth_handler()
        self.room_handler = hs.get_room_handler()
        self.message_handler = hs.get_message_handler()
        self.clock = hs.get_clock()
        self.server_name = hs.config.server_name
        
    async def handle_send_transaction(self, origin: str, transaction_id: str,
                                    request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发送事务请求
        
        PUT /_matrix/federation/v1/send/{txnId}
        
        Args:
            origin: 发送方服务器名
            transaction_id: 事务ID
            request_data: 事务数据
            
        Returns:
            事务处理响应
        """
        logger.info(f"Processing send transaction from {origin}: {transaction_id}")
        
        try:
            # 验证发送方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 处理事务中的事件
            pdus = request_data.get('pdus', [])
            edus = request_data.get('edus', [])
            
            # 处理PDU事件（持久化数据单元）
            pdu_results = {}
            for pdu in pdus:
                try:
                    result = await self.federation_handler.handle_incoming_event(
                        origin=origin,
                        event=pdu
                    )
                    pdu_results[pdu.get('event_id', '')] = result
                except Exception as e:
                    logger.warning(f"Failed to process PDU {pdu.get('event_id')}: {e}")
                    pdu_results[pdu.get('event_id', '')] = {
                        'error': str(e)
                    }
                    
            # 处理EDU事件（临时数据单元）
            for edu in edus:
                try:
                    await self.federation_handler.handle_incoming_edu(
                        origin=origin,
                        edu=edu
                    )
                except Exception as e:
                    logger.warning(f"Failed to process EDU {edu.get('edu_type')}: {e}")
                    
            logger.info(f"Transaction processed: {len(pdus)} PDUs, {len(edus)} EDUs")
            
            return {
                'pdus': pdu_results
            }, 200
            
        except Exception as e:
            logger.error(f"Send transaction error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_event(self, origin: str, event_id: str) -> Dict[str, Any]:
        """
        处理获取事件请求
        
        GET /_matrix/federation/v1/event/{eventId}
        
        Args:
            origin: 请求方服务器名
            event_id: 事件ID
            
        Returns:
            事件数据响应
        """
        logger.debug(f"Processing get event from {origin}: {event_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 获取事件
            event = await self.federation_handler.get_event_for_federation(
                event_id=event_id,
                origin=origin
            )
            
            if not event:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Event not found'
                }, 404
                
            return {
                'pdus': [event]
            }, 200
            
        except Exception as e:
            logger.error(f"Get event error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_state(self, origin: str, room_id: str,
                             event_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理获取房间状态请求
        
        GET /_matrix/federation/v1/state/{roomId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            event_id: 可选的事件ID
            
        Returns:
            房间状态响应
        """
        logger.debug(f"Processing get state from {origin}: {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 获取房间状态
            state_events = await self.federation_handler.get_room_state_for_federation(
                room_id=room_id,
                event_id=event_id,
                origin=origin
            )
            
            if state_events is None:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Room not found or access denied'
                }, 404
                
            return {
                'pdus': state_events,
                'auth_chain': []  # 简化实现
            }, 200
            
        except Exception as e:
            logger.error(f"Get state error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_state_ids(self, origin: str, room_id: str,
                                 event_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理获取房间状态ID请求
        
        GET /_matrix/federation/v1/state_ids/{roomId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            event_id: 可选的事件ID
            
        Returns:
            房间状态ID响应
        """
        logger.debug(f"Processing get state IDs from {origin}: {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 获取房间状态ID
            state_ids = await self.federation_handler.get_room_state_ids_for_federation(
                room_id=room_id,
                event_id=event_id,
                origin=origin
            )
            
            if state_ids is None:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Room not found or access denied'
                }, 404
                
            return {
                'pdu_ids': state_ids,
                'auth_chain_ids': []  # 简化实现
            }, 200
            
        except Exception as e:
            logger.error(f"Get state IDs error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_make_join(self, origin: str, room_id: str,
                             user_id: str) -> Dict[str, Any]:
        """
        处理创建加入事件请求
        
        GET /_matrix/federation/v1/make_join/{roomId}/{userId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            加入事件模板响应
        """
        logger.info(f"Processing make join from {origin}: {user_id} -> {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 验证用户ID是否属于请求方服务器
            if not user_id.endswith(f':{origin}'):
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User does not belong to origin server'
                }, 403
                
            # 创建加入事件模板
            join_event = await self.federation_handler.make_join_event(
                room_id=room_id,
                user_id=user_id,
                origin=origin
            )
            
            if not join_event:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Cannot join room'
                }, 403
                
            return {
                'event': join_event,
                'room_version': '9'  # 默认房间版本
            }, 200
            
        except Exception as e:
            logger.error(f"Make join error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_send_join(self, origin: str, room_id: str,
                             event_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发送加入事件请求
        
        PUT /_matrix/federation/v2/send_join/{roomId}/{eventId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            event_id: 事件ID
            request_data: 加入事件数据
            
        Returns:
            加入处理响应
        """
        logger.info(f"Processing send join from {origin}: {event_id} -> {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 处理加入事件
            result = await self.federation_handler.handle_join_event(
                origin=origin,
                room_id=room_id,
                event_id=event_id,
                event=request_data
            )
            
            if not result:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Join rejected'
                }, 403
                
            # 获取房间状态用于响应
            state_events = await self.federation_handler.get_room_state_for_federation(
                room_id=room_id,
                origin=origin
            )
            
            return {
                'state': state_events or [],
                'auth_chain': [],  # 简化实现
                'origin': self.server_name,
                'event': result
            }, 200
            
        except Exception as e:
            logger.error(f"Send join error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_make_leave(self, origin: str, room_id: str,
                              user_id: str) -> Dict[str, Any]:
        """
        处理创建离开事件请求
        
        GET /_matrix/federation/v1/make_leave/{roomId}/{userId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            离开事件模板响应
        """
        logger.info(f"Processing make leave from {origin}: {user_id} -> {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 验证用户ID是否属于请求方服务器
            if not user_id.endswith(f':{origin}'):
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'User does not belong to origin server'
                }, 403
                
            # 创建离开事件模板
            leave_event = await self.federation_handler.make_leave_event(
                room_id=room_id,
                user_id=user_id,
                origin=origin
            )
            
            if not leave_event:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Cannot leave room'
                }, 403
                
            return {
                'event': leave_event,
                'room_version': '9'  # 默认房间版本
            }, 200
            
        except Exception as e:
            logger.error(f"Make leave error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_send_leave(self, origin: str, room_id: str,
                              event_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发送离开事件请求
        
        PUT /_matrix/federation/v2/send_leave/{roomId}/{eventId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            event_id: 事件ID
            request_data: 离开事件数据
            
        Returns:
            离开处理响应
        """
        logger.info(f"Processing send leave from {origin}: {event_id} -> {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 处理离开事件
            result = await self.federation_handler.handle_leave_event(
                origin=origin,
                room_id=room_id,
                event_id=event_id,
                event=request_data
            )
            
            if not result:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Leave rejected'
                }, 403
                
            return {}, 200
            
        except Exception as e:
            logger.error(f"Send leave error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_invite(self, origin: str, room_id: str,
                          event_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理邀请事件请求
        
        PUT /_matrix/federation/v2/invite/{roomId}/{eventId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            event_id: 事件ID
            request_data: 邀请事件数据
            
        Returns:
            邀请处理响应
        """
        logger.info(f"Processing invite from {origin}: {event_id} -> {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 处理邀请事件
            result = await self.federation_handler.handle_invite_event(
                origin=origin,
                room_id=room_id,
                event_id=event_id,
                event=request_data
            )
            
            if not result:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Invite rejected'
                }, 403
                
            return {
                'event': result
            }, 200
            
        except Exception as e:
            logger.error(f"Invite error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_missing_events(self, origin: str, room_id: str,
                                      request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理获取缺失事件请求
        
        POST /_matrix/federation/v1/get_missing_events/{roomId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            request_data: 请求数据
            
        Returns:
            缺失事件响应
        """
        logger.debug(f"Processing get missing events from {origin}: {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 解析请求参数
            earliest_events = request_data.get('earliest_events', [])
            latest_events = request_data.get('latest_events', [])
            limit = min(request_data.get('limit', 10), 20)  # 限制最大数量
            
            # 获取缺失事件
            missing_events = await self.federation_handler.get_missing_events(
                room_id=room_id,
                earliest_events=earliest_events,
                latest_events=latest_events,
                limit=limit,
                origin=origin
            )
            
            return {
                'events': missing_events or []
            }, 200
            
        except Exception as e:
            logger.error(f"Get missing events error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_backfill(self, origin: str, room_id: str,
                            v: List[str], limit: int = 10) -> Dict[str, Any]:
        """
        处理回填事件请求
        
        GET /_matrix/federation/v1/backfill/{roomId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            v: 事件ID列表
            limit: 限制数量
            
        Returns:
            回填事件响应
        """
        logger.debug(f"Processing backfill from {origin}: {room_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 限制回填数量
            limit = min(limit, 100)
            
            # 获取回填事件
            events = await self.federation_handler.get_backfill_events(
                room_id=room_id,
                event_ids=v,
                limit=limit,
                origin=origin
            )
            
            return {
                'pdus': events or []
            }, 200
            
        except Exception as e:
            logger.error(f"Backfill error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_query_auth(self, origin: str, room_id: str,
                              event_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理查询认证请求
        
        POST /_matrix/federation/v1/query_auth/{roomId}/{eventId}
        
        Args:
            origin: 请求方服务器名
            room_id: 房间ID
            event_id: 事件ID
            request_data: 请求数据
            
        Returns:
            认证查询响应
        """
        logger.debug(f"Processing query auth from {origin}: {event_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 简化实现：返回空的认证链
            return {
                'auth_chain': [],
                'rejects': {},
                'missing': []
            }, 200
            
        except Exception as e:
            logger.error(f"Query auth error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_version(self) -> Dict[str, Any]:
        """
        处理版本信息请求
        
        GET /_matrix/federation/v1/version
        
        Returns:
            版本信息响应
        """
        return {
            'server': {
                'name': 'Synapse',
                'version': '1.0.0'
            }
        }, 200
        
    async def handle_query_profile(self, origin: str, user_id: str,
                                 field: Optional[str] = None) -> Dict[str, Any]:
        """
        处理查询用户资料请求
        
        GET /_matrix/federation/v1/query/profile
        
        Args:
            origin: 请求方服务器名
            user_id: 用户ID
            field: 可选的字段名
            
        Returns:
            用户资料响应
        """
        logger.debug(f"Processing query profile from {origin}: {user_id}")
        
        try:
            # 验证请求方服务器
            if not origin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Missing origin server'
                }, 403
                
            # 检查用户是否属于本服务器
            if not user_id.endswith(f':{self.server_name}'):
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'User not found on this server'
                }, 404
                
            # 简化实现：返回基本用户信息
            profile = {
                'displayname': user_id.split(':')[0][1:],  # 使用用户名作为显示名
                'avatar_url': None
            }
            
            if field:
                if field in profile:
                    return {field: profile[field]}, 200
                else:
                    return {
                        'errcode': 'M_NOT_FOUND',
                        'error': f'Field {field} not found'
                    }, 404
            else:
                return profile, 200
                
        except Exception as e:
            logger.error(f"Query profile error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500