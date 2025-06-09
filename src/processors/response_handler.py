"""
Response Handler Processor - Handles sending Discord messages with chunking.

Features:
- Message chunking for long responses
- Typing indicators
- Error handling for Discord API issues
- Response delay based on enthusiasm scores
"""

import asyncio
from .base_processor import BaseProcessor, MessageContext, ProcessorError, get_honcho_user


class ResponseHandlerProcessor(BaseProcessor):
    """
    Processor that handles sending responses to Discord channels.
    
    Manages message chunking, typing indicators, and response delays.
    """
    
    def __init__(self, honcho_client, app):
        super().__init__("response_handler")
        self.honcho_client = honcho_client
        self.app = app
        
        # Configuration
        self.chunk_size = 1900  # Discord message limit with safety margin
        self.use_typing_indicator = True
        self.response_delay_enabled = True
    
    async def process(self, context: MessageContext, response_content: str) -> bool:
        """
        Send response to Discord channel with appropriate formatting and delays.
        
        Args:
            context: Message context
            response_content: Generated response text
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Apply response delay based on enthusiasm score
            if self.response_delay_enabled:
                enthusiasm_score = context.get_data("enthusiasm_score", 9)
                delay = self._calculate_response_delay(enthusiasm_score)
                if delay > 0:
                    self.logger.debug(f"Applying response delay: {delay}s (enthusiasm: {enthusiasm_score})")
                    await asyncio.sleep(delay)
            
            # Send the response with chunking if needed
            await self._send_chunked_message(context, response_content)
            
            # Save to Honcho
            await self._save_to_honcho(context, response_content)
            
            return True
            
        except Exception as e:
            raise ProcessorError("response_handler", f"Error sending response: {e}", e)
    
    def _calculate_response_delay(self, enthusiasm_score: int) -> float:
        """
        Calculate response delay based on enthusiasm score.
        Lower enthusiasm = longer delay (more hesitation)
        """
        if enthusiasm_score >= 8:
            return 0.0  # Immediate response for high enthusiasm
        elif enthusiasm_score >= 6:
            return 0.5  # Short delay for medium-high enthusiasm
        elif enthusiasm_score >= 4:
            return 1.0  # Medium delay for medium enthusiasm
        else:
            return 2.0  # Longer delay for low enthusiasm
    
    async def _send_chunked_message(self, context: MessageContext, response_content: str) -> None:
        """Send message with chunking if needed"""
        if not response_content.strip():
            self.logger.warning("Attempted to send empty response")
            return
        
        if len(response_content) <= self.chunk_size:
            # Single message
            await context.channel.send(response_content)
        else:
            # Need to chunk the message
            chunks = self._chunk_message(response_content)
            
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # Small delay between chunks
                    await asyncio.sleep(0.5)
                await context.channel.send(chunk)
    
    def _chunk_message(self, content: str) -> list[str]:
        """
        Split message into chunks at natural breakpoints.
        Tries to split at newlines to preserve formatting.
        """
        if len(content) <= self.chunk_size:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Split by lines first to preserve formatting
        lines = content.splitlines(keepends=True)
        
        for line in lines:
            # If this line alone is too long, we need to split it
            if len(line) > self.chunk_size:
                # Finish current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                    current_chunk = ""
                
                # Split the long line by words
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    if len(current_line + word) > self.chunk_size:
                        if current_line:
                            chunks.append(current_line.rstrip())
                            current_line = word + " "
                        else:
                            # Single word too long, just add it
                            chunks.append(word)
                            current_line = ""
                    else:
                        current_line += word + " "
                
                if current_line:
                    current_chunk = current_line
            
            # Check if adding this line would exceed chunk size
            elif len(current_chunk + line) > self.chunk_size:
                # Save current chunk and start new one
                chunks.append(current_chunk.rstrip())
                current_chunk = line
            else:
                # Add line to current chunk
                current_chunk += line
        
        # Add final chunk if it exists
        if current_chunk:
            chunks.append(current_chunk.rstrip())
        
        return chunks
    
    async def _save_to_honcho(self, context: MessageContext, response_content: str) -> None:
        """Save user message and bot response to Honcho"""
        try:
            # Get user and session
            user = get_honcho_user(self.honcho_client, self.app.id, context.author)
            
            # Import here to avoid circular imports
            from honcho_utils import get_session
            location_id = str(context.channel.id)
            session, _ = get_session(
                self.honcho_client, self.app.id, user.id, {location_id: True}, create=True
            )
            
            if session:
                # Save both user message and bot response
                self.honcho_client.apps.users.sessions.messages.batch(
                    app_id=self.app.id,
                    user_id=user.id,
                    session_id=session.id,
                    messages=[
                        {"content": context.clean_content, "is_user": True},
                        {"content": response_content, "is_user": False},
                    ],
                )
                
                self.logger.debug(f"Saved conversation to Honcho session {session.id}")
            
        except Exception as e:
            # Don't raise error here - message was sent successfully
            self.logger.error(f"Error saving to Honcho: {e}")
    
    async def send_rate_limit_message(self, context: MessageContext) -> None:
        """Send rate limit message to user"""
        try:
            rate_limit_message = context.get_data("rate_limit_message", "Please wait before sending another message.")
            await context.channel.send(rate_limit_message)
        except Exception as e:
            self.logger.error(f"Error sending rate limit message: {e}")