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

import logging
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from synapse.api.errors import StoreError
from synapse.storage._base import SQLBaseStore
from synapse.storage.database import (
    DatabasePool,
    LoggingDatabaseConnection,
    LoggingTransaction,
)
from synapse.storage.engines import PostgresEngine
from synapse.types import JsonDict
from synapse.util import json_encoder

if TYPE_CHECKING:
    from synapse.server import HomeServer

logger = logging.getLogger(__name__)


class FriendsWorkerStore(SQLBaseStore):
    """好友关系数据存储的工作类"""

    def __init__(
        self,
        database: DatabasePool,
        db_conn: LoggingDatabaseConnection,
        hs: "HomeServer",
    ):
        super().__init__(database, db_conn, hs)
        self.database_engine = database.engine

    async def get_friendship(
        self, user1_id: str, user2_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取两个用户之间的好友关系
        
        Args:
            user1_id: 用户1的ID
            user2_id: 用户2的ID
            
        Returns:
            好友关系信息，如果不存在则返回None
            
        Raises:
            StoreError: 数据库操作失败时抛出
        """
        if not user1_id or not user2_id:
            logger.warning("get_friendship called with empty user IDs")
            return None
            
        def _get_friendship_txn(txn: LoggingTransaction) -> Optional[Dict[str, Any]]:
            try:
                sql = """
                    SELECT user1_id, user2_id, status, created_ts
                    FROM user_friendships
                    WHERE (user1_id = ? AND user2_id = ?)
                       OR (user1_id = ? AND user2_id = ?)
                    LIMIT 1
                """
                txn.execute(sql, (user1_id, user2_id, user2_id, user1_id))
                row = txn.fetchone()
                if row:
                    return {
                        "user1_id": row[0],
                        "user2_id": row[1],
                        "status": row[2],
                        "created_ts": row[3],
                    }
                return None
            except Exception as e:
                logger.error(f"Failed to get friendship between {user1_id} and {user2_id}: {e}")
                raise StoreError(500, "Failed to retrieve friendship")

        try:
            return await self.db_pool.runInteraction(
                "get_friendship", _get_friendship_txn
            )
        except Exception as e:
            logger.error(f"Database error in get_friendship: {e}")
            raise

    async def get_user_friendships(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户的所有好友关系
        
        Args:
            user_id: 用户ID
            limit: 返回结果数量限制
            offset: 偏移量
            
        Returns:
            好友关系列表
        """
        if not user_id:
            raise StoreError(400, "User ID cannot be empty")
        if limit <= 0 or limit > 1000:
            raise StoreError(400, "Limit must be between 1 and 1000")
        if offset < 0:
            raise StoreError(400, "Offset must be non-negative")
            
        def _get_user_friendships_txn(txn: LoggingTransaction) -> List[Dict[str, Any]]:
            try:
                sql = """
                    SELECT user1_id, user2_id, status, created_ts
                    FROM user_friendships
                    WHERE (user1_id = ? OR user2_id = ?)
                      AND status = 'active'
                    ORDER BY created_ts DESC
                    LIMIT ? OFFSET ?
                """
                txn.execute(sql, (user_id, user_id, limit, offset))
                rows = txn.fetchall()
                
                friendships = []
                for row in rows:
                    friend_id = row[1] if row[0] == user_id else row[0]
                    friendships.append({
                        "friend_id": friend_id,
                        "status": row[2],
                        "created_ts": row[3],
                    })
                
                logger.info(f"Retrieved {len(friendships)} friendships for user {user_id} (limit: {limit}, offset: {offset})")
                return friendships
            except Exception as e:
                logger.error(f"Failed to get friendships for user {user_id}: {e}")
                raise StoreError(500, f"Database error: {e}")

        return await self.db_pool.runInteraction(
            "get_user_friendships", _get_user_friendships_txn
        )

    async def create_friendship(
        self, user1_id: str, user2_id: str, created_ts: int
    ) -> None:
        """创建好友关系
        
        Args:
            user1_id: 用户1的ID
            user2_id: 用户2的ID
            created_ts: 创建时间戳
            
        Raises:
            StoreError: 数据库操作失败时抛出
        """
        if not user1_id or not user2_id:
            raise StoreError(400, "User IDs cannot be empty")
            
        if user1_id == user2_id:
            raise StoreError(400, "Cannot create friendship with self")
            
        # 确保user1_id < user2_id，保持一致性
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
            
        def _create_friendship_txn(txn: LoggingTransaction) -> None:
            try:
                # 检查是否已存在好友关系
                check_sql = """
                    SELECT 1 FROM user_friendships
                    WHERE user1_id = ? AND user2_id = ?
                    LIMIT 1
                """
                txn.execute(check_sql, (user1_id, user2_id))
                if txn.fetchone():
                    logger.warning(f"Friendship already exists between {user1_id} and {user2_id}")
                    return
                    
                sql = """
                    INSERT INTO user_friendships (user1_id, user2_id, status, created_ts)
                    VALUES (?, ?, 'active', ?)
                """
                txn.execute(sql, (user1_id, user2_id, created_ts))
                logger.info(f"Created friendship between {user1_id} and {user2_id}")
            except Exception as e:
                logger.error(f"Failed to create friendship between {user1_id} and {user2_id}: {e}")
                raise StoreError(500, "Failed to create friendship")

        try:
            await self.db_pool.runInteraction(
                "create_friendship", _create_friendship_txn
            )
        except Exception as e:
            logger.error(f"Database error in create_friendship: {e}")
            raise

    async def remove_friendship(self, user1_id: str, user2_id: str) -> bool:
        """删除好友关系
        
        Args:
            user1_id: 用户1的ID
            user2_id: 用户2的ID
            
        Returns:
            是否成功删除
        """
        def _remove_friendship_txn(txn: LoggingTransaction) -> bool:
            sql = """
                DELETE FROM user_friendships
                WHERE (user1_id = ? AND user2_id = ?)
                   OR (user1_id = ? AND user2_id = ?)
            """
            txn.execute(sql, (user1_id, user2_id, user2_id, user1_id))
            return txn.rowcount > 0

        return await self.db_pool.runInteraction(
            "remove_friendship", _remove_friendship_txn
        )

    async def get_friend_request(
        self, sender_user_id: str, target_user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取好友请求
        
        Args:
            sender_user_id: 发送者用户ID
            target_user_id: 目标用户ID
            
        Returns:
            好友请求信息，如果不存在则返回None
        """
        def _get_friend_request_txn(txn: LoggingTransaction) -> Optional[Dict[str, Any]]:
            sql = """
                SELECT request_id, sender_user_id, target_user_id, message, 
                       status, created_ts, updated_ts
                FROM friend_requests
                WHERE sender_user_id = ? AND target_user_id = ?
                ORDER BY created_ts DESC
                LIMIT 1
            """
            txn.execute(sql, (sender_user_id, target_user_id))
            row = txn.fetchone()
            if row:
                return {
                    "request_id": row[0],
                    "sender_user_id": row[1],
                    "target_user_id": row[2],
                    "message": row[3],
                    "status": row[4],
                    "created_ts": row[5],
                    "updated_ts": row[6],
                }
            return None

        return await self.db_pool.runInteraction(
            "get_friend_request", _get_friend_request_txn
        )

    async def get_friend_request_by_id(
        self, request_id: str
    ) -> Optional[Dict[str, Any]]:
        """根据请求ID获取好友请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            好友请求信息，如果不存在则返回None
        """
        def _get_friend_request_by_id_txn(txn: LoggingTransaction) -> Optional[Dict[str, Any]]:
            sql = """
                SELECT request_id, sender_user_id, target_user_id, message, 
                       status, created_ts, updated_ts
                FROM friend_requests
                WHERE request_id = ?
            """
            txn.execute(sql, (request_id,))
            row = txn.fetchone()
            if row:
                return {
                    "request_id": row[0],
                    "sender_user_id": row[1],
                    "target_user_id": row[2],
                    "message": row[3],
                    "status": row[4],
                    "created_ts": row[5],
                    "updated_ts": row[6],
                }
            return None

        return await self.db_pool.runInteraction(
            "get_friend_request_by_id", _get_friend_request_by_id_txn
        )

    async def create_friend_request(
        self,
        sender_user_id: str,
        target_user_id: str,
        message: Optional[str],
        created_ts: int,
    ) -> str:
        """创建好友请求
        
        Args:
            sender_user_id: 发送者用户ID
            target_user_id: 目标用户ID
            message: 请求消息
            created_ts: 创建时间戳
            
        Returns:
            请求ID
            
        Raises:
            StoreError: 数据库操作失败时抛出
        """
        if not sender_user_id or not target_user_id:
            raise StoreError(400, "User IDs cannot be empty")
            
        if sender_user_id == target_user_id:
            raise StoreError(400, "Cannot send friend request to self")
            
        def _create_friend_request_txn(txn: LoggingTransaction) -> str:
            try:
                # 检查是否已存在待处理的请求
                check_sql = """
                    SELECT 1 FROM friend_requests
                    WHERE sender_user_id = ? AND target_user_id = ? AND status = 'pending'
                    LIMIT 1
                """
                txn.execute(check_sql, (sender_user_id, target_user_id))
                if txn.fetchone():
                    logger.warning(f"Pending friend request already exists from {sender_user_id} to {target_user_id}")
                    raise StoreError(409, "Friend request already exists")
                
                # 生成请求ID
                request_id = self._generate_request_id()
                
                sql = """
                    INSERT INTO friend_requests 
                    (request_id, sender_user_id, target_user_id, message, status, created_ts, updated_ts)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """
                txn.execute(sql, (
                    request_id, sender_user_id, target_user_id, message, 
                    created_ts, created_ts
                ))
                logger.info(f"Created friend request {request_id} from {sender_user_id} to {target_user_id}")
                return request_id
            except StoreError:
                raise
            except Exception as e:
                logger.error(f"Failed to create friend request from {sender_user_id} to {target_user_id}: {e}")
                raise StoreError(500, "Failed to create friend request")

        try:
            return await self.db_pool.runInteraction(
                "create_friend_request", _create_friend_request_txn
            )
        except Exception as e:
            logger.error(f"Database error in create_friend_request: {e}")
            raise

    async def update_friend_request_status(
        self, request_id: str, status: str, updated_ts: int
    ) -> None:
        """更新好友请求状态
        
        Args:
            request_id: 请求ID
            status: 新状态
            updated_ts: 更新时间戳
        """
        def _update_friend_request_status_txn(txn: LoggingTransaction) -> None:
            sql = """
                UPDATE friend_requests
                SET status = ?, updated_ts = ?
                WHERE request_id = ?
            """
            txn.execute(sql, (status, updated_ts, request_id))

        await self.db_pool.runInteraction(
            "update_friend_request_status", _update_friend_request_status_txn
        )

    async def get_friend_requests_sent_by_user(
        self, user_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户发送的好友请求
        
        Args:
            user_id: 用户ID
            status: 请求状态过滤 (pending, accepted, rejected)
            limit: 返回结果数量限制
            offset: 偏移量
            
        Returns:
            好友请求列表
        """
        if not user_id:
            raise StoreError(400, "User ID cannot be empty")
        if limit <= 0 or limit > 500:
            raise StoreError(400, "Limit must be between 1 and 500")
        if offset < 0:
            raise StoreError(400, "Offset must be non-negative")
        if status and status not in ['pending', 'accepted', 'rejected']:
            raise StoreError(400, "Invalid status filter")
            
        def _get_friend_requests_sent_txn(txn: LoggingTransaction) -> List[Dict[str, Any]]:
            try:
                if status:
                    sql = """
                        SELECT request_id, sender_user_id, target_user_id, message, 
                               status, created_ts, updated_ts
                        FROM friend_requests
                        WHERE sender_user_id = ? AND status = ?
                        ORDER BY created_ts DESC
                        LIMIT ? OFFSET ?
                    """
                    txn.execute(sql, (user_id, status, limit, offset))
                else:
                    sql = """
                        SELECT request_id, sender_user_id, target_user_id, message, 
                               status, created_ts, updated_ts
                        FROM friend_requests
                        WHERE sender_user_id = ?
                        ORDER BY created_ts DESC
                        LIMIT ? OFFSET ?
                    """
                    txn.execute(sql, (user_id, limit, offset))
                    
                rows = txn.fetchall()
                requests = [
                    {
                        "request_id": row[0],
                        "sender_user_id": row[1],
                        "target_user_id": row[2],
                        "message": row[3],
                        "status": row[4],
                        "created_ts": row[5],
                        "updated_ts": row[6],
                    }
                    for row in rows
                ]
                
                logger.info(f"Retrieved {len(requests)} sent friend requests for user {user_id} (status: {status}, limit: {limit}, offset: {offset})")
                return requests
            except Exception as e:
                logger.error(f"Failed to get sent friend requests for user {user_id}: {e}")
                raise StoreError(500, f"Database error: {e}")

        return await self.db_pool.runInteraction(
            "get_friend_requests_sent_by_user", _get_friend_requests_sent_txn
        )

    async def get_friend_requests_received_by_user(
        self, user_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户接收的好友请求
        
        Args:
            user_id: 用户ID
            status: 请求状态过滤 (pending, accepted, rejected)
            limit: 返回结果数量限制
            offset: 偏移量
            
        Returns:
            好友请求列表
        """
        if not user_id:
            raise StoreError(400, "User ID cannot be empty")
        if limit <= 0 or limit > 500:
            raise StoreError(400, "Limit must be between 1 and 500")
        if offset < 0:
            raise StoreError(400, "Offset must be non-negative")
        if status and status not in ['pending', 'accepted', 'rejected']:
            raise StoreError(400, "Invalid status filter")
            
        def _get_friend_requests_received_txn(txn: LoggingTransaction) -> List[Dict[str, Any]]:
            try:
                if status:
                    sql = """
                        SELECT request_id, sender_user_id, target_user_id, message, 
                               status, created_ts, updated_ts
                        FROM friend_requests
                        WHERE target_user_id = ? AND status = ?
                        ORDER BY created_ts DESC
                        LIMIT ? OFFSET ?
                    """
                    txn.execute(sql, (user_id, status, limit, offset))
                else:
                    sql = """
                        SELECT request_id, sender_user_id, target_user_id, message, 
                               status, created_ts, updated_ts
                        FROM friend_requests
                        WHERE target_user_id = ?
                        ORDER BY created_ts DESC
                        LIMIT ? OFFSET ?
                    """
                    txn.execute(sql, (user_id, limit, offset))
                    
                rows = txn.fetchall()
                requests = [
                    {
                        "request_id": row[0],
                        "sender_user_id": row[1],
                        "target_user_id": row[2],
                        "message": row[3],
                        "status": row[4],
                        "created_ts": row[5],
                        "updated_ts": row[6],
                    }
                    for row in rows
                ]
                
                logger.info(f"Retrieved {len(requests)} received friend requests for user {user_id} (status: {status}, limit: {limit}, offset: {offset})")
                return requests
            except Exception as e:
                logger.error(f"Failed to get received friend requests for user {user_id}: {e}")
                raise StoreError(500, f"Database error: {e}")

        return await self.db_pool.runInteraction(
            "get_friend_requests_received_by_user", _get_friend_requests_received_txn
        )

    async def create_user_block(
        self, blocker_user_id: str, blocked_user_id: str, created_ts: int
    ) -> None:
        """创建用户屏蔽关系
        
        Args:
            blocker_user_id: 屏蔽者用户ID
            blocked_user_id: 被屏蔽用户ID
            created_ts: 创建时间戳
            
        Raises:
            StoreError: 数据库操作失败时抛出
        """
        if not blocker_user_id or not blocked_user_id:
            raise StoreError(400, "User IDs cannot be empty")
            
        if blocker_user_id == blocked_user_id:
            raise StoreError(400, "Cannot block self")
            
        def _create_user_block_txn(txn: LoggingTransaction) -> None:
            try:
                # 先检查是否已存在屏蔽关系
                check_sql = """
                    SELECT 1 FROM user_blocks
                    WHERE blocker_user_id = ? AND blocked_user_id = ?
                    LIMIT 1
                """
                txn.execute(check_sql, (blocker_user_id, blocked_user_id))
                if txn.fetchone() is None:
                    # 如果不存在，则插入新记录
                    insert_sql = """
                        INSERT INTO user_blocks (blocker_user_id, blocked_user_id, created_ts)
                        VALUES (?, ?, ?)
                    """
                    txn.execute(insert_sql, (blocker_user_id, blocked_user_id, created_ts))
                    logger.info(f"Created user block: {blocker_user_id} blocked {blocked_user_id}")
                else:
                    logger.warning(f"Block relationship already exists: {blocker_user_id} -> {blocked_user_id}")
            except Exception as e:
                logger.error(f"Failed to create user block {blocker_user_id} -> {blocked_user_id}: {e}")
                raise StoreError(500, "Failed to create user block")

        try:
            await self.db_pool.runInteraction(
                "create_user_block", _create_user_block_txn
            )
        except Exception as e:
            logger.error(f"Database error in create_user_block: {e}")
            raise

    async def remove_user_block(
        self, blocker_user_id: str, blocked_user_id: str
    ) -> bool:
        """删除用户屏蔽关系
        
        Args:
            blocker_user_id: 屏蔽者用户ID
            blocked_user_id: 被屏蔽用户ID
            
        Returns:
            是否成功删除
        """
        def _remove_user_block_txn(txn: LoggingTransaction) -> bool:
            sql = """
                DELETE FROM user_blocks
                WHERE blocker_user_id = ? AND blocked_user_id = ?
            """
            txn.execute(sql, (blocker_user_id, blocked_user_id))
            return txn.rowcount > 0

        return await self.db_pool.runInteraction(
            "remove_user_block", _remove_user_block_txn
        )

    async def get_user_blocks(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户屏蔽的所有用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            屏蔽关系列表
        """
        def _get_user_blocks_txn(txn: LoggingTransaction) -> List[Dict[str, Any]]:
            sql = """
                SELECT blocker_user_id, blocked_user_id, created_ts
                FROM user_blocks
                WHERE blocker_user_id = ?
                ORDER BY created_ts DESC
            """
            txn.execute(sql, (user_id,))
            rows = txn.fetchall()
            return [
                {
                    "blocker_user_id": row[0],
                    "blocked_user_id": row[1],
                    "created_ts": row[2],
                }
                for row in rows
            ]

        return await self.db_pool.runInteraction(
            "get_user_blocks", _get_user_blocks_txn
        )

    async def is_user_blocked(
        self, blocker_user_id: str, blocked_user_id: str
    ) -> bool:
        """检查用户是否被屏蔽
        
        Args:
            blocker_user_id: 屏蔽者用户ID
            blocked_user_id: 被屏蔽用户ID
            
        Returns:
            是否被屏蔽
        """
        def _is_user_blocked_txn(txn: LoggingTransaction) -> bool:
            sql = """
                SELECT 1 FROM user_blocks
                WHERE blocker_user_id = ? AND blocked_user_id = ?
                LIMIT 1
            """
            txn.execute(sql, (blocker_user_id, blocked_user_id))
            return txn.fetchone() is not None

        return await self.db_pool.runInteraction(
            "is_user_blocked", _is_user_blocked_txn
        )

    def _generate_request_id(self) -> str:
        """生成唯一的请求ID"""
        return str(uuid.uuid4())


class FriendsStore(FriendsWorkerStore):
    """好友关系数据存储的主类"""
    pass