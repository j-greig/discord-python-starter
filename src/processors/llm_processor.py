"""
LLM Processor - Handles API calls to language model providers.

Supports:
- Anthropic (with prompt caching)
- OpenAI/OpenRouter
- Unified interface for multiple providers
- Base context and chat history integration
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from .base_processor import BaseProcessor, MessageContext, ProcessorError, get_honcho_user


class LLMProcessor(BaseProcessor):
    """
    Processor that handles LLM API calls for response generation.
    
    Supports multiple providers with consistent interface.
    Handles prompt caching, base context, and chat history.
    """
    
    def __init__(self, honcho_client, app):
        super().__init__("llm")
        
        self.honcho_client = honcho_client
        self.app = app
        
        # Configuration
        self.api_provider = os.getenv("API_PROVIDER", "anthropic").lower()
        self.model_name = self._get_model_name()
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        self.enable_prompt_caching = os.getenv("ENABLE_PROMPT_CACHING", "true").lower() == "true"
        
        # System prompt configuration
        self.system_prompt = self._load_system_prompt()
        self.base_context_file = os.getenv("BASE_CONTEXT_FILE", "base_context.json")
        
        # Initialize API client
        self.client = self._initialize_client()
        
        self.logger.info(f"LLM processor initialized with {self.api_provider} provider")
        self.logger.info(f"Model: {self.model_name}, Max tokens: {self.max_tokens}")
        self.logger.info(f"Prompt caching: {'enabled' if self.enable_prompt_caching else 'disabled'}")
    
    def _get_model_name(self) -> str:
        """Get model name with provider-specific defaults"""
        model_name = os.getenv("MODEL_NAME")
        if not model_name:
            model_name = (
                "claude-3-5-sonnet-20241022" if self.api_provider == "anthropic" else "gpt-4"
            )
        
        # Ensure we're using correct Anthropic model names (not OpenRouter format)
        if self.api_provider == "anthropic" and "anthropic/" in model_name:
            model_name = model_name.replace("anthropic/", "")
            
        return model_name
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file or environment variable"""
        system_prompt_file = os.getenv("SYSTEM_PROMPT_FILE")
        if system_prompt_file and os.path.exists(system_prompt_file):
            try:
                with open(system_prompt_file, "r", encoding="utf-8") as f:
                    prompt = f.read().strip()
                    self.logger.info(f"Loaded system prompt from {system_prompt_file}")
                    return prompt
            except Exception as e:
                self.logger.error(f"Error loading system prompt from file: {e}")
                self.logger.info("Falling back to environment variable")
        
        return os.getenv("SYSTEM_PROMPT", "You are a helpful AI assistant.")
    
    def _initialize_client(self):
        """Initialize the appropriate API client based on provider"""
        if self.api_provider == "anthropic":
            try:
                import anthropic
                
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ProcessorError("llm", "ANTHROPIC_API_KEY not set")
                
                # Configure with cache TTL header if caching enabled
                if self.enable_prompt_caching:
                    client = anthropic.Anthropic(
                        api_key=api_key,
                        default_headers={"anthropic-beta": "extended-cache-ttl-2025-04-11"},
                    )
                    self.logger.info("Using Anthropic API with 1-hour cache TTL enabled")
                else:
                    client = anthropic.Anthropic(api_key=api_key)
                    self.logger.info("Using Anthropic API")
                
                return client
                
            except ImportError:
                raise ProcessorError("llm", "Anthropic library not installed. Run: pip install anthropic")
                
        elif self.api_provider == "openai":
            try:
                from openai import OpenAI
                
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ProcessorError("llm", "OPENAI_API_KEY not set")
                
                base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                client = OpenAI(api_key=api_key, base_url=base_url)
                self.logger.info(f"Using OpenAI API with base URL: {base_url}")
                
                return client
                
            except ImportError:
                raise ProcessorError("llm", "OpenAI library not installed. Run: pip install openai")
        else:
            raise ProcessorError("llm", f"Unsupported API_PROVIDER: {self.api_provider}. Use 'anthropic' or 'openai'")
    
    def _load_base_context(self) -> List[Dict[str, Any]]:
        """Load base context from JSON file"""
        try:
            if os.path.exists(self.base_context_file):
                with open(self.base_context_file, "r", encoding="utf-8") as f:
                    base_context = json.load(f)
                    self.logger.debug(f"Loaded base context with {len(base_context)} messages")
                    return base_context
            else:
                self.logger.debug(f"Base context file {self.base_context_file} not found")
                return []
        except Exception as e:
            self.logger.error(f"Error loading base context: {e}")
            return []
    
    async def process(self, context: MessageContext) -> str:
        """
        Generate LLM response for the given message context.
        
        Returns:
            Generated response string
        """
        try:
            # Get chat history from Honcho
            chat_history = self._get_chat_history(context)
            
            # Generate response using appropriate provider
            if self.api_provider == "anthropic":
                return await self._call_anthropic(context.clean_content, chat_history)
            elif self.api_provider == "openai":
                return await self._call_openai(context.clean_content, chat_history)
            
        except Exception as e:
            raise ProcessorError("llm", f"Error generating response: {e}", e)
    
    def _get_chat_history(self, context: MessageContext) -> List[Any]:
        """Get recent chat history from Honcho"""
        try:
            # Get user and session for this context
            user = get_honcho_user(self.honcho_client, self.app.id, context.author)
            
            # Import here to avoid circular imports
            from honcho_utils import get_session
            location_id = str(context.channel.id)
            session, _ = get_session(
                self.honcho_client, self.app.id, user.id, {location_id: True}, create=True
            )
            
            if session:
                history_iter = self.honcho_client.apps.users.sessions.messages.list(
                    app_id=self.app.id, session_id=session.id, user_id=user.id, size=10
                )
                return list(msg for msg in history_iter)
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting chat history: {e}")
            return []
    
    async def _call_anthropic(self, prompt: str, chat_history: List[Any]) -> str:
        """Call Anthropic API with prompt caching support"""
        # Create token-aware system prompt
        token_aware_prompt = f"{self.system_prompt}\n\nIMPORTANT: You have a strict limit of {self.max_tokens} tokens for your response. Keep your answers concise and complete within this limit. If you need to provide a long response, prioritize the most important information and indicate if there's more to discuss."
        
        messages = []
        
        # Add base context
        base_context = self._load_base_context()
        
        if self.enable_prompt_caching and base_context:
            # CACHING ENABLED: Add base context with prompt caching
            # Add all base context messages except the last one normally
            messages.extend(base_context[:-1])
            
            # Add the last base context message with cache control
            last_base_message = base_context[-1].copy()
            if "content" in last_base_message:
                # Handle both string and list content formats
                if isinstance(last_base_message["content"], str):
                    last_base_message["content"] = [
                        {
                            "type": "text",
                            "text": last_base_message["content"],
                            "cache_control": {"type": "ephemeral", "ttl": "1h"},
                        }
                    ]
                elif isinstance(last_base_message["content"], list):
                    # If already a list, add cache control to the last content block
                    last_base_message["content"] = last_base_message["content"].copy()
                    if last_base_message["content"]:
                        last_content = last_base_message["content"][-1].copy()
                        last_content["cache_control"] = {
                            "type": "ephemeral",
                            "ttl": "1h",
                        }
                        last_base_message["content"][-1] = last_content
            
            messages.append(last_base_message)
        elif base_context:
            # CACHING DISABLED: Add base context normally
            messages.extend(base_context)
        
        # Add chat history from Honcho (not cached as it changes frequently)
        if chat_history:
            messages.extend(
                [
                    {
                        "role": "user" if msg.is_user else "assistant",
                        "content": msg.content,
                    }
                    for msg in chat_history
                ]
            )
        
        # Add current user message (not cached as it's always new)
        messages.append({"role": "user", "content": prompt})
        
        # Prepare system prompt
        if self.enable_prompt_caching:
            # CACHING ENABLED: Use cached system prompt with 1-hour TTL
            system_prompt_param = [
                {
                    "type": "text",
                    "text": token_aware_prompt,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                }
            ]
        else:
            # CACHING DISABLED: Use regular system prompt
            system_prompt_param = token_aware_prompt
        
        # Call Anthropic API
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=system_prompt_param,
            messages=messages,
        )
        
        # Log cache performance for monitoring (only when caching is enabled)
        if self.enable_prompt_caching and hasattr(response, "usage"):
            usage = response.usage
            if hasattr(usage, "cache_creation_input_tokens") and hasattr(
                usage, "cache_read_input_tokens"
            ):
                self.logger.info(
                    f"Cache performance - Created: {usage.cache_creation_input_tokens}, Read: {usage.cache_read_input_tokens}"
                )
        
        return response.content[0].text
    
    async def _call_openai(self, prompt: str, chat_history: List[Any]) -> str:
        """Call OpenAI API"""
        # Create token-aware system prompt
        token_aware_prompt = f"{self.system_prompt}\n\nIMPORTANT: You have a strict limit of {self.max_tokens} tokens for your response. Keep your answers concise and complete within this limit. If you need to provide a long response, prioritize the most important information and indicate if there's more to discuss."
        
        messages = []
        
        # Add base context
        base_context = self._load_base_context()
        messages.extend(base_context)
        
        # Add chat history from Honcho
        if chat_history:
            messages.extend(
                [
                    {
                        "role": "user" if msg.is_user else "assistant",
                        "content": msg.content,
                    }
                    for msg in chat_history
                ]
            )
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        # For OpenAI, system prompt goes in messages array
        openai_messages = [{"role": "system", "content": token_aware_prompt}]
        openai_messages.extend(messages)
        
        response = self.client.chat.completions.create(
            model=self.model_name, 
            messages=openai_messages, 
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content