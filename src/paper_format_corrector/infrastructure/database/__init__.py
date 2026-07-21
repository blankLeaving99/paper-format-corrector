"""MySQL 数据库模块

提供连接管理、建表 DDL、Repository 实现。
数据库名称: paper_format_corrector
"""

from .connection import DatabaseManager, get_connection
from .schema import initialize_database, get_all_ddl
from .template_repo import MySQLTemplateRepository
from .report_repo import MySQLReportRepository

__all__ = [
    "DatabaseManager",
    "get_connection",
    "initialize_database",
    "get_all_ddl",
    "MySQLTemplateRepository",
    "MySQLReportRepository",
]
