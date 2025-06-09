"""
Rate limiting processor for Discord bot messages.

Provides global rate limiting to prevent bot overload.
Tracks bot message timestamps and enforces silent cooldowns.
"""

import logging
import time
from typing import List

logger = logging.getLogger(__name__)

# Bot rate limit constants
MAX_MESSAGES_PER_MINUTE = 3
RATE_LIMIT_WINDOW = 60  # seconds
SHOW_RATE_LIMIT_LOGS = False  # Set to True for debugging
    
class RateLimiter:
    """
    Manages global rate limiting for this Discord bot's message rate.
    Tracks bot message timestamps and enforces silent cooldowns.
    """
    def __init__(self):
        # Store bot message timestamps
        self._bot_messages: List[float] = []
        
    def _cleanup_old_messages(self) -> None:
        """Remove messages outside the time window"""
        current_time = time.time()
        self._bot_messages = [
            timestamp for timestamp in self._bot_messages
            if current_time - timestamp <= RATE_LIMIT_WINDOW
        ]
        
        # Safety: Cap list size to prevent memory leaks
        if len(self._bot_messages) > MAX_MESSAGES_PER_MINUTE * 2:
            self._bot_messages = self._bot_messages[-MAX_MESSAGES_PER_MINUTE:]
    
    def check_rate_limit(self) -> bool:
        """
        Check if bot has exceeded rate limit.
        
        Returns:
            bool: True if bot should be rate limited (silent cooldown)
        """
        current_time = time.time()
        
        # Clean up old messages first
        self._cleanup_old_messages()
        
        # Check if at rate limit
        if len(self._bot_messages) >= MAX_MESSAGES_PER_MINUTE:
            return True
            
        # Add new message timestamp
        self._bot_messages.append(current_time)
        return False

def create_rate_limiter() -> RateLimiter:
    """
    Create a new RateLimiter instance.
    
    Returns:
        RateLimiter: Bot rate limiter instance
    """
    if SHOW_RATE_LIMIT_LOGS:
        logger.info(f"Rate limit: {MAX_MESSAGES_PER_MINUTE} messages per {RATE_LIMIT_WINDOW} seconds")
    return RateLimiter()