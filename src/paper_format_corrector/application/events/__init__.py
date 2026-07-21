"""Application events package.

Events represent domain occurrences that other parts of the system may react to.
"""

from .document_events import DocumentCorrected, DocumentFailed
from .template_events import TemplateApplied, TemplateLoaded

__all__ = [
    "DocumentCorrected",
    "DocumentFailed",
    "TemplateApplied",
    "TemplateLoaded",
]
