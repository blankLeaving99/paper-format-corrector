"""MySQL 连接管理器

提供线程安全的连接池管理和配置加载。
支持从 config.yaml 或环境变量读取数据库配置。
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import yaml

logger = logging.getLogger(__name__)

# 默认数据库名称
DEFAULT_DB_NAME = "paper_format_corrector"

# 默认连接配置
_DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": DEFAULT_DB_NAME,
    "charset": "utf8mb4",
    "connect_timeout": 10,
    "read_timeout": 30,
    "write_timeout": 30,
}


class DatabaseManager:
    """MySQL 数据库连接管理器

    线程安全，支持上下文管理器自动提交/回滚。

    Usage:
        db = DatabaseManager(config)
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = {**_DEFAULT_CONFIG, **(config or {})}
        self._lock = threading.Lock()
        self._connection = None

    @classmethod
    def from_config_file(cls, config_path: str | Path | None = None) -> DatabaseManager:
        """从 config.yaml 加载数据库配置"""
        config = {}
        if config_path is None:
            config_path = Path("config/config.yaml")
        else:
            config_path = Path(config_path)

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                config = data.get("database", {})
            except Exception as e:
                logger.warning(f"读取数据库配置失败: {e}")

        # 环境变量覆盖（优先级最高）
        env_overrides = {
            "host": "DB_HOST",
            "port": "DB_PORT",
            "user": "DB_USER",
            "password": "DB_PASSWORD",
            "database": "DB_NAME",
        }
        for key, env_var in env_overrides.items():
            val = os.environ.get(env_var)
            if val:
                config[key] = int(val) if key == "port" else val

        return cls(config)

    @property
    def database_name(self) -> str:
        return self._config.get("database", DEFAULT_DB_NAME)

    def get_connection_params(self) -> dict[str, Any]:
        """获取连接参数（不含 database，用于创建数据库时使用）"""
        params = {k: v for k, v in self._config.items() if k not in ("database", "pool_size", "pool_recycle")}
        return params

    def get_full_params(self) -> dict[str, Any]:
        """获取完整连接参数（过滤掉非 pymysql 参数）"""
        params = dict(self._config)
        # 移除 pymysql 不接受的参数
        for key in ("pool_size", "pool_recycle", "read_timeout", "write_timeout"):
            params.pop(key, None)
        # 将 read_timeout/write_timeout 映射为 pymysql 参数
        if "read_timeout" in self._config:
            params["read_timeout"] = self._config["read_timeout"]
        if "write_timeout" in self._config:
            params["write_timeout"] = self._config["write_timeout"]
        return params

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """获取数据库连接的上下文管理器

        自动处理连接的打开、提交和关闭。
        异常时自动回滚。
        """
        import pymysql

        conn = None
        try:
            conn = pymysql.connect(**self.get_full_params())
            conn.autocommit(False)
            yield conn
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def cursor(self, dict_cursor: bool = True) -> Generator[Any, None, None]:
        """获取游标的上下文管理器

        Args:
            dict_cursor: True 返回 DictCursor，False 返回普通元组游标
        """
        import pymysql

        with self.connection() as conn:
            if dict_cursor:
                cur = conn.cursor(pymysql.cursors.DictCursor)
            else:
                cur = conn.cursor()
            try:
                yield cur
            finally:
                cur.close()

    def create_database_if_not_exists(self) -> None:
        """如果数据库不存在则创建"""
        import pymysql

        params = self.get_connection_params()
        db_name = self._config["database"]
        conn = pymysql.connect(**params)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
            logger.info(f"数据库 '{db_name}' 就绪")
        finally:
            conn.close()

    def test_connection(self) -> dict[str, Any]:
        """测试数据库连接是否可用"""
        import pymysql

        try:
            with self.cursor() as cur:
                cur.execute("SELECT VERSION() as version, DATABASE() as current_db")
                row = cur.fetchone()
                return {
                    "connected": True,
                    "mysql_version": row["version"] if row else "",
                    "database": row["current_db"] if row else "",
                }
        except pymysql.Error as e:
            return {
                "connected": False,
                "error": str(e),
                "database": self._config.get("database", ""),
            }


def get_connection(config: dict[str, Any] | None = None) -> DatabaseManager:
    """快捷函数：创建 DatabaseManager 实例"""
    if config:
        return DatabaseManager(config)
    return DatabaseManager.from_config_file()
