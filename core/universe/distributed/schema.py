"""
Database schema for Distributed Runtime

Creates and manages database tables for agent nodes, task assignments, and health monitoring.
"""

import sqlite3
from typing import Optional
import logging

logger = logging.getLogger(__name__)


SCHEMA_VERSION = "1.0.0"


# SQL statements for table creation
CREATE_AGENT_NODES = """
CREATE TABLE IF NOT EXISTS agent_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node_id TEXT UNIQUE NOT NULL,
  node_name TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  port INTEGER NOT NULL,
  capacity INTEGER DEFAULT 10,
  status TEXT DEFAULT 'online',
  last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_NODE_HEALTH = """
CREATE TABLE IF NOT EXISTS node_health (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node_id TEXT NOT NULL,
  cpu_usage REAL DEFAULT 0.0,
  memory_usage REAL DEFAULT 0.0,
  disk_usage REAL DEFAULT 0.0,
  task_count INTEGER DEFAULT 0,
  error_count INTEGER DEFAULT 0,
  response_time_ms REAL DEFAULT 0.0,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (node_id) REFERENCES agent_nodes(node_id),
  UNIQUE(node_id, timestamp)
);
"""

CREATE_DISTRIBUTED_TASKS = """
CREATE TABLE IF NOT EXISTS distributed_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT UNIQUE NOT NULL,
  task_type TEXT NOT NULL,
  agent_id TEXT,
  node_id TEXT,
  status TEXT DEFAULT 'pending',
  priority INTEGER DEFAULT 2,
  sla_max_duration_ms INTEGER DEFAULT 5000,
  sla_max_retries INTEGER DEFAULT 3,
  sla_timeout_ms INTEGER DEFAULT 10000,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  result TEXT,
  error TEXT,
  retry_count INTEGER DEFAULT 0,
  affinity_tags TEXT,
  dependencies TEXT,
  FOREIGN KEY (node_id) REFERENCES agent_nodes(node_id)
);
"""

CREATE_TASK_ROUTING = """
CREATE TABLE IF NOT EXISTS task_routing (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  source_node_id TEXT NOT NULL,
  target_node_id TEXT NOT NULL,
  hop_count INTEGER DEFAULT 0,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (task_id) REFERENCES distributed_tasks(task_id),
  FOREIGN KEY (source_node_id) REFERENCES agent_nodes(node_id),
  FOREIGN KEY (target_node_id) REFERENCES agent_nodes(node_id)
);
"""

CREATE_SERVICE_INSTANCES = """
CREATE TABLE IF NOT EXISTS service_instances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_id TEXT UNIQUE NOT NULL,
  service_name TEXT NOT NULL,
  address TEXT NOT NULL,
  port INTEGER NOT NULL,
  weight INTEGER DEFAULT 10,
  status TEXT DEFAULT 'passing',
  tags TEXT,
  metadata TEXT,
  registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_health_check TIMESTAMP,
  is_deregistered BOOLEAN DEFAULT 0,
  deregistration_time TIMESTAMP
);
"""

CREATE_HEALTH_CHECKS = """
CREATE TABLE IF NOT EXISTS health_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_id TEXT UNIQUE NOT NULL,
  service_id TEXT NOT NULL,
  check_type TEXT NOT NULL,
  status TEXT DEFAULT 'unknown',
  interval_ms INTEGER DEFAULT 10000,
  timeout_ms INTEGER DEFAULT 5000,
  output TEXT,
  consecutive_failures INTEGER DEFAULT 0,
  failure_threshold INTEGER DEFAULT 3,
  last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (service_id) REFERENCES service_instances(service_id)
);
"""

CREATE_CACHE_ENTRIES = """
CREATE TABLE IF NOT EXISTS cache_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cache_key TEXT UNIQUE NOT NULL,
  cache_value TEXT NOT NULL,
  ttl_seconds INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  access_count INTEGER DEFAULT 0,
  tags TEXT,
  UNIQUE(cache_key)
);
"""

CREATE_LOAD_BALANCER_STATE = """
CREATE TABLE IF NOT EXISTS load_balancer_state (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  backend_id TEXT NOT NULL,
  total_requests INTEGER DEFAULT 0,
  successful_requests INTEGER DEFAULT 0,
  failed_requests INTEGER DEFAULT 0,
  avg_response_time_ms REAL DEFAULT 0.0,
  circuit_state TEXT DEFAULT 'closed',
  cpu_usage REAL DEFAULT 0.0,
  memory_usage REAL DEFAULT 0.0,
  queue_depth INTEGER DEFAULT 0,
  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agent_nodes_status ON agent_nodes(status);
CREATE INDEX IF NOT EXISTS idx_agent_nodes_last_heartbeat ON agent_nodes(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_distributed_tasks_status ON distributed_tasks(status);
CREATE INDEX IF NOT EXISTS idx_distributed_tasks_node_id ON distributed_tasks(node_id);
CREATE INDEX IF NOT EXISTS idx_distributed_tasks_created_at ON distributed_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_service_instances_name ON service_instances(service_name);
CREATE INDEX IF NOT EXISTS idx_service_instances_status ON service_instances(status);
CREATE INDEX IF NOT EXISTS idx_cache_entries_ttl ON cache_entries(ttl_seconds);
CREATE INDEX IF NOT EXISTS idx_cache_entries_tags ON cache_entries(tags);
CREATE INDEX IF NOT EXISTS idx_node_health_node_id ON node_health(node_id);
CREATE INDEX IF NOT EXISTS idx_node_health_timestamp ON node_health(timestamp);
"""


class DatabaseSchema:
    """Manage database schema for distributed runtime."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Connect to database."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        return self.connection

    def disconnect(self) -> None:
        """Disconnect from database."""
        if self.connection:
            self.connection.close()

    def create_all_tables(self) -> bool:
        """Create all required tables."""
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()

            tables = [
                CREATE_AGENT_NODES,
                CREATE_NODE_HEALTH,
                CREATE_DISTRIBUTED_TASKS,
                CREATE_TASK_ROUTING,
                CREATE_SERVICE_INSTANCES,
                CREATE_HEALTH_CHECKS,
                CREATE_CACHE_ENTRIES,
                CREATE_LOAD_BALANCER_STATE,
                CREATE_INDEXES,
            ]

            for table_sql in tables:
                cursor.executescript(table_sql)

            self.connection.commit()
            logger.info("All database tables created successfully")
            return True

        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def drop_all_tables(self) -> bool:
        """Drop all tables (for testing)."""
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")

            self.connection.commit()
            logger.info("All tables dropped")
            return True

        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            return False

    def init_database(self) -> bool:
        """Initialize database with schema."""
        self.connect()
        self.create_all_tables()
        return True


# Helper functions for common operations

def insert_agent_node(
    connection: sqlite3.Connection,
    node_id: str,
    node_name: str,
    ip_address: str,
    port: int,
    capacity: int = 10
) -> bool:
    """Insert an agent node."""
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO agent_nodes (node_id, node_name, ip_address, port, capacity)
            VALUES (?, ?, ?, ?, ?)
            """,
            (node_id, node_name, ip_address, port, capacity)
        )
        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Error inserting node: {e}")
        return False


def update_node_health(
    connection: sqlite3.Connection,
    node_id: str,
    cpu_usage: float,
    memory_usage: float,
    disk_usage: float,
    task_count: int,
    error_count: int
) -> bool:
    """Update node health metrics."""
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO node_health (node_id, cpu_usage, memory_usage, disk_usage, task_count, error_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (node_id, cpu_usage, memory_usage, disk_usage, task_count, error_count)
        )
        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating health: {e}")
        return False


def insert_distributed_task(
    connection: sqlite3.Connection,
    task_id: str,
    task_type: str,
    node_id: str,
    status: str = "pending",
    priority: int = 2
) -> bool:
    """Insert a distributed task."""
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO distributed_tasks (task_id, task_type, node_id, status, priority)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, task_type, node_id, status, priority)
        )
        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Error inserting task: {e}")
        return False


def get_agent_stats(connection: sqlite3.Connection, node_id: str) -> dict:
    """Get statistics for an agent node."""
    try:
        cursor = connection.cursor()

        # Get node info
        cursor.execute(
            "SELECT * FROM agent_nodes WHERE node_id = ?",
            (node_id,)
        )
        node_row = cursor.fetchone()

        if not node_row:
            return {}

        # Get latest health
        cursor.execute(
            """
            SELECT cpu_usage, memory_usage, disk_usage, task_count, error_count
            FROM node_health WHERE node_id = ? ORDER BY timestamp DESC LIMIT 1
            """,
            (node_id,)
        )
        health_row = cursor.fetchone()

        # Get task stats
        cursor.execute(
            """
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM distributed_tasks WHERE node_id = ?
            """,
            (node_id,)
        )
        task_row = cursor.fetchone()

        return {
            'node_id': node_id,
            'node_name': node_row['node_name'],
            'ip_address': node_row['ip_address'],
            'port': node_row['port'],
            'capacity': node_row['capacity'],
            'status': node_row['status'],
            'last_heartbeat': node_row['last_heartbeat'],
            'cpu_usage': health_row['cpu_usage'] if health_row else 0,
            'memory_usage': health_row['memory_usage'] if health_row else 0,
            'disk_usage': health_row['disk_usage'] if health_row else 0,
            'total_tasks': task_row['total'] if task_row else 0,
            'completed_tasks': task_row['completed'] if task_row else 0,
            'failed_tasks': task_row['failed'] if task_row else 0,
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {}


if __name__ == "__main__":
    # Initialize database
    schema = DatabaseSchema("distributed_runtime.db")
    schema.init_database()
    print("Database initialized successfully")
