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
Matrix Synapse 媒体API

这个模块实现了Matrix协议的媒体相关API端点。
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class MediaAPI:
    """
    媒体API处理器
    
    实现Matrix协议的媒体上传、下载、缩略图等API端点。
    """
    
    def __init__(self, hs):
        self.hs = hs
        self.auth_handler = hs.get_auth_handler()
        self.media_handler = hs.get_media_handler()
        self.clock = hs.get_clock()
        
    async def handle_upload_media(self, access_token: str, content: bytes,
                                content_type: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        处理媒体上传请求
        
        POST /_matrix/media/r0/upload
        
        Args:
            access_token: 访问令牌
            content: 文件内容
            content_type: MIME类型
            filename: 文件名
            
        Returns:
            上传响应
        """
        logger.info(f"Processing media upload request: {filename}, type: {content_type}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            user_id = user_info['user_id']
            
            # 上传媒体
            upload_result = await self.media_handler.upload_media(
                content=content,
                content_type=content_type,
                filename=filename,
                user_id=user_id
            )
            
            logger.info(f"Media uploaded successfully: {upload_result['content_uri']}")
            
            return {
                'content_uri': upload_result['content_uri']
            }, 200
            
        except ValueError as e:
            logger.warning(f"Media upload failed: {e}")
            return {
                'errcode': 'M_TOO_LARGE' if 'too large' in str(e).lower() else 'M_INVALID_PARAM',
                'error': str(e)
            }, 413 if 'too large' in str(e).lower() else 400
        except Exception as e:
            logger.error(f"Media upload error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_download_media(self, server_name: str, media_id: str,
                                  allow_remote: bool = True) -> Tuple[bytes, str, str, int]:
        """
        处理媒体下载请求
        
        GET /_matrix/media/r0/download/{serverName}/{mediaId}
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            allow_remote: 是否允许远程下载
            
        Returns:
            (文件内容, MIME类型, 文件名, HTTP状态码)
        """
        logger.debug(f"Processing media download request: {server_name}/{media_id}")
        
        try:
            # 下载媒体
            content, content_type, filename = await self.media_handler.download_media(
                server_name=server_name,
                media_id=media_id
            )
            
            logger.debug(f"Media downloaded successfully: {len(content)} bytes")
            
            return content, content_type, filename, 200
            
        except FileNotFoundError as e:
            logger.warning(f"Media not found: {e}")
            error_content = json.dumps({
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }).encode('utf-8')
            return error_content, 'application/json', 'error.json', 404
        except Exception as e:
            logger.error(f"Media download error: {e}")
            error_content = json.dumps({
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }).encode('utf-8')
            return error_content, 'application/json', 'error.json', 500
            
    async def handle_get_thumbnail(self, server_name: str, media_id: str,
                                 width: int, height: int, method: str = 'scale',
                                 allow_remote: bool = True) -> Tuple[bytes, str, int]:
        """
        处理缩略图获取请求
        
        GET /_matrix/media/r0/thumbnail/{serverName}/{mediaId}
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            width: 宽度
            height: 高度
            method: 缩放方法
            allow_remote: 是否允许远程下载
            
        Returns:
            (缩略图内容, MIME类型, HTTP状态码)
        """
        logger.debug(f"Processing thumbnail request: {server_name}/{media_id} {width}x{height}")
        
        try:
            # 获取缩略图
            thumbnail_content, thumbnail_type = await self.media_handler.get_thumbnail(
                server_name=server_name,
                media_id=media_id,
                width=width,
                height=height,
                method=method
            )
            
            logger.debug(f"Thumbnail retrieved successfully: {len(thumbnail_content)} bytes")
            
            return thumbnail_content, thumbnail_type, 200
            
        except FileNotFoundError as e:
            logger.warning(f"Thumbnail not found: {e}")
            error_content = json.dumps({
                'errcode': 'M_NOT_FOUND',
                'error': str(e)
            }).encode('utf-8')
            return error_content, 'application/json', 404
        except Exception as e:
            logger.error(f"Thumbnail error: {e}")
            error_content = json.dumps({
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }).encode('utf-8')
            return error_content, 'application/json', 500
            
    async def handle_get_media_info(self, server_name: str, media_id: str) -> Dict[str, Any]:
        """
        处理媒体信息获取请求
        
        GET /_matrix/media/r0/info/{serverName}/{mediaId}
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            媒体信息响应
        """
        logger.debug(f"Processing media info request: {server_name}/{media_id}")
        
        try:
            # 获取媒体信息
            media_info = await self.media_handler.get_media_info(
                server_name=server_name,
                media_id=media_id
            )
            
            if not media_info:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Media not found'
                }, 404
                
            return media_info, 200
            
        except Exception as e:
            logger.error(f"Media info error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_url_preview(self, access_token: str, url: str,
                                   ts: Optional[int] = None) -> Dict[str, Any]:
        """
        处理URL预览请求
        
        GET /_matrix/media/r0/preview_url
        
        Args:
            access_token: 访问令牌
            url: 要预览的URL
            ts: 时间戳
            
        Returns:
            URL预览响应
        """
        logger.debug(f"Processing URL preview request: {url}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 简单的URL预览实现
            # 实际实现应该获取URL内容并解析元数据
            preview_data = {
                'og:url': url,
                'og:title': 'URL Preview',
                'og:description': f'Preview for {url}',
                'matrix:image:size': 0
            }
            
            return preview_data, 200
            
        except Exception as e:
            logger.error(f"URL preview error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_get_config(self) -> Dict[str, Any]:
        """
        处理媒体配置获取请求
        
        GET /_matrix/media/r0/config
        
        Returns:
            媒体配置响应
        """
        logger.debug("Processing media config request")
        
        try:
            return {
                'm.upload.size': self.media_handler.max_upload_size
            }, 200
            
        except Exception as e:
            logger.error(f"Media config error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    def parse_content_disposition(self, filename: Optional[str]) -> str:
        """
        生成Content-Disposition头
        
        Args:
            filename: 文件名
            
        Returns:
            Content-Disposition字符串
        """
        return self.media_handler.get_content_disposition(filename)
        
    def validate_media_request(self, server_name: str, media_id: str) -> bool:
        """
        验证媒体请求参数
        
        Args:
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            验证结果
        """
        # 检查服务器名称格式
        if not server_name or len(server_name) > 255:
            return False
            
        # 检查媒体ID格式
        if not media_id or len(media_id) > 255:
            return False
            
        # 检查是否包含非法字符
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', server_name):
            return False
            
        if not re.match(r'^[a-zA-Z0-9._-]+$', media_id):
            return False
            
        return True
        
    def validate_thumbnail_params(self, width: int, height: int, method: str) -> bool:
        """
        验证缩略图参数
        
        Args:
            width: 宽度
            height: 高度
            method: 缩放方法
            
        Returns:
            验证结果
        """
        # 检查尺寸范围
        if width <= 0 or height <= 0:
            return False
            
        if width > 2048 or height > 2048:
            return False
            
        # 检查缩放方法
        if method not in ['crop', 'scale']:
            return False
            
        return True
        
    def get_cache_headers(self, max_age: int = 86400) -> Dict[str, str]:
        """
        生成缓存头
        
        Args:
            max_age: 最大缓存时间（秒）
            
        Returns:
            缓存头字典
        """
        return {
            'Cache-Control': f'public, max-age={max_age}, immutable',
            'Expires': self._format_http_date(self.clock.time() + max_age)
        }
        
    def _format_http_date(self, timestamp: float) -> str:
        """
        格式化HTTP日期
        
        Args:
            timestamp: 时间戳
            
        Returns:
            HTTP日期字符串
        """
        import time
        import email.utils
        return email.utils.formatdate(timestamp, usegmt=True)
        
    async def handle_delete_media(self, access_token: str, server_name: str,
                                media_id: str) -> Dict[str, Any]:
        """
        处理媒体删除请求（管理员功能）
        
        DELETE /_synapse/admin/v1/media/{serverName}/{mediaId}
        
        Args:
            access_token: 访问令牌
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            删除响应
        """
        logger.info(f"Processing media delete request: {server_name}/{media_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 检查管理员权限
            is_admin = await self.auth_handler.is_server_admin(user_info['user_id'])
            if not is_admin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Admin access required'
                }, 403
                
            # 删除媒体
            success = await self.media_handler.delete_media(
                media_id=media_id,
                server_name=server_name
            )
            
            if success:
                logger.info(f"Media deleted successfully: {server_name}/{media_id}")
                return {
                    'deleted_media': [media_id],
                    'total': 1
                }, 200
            else:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Media not found'
                }, 404
                
        except Exception as e:
            logger.error(f"Media delete error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500
            
    async def handle_quarantine_media(self, access_token: str, server_name: str,
                                    media_id: str) -> Dict[str, Any]:
        """
        处理媒体隔离请求（管理员功能）
        
        POST /_synapse/admin/v1/media/quarantine/{serverName}/{mediaId}
        
        Args:
            access_token: 访问令牌
            server_name: 服务器名称
            media_id: 媒体ID
            
        Returns:
            隔离响应
        """
        logger.info(f"Processing media quarantine request: {server_name}/{media_id}")
        
        try:
            # 验证访问令牌
            user_info = await self.auth_handler.get_user_by_access_token(access_token)
            if not user_info:
                return {
                    'errcode': 'M_UNKNOWN_TOKEN',
                    'error': 'Invalid access token'
                }, 401
                
            # 检查管理员权限
            is_admin = await self.auth_handler.is_server_admin(user_info['user_id'])
            if not is_admin:
                return {
                    'errcode': 'M_FORBIDDEN',
                    'error': 'Admin access required'
                }, 403
                
            # 隔离媒体（标记为不可访问）
            success = await self.media_handler.quarantine_media(
                media_id=media_id,
                server_name=server_name
            )
            
            if success:
                logger.info(f"Media quarantined successfully: {server_name}/{media_id}")
                return {
                    'num_quarantined': 1
                }, 200
            else:
                return {
                    'errcode': 'M_NOT_FOUND',
                    'error': 'Media not found'
                }, 404
                
        except Exception as e:
            logger.error(f"Media quarantine error: {e}")
            return {
                'errcode': 'M_UNKNOWN',
                'error': 'Internal server error'
            }, 500