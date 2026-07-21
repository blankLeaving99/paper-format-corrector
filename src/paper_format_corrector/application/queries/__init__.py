"""Application queries package.

Queries represent read operations that don't change system state.
Following CQRS pattern - queries read, commands modify.
"""

from .report_query import ReportQuery

__all__ = ["ReportQuery"]
