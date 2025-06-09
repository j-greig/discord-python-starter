"""
Processor system for modular Discord bot features.

Each processor handles a specific aspect of message processing:
- Rate limiting
- Should-reply logic  
- Enthusiasm scoring
- LLM response generation
- Response handling

Processors are designed to be:
- Self-contained with clear interfaces
- Configurable via environment/config files
- Testable in isolation
- Swappable implementations
"""

from .base_processor import BaseProcessor, MessageContext, ProcessorPipeline
from .llm_processor import LLMProcessor
from .response_handler import ResponseHandlerProcessor
from .status_coordinator import StatusCoordinatorProcessor
from .unified_enthusiasm import UnifiedEnthusiasmProcessor

__all__ = [
    "BaseProcessor",
    "MessageContext", 
    "ProcessorPipeline",
    "LLMProcessor",
    "ResponseHandlerProcessor",
    "StatusCoordinatorProcessor",
    "UnifiedEnthusiasmProcessor"
]