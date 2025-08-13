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
Matrix Synapse 认证API

这个模块实现了Matrix协议的认证相关API端点。
"""

import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)


class AuthAPI:
    """
    认证API处理器
    
    实现Matrix协议的用户认证、注册、登录等API端点。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.auth_handler = hs.get_auth_handler()
        self.device_handler = hs.get_device_handler()
        self.clock = hs.get_clock()
        
    async def handle_register(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户注册请求
        
        POST /_matrix/client/r0/register
        
        Args:
            request_data: 请求数据
            
        Returns:
            注册响应
        """
        logger.info("Processing user registration request")
        
        # 解析请求参数
        username = request_data.get('username')
        password = request_data.get('password')
        device_id = request_data.get('device_id')
        initial_device_display_name = request_data.get('initial_device_display_name')
        
        # 验证必需参数
        if not username or not password:
            return {
                'errcode': 'M_MISSING_PARAM',
                'error': 'Missing username or password'
            }, 400
            
        try:
            # 注册用户
            user_id = await self.auth_handler.register_user(
                username=username,
                password=password
            )
            
            # 注册设备
            device_info = await self.device_handler.register_device(
                user_id=user_id,
                device_id=device_id,
                display_name=initial_device_display_name
            )
            
            # 生成访问令牌
            access_token = await self.auth_handler.create_access_token(
                user_id=user_id,
                device_id=device_info['device_id']
            )
            
            logger.info(f"User registered successfully: {user_id}")
            
            return {
                'user_id': user_id,
                'access_token': access_token,
                'device_id': device_info['device_id'],
                'home_server': self.hs.hostname
            }, 200
            
        except ValueError as e:
            logger.warning(f"Registration failed: {e}")
            return {
                'errcode': 'M_USER_IN_USE',
                'error': str(e)
            }, 400
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_login(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户登录请求
        
        POST /_matrix/client/r0/login
        
        Args:
            request_data: 请求数据
            
        Returns:
            登录响应
        """
        logger.info("Processing user login request")
        
        # 解析请求参数
        login_type = request_data.get('type', 'm.login.password')
        identifier = request_data.get('identifier', {})
        password = request_data.get('password')
        device_id = request_data.get('device_id')
        initial_device_display_name = request_data.get('initial_device_display_name')
        
        # 支持旧格式的用户名
        if 'user' in request_data:
            identifier = {'type': 'm.id.user', 'user': request_data['user']}
            
        # 验证登录类型
        if login_type != 'm.login.password':
            return {
                'errcode': 'M_UNKNOWN',
                'error': f'Unknown login type: {login_type}'
            }, 400
            
        # 验证必需参数
        if not identifier or not password:
            return {
                'errcode': 'M_MISSING_PARAM',
                'error': 'Missing identifier or password'
            }, 400
            
        try:
            # 获取用户名
            if identifier.get('type') == 'm.id.user':
                username = identifier.get('user')
            elif identifier.get('type') == 'm.id.thirdparty':
                # 第三方标识符登录（暂不支持）
                return {
                    'errcode': 'M_UNKNOWN',
                    'error': 'Third-party login not supported'
                }, 400
            else:
                username = identifier.get('user')
                
            if not username:
                return {
                    'errcode': 'M_MISSING_PARAM',
                    'error': 'Missing username'
                }, 400
                
            # 验证用户凭据
            user_id = await self.auth_handler.validate_login(
                username=username,
                password=password
            )
            
            if not user_id:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Invalid username or password'
                }, 403
                
            # 注册或更新设备
            device_info = await self.device_handler.register_device(
                user_id=user_id,
                device_id=device_id,
                display_name=initial_device_display_name
            )
            
            # 生成访问令牌
            access_token = await self.auth_handler.create_access_token(
                user_id=user_id,
                device_id=device_info['device_id']
            )
            
            logger.info(f"User logged in successfully: {user_id}")
            
            return {
                'user_id': user_id,
                'access_token': access_token,
                'device_id': device_info['device_id'],
                'home_server': self.hs.hostname,
                'well_known': {
                    'm.homeserver': {
                        'base_url': f'https://{self.hs.hostname}'
                    }
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_logout(self, access_token: str) -> Dict[str, Any]:
        """
        处理用户登出请求
        
        POST /_matrix/client/r0/logout
        
        Args:
            access_token: 访问令牌
            
        Returns:
            登出响应
        """
        logger.info("Processing user logout request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 删除访问令牌
            await self.auth_handler.delete_access_token(access_token)
            
            logger.info(f"User logged out successfully: {user_info['user_id']}")
            
            return {}, 200
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_logout_all(self, access_token: str) -> Dict[str, Any]:
        """
        处理用户全部登出请求
        
        POST /_matrix/client/r0/logout/all
        
        Args:
            access_token: 访问令牌
            
        Returns:
            登出响应
        """
        logger.info("Processing user logout all request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 删除用户所有访问令牌
            await self.auth_handler.delete_all_access_tokens(user_info['user_id'])
            
            logger.info(f"User logged out from all devices: {user_info['user_id']}")
            
            return {}, 200
            
        except Exception as e:
            logger.error(f"Logout all error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_whoami(self, access_token: str) -> Dict[str, Any]:
        """
        处理用户身份查询请求
        
        GET /_matrix/client/r0/account/whoami
        
        Args:
            access_token: 访问令牌
            
        Returns:
            用户身份信息
        """
        logger.debug("Processing whoami request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            return {
                'user_id': user_info['user_id'],
                'device_id': user_info.get('device_id')
            }, 200
            
        except Exception as e:
            logger.error(f"Whoami error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_change_password(self, access_token: str, 
                                   request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理修改密码请求
        
        POST /_matrix/client/r0/account/password
        
        Args:
            access_token: 访问令牌
            request_data: 请求数据
            
        Returns:
            修改密码响应
        """
        logger.info("Processing change password request")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 解析请求参数
            new_password = request_data.get('new_password')
            if not new_password:
                return {
                    'errcode': 'M_MISSING_PARAM',
                    'error': 'Missing new_password'
                }, 400
                
            # 修改密码
            success = await self.auth_handler.change_password(
                user_id=user_info['user_id'],
                new_password=new_password
            )
            
            if success:
                logger.info(f"Password changed successfully for user: {user_info['user_id']}")
                return {}, 200
            else:
                return {
                    'errcode': 'M_UNKNOWN',
                    'error': 'Failed to change password'
                }, 500
                
        except Exception as e:
            logger.error(f"Change password error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_login_flows(self) -> Dict[str, Any]:
        """
        处理登录流程查询请求
        
        GET /_matrix/client/r0/login
        
        Returns:
            支持的登录流程
        """
        logger.debug("Processing login flows request")
        
        return {
            'flows': [
                {'type': 'm.login.password'}
            ]
        }, 200
        
    async def handle_register_available(self, username: str) -> Dict[str, Any]:
        """
        处理用户名可用性查询请求
        
        GET /_matrix/client/r0/register/available
        
        Args:
            username: 用户名
            
        Returns:
            用户名可用性信息
        """
        logger.debug(f"Checking username availability: {username}")
        
        try:
            # 检查用户名是否已存在
            user_exists = await self.auth_handler.check_user_exists(username)
            
            if user_exists:
                return {
                    'errcode': 'M_USER_IN_USE',
                    'error': 'Username is already in use'
                }, 400
            else:
                return {
                    'available': True
                }, 200
                
        except Exception as e:
            logger.error(f"Username availability check error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    def get_auth_header(self, request_headers: Dict[str, str]) -> Optional[str]:
        """
        从请求头中提取访问令牌
        
        Args:
            request_headers: 请求头字典
            
        Returns:
            访问令牌，如果不存在则返回None
        """
        auth_header = request_headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # 移除 'Bearer ' 前缀
        return None
        
    def get_access_token_from_query(self, query_string: str) -> Optional[str]:
        """
        从查询字符串中提取访问令牌
        
        Args:
            query_string: 查询字符串
            
        Returns:
            访问令牌，如果不存在则返回None
        """
        if not query_string:
            return None
            
        params = parse_qs(query_string)
        access_tokens = params.get('access_token', [])
        
        if access_tokens:
            return access_tokens[0]
        return None