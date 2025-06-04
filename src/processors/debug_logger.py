"""
Debug logging processor for Discord bot.
Logs message interactions and LLM context for debugging and analysis.
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def log_interaction(user_input: str, bot_response: str, channel_id: str, user_id: str, session_id: str, message_count: int = 0, llm_messages: list = None):
    """
    Log a complete bot interaction to JSON file for debugging.
    Optionally includes the full LLM message context.
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "channel_id": str(channel_id),
        "user_id": str(user_id),
        "session_id": session_id,
        "user_input": user_input,
        "bot_response": bot_response,
        "message_count": message_count
    }
    
    # Include full LLM context if provided
    if llm_messages:
        log_entry["llm_context"] = llm_messages
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/message_logs.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.debug(f"Logged interaction for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")


def log_llm_context(messages: list, session_id: str):
    """
    Log just the LLM message context for debugging few-shot examples, etc.
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "llm_context",
        "session_id": session_id,
        "message_context": messages,
        "context_length": len(messages)
    }
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/llm_debug.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, indent=2) + "\n")
        logger.debug(f"Logged LLM context for session {session_id}: {len(messages)} messages")
    except Exception as e:
        logger.warning(f"Failed to log LLM context: {e}")