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
Matrix Synapse 设备API

这个模块实现了Matrix协议的设备相关API端点。
"""

import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DeviceAPI:
    """
    设备API处理器
    
    实现Matrix协议的设备管理、端到端加密等API端点。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.auth_handler = hs.get_auth_handler()
        self.device_handler = hs.get_device_handler()
        self.clock = hs.get_clock()
        
    async def handle_get_devices(self, access_token: str) -> Dict[str, Any]:
        """
        处理获取设备列表请求
        
        GET /_matrix/client/r0/devices
        
        Args:
            access_token: 访问令牌
            
        Returns:
            设备列表响应
        """
        logger.debug("Processing get devices request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 获取用户设备列表
            devices = await self.device_handler.get_user_devices(user_id)
            
            return {
                'devices': devices
            }, 200
            
        except Exception as e:
            logger.error(f"Get devices error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_device(self, access_token: str, device_id: str) -> Dict[str, Any]:
        """
        处理获取单个设备请求
        
        GET /_matrix/client/r0/devices/{deviceId}
        
        Args:
            access_token: 访问令牌
            device_id: 设备ID
            
        Returns:
            设备信息响应
        """
        logger.debug(f"Processing get device request: {device_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 获取设备信息
            device = await self.device_handler.get_device(user_id, device_id)
            
            if not device:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Device not found'
                }, 404
                
            return device, 200
            
        except Exception as e:
            logger.error(f"Get device error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_update_device(self, access_token: str, device_id: str,
                                 request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理更新设备请求
        
        PUT /_matrix/client/r0/devices/{deviceId}
        
        Args:
            access_token: 访问令牌
            device_id: 设备ID
            request_data: 请求数据
            
        Returns:
            更新设备响应
        """
        logger.info(f"Processing update device request: {device_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 更新设备信息
            display_name = request_data.get('display_name')
            
            success = await self.device_handler.update_device(
                user_id=user_id,
                device_id=device_id,
                display_name=display_name
            )
            
            if success:
                logger.info(f"Device updated successfully: {device_id}")
                return {}, 200
            else:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Device not found'
                }, 404
                
        except ValueError as e:
            logger.warning(f"Update device failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Update device error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_delete_device(self, access_token: str, device_id: str,
                                 request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理删除设备请求
        
        DELETE /_matrix/client/r0/devices/{deviceId}
        
        Args:
            access_token: 访问令牌
            device_id: 设备ID
            request_data: 请求数据（可能包含认证信息）
            
        Returns:
            删除设备响应
        """
        logger.info(f"Processing delete device request: {device_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 检查是否需要额外认证（删除设备通常需要密码确认）
            if request_data and 'auth' in request_data:
                auth_data = request_data['auth']
                auth_type = auth_data.get('type')
                
                if auth_type == 'm.login.password':
                    password = auth_data.get('password')
                    if password:
                        # 验证密码
                        valid = await self.auth_handler.validate_login(
                            username=user_id.split(':')[0][1:],  # 移除@前缀
                            password=password
                        )
                        if not valid:
                            return {
                                'errcode': 'M_FORBIDDEN',
                                'error': 'Invalid password'
                            }, 403
                    else:
                        return {
                            'errcode': 'M_MISSING_PARAM',
                            'error': 'Missing password'
                        }, 400
                else:
                    return {
                        'errcode': 'M_UNKNOWN',
                        'error': f'Unknown auth type: {auth_type}'
                    }, 400
            else:
                # 如果没有提供认证信息，要求用户认证
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Authentication required',
                    'flows': [
                        {'stages': ['m.login.password']}
                    ],
                    'params': {}
                }, 401
                
            # 删除设备
            success = await self.device_handler.delete_device(
                user_id=user_id,
                device_id=device_id
            )
            
            if success:
                logger.info(f"Device deleted successfully: {device_id}")
                return {}, 200
            else:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Device not found'
                }, 404
                
        except ValueError as e:
            logger.warning(f"Delete device failed: {e}")
            return {
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }, 404
        except Exception as e:
            logger.error(f"Delete device error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_delete_devices(self, access_token: str,
                                  request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理批量删除设备请求
        
        POST /_matrix/client/r0/delete_devices
        
        Args:
            access_token: 访问令牌
            request_data: 请求数据
            
        Returns:
            批量删除设备响应
        """
        logger.info("Processing delete devices request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 获取要删除的设备列表
            device_ids = request_data.get('devices', [])
            if not device_ids:
                return {
                    'errcode': 'M_MISSING_PARAM',
                    'error': 'Missing devices list'
                }, 400
                
            # 检查认证信息
            if 'auth' in request_data:
                auth_data = request_data['auth']
                auth_type = auth_data.get('type')
                
                if auth_type == 'm.login.password':
                    password = auth_data.get('password')
                    if password:
                        # 验证密码
                        valid = await self.auth_handler.validate_login(
                            username=user_id.split(':')[0][1:],  # 移除@前缀
                            password=password
                        )
                        if not valid:
                            return {
                                'errcode': 'M_FORBIDDEN',
                                'error': 'Invalid password'
                            }, 403
                    else:
                        return {
                            'errcode': 'M_MISSING_PARAM',
                            'error': 'Missing password'
                        }, 400
                else:
                    return {
                        'errcode': 'M_UNKNOWN',
                        'error': f'Unknown auth type: {auth_type}'
                    }, 400
            else:
                # 如果没有提供认证信息，要求用户认证
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Authentication required',
                    'flows': [
                        {'stages': ['m.login.password']}
                    ],
                    'params': {}
                }, 401
                
            # 批量删除设备
            results = await self.device_handler.delete_devices(
                user_id=user_id,
                device_ids=device_ids
            )
            
            # 检查是否有失败的删除
            failed_devices = [device_id for device_id, success in results.items() if not success]
            
            if failed_devices:
                logger.warning(f"Some devices failed to delete: {failed_devices}")
                
            logger.info(f"Devices deletion completed: {len(device_ids)} requested, {len(failed_devices)} failed")
            
            return {}, 200
            
        except Exception as e:
            logger.error(f"Delete devices error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_upload_keys(self, access_token: str,
                               request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理上传设备密钥请求
        
        POST /_matrix/client/r0/keys/upload
        
        Args:
            access_token: 访问令牌
            request_data: 请求数据
            
        Returns:
            上传密钥响应
        """
        logger.info("Processing upload keys request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            device_id = user_info.get('device_id')
            
            if not device_id:
                return {
                    'errcode': 'M_MISSING_PARAM',
                    'error': 'Device ID not found in token'
                }, 400
                
            # 上传设备密钥
            result = await self.device_handler.upload_device_keys(
                user_id=user_id,
                device_id=device_id,
                keys=request_data
            )
            
            logger.info(f"Keys uploaded successfully for device: {device_id}")
            
            return result, 200
            
        except ValueError as e:
            logger.warning(f"Upload keys failed: {e}")
            return {
                'errcode': 'M_INVALID_PARAM',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Upload keys error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_query_keys(self, access_token: str,
                              request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理查询设备密钥请求
        
        POST /_matrix/client/r0/keys/query
        
        Args:
            access_token: 访问令牌
            request_data: 请求数据
            
        Returns:
            查询密钥响应
        """
        logger.debug("Processing query keys request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 解析查询参数
            device_keys = request_data.get('device_keys', {})
            
            # 查询设备密钥
            result_keys = {}
            
            for user_id, device_list in device_keys.items():
                if isinstance(device_list, list):
                    # 查询指定设备的密钥
                    user_keys = await self.device_handler.get_device_keys(
                        user_id=user_id,
                        device_ids=device_list
                    )
                else:
                    # 查询用户所有设备的密钥
                    user_keys = await self.device_handler.get_device_keys(
                        user_id=user_id
                    )
                    
                if user_keys:
                    result_keys.update(user_keys)
                    
            return {
                'device_keys': result_keys,
                'failures': {}
            }, 200
            
        except Exception as e:
            logger.error(f"Query keys error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_claim_keys(self, access_token: str,
                              request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理获取一次性密钥请求
        
        POST /_matrix/client/r0/keys/claim
        
        Args:
            access_token: 访问令牌
            request_data: 请求数据
            
        Returns:
            获取一次性密钥响应
        """
        logger.debug("Processing claim keys request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 解析密钥请求
            one_time_keys = request_data.get('one_time_keys', {})
            
            # 获取一次性密钥
            result = await self.device_handler.claim_one_time_keys(one_time_keys)
            
            return {
                'one_time_keys': result.get('one_time_keys', {}),
                'failures': {}
            }, 200
            
        except Exception as e:
            logger.error(f"Claim keys error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_key_changes(self, access_token: str,
                               from_token: str, to_token: str) -> Dict[str, Any]:
        """
        处理密钥变更查询请求
        
        GET /_matrix/client/r0/keys/changes
        
        Args:
            access_token: 访问令牌
            from_token: 起始令牌
            to_token: 结束令牌
            
        Returns:
            密钥变更响应
        """
        logger.debug("Processing key changes request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 简单实现：返回空的变更列表
            # 实际实现应该查询指定时间范围内的密钥变更
            return {
                'changed': [],
                'left': []
            }, 200
            
        except Exception as e:
            logger.error(f"Key changes error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500