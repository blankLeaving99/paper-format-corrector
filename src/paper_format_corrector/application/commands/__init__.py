"""Application commands package.

Commands represent write operations that change system state.
Following CQRS pattern - commands modify, queries read.
"""

from .correct_document import CorrectDocumentCommand
from .batch_process import BatchProcessCommand

__all__ = ["CorrectDocumentCommand", "BatchProcessCommand"]
