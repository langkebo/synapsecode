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
Matrix Synapse 数据库引擎

这个模块提供了不同数据库引擎的抽象和实现，
包括 SQLite 和 PostgreSQL 的支持。
"""

import logging
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseDatabaseEngine(ABC):
    """
    数据库引擎基类
    
    定义了所有数据库引擎必须实现的接口。
    """
    
    def __init__(self, database_config: Dict[str, Any]):
        self.database_config = database_config
        self.module = None
        self.database_type = "unknown"
        
    @abstractmethod
    async def create_connection(self) -> Any:
        """
        创建数据库连接
        
        Returns:
            数据库连接对象
        """
        pass
        
    @abstractmethod
    def get_db_locale(self, txn) -> str:
        """
        获取数据库的区域设置
        
        Args:
            txn: 数据库事务对象
            
        Returns:
            区域设置字符串
        """
        pass
        
    @abstractmethod
    def convert_param_style(self, sql: str) -> str:
        """
        转换SQL参数样式
        
        Args:
            sql: 原始SQL语句
            
        Returns:
            转换后的SQL语句
        """
        pass


class Sqlite3Engine(BaseDatabaseEngine):
    """
    SQLite3 数据库引擎
    
    提供 SQLite3 数据库的连接和操作支持。
    """
    
    def __init__(self, database_config: Dict[str, Any]):
        super().__init__(database_config)
        self.database_type = "sqlite3"
        
        try:
            import sqlite3
            self.module = sqlite3
        except ImportError:
            logger.error("SQLite3 module not available")
            raise
            
    async def create_connection(self) -> Any:
        """
        创建 SQLite3 连接
        
        Returns:
            SQLite3 连接对象
        """
        database_path = self.database_config.get("database", ":memory:")
        logger.debug(f"Creating SQLite3 connection to: {database_path}")
        
        connection = self.module.connect(
            database_path,
            check_same_thread=False,
            isolation_level=None
        )
        
        # 设置 SQLite 优化参数
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA cache_size=10000")
        connection.execute("PRAGMA temp_store=memory")
        
        return connection
        
    def get_db_locale(self, txn) -> str:
        """
        获取 SQLite 数据库的区域设置
        
        Args:
            txn: SQLite 事务对象
            
        Returns:
            区域设置字符串
        """
        return "C"
        
    def convert_param_style(self, sql: str) -> str:
        """
        转换为 SQLite 参数样式
        
        Args:
            sql: 原始SQL语句
            
        Returns:
            转换后的SQL语句
        """
        # SQLite 使用 ? 作为参数占位符
        return sql.replace("%s", "?")


class PostgresEngine(BaseDatabaseEngine):
    """
    PostgreSQL 数据库引擎
    
    提供 PostgreSQL 数据库的连接和操作支持。
    """
    
    def __init__(self, database_config: Dict[str, Any]):
        super().__init__(database_config)
        self.database_type = "postgresql"
        
        try:
            import psycopg2
            self.module = psycopg2
        except ImportError:
            logger.error("psycopg2 module not available")
            raise
            
    async def create_connection(self) -> Any:
        """
        创建 PostgreSQL 连接
        
        Returns:
            PostgreSQL 连接对象
        """
        connection_params = {
            "host": self.database_config.get("host", "localhost"),
            "port": self.database_config.get("port", 5432),
            "database": self.database_config.get("database", "synapse"),
            "user": self.database_config.get("user", "synapse_user"),
            "password": self.database_config.get("password", "")
        }
        
        logger.debug(f"Creating PostgreSQL connection to: {connection_params['host']}:{connection_params['port']}")
        
        connection = self.module.connect(**connection_params)
        connection.set_isolation_level(self.module.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        
        return connection
        
    def get_db_locale(self, txn) -> str:
        """
        获取 PostgreSQL 数据库的区域设置
        
        Args:
            txn: PostgreSQL 事务对象
            
        Returns:
            区域设置字符串
        """
        txn.execute("SELECT datcollate FROM pg_database WHERE datname = current_database()")
        result = txn.fetchone()
        return result[0] if result else "C"
        
    def convert_param_style(self, sql: str) -> str:
        """
        转换为 PostgreSQL 参数样式
        
        Args:
            sql: 原始SQL语句
            
        Returns:
            转换后的SQL语句
        """
        # PostgreSQL 使用 %s 作为参数占位符
        return sql


def create_engine(database_config: Dict[str, Any]) -> BaseDatabaseEngine:
    """
    根据配置创建数据库引擎
    
    Args:
        database_config: 数据库配置字典
        
    Returns:
        数据库引擎实例
        
    Raises:
        ValueError: 不支持的数据库类型
    """
    database_type = database_config.get("name", "sqlite3")
    
    if database_type == "sqlite3":
        return Sqlite3Engine(database_config)
    elif database_type in ["postgresql", "psycopg2"]:
        return PostgresEngine(database_config)
    else:
        raise ValueError(f"Unsupported database type: {database_type}")


# 导出主要类和函数
__all__ = [
    "BaseDatabaseEngine",
    "Sqlite3Engine",
    "PostgresEngine",
    "create_engine"
]