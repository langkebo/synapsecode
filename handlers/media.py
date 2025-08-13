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
Matrix Synapse 媒体处理器

这个模块处理媒体文件的上传、下载、缩略图生成等操作。
"""

import logging
import os
import hashlib
import mimetypes
from typing import Dict, Any, Optional, Tuple, IO
from urllib.parse import quote

logger = logging.getLogger(__name__)


class MediaHandler:
    """
    媒体处理器
    
    处理媒体文件的上传、下载、存储和缩略图生成。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.store = hs.get_datastore()
        self.clock = hs.get_clock()
        self.config = hs.config
        
        # 媒体存储配置
        self.media_store_path = getattr(self.config, 'media_store_path', '/data/media')
        self.max_upload_size = getattr(self.config, 'max_upload_size', 50 * 1024 * 1024)  # 50MB
        self.max_image_pixels = getattr(self.config, 'max_image_pixels', 32 * 1024 * 1024)  # 32M pixels
        
        # 支持的媒体类型
        self.allowed_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/webm', 'video/ogg',
            'audio/mp3', 'audio/ogg', 'audio/wav', 'audio/flac',
            'application/pdf', 'text/plain'
        }
        
        # 缩略图尺寸
        self.thumbnail_sizes = [
            (32, 32), (96, 96), (320, 240), (640, 480), (800, 600)
        ]
        
    def _generate_media_id(self) -> str:
        """
        生成媒体ID
        
        Returns:
            媒体ID字符串
        """
        import secrets
        return secrets.token_urlsafe(24)
        
    def _get_media_path(self, media_id: str, server_name: str) -> str:
        """
        获取媒体文件存储路径
        
        Args:
            media_id: 媒体ID
            server_name: 服务器名称
            
        Returns:
            文件路径
        """
        # 使用哈希分散存储
        hash_prefix = hashlib.sha256(media_id.encode()).hexdigest()[:2]
        return os.path.join(
            self.media_store_path,
            'local_content' if server_name == self.hs.hostname else 'remote_content',
            server_name,
            hash_prefix,
            media_id
        )
        
    def _get_thumbnail_path(self, media_id: str, server_name: str,
                           width: int, height: int, method: str = 'scale') -> str:
        """
        获取缩略图存储路径
        
        Args:
            media_id: 媒体ID
            server_name: 服务器名称
            width: 宽度
            height: 高度
            method: 缩放方法
            
        Returns:
            缩略图路径
        """
        hash_prefix = hashlib.sha256(media_id.encode()).hexdigest()[:2]
        filename = f"{width}x{height}_{method}"
        return os.path.join(
            self.media_store_path,
            'local_thumbnails' if server_name == self.hs.hostname else 'remote_thumbnails',
            server_name,
            hash_prefix,
            media_id,
            filename
        )
        
    async def upload_media(self, content: bytes, content_type: str,
                          filename: Optional[str] = None,
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        上传媒体文件
        
        Args:
            content: 文件内容
            content_type: MIME类型
            filename: 文件名
            user_id: 上传用户ID
            
        Returns:
            上传结果，包含媒体ID和URI
        """
        logger.info(f"Uploading media: {filename}, type: {content_type}, size: {len(content)}")
        
        # 检查文件大小
        if len(content) > self.max_upload_size:
            raise ValueError(f"File too large: {len(content)} bytes (max: {self.max_upload_size})")
            
        # 检查媒体类型
        if content_type not in self.allowed_types:
            logger.warning(f"Unsupported media type: {content_type}")
            
        # 生成媒体ID
        media_id = self._generate_media_id()
        server_name = self.hs.hostname
        
        # 计算文件哈希
        content_hash = hashlib.sha256(content).hexdigest()
        
        # 获取存储路径
        file_path = self._get_media_path(media_id, server_name)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(content)
            
        # 存储媒体信息到数据库
        await self.store.store_local_media(
            media_id=media_id,
            media_type=content_type,
            media_length=len(content),
            user_id=user_id,
            created_ts=self.clock.time_msec(),
            upload_name=filename,
            file_path=file_path,
            content_hash=content_hash
        )
        
        # 如果是图片，生成缩略图
        if content_type.startswith('image/'):
            try:
                await self._generate_thumbnails(media_id, server_name, file_path, content_type)
            except Exception as e:
                logger.warning(f"Failed to generate thumbnails for {media_id}: {e}")
                
        media_uri = f"mxc://{server_name}/{media_id}"
        logger.info(f"Media uploaded successfully: {media_uri}")
        
        return {
            "media_id": media_id,
            "content_uri": media_uri,
            "content_type": content_type,
            "content_length": len(content)
        }
        
    async def download_media(self, server_name: str, media_id: str) -> Tuple[bytes, str, str]:
        """
        下载媒体文件
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            (文件内容, MIME类型, 文件名)
        """
        logger.debug(f"Downloading media: {server_name}/{media_id}")
        
        # 检查是否为本地媒体
        if server_name == self.hs.hostname:
            return await self._download_local_media(media_id)
        else:
            return await self._download_remote_media(server_name, media_id)
            
    async def _download_local_media(self, media_id: str) -> Tuple[bytes, str, str]:
        """
        下载本地媒体文件
        
        Args:
            media_id: 媒体ID
            
        Returns:
            (文件内容, MIME类型, 文件名)
        """
        # 从数据库获取媒体信息
        media_info = await self.store.get_local_media(media_id)
        if not media_info:
            raise FileNotFoundError(f"Media {media_id} not found")
            
        file_path = media_info['file_path']
        if not os.path.exists(file_path):
            # 尝试重新构建路径
            file_path = self._get_media_path(media_id, self.hs.hostname)
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Media file not found: {file_path}")
            
        # 读取文件内容
        with open(file_path, 'rb') as f:
            content = f.read()
            
        return (
            content,
            media_info['media_type'],
            media_info.get('upload_name', media_id)
        )
        
    async def _download_remote_media(self, server_name: str, media_id: str) -> Tuple[bytes, str, str]:
        """
        下载远程媒体文件
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            (文件内容, MIME类型, 文件名)
        """
        # 检查本地缓存
        cached_media = await self.store.get_cached_remote_media(server_name, media_id)
        if cached_media:
            file_path = cached_media['file_path']
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                return (
                    content,
                    cached_media['media_type'],
                    cached_media.get('upload_name', media_id)
                )
                
        # 从远程服务器下载
        logger.info(f"Downloading remote media from {server_name}: {media_id}")
        
        # 这里应该实现实际的远程下载逻辑
        # 为了简化，我们返回一个占位符
        raise NotImplementedError("Remote media download not implemented")
        
    async def get_thumbnail(self, server_name: str, media_id: str,
                           width: int, height: int, method: str = 'scale') -> Tuple[bytes, str]:
        """
        获取缩略图
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            width: 宽度
            height: 高度
            method: 缩放方法
            
        Returns:
            (缩略图内容, MIME类型)
        """
        logger.debug(f"Getting thumbnail: {server_name}/{media_id} {width}x{height}")
        
        # 获取缩略图路径
        thumbnail_path = self._get_thumbnail_path(
            media_id, server_name, width, height, method
        )
        
        # 检查缩略图是否存在
        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as f:
                content = f.read()
            return content, 'image/jpeg'
            
        # 如果缩略图不存在，尝试生成
        if server_name == self.hs.hostname:
            media_info = await self.store.get_local_media(media_id)
            if media_info and media_info['media_type'].startswith('image/'):
                file_path = media_info['file_path']
                if not os.path.exists(file_path):
                    file_path = self._get_media_path(media_id, server_name)
                    
                if os.path.exists(file_path):
                    thumbnail_content = await self._generate_single_thumbnail(
                        file_path, width, height, method
                    )
                    if thumbnail_content:
                        # 保存缩略图
                        os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                        with open(thumbnail_path, 'wb') as f:
                            f.write(thumbnail_content)
                        return thumbnail_content, 'image/jpeg'
                        
        raise FileNotFoundError(f"Thumbnail not found: {width}x{height}")
        
    async def _generate_thumbnails(self, media_id: str, server_name: str,
                                  file_path: str, content_type: str):
        """
        生成所有尺寸的缩略图
        
        Args:
            media_id: 媒体ID
            server_name: 服务器名称
            file_path: 原始文件路径
            content_type: MIME类型
        """
        if not content_type.startswith('image/'):
            return
            
        logger.debug(f"Generating thumbnails for {media_id}")
        
        for width, height in self.thumbnail_sizes:
            try:
                thumbnail_content = await self._generate_single_thumbnail(
                    file_path, width, height, 'scale'
                )
                
                if thumbnail_content:
                    thumbnail_path = self._get_thumbnail_path(
                        media_id, server_name, width, height, 'scale'
                    )
                    
                    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                    with open(thumbnail_path, 'wb') as f:
                        f.write(thumbnail_content)
                        
                    logger.debug(f"Generated thumbnail: {width}x{height}")
                    
            except Exception as e:
                logger.warning(f"Failed to generate {width}x{height} thumbnail: {e}")
                
    async def _generate_single_thumbnail(self, file_path: str, width: int, height: int,
                                        method: str = 'scale') -> Optional[bytes]:
        """
        生成单个缩略图
        
        Args:
            file_path: 原始文件路径
            width: 宽度
            height: 高度
            method: 缩放方法
            
        Returns:
            缩略图内容，失败返回None
        """
        try:
            # 这里应该使用PIL或其他图像处理库
            # 为了简化，我们返回一个占位符
            logger.debug(f"Generating thumbnail: {width}x{height} from {file_path}")
            
            # 简单的占位符实现
            # 实际实现应该使用PIL:
            # from PIL import Image
            # with Image.open(file_path) as img:
            #     img.thumbnail((width, height), Image.LANCZOS)
            #     ...
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
            
    async def delete_media(self, media_id: str, server_name: Optional[str] = None) -> bool:
        """
        删除媒体文件
        
        Args:
            media_id: 媒体ID
            server_name: 服务器名称（可选，默认为本地）
            
        Returns:
            删除成功返回True
        """
        if server_name is None:
            server_name = self.hs.hostname
            
        logger.info(f"Deleting media: {server_name}/{media_id}")
        
        # 获取文件路径
        file_path = self._get_media_path(media_id, server_name)
        
        # 删除原始文件
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 删除缩略图
        for width, height in self.thumbnail_sizes:
            thumbnail_path = self._get_thumbnail_path(
                media_id, server_name, width, height, 'scale'
            )
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                
        # 从数据库删除记录
        if server_name == self.hs.hostname:
            await self.store.delete_local_media(media_id)
        else:
            await self.store.delete_cached_remote_media(server_name, media_id)
            
        logger.info(f"Media deleted: {media_id}")
        return True
        
    async def get_media_info(self, server_name: str, media_id: str) -> Optional[Dict[str, Any]]:
        """
        获取媒体信息
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            媒体信息
        """
        if server_name == self.hs.hostname:
            media_info = await self.store.get_local_media(media_id)
        else:
            media_info = await self.store.get_cached_remote_media(server_name, media_id)
            
        if not media_info:
            return None
            
        return {
            "media_id": media_id,
            "media_type": media_info['media_type'],
            "media_length": media_info['media_length'],
            "upload_name": media_info.get('upload_name'),
            "created_ts": media_info.get('created_ts')
        }
        
    def get_content_disposition(self, filename: Optional[str]) -> str:
        """
        生成Content-Disposition头
        
        Args:
            filename: 文件名
            
        Returns:
            Content-Disposition字符串
        """
        if filename:
            # 对文件名进行URL编码以支持非ASCII字符
            encoded_filename = quote(filename.encode('utf-8'))
            return f'inline; filename*=UTF-8\'\'\'{encoded_filename}'
        else:
            return 'inline'
            
    def guess_content_type(self, filename: str) -> str:
        """
        根据文件名猜测MIME类型
        
        Args:
            filename: 文件名
            
        Returns:
            MIME类型
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'