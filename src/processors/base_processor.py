"""
Base processor class for Discord bot message processing pipeline.

Provides common interface and utilities for all processors.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MessageContext:
    """
    Standardized context object passed between processors.
    Contains all Discord message/channel/user data needed for processing.
    """
    
    def __init__(self, message, bot):
        self.message = message
        self.bot = bot
        
        # Basic message info
        self.content = message.content
        self.author = message.author
        self.channel = message.channel
        self.guild = message.guild
        
        # Processed content (without bot mentions)
        self.clean_content = self._clean_content()
        
        # Bot-specific data
        self.is_mentioned = bot.user.mentioned_in(message)
        self.mentioned_users = message.mentions
        
        # Extensible data store for processors to add information
        self.data = {}
    
    def _clean_content(self) -> str:
        """Remove bot mentions from message content"""
        content = self.message.content.replace(f"<@{self.bot.user.id}>", "").strip()
        return content if content else ""
    
    def set_data(self, key: str, value: Any) -> None:
        """Store processor-specific data"""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve processor-specific data"""
        return self.data.get(key, default)


class BaseProcessor(ABC):
    """
    Abstract base class for all message processors.
    
    Processors should:
    1. Be stateless where possible (state in context or external storage)
    2. Have clear input/output contracts
    3. Handle their own configuration
    4. Include proper error handling and logging
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"processor.{name}")
        self.config = self._load_config()
        self.enabled = self._is_enabled()
        
        if self.enabled:
            self.logger.info(f"{name} processor initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load processor-specific configuration.
        Override in subclasses to load from files, environment, etc.
        """
        return {}
    
    def _is_enabled(self) -> bool:
        """
        Check if this processor is enabled.
        Default: check environment variable {PROCESSOR_NAME}_ENABLED
        """
        env_var = f"{self.name.upper()}_ENABLED"
        return os.getenv(env_var, "true").lower() == "true"
    
    @abstractmethod
    async def process(self, context: MessageContext) -> Any:
        """
        Process the message context and return a result.
        
        Args:
            context: MessageContext with message data and processor state
            
        Returns:
            Processor-specific result (bool, int, str, etc.)
            
        Raises:
            ProcessorError: When processing fails
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if processor is enabled"""
        return self.enabled


class ProcessorError(Exception):
    """Base exception for processor errors"""
    
    def __init__(self, processor_name: str, message: str, original_error: Optional[Exception] = None):
        self.processor_name = processor_name
        self.original_error = original_error
        super().__init__(f"[{processor_name}] {message}")


class ProcessorPipeline:
    """
    Orchestrates multiple processors in sequence.
    Provides error handling and logging for the entire pipeline.
    """
    
    def __init__(self):
        self.processors = []
        self.logger = logging.getLogger("processor.pipeline")
    
    def add_processor(self, processor: BaseProcessor) -> None:
        """Add a processor to the pipeline"""
        if processor.is_enabled():
            self.processors.append(processor)
            self.logger.info(f"Added {processor.name} processor to pipeline")
        else:
            self.logger.info(f"Skipped disabled processor: {processor.name}")
    
    async def process(self, context: MessageContext) -> Dict[str, Any]:
        """
        Run all processors in sequence, collecting results.
        
        Returns:
            Dictionary mapping processor names to their results
        """
        results = {}
        
        for processor in self.processors:
            try:
                result = await processor.process(context)
                results[processor.name] = result
                self.logger.debug(f"{processor.name}: {result}")
                
            except ProcessorError as e:
                self.logger.error(f"Processor error: {e}")
                results[processor.name] = {"error": str(e)}
                
            except Exception as e:
                self.logger.error(f"Unexpected error in {processor.name}: {e}")
                results[processor.name] = {"error": f"Unexpected error: {e}"}
        
        return results


# Utility functions to reduce code duplication across processors
def get_discord_user_id(author) -> str:
    """
    Create standardized Discord user ID for Honcho.
    
    Args:
        author: Discord message author or interaction author
        
    Returns:
        Formatted user ID string: "discord_{user_id}"
    """
    return f"discord_{str(author.id)}"


def get_honcho_user(honcho_client, app_id: str, author):
    """
    Get or create Honcho user for Discord author.
    
    Args:
        honcho_client: Honcho client instance
        app_id: Honcho app ID
        author: Discord message author or interaction author
        
    Returns:
        Honcho user object
    """
    user_id = get_discord_user_id(author)
    return honcho_client.apps.users.get_or_create(name=user_id, app_id=app_id)


def get_honcho_session(honcho_client, app_id: str, user_id: str, channel_id: str):
    """
    Get or create Honcho session for user in channel.
    
    Args:
        honcho_client: Honcho client instance
        app_id: Honcho app ID
        user_id: Honcho user ID
        channel_id: Discord channel ID
        
    Returns:
        Tuple of (session, is_new)
    """
    from honcho_utils import get_session
    location_id = str(channel_id)
    return get_session(
        honcho_client, app_id, user_id, {location_id: True}, create=True
    )