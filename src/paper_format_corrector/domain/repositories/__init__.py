"""Domain repositories package.

Abstract repository interfaces for document and template persistence.
Implementations live in infrastructure/.
"""

from .document import DocumentRepository
from .template import TemplateRepository

__all__ = ["DocumentRepository", "TemplateRepository"]
