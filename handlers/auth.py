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
Matrix Synapse 用户认证处理器

这个模块处理用户认证相关的操作，包括登录、注册、密码验证等。
"""

import logging
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class AuthHandler:
    """
    用户认证处理器
    
    处理用户认证、注册、登录和访问令牌管理。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.store = hs.get_datastore()
        self.clock = hs.get_clock()
        self.config = hs.config
        self.password_policy = hs.config.password_policy
        
    async def check_user_exists(self, user_id: str) -> bool:
        """
        检查用户是否存在
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户存在返回True，否则返回False
        """
        logger.debug(f"Checking if user exists: {user_id}")
        user = await self.store.get_user_by_id(user_id)
        return user is not None
        
    async def validate_password(self, user_id: str, password: str) -> bool:
        """
        验证用户密码
        
        Args:
            user_id: 用户ID
            password: 明文密码
            
        Returns:
            密码正确返回True，否则返回False
        """
        logger.debug(f"Validating password for user: {user_id}")
        
        user = await self.store.get_user_by_id(user_id)
        if not user:
            return False
            
        stored_hash = user.get("password_hash")
        if not stored_hash:
            return False
            
        return self._verify_password(password, stored_hash)
        
    def _hash_password(self, password: str) -> str:
        """
        对密码进行哈希处理
        
        Args:
            password: 明文密码
            
        Returns:
            密码哈希值
        """
        # 使用 bcrypt 或类似的安全哈希算法
        # 这里简化为 SHA256 + salt
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"sha256${salt}${password_hash}"
        
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """
        验证密码哈希
        
        Args:
            password: 明文密码
            stored_hash: 存储的密码哈希
            
        Returns:
            密码匹配返回True，否则返回False
        """
        try:
            algorithm, salt, hash_value = stored_hash.split("$")
            if algorithm == "sha256":
                computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                return computed_hash == hash_value
        except ValueError:
            pass
        return False
        
    async def register_user(self, user_id: str, password: str, 
                          display_name: Optional[str] = None,
                          admin: bool = False) -> Dict[str, Any]:
        """
        注册新用户
        
        Args:
            user_id: 用户ID
            password: 密码
            display_name: 显示名称
            admin: 是否为管理员
            
        Returns:
            注册结果字典
            
        Raises:
            ValueError: 用户已存在或密码不符合策略
        """
        logger.info(f"Registering new user: {user_id}")
        
        # 检查用户是否已存在
        if await self.check_user_exists(user_id):
            raise ValueError(f"User {user_id} already exists")
            
        # 验证密码策略
        if self.password_policy:
            self.password_policy.validate_password(password, user_id)
            
        # 创建密码哈希
        password_hash = self._hash_password(password)
        
        # 存储用户
        creation_ts = self.clock.time_msec()
        success = await self.store.create_user(
            user_id=user_id,
            password_hash=password_hash,
            creation_ts=creation_ts,
            admin=admin,
            display_name=display_name
        )
        
        if not success:
            raise RuntimeError("Failed to create user")
            
        logger.info(f"User {user_id} registered successfully")
        return {
            "user_id": user_id,
            "creation_ts": creation_ts,
            "admin": admin
        }
        
    async def login_user(self, user_id: str, password: str, 
                        device_id: Optional[str] = None,
                        device_display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            user_id: 用户ID
            password: 密码
            device_id: 设备ID
            device_display_name: 设备显示名称
            
        Returns:
            登录结果字典，包含访问令牌等信息
            
        Raises:
            ValueError: 用户不存在或密码错误
        """
        logger.info(f"User login attempt: {user_id}")
        
        # 验证用户和密码
        if not await self.validate_password(user_id, password):
            raise ValueError("Invalid username or password")
            
        # 生成访问令牌
        access_token = self._generate_access_token()
        
        # 如果没有提供设备ID，生成一个
        if not device_id:
            device_id = self._generate_device_id()
            
        # 存储访问令牌和设备信息
        await self.store.store_access_token(
            user_id=user_id,
            token=access_token,
            device_id=device_id
        )
        
        await self.store.store_device(
            user_id=user_id,
            device_id=device_id,
            display_name=device_display_name,
            last_seen=self.clock.time_msec()
        )
        
        logger.info(f"User {user_id} logged in successfully")
        return {
            "user_id": user_id,
            "access_token": access_token,
            "device_id": device_id,
            "home_server": self.hs.hostname
        }
        
    def _generate_access_token(self) -> str:
        """
        生成访问令牌
        
        Returns:
            访问令牌字符串
        """
        return f"syt_{secrets.token_urlsafe(32)}"
        
    def _generate_device_id(self) -> str:
        """
        生成设备ID
        
        Returns:
            设备ID字符串
        """
        return secrets.token_urlsafe(16)
        
    async def logout_user(self, access_token: str) -> bool:
        """
        用户登出
        
        Args:
            access_token: 访问令牌
            
        Returns:
            登出成功返回True，否则返回False
        """
        logger.info(f"User logout with token: {access_token[:10]}...")
        
        # 删除访问令牌
        success = await self.store.delete_access_token(access_token)
        
        if success:
            logger.info("User logged out successfully")
        else:
            logger.warning("Failed to logout user")
            
        return success
        
    async def get_user_by_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        根据访问令牌获取用户信息
        
        Args:
            access_token: 访问令牌
            
        Returns:
            用户信息字典，如果令牌无效则返回None
        """
        logger.debug(f"Getting user by access token: {access_token[:10]}...")
        
        token_info = await self.store.get_user_by_access_token(access_token)
        if not token_info:
            return None
            
        user_id = token_info.get("user_id")
        if not user_id:
            return None
            
        user = await self.store.get_user_by_id(user_id)
        if user:
            # 更新最后使用时间
            await self.store.update_access_token_last_used(
                access_token, 
                self.clock.time_msec()
            )
            
        return user
        
    async def change_password(self, user_id: str, old_password: str, 
                            new_password: str) -> bool:
        """
        修改用户密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            修改成功返回True，否则返回False
            
        Raises:
            ValueError: 旧密码错误或新密码不符合策略
        """
        logger.info(f"Changing password for user: {user_id}")
        
        # 验证旧密码
        if not await self.validate_password(user_id, old_password):
            raise ValueError("Invalid old password")
            
        # 验证新密码策略
        if self.password_policy:
            self.password_policy.validate_password(new_password, user_id)
            
        # 生成新密码哈希
        new_password_hash = self._hash_password(new_password)
        
        # 更新密码
        success = await self.store.update_user_password(
            user_id, 
            new_password_hash
        )
        
        if success:
            logger.info(f"Password changed successfully for user: {user_id}")
            # 可选：使所有现有访问令牌失效
            await self.store.invalidate_user_access_tokens(user_id)
        else:
            logger.error(f"Failed to change password for user: {user_id}")
            
        return success