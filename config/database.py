# Copyright 2014-2016 OpenMarket Ltd
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
from typing import Any, Dict, List, Optional

from synapse.config._base import Config, ConfigError
from synapse.config._util import validate_config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = """
# Database configuration
database:
  # The database engine name
  name: sqlite3
  # Database-specific arguments
  args:
    # Path to the database file for SQLite
    database: /data/homeserver.db
    
    # For PostgreSQL, use:
    # user: synapse_user
    # password: secretpassword
    # database: synapse
    # host: localhost
    # port: 5432
    # cp_min: 5
    # cp_max: 10
    
    # Connection pool settings (for PostgreSQL)
    # cp_min: 5
    # cp_max: 10
    # cp_reconnect: true
    
    # SQLite-specific settings
    # journal_mode: WAL
    # synchronous: NORMAL
    # cache_size: -2000  # 2MB cache
"""


class DatabaseConnectionConfig:
    """Configuration for a database connection."""
    
    def __init__(self, name: str, db_config: Dict[str, Any]):
        self.name = name
        self.config = db_config.copy()
        
        # Validate database name
        if name not in ["sqlite3", "psycopg2", "psycopg2cffi"]:
            raise ConfigError(f"Unsupported database engine: {name}")
            
        # Set default args if not provided
        if "args" not in self.config:
            self.config["args"] = {}
            
        # Database-specific validation and defaults
        if name == "sqlite3":
            self._setup_sqlite_config()
        elif name in ["psycopg2", "psycopg2cffi"]:
            self._setup_postgres_config()
            
        # Set database engine for compatibility
        self.database_engine = name
            
    def _setup_sqlite_config(self) -> None:
        """Setup SQLite-specific configuration."""
        args = self.config["args"]
        
        # Default database path
        if "database" not in args:
            args["database"] = "/data/homeserver.db"
            
        # SQLite optimization settings for low-resource servers
        if "journal_mode" not in args:
            args["journal_mode"] = "WAL"
            
        if "synchronous" not in args:
            args["synchronous"] = "NORMAL"
            
        if "cache_size" not in args:
            args["cache_size"] = -2000  # 2MB cache
            
        if "temp_store" not in args:
            args["temp_store"] = "memory"
            
        if "mmap_size" not in args:
            args["mmap_size"] = 268435456  # 256MB
            
    def _setup_postgres_config(self) -> None:
        """Setup PostgreSQL-specific configuration."""
        args = self.config["args"]
        
        # Required PostgreSQL settings
        required_keys = ["user", "database"]
        for key in required_keys:
            if key not in args:
                raise ConfigError(f"Missing required PostgreSQL config: {key}")
                
        # Default connection pool settings for low-resource servers
        if "cp_min" not in args:
            args["cp_min"] = 2
            
        if "cp_max" not in args:
            args["cp_max"] = 5
            
        if "cp_reconnect" not in args:
            args["cp_reconnect"] = True
            
        # Default host and port
        if "host" not in args:
            args["host"] = "localhost"
            
        if "port" not in args:
            args["port"] = 5432


class DatabaseConfig(Config):
    """Configuration for database connections."""
    
    section = "database"
    
    def __init__(self, root_config: Optional[Dict[str, Any]] = None):
        super().__init__(root_config)
        self.databases: List[DatabaseConnectionConfig] = []
        
    def read_config(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """Read database configuration from config dict."""
        # Handle both single database and multiple databases
        database_config = config.get("database")
        databases_config = config.get("databases")
        
        if database_config and databases_config:
            raise ConfigError("Cannot specify both 'database' and 'databases'")
            
        if database_config:
            # Single database configuration
            db_name = database_config.get("name")
            if not db_name:
                raise ConfigError("Database name is required")
                
            self.databases = [DatabaseConnectionConfig(db_name, database_config)]
            
        elif databases_config:
            # Multiple databases configuration
            self.databases = []
            for db_config in databases_config:
                db_name = db_config.get("name")
                if not db_name:
                    raise ConfigError("Database name is required for each database")
                self.databases.append(DatabaseConnectionConfig(db_name, db_config))
                
        else:
            # Default SQLite configuration
            default_config = {
                "name": "sqlite3",
                "args": {
                    "database": "/data/homeserver.db"
                }
            }
            self.databases = [DatabaseConnectionConfig("sqlite3", default_config)]
            
        # Validate at least one database is configured
        if not self.databases:
            raise ConfigError("At least one database must be configured")
            
    def generate_config_section(self, data_dir_path: str, **kwargs: Any) -> str:
        """Generate the database configuration section."""
        return DEFAULT_CONFIG
        
    @property
    def database_config(self) -> DatabaseConnectionConfig:
        """Get the main database configuration."""
        return self.databases[0]
        
    def get_single_database(self) -> DatabaseConnectionConfig:
        """Get the single database configuration.
        
        Returns:
            The database configuration.
            
        Raises:
            ConfigError: If multiple databases are configured.
        """
        if len(self.databases) != 1:
            raise ConfigError(
                "Multiple databases configured, use get_databases() instead"
            )
        return self.databases[0]
        
    def get_databases(self) -> List[DatabaseConnectionConfig]:
        """Get all database configurations.
        
        Returns:
            List of database configurations.
        """
        return self.databases.copy()
        
    def validate_database_config(self) -> None:
        """Validate the database configuration."""
        for db_config in self.databases:
            # Check if database engine is supported
            if db_config.name not in ["sqlite3", "psycopg2", "psycopg2cffi"]:
                raise ConfigError(f"Unsupported database engine: {db_config.name}")
                
            # Validate SQLite configuration
            if db_config.name == "sqlite3":
                args = db_config.config.get("args", {})
                if "database" not in args:
                    raise ConfigError("SQLite database path is required")
                    
            # Validate PostgreSQL configuration
            elif db_config.name in ["psycopg2", "psycopg2cffi"]:
                args = db_config.config.get("args", {})
                required_keys = ["user", "database"]
                for key in required_keys:
                    if key not in args:
                        raise ConfigError(f"PostgreSQL {key} is required")
                        
    def is_sqlite(self) -> bool:
        """Check if the main database is SQLite.
        
        Returns:
            True if using SQLite, False otherwise.
        """
        return self.database_config.name == "sqlite3"
        
    def is_postgres(self) -> bool:
        """Check if the main database is PostgreSQL.
        
        Returns:
            True if using PostgreSQL, False otherwise.
        """
        return self.database_config.name in ["psycopg2", "psycopg2cffi"]