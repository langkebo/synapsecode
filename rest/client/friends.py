# Copyright 2024 OpenMarket Ltd
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

"""好友管理相关的REST API端点"""

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Tuple

from synapse.api.errors import Codes, SynapseError
from synapse.http.server import HttpServer
from synapse.http.servlet import (
    RestServlet,
    parse_integer,
    parse_json_object_from_request,
    parse_string,
)
from synapse.http.site import SynapseRequest
from synapse.rest.client._base import client_patterns
from synapse.types import JsonDict

if TYPE_CHECKING:
    from synapse.server import HomeServer

logger = logging.getLogger(__name__)


class FriendRequestServlet(RestServlet):
    """处理好友请求的发送"""
    
    PATTERNS = client_patterns("/friends/request", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """发送好友请求
        
        请求体格式:
        {
            "user_id": "@target:example.com",
            "message": "Hello, let's be friends!"
        }
        """
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        content = parse_json_object_from_request(request)
        
        target_user_id = content.get("user_id")
        if not target_user_id:
            raise SynapseError(
                HTTPStatus.BAD_REQUEST, "Missing user_id", Codes.MISSING_PARAM
            )
            
        message = content.get("message")
        
        result = await self.friends_handler.send_friend_request(
            requester, target_user_id, message
        )
        
        return HTTPStatus.OK, result


class FriendRequestResponseServlet(RestServlet):
    """处理好友请求的响应"""
    
    PATTERNS = client_patterns("/friends/request/(?P<request_id>[^/]*)/response", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_POST(
        self, request: SynapseRequest, request_id: str
    ) -> Tuple[int, JsonDict]:
        """响应好友请求
        
        请求体格式:
        {
            "accept": true
        }
        """
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        content = parse_json_object_from_request(request)
        
        accept = content.get("accept")
        if accept is None:
            raise SynapseError(
                HTTPStatus.BAD_REQUEST, "Missing accept parameter", Codes.MISSING_PARAM
            )
            
        if not isinstance(accept, bool):
            raise SynapseError(
                HTTPStatus.BAD_REQUEST, "accept must be a boolean", Codes.INVALID_PARAM
            )
            
        result = await self.friends_handler.respond_to_friend_request(
            requester, request_id, accept
        )
        
        return HTTPStatus.OK, result


class FriendRequestsServlet(RestServlet):
    """获取好友请求列表"""
    
    PATTERNS = client_patterns("/friends/requests", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """获取好友请求列表
        
        查询参数:
        - direction: "sent" 或 "received" (默认: "received")
        """
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        
        direction = parse_string(
            request, "direction", default="received", allowed_values=["sent", "received"]
        )
        
        requests = await self.friends_handler.get_friend_requests(requester, direction)
        
        return HTTPStatus.OK, {"requests": requests}


class FriendsListServlet(RestServlet):
    """获取好友列表"""
    
    PATTERNS = client_patterns("/friends", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """获取好友列表"""
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        
        friends = await self.friends_handler.get_friends_list(requester)
        
        return HTTPStatus.OK, {"friends": friends}


class FriendRemoveServlet(RestServlet):
    """删除好友"""
    
    PATTERNS = client_patterns("/friends/(?P<user_id>[^/]*)", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_DELETE(
        self, request: SynapseRequest, user_id: str
    ) -> Tuple[int, JsonDict]:
        """删除好友关系"""
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        
        result = await self.friends_handler.remove_friend(requester, user_id)
        
        return HTTPStatus.OK, result


class FriendSearchServlet(RestServlet):
    """搜索用户（用于添加好友）"""
    
    PATTERNS = client_patterns("/friends/search", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """搜索用户
        
        查询参数:
        - q: 搜索关键词
        - limit: 结果数量限制 (默认: 10)
        """
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        
        search_term = parse_string(request, "q", required=True)
        limit = parse_integer(request, "limit", default=10)
        
        if limit < 1 or limit > 100:
            raise SynapseError(
                HTTPStatus.BAD_REQUEST, "limit must be between 1 and 100", Codes.INVALID_PARAM
            )
            
        results = await self.friends_handler.search_users(requester, search_term, limit)
        
        return HTTPStatus.OK, {"results": results}


class UserBlockServlet(RestServlet):
    """屏蔽用户"""
    
    PATTERNS = client_patterns("/friends/block", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """屏蔽用户
        
        请求体格式:
        {
            "user_id": "@target:example.com"
        }
        """
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        content = parse_json_object_from_request(request)
        
        target_user_id = content.get("user_id")
        if not target_user_id:
            raise SynapseError(
                HTTPStatus.BAD_REQUEST, "Missing user_id", Codes.MISSING_PARAM
            )
            
        result = await self.friends_handler.block_user(requester, target_user_id)
        
        return HTTPStatus.OK, result


class UserUnblockServlet(RestServlet):
    """取消屏蔽用户"""
    
    PATTERNS = client_patterns("/friends/unblock", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """取消屏蔽用户
        
        请求体格式:
        {
            "user_id": "@target:example.com"
        }
        """
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        content = parse_json_object_from_request(request)
        
        target_user_id = content.get("user_id")
        if not target_user_id:
            raise SynapseError(
                HTTPStatus.BAD_REQUEST, "Missing user_id", Codes.MISSING_PARAM
            )
            
        result = await self.friends_handler.unblock_user(requester, target_user_id)
        
        return HTTPStatus.OK, result


class BlockedUsersServlet(RestServlet):
    """获取被屏蔽用户列表"""
    
    PATTERNS = client_patterns("/friends/blocked", v1=True)
    CATEGORY = "Friend management requests"

    def __init__(self, hs: "HomeServer"):
        super().__init__()
        self.hs = hs
        self.auth = hs.get_auth()
        self.friends_handler = hs.get_friends_handler()

    async def on_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        """获取被屏蔽用户列表"""
        requester = await self.auth.get_user_by_req(request, allow_guest=False)
        
        blocked_users = await self.friends_handler.get_blocked_users(requester)
        
        return HTTPStatus.OK, {"blocked_users": blocked_users}


def register_servlets(hs: "HomeServer", http_server: HttpServer) -> None:
    """注册好友管理相关的servlet"""
    FriendRequestServlet(hs).register(http_server)
    FriendRequestResponseServlet(hs).register(http_server)
    FriendRequestsServlet(hs).register(http_server)
    FriendsListServlet(hs).register(http_server)
    FriendRemoveServlet(hs).register(http_server)
    FriendSearchServlet(hs).register(http_server)
    UserBlockServlet(hs).register(http_server)
    UserUnblockServlet(hs).register(http_server)
    BlockedUsersServlet(hs).register(http_server)