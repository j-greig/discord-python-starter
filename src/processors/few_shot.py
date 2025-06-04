"""
Few-shot prompting processor for Discord bot.
Loads few-shot examples from examples.json and injects them into message context for better LLM responses.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)


def add_few_shot_examples(messages: list, examples_file: str = "examples.json") -> list:
    """
    Add few-shot examples from examples.json to the messages array if file exists.
    Returns new message array with system prompt + examples + existing messages.
    """
    try:
        # Look for examples file in project root (where bot is run from)
        if os.path.exists(examples_file):
            with open(examples_file, 'r', encoding='utf-8') as f:
                examples = json.load(f)
        else:
            # No examples file found
            logger.warning(f"{examples_file} not found at {os.path.abspath(examples_file)}")
            return messages
        
        if not examples or not isinstance(examples, list):
            logger.warning("examples.json is empty or invalid format")
            return messages
        
        # Start with system message
        enhanced_messages = [messages[0]] if messages and messages[0].get("role") == "system" else []
        
        # Add examples as message pairs
        for example in examples:
            if "user" in example and "assistant" in example:
                enhanced_messages.append({"role": "user", "content": example["user"]})
                enhanced_messages.append({"role": "assistant", "content": example["assistant"]})
        
        # Add remaining original messages (excluding system)
        enhanced_messages.extend(msg for msg in messages if msg.get("role") != "system")
        
        logger.info(f"Added {len(examples)} few-shot examples from examples.json")
        return enhanced_messages
        
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in examples.json: {e}")
        return messages
    except Exception as e:
        logger.warning(f"Error loading examples.json: {e}")
        return messages