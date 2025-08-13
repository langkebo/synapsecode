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
Matrix Synapse 设备管理处理器

这个模块处理设备相关的操作，包括设备注册、管理、端到端加密等。
"""

import logging
import secrets
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DeviceHandler:
    """
    设备管理处理器
    
    处理用户设备的注册、管理和端到端加密密钥。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.store = hs.get_datastore()
        self.clock = hs.get_clock()
        self.config = hs.config
        
    def _generate_device_id(self) -> str:
        """
        生成设备ID
        
        Returns:
            设备ID字符串
        """
        return secrets.token_urlsafe(16)
        
    async def register_device(self, user_id: str, device_id: Optional[str] = None,
                             display_name: Optional[str] = None,
                             ip_address: Optional[str] = None,
                             user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        注册新设备
        
        Args:
            user_id: 用户ID
            device_id: 设备ID（可选，如果不提供则自动生成）
            display_name: 设备显示名称
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            设备信息
        """
        logger.info(f"Registering device for user {user_id}")
        
        # 如果没有提供设备ID，生成一个
        if not device_id:
            device_id = self._generate_device_id()
            
        # 检查设备是否已存在
        existing_device = await self.store.get_device(user_id, device_id)
        if existing_device:
            # 更新现有设备信息
            await self.store.update_device(
                user_id=user_id,
                device_id=device_id,
                display_name=display_name,
                last_seen=self.clock.time_msec(),
                ip_address=ip_address,
                user_agent=user_agent
            )
        else:
            # 创建新设备
            await self.store.create_device(
                user_id=user_id,
                device_id=device_id,
                display_name=display_name,
                last_seen=self.clock.time_msec(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        logger.info(f"Device {device_id} registered for user {user_id}")
        return {
            "device_id": device_id,
            "display_name": display_name,
            "last_seen_ts": self.clock.time_msec()
        }
        
    async def get_device(self, user_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        """
        获取设备信息
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            
        Returns:
            设备信息，如果设备不存在则返回None
        """
        logger.debug(f"Getting device {device_id} for user {user_id}")
        
        device = await self.store.get_device(user_id, device_id)
        if not device:
            return None
            
        return {
            "device_id": device["device_id"],
            "display_name": device["display_name"],
            "last_seen_ts": device["last_seen"],
            "last_seen_ip": device["ip_address"]
        }
        
    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的所有设备
        
        Args:
            user_id: 用户ID
            
        Returns:
            设备列表
        """
        logger.debug(f"Getting all devices for user {user_id}")
        
        devices = await self.store.get_user_devices(user_id)
        
        return [
            {
                "device_id": device["device_id"],
                "display_name": device["display_name"],
                "last_seen_ts": device["last_seen"],
                "last_seen_ip": device["ip_address"]
            }
            for device in devices
        ]
        
    async def update_device(self, user_id: str, device_id: str,
                           display_name: Optional[str] = None) -> bool:
        """
        更新设备信息
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            display_name: 新的显示名称
            
        Returns:
            更新成功返回True，否则返回False
        """
        logger.info(f"Updating device {device_id} for user {user_id}")
        
        # 检查设备是否存在
        device = await self.store.get_device(user_id, device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found for user {user_id}")
            
        # 更新设备信息
        success = await self.store.update_device(
            user_id=user_id,
            device_id=device_id,
            display_name=display_name
        )
        
        if success:
            logger.info(f"Device {device_id} updated successfully")
        else:
            logger.error(f"Failed to update device {device_id}")
            
        return success
        
    async def delete_device(self, user_id: str, device_id: str) -> bool:
        """
        删除设备
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            
        Returns:
            删除成功返回True，否则返回False
        """
        logger.info(f"Deleting device {device_id} for user {user_id}")
        
        # 检查设备是否存在
        device = await self.store.get_device(user_id, device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found for user {user_id}")
            
        # 删除设备相关的访问令牌
        await self.store.delete_access_tokens_for_device(user_id, device_id)
        
        # 删除设备的加密密钥
        await self.store.delete_device_keys(user_id, device_id)
        
        # 删除设备
        success = await self.store.delete_device(user_id, device_id)
        
        if success:
            logger.info(f"Device {device_id} deleted successfully")
        else:
            logger.error(f"Failed to delete device {device_id}")
            
        return success
        
    async def delete_devices(self, user_id: str, device_ids: List[str]) -> Dict[str, bool]:
        """
        批量删除设备
        
        Args:
            user_id: 用户ID
            device_ids: 设备ID列表
            
        Returns:
            删除结果字典，键为设备ID，值为删除是否成功
        """
        logger.info(f"Deleting {len(device_ids)} devices for user {user_id}")
        
        results = {}
        for device_id in device_ids:
            try:
                success = await self.delete_device(user_id, device_id)
                results[device_id] = success
            except Exception as e:
                logger.error(f"Failed to delete device {device_id}: {e}")
                results[device_id] = False
                
        return results
        
    async def upload_device_keys(self, user_id: str, device_id: str,
                                keys: Dict[str, Any]) -> Dict[str, Any]:
        """
        上传设备加密密钥
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            keys: 密钥数据
            
        Returns:
            上传结果
        """
        logger.info(f"Uploading keys for device {device_id} of user {user_id}")
        
        # 验证设备存在
        device = await self.store.get_device(user_id, device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found for user {user_id}")
            
        # 验证密钥格式
        if not self._validate_device_keys(keys, user_id, device_id):
            raise ValueError("Invalid device keys format")
            
        # 存储设备密钥
        await self.store.store_device_keys(user_id, device_id, keys)
        
        # 存储一次性密钥
        one_time_keys = keys.get("one_time_keys", {})
        if one_time_keys:
            await self.store.store_one_time_keys(
                user_id, device_id, one_time_keys
            )
            
        logger.info(f"Keys uploaded successfully for device {device_id}")
        return {
            "one_time_key_counts": {
                algorithm: len(keys_for_alg)
                for algorithm, keys_for_alg in one_time_keys.items()
            }
        }
        
    def _validate_device_keys(self, keys: Dict[str, Any], 
                             user_id: str, device_id: str) -> bool:
        """
        验证设备密钥格式
        
        Args:
            keys: 密钥数据
            user_id: 用户ID
            device_id: 设备ID
            
        Returns:
            密钥有效返回True，否则返回False
        """
        try:
            # 检查必需字段
            if keys.get("user_id") != user_id:
                return False
            if keys.get("device_id") != device_id:
                return False
                
            # 检查算法和密钥
            algorithms = keys.get("algorithms", [])
            device_keys = keys.get("keys", {})
            
            if not algorithms or not device_keys:
                return False
                
            # 检查签名
            signatures = keys.get("signatures", {})
            if user_id not in signatures:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating device keys: {e}")
            return False
            
    async def get_device_keys(self, user_id: str, 
                             device_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取设备加密密钥
        
        Args:
            user_id: 用户ID
            device_ids: 设备ID列表（可选）
            
        Returns:
            设备密钥数据
        """
        logger.debug(f"Getting device keys for user {user_id}")
        
        if device_ids is None:
            # 获取用户所有设备的密钥
            device_keys = await self.store.get_user_device_keys(user_id)
        else:
            # 获取指定设备的密钥
            device_keys = {}
            for device_id in device_ids:
                keys = await self.store.get_device_keys(user_id, device_id)
                if keys:
                    device_keys[device_id] = keys
                    
        return {
            user_id: device_keys
        }
        
    async def claim_one_time_keys(self, key_claims: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        获取一次性密钥
        
        Args:
            key_claims: 密钥请求，格式为 {user_id: {device_id: algorithm}}
            
        Returns:
            一次性密钥数据
        """
        logger.debug(f"Claiming one-time keys for {len(key_claims)} users")
        
        claimed_keys = {}
        
        for user_id, device_claims in key_claims.items():
            user_keys = {}
            
            for device_id, algorithm in device_claims.items():
                # 获取并删除一次性密钥
                key = await self.store.claim_one_time_key(
                    user_id, device_id, algorithm
                )
                
                if key:
                    user_keys[device_id] = {algorithm: key}
                    
            if user_keys:
                claimed_keys[user_id] = user_keys
                
        return {"one_time_keys": claimed_keys}
        
    async def update_device_last_seen(self, user_id: str, device_id: str,
                                     ip_address: Optional[str] = None,
                                     user_agent: Optional[str] = None):
        """
        更新设备最后使用时间
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            ip_address: IP地址
            user_agent: 用户代理
        """
        await self.store.update_device(
            user_id=user_id,
            device_id=device_id,
            last_seen=self.clock.time_msec(),
            ip_address=ip_address,
            user_agent=user_agent
        )
