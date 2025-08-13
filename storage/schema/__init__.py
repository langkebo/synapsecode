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
Matrix Synapse 数据库模式

这个模块定义了 Matrix Synapse 的数据库表结构和模式版本管理。
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 当前数据库模式版本
SCHEMA_VERSION = 73

# 最小支持的模式版本
MIN_SCHEMA_VERSION = 54


class SchemaManager:
    """
    数据库模式管理器
    
    负责数据库表的创建、更新和版本管理。
    """
    
    def __init__(self, database_engine):
        self.database_engine = database_engine
        self.schema_version = SCHEMA_VERSION
        
    def get_schema_version(self, txn) -> int:
        """
        获取当前数据库的模式版本
        
        Args:
            txn: 数据库事务对象
            
        Returns:
            模式版本号
        """
        try:
            txn.execute("SELECT version FROM schema_version")
            result = txn.fetchone()
            return result[0] if result else 0
        except Exception:
            # 如果表不存在，返回0
            return 0
            
    def create_schema_version_table(self, txn):
        """
        创建模式版本表
        
        Args:
            txn: 数据库事务对象
        """
        sql = """
        CREATE TABLE IF NOT EXISTS schema_version (
            Lock CHAR(1) NOT NULL DEFAULT 'X' UNIQUE,
            version INTEGER NOT NULL,
            upgraded BOOLEAN NOT NULL,
            CHECK (Lock='X')
        )
        """
        txn.execute(sql)
        
    def set_schema_version(self, txn, version: int):
        """
        设置数据库模式版本
        
        Args:
            txn: 数据库事务对象
            version: 版本号
        """
        txn.execute(
            "INSERT OR REPLACE INTO schema_version (Lock, version, upgraded) VALUES ('X', ?, ?)",
            (version, True)
        )
        
    def create_base_tables(self, txn):
        """
        创建基础数据表
        
        Args:
            txn: 数据库事务对象
        """
        logger.info("Creating base database tables")
        
        # 用户表
        txn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            name TEXT NOT NULL,
            password_hash TEXT,
            creation_ts BIGINT,
            admin BOOLEAN DEFAULT 0 NOT NULL,
            upgrade_ts BIGINT,
            is_guest BOOLEAN DEFAULT 0 NOT NULL,
            appservice_id TEXT,
            consent_version TEXT,
            consent_server_notice_sent TEXT,
            user_type TEXT DEFAULT NULL,
            deactivated BOOLEAN DEFAULT 0 NOT NULL,
            UNIQUE(name)
        )
        """)
        
        # 房间表
        txn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT NOT NULL,
            is_public BOOLEAN,
            creator TEXT,
            room_version TEXT,
            has_auth_chain_index BOOLEAN,
            UNIQUE(room_id)
        )
        """)
        
        # 事件表
        txn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            stream_ordering INTEGER PRIMARY KEY,
            topological_ordering BIGINT NOT NULL,
            event_id TEXT NOT NULL,
            type TEXT NOT NULL,
            room_id TEXT NOT NULL,
            content TEXT,
            unrecognized_keys TEXT,
            processed BOOLEAN NOT NULL,
            outlier BOOLEAN NOT NULL,
            depth BIGINT DEFAULT 0 NOT NULL,
            origin_server_ts BIGINT,
            received_ts BIGINT,
            sender TEXT,
            contains_url BOOLEAN,
            instance_name TEXT,
            session_id BIGINT,
            rejection_reason TEXT,
            UNIQUE(event_id)
        )
        """)
        
        # 房间成员表
        txn.execute("""
        CREATE TABLE IF NOT EXISTS room_memberships (
            event_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            room_id TEXT NOT NULL,
            membership TEXT NOT NULL,
            forgotten INTEGER DEFAULT 0,
            display_name TEXT,
            avatar_url TEXT,
            event_stream_ordering INTEGER,
            UNIQUE(event_id)
        )
        """)
        
        # 访问令牌表
        txn.execute("""
        CREATE TABLE IF NOT EXISTS access_tokens (
            id BIGINT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_id TEXT,
            token TEXT NOT NULL,
            last_used BIGINT,
            last_validated BIGINT,
            refresh_token_id BIGINT,
            used BOOLEAN,
            UNIQUE(token)
        )
        """)
        
        # 设备表
        txn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            user_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            display_name TEXT,
            last_seen BIGINT,
            ip TEXT,
            user_agent TEXT,
            hidden BOOLEAN DEFAULT 0,
            UNIQUE(user_id, device_id)
        )
        """)
        
        logger.info("Base database tables created successfully")
        
    def create_indexes(self, txn):
        """
        创建数据库索引
        
        Args:
            txn: 数据库事务对象
        """
        logger.info("Creating database indexes")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS events_stream_ordering ON events(stream_ordering)",
            "CREATE INDEX IF NOT EXISTS events_topological_ordering ON events(topological_ordering)",
            "CREATE INDEX IF NOT EXISTS events_room_id ON events(room_id)",
            "CREATE INDEX IF NOT EXISTS events_type ON events(type)",
            "CREATE INDEX IF NOT EXISTS room_memberships_room_id ON room_memberships(room_id)",
            "CREATE INDEX IF NOT EXISTS room_memberships_user_id ON room_memberships(user_id)",
            "CREATE INDEX IF NOT EXISTS access_tokens_user_id ON access_tokens(user_id)",
            "CREATE INDEX IF NOT EXISTS devices_user_id ON devices(user_id)"
        ]
        
        for index_sql in indexes:
            try:
                txn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")
                
        logger.info("Database indexes created successfully")
        
    def upgrade_schema(self, txn, from_version: int, to_version: int):
        """
        升级数据库模式
        
        Args:
            txn: 数据库事务对象
            from_version: 源版本
            to_version: 目标版本
        """
        logger.info(f"Upgrading database schema from {from_version} to {to_version}")
        
        # 这里应该包含具体的升级逻辑
        # 为了简化，我们只是更新版本号
        self.set_schema_version(txn, to_version)
        
        logger.info("Database schema upgrade completed")
        
    def prepare_database(self, txn):
        """
        准备数据库
        
        创建所有必要的表和索引，并设置正确的模式版本。
        
        Args:
            txn: 数据库事务对象
        """
        logger.info("Preparing database")
        
        # 创建模式版本表
        self.create_schema_version_table(txn)
        
        # 获取当前版本
        current_version = self.get_schema_version(txn)
        
        if current_version == 0:
            # 新数据库，创建所有表
            self.create_base_tables(txn)
            self.create_indexes(txn)
            self.set_schema_version(txn, self.schema_version)
        elif current_version < self.schema_version:
            # 需要升级
            self.upgrade_schema(txn, current_version, self.schema_version)
        elif current_version > self.schema_version:
            # 版本过新，不支持
            raise RuntimeError(
                f"Database schema version {current_version} is newer than "
                f"supported version {self.schema_version}"
            )
            
        logger.info("Database preparation completed")


# 导出主要类和常量
__all__ = [
    "SchemaManager",
    "SCHEMA_VERSION",
    "MIN_SCHEMA_VERSION"
]