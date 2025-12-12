"""
ML-Enhanced Chat Handler
Backwards compatibility wrapper - use EnhancedChatHandler directly instead.

This module is deprecated. The main EnhancedChatHandler already includes ML integration
through the optimized LLM engine. Import EnhancedChatHandler from chat_handler.py instead.
"""

import logging
from .chat_handler import EnhancedChatHandler

logger = logging.getLogger(__name__)

# For backwards compatibility, expose the same interface
MLEnhancedChatHandler = EnhancedChatHandler

