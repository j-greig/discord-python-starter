"""
Unified Enthusiasm Processor - Single processor for context gathering + turn-taking decisions.

Consolidates the functionality of multiple processors into one unified flow:
- Gathers all bot context variables (like enthusiasm_flow.md)
- Makes single LLM call for reasoning + scoring
- Provides comprehensive logging and optional verbose Discord display

Based on PRD_UNIFIED_ENTHUSIASM_FLOW_V1.md
"""

import os
import json
import logging
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from .base_processor import BaseProcessor, MessageContext, ProcessorError
import discord


class UnifiedEnthusiasmProcessor(BaseProcessor):
    """
    Single processor that gathers all bot context and makes turn-taking decisions.
    
    Implements the enthusiasm_flow.md pattern of "gather all context → single reasoning call → decision"
    while maintaining all functionality from our current 6-processor pipeline.
    """
    
    def __init__(self, honcho_client=None, app=None):
        super().__init__("unified_enthusiasm")
        
        # Dependencies
        self.honcho_client = honcho_client
        self.app = app
        
        # Configuration
        self.threshold = int(os.getenv("ENTHUSIASM_THRESHOLD", "5"))
        self.model_name = os.getenv("ENTHUSIASM_MODEL", "claude-3-haiku-20240307")
        if "anthropic/" in self.model_name:
            self.model_name = self.model_name.replace("anthropic/", "")
        
        # Random delay configuration (1-3 seconds for breathing space)
        self.random_delay_enabled = os.getenv("RANDOM_DELAY_ENABLED", "true").lower() == "true"
        self.min_delay_seconds = float(os.getenv("MIN_DELAY_SECONDS", "1.0"))
        self.max_delay_seconds = float(os.getenv("MAX_DELAY_SECONDS", "3.0"))
        
        # Bot identity
        self.bot_name = os.getenv("BOT_NAME", "Assistant").strip('"')
        self.bot_skills = self._load_bot_skills()
        self.bot_personality = self._load_personality()
        
        # Logging configuration
        self.debug = os.getenv("ENTHUSIASM_DEBUG", "true").lower() == "true"
        self.verbose_discord = os.getenv("VERBOSE_REASONING", "false").lower() == "true"
        
        # Rate limiting moved to top level bot_processors.py
        
        # Context caching
        self.context_cache_enabled = os.getenv("ENTHUSIASM_CONTEXT_CACHE", "true").lower() == "true"
        self._context_cache = {}
        
        # Initialize Anthropic client
        self.client = self._initialize_anthropic_client()
        
        self.logger.info(f"Unified enthusiasm processor initialized")
        self.logger.info(f"Skills: {self.bot_skills}")
        self.logger.info(f"Verbose Discord mode: {self.verbose_discord}")
        self.logger.info(f"Random delay: {self.random_delay_enabled} ({self.min_delay_seconds}-{self.max_delay_seconds}s)")
        
    def _load_bot_skills(self) -> List[str]:
        """Load bot skills from environment"""
        skills_str = os.getenv("BOT_SKILLS", "").strip('"')
        if skills_str:
            return [skill.strip() for skill in skills_str.split(",") if skill.strip()]
        return []
    
    def _load_personality(self) -> str:
        """Load bot personality (same logic as EnthusiasmScorer)"""
        # Check for personality file first
        personality_file = os.getenv("PERSONALITY_FILE")
        if personality_file and os.path.exists(personality_file):
            try:
                with open(personality_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                self.logger.error(f"Error loading personality file: {e}")
        
        # Fallback to environment variable or default
        personality = os.getenv("BOT_PERSONALITY", "")
        if not personality:
            # Default test personalities based on bot name
            if "data" in self.bot_name.lower():
                personality = "Extremely shy data analyst who only speaks when directly asked about numbers, statistics, or data. Avoids interrupting conversations. Loves spreadsheets and precise analysis."
            elif "splash" in self.bot_name.lower():
                personality = "Enthusiastic artist who sees colors and patterns everywhere. Jumps into any creative discussion. Very confident and expressive. Always wants to contribute creatively."
            else:
                personality = "A fun, dry-humoured cat who is curious and friendly once she gets over her shyness"
        
        return personality
    
    def _initialize_anthropic_client(self):
        """Initialize Anthropic client for LLM calls"""
        try:
            import anthropic
            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ProcessorError("unified_enthusiasm", "ANTHROPIC_API_KEY not set")
            
            client = anthropic.Anthropic(api_key=api_key)
            self.logger.info("Initialized Anthropic client for unified enthusiasm")
            return client
            
        except ImportError:
            raise ProcessorError("unified_enthusiasm", "Anthropic library required")
    
    async def process(self, context: MessageContext) -> Dict[str, Any]:
        """
        Process message with unified context gathering + turn-taking decision.
        
        Returns:
            Dict with enthusiasm_score, reasoning, activities, and decision info
        """
        try:
            # Step 1: Basic validation (like ContextBuilder)
            if not await self._basic_validation(context):
                return {"should_skip": True, "reason": "basic_validation_failed"}
            
            # Step 2: Add random delay for breathing space in conversation flow
            await self._add_random_delay(context)
            
            # Step 3: Rate limiting is now handled at top level in bot_processors.py
            
            # Step 4: Gather complete bot context (all variables from enthusiasm_flow.md)
            bot_context = await self._gather_bot_context(context)
            
            # Step 5: Check other bot statuses before making decision
            other_bot_statuses = await self._check_other_bot_statuses(context, bot_context)
            
            # Step 6: Make single LLM call for reasoning + scoring
            reasoning_response = await self._call_unified_llm(bot_context, context, other_bot_statuses)
            
            # Step 7: Parse response
            parsed_result = self._parse_llm_response(reasoning_response)
            
            # Step 8: Make decision
            should_respond = parsed_result["score"] >= self.threshold
            
            # Step 9: Rate limiting and status are now handled at top level in bot_processors.py
            
            # Step 10: Log everything
            await self._log_decision(context, bot_context, reasoning_response, parsed_result, should_respond)
            
            # Step 11: Prepare verbose Discord display if enabled
            verbose_prefix = ""
            if self.verbose_discord:
                try:
                    # Include bot_context and message content for debug logging
                    parsed_result_with_context = parsed_result.copy()
                    parsed_result_with_context['bot_context'] = bot_context
                    parsed_result_with_context['message_content'] = context.content
                    verbose_prefix = self._format_verbose_prefix(parsed_result_with_context)
                except Exception as e:
                    self.logger.error(f"Error formatting verbose prefix: {e}")
                    verbose_prefix = f"🤖 **Response Decision** (enthusiasm: {parsed_result['score']}/9, threshold: {self.threshold}) → **{'RESPOND' if should_respond else 'SKIP'}**\n💭 *Error formatting debug info*\n\n--------\n"
            
            return {
                "should_skip": not should_respond,
                "enthusiasm_score": parsed_result["score"],
                "reasoning": parsed_result["reasoning"],
                "topic_change": parsed_result.get("topic_change", False),
                "activities": parsed_result["activities"],
                "bot_context": bot_context,
                "other_bot_statuses": other_bot_statuses,
                "verbose_prefix": verbose_prefix,
                "decision": "RESPOND" if should_respond else "SKIP"
            }
            
        except Exception as e:
            self.logger.error(f"Error in unified enthusiasm processing: {e}")
            # Fallback to safe response
            return {"should_skip": False, "enthusiasm_score": 8, "reasoning": f"Error: {e}", "topic_change": False}
    
    async def _basic_validation(self, context: MessageContext) -> bool:
        """Basic message validation (from ContextBuilder logic)"""
        # Skip self-messages
        if context.author == context.bot.user:
            self.logger.debug("⏭️ Skipping self-message")
            return False
        
        # Skip DMs
        if hasattr(context.channel, 'type') and str(context.channel.type) == 'private':
            self.logger.debug("⏭️ Skipping DM")
            return False
        
        # Let LLM evaluate all messages for enthusiasm scoring
        # (removed keyword fast path to allow organic participation per enthusiasm_flow.md)
        return True
    
    async def _add_random_delay(self, context: MessageContext) -> None:
        """Add random delay for breathing space in conversation flow"""
        if not self.random_delay_enabled:
            return
        
        delay_seconds = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        self.logger.info(f"🕐 Adding random delay: {delay_seconds:.1f}s for breathing space")
        
        try:
            await asyncio.sleep(delay_seconds)
        except asyncio.CancelledError:
            self.logger.debug("Random delay cancelled")
            raise
    
    def _has_response_triggers(self, context: MessageContext) -> bool:
        """Check if message has any triggers for responding"""
        # Direct mention
        if context.is_mentioned:
            return True
        
        # Name variants and topics (from bot.py logic)
        content_lower = context.content.lower()
        
        # Build name variants
        name_variants = [self.bot_name.lower()]
        bot_name_variants = os.getenv("BOT_NAME_VARIANTS", "").strip('"')
        if bot_name_variants:
            name_variants.extend([v.strip().lower() for v in bot_name_variants.split(",") if v.strip()])
        
        # Check name variants
        if any(variant in content_lower for variant in name_variants):
            return True
        
        # Build and check topics
        bot_topics = os.getenv("BOT_TOPICS", "").strip('"')
        if bot_topics:
            topics = [t.strip().lower() for t in bot_topics.split(",") if t.strip()]
            if any(topic in content_lower for topic in topics):
                return True
        
        return False
    
    # Rate limiting methods moved to top level bot_processors.py
    
    async def _gather_bot_context(self, context: MessageContext) -> Dict[str, Any]:
        """Gather all bot context variables (enthusiasm_flow.md + enhancements)"""
        
        # Get Discord context (server, channel, entities)
        discord_context = await self._get_discord_context(context)
        
        # Get recent messages
        recent_messages = await self._get_recent_messages(context, limit=10)
        
        # Get chat history from Honcho (if available)
        chat_history = await self._get_chat_history(context)
        
        # Analyze conversation flow
        conversation_analysis = self._analyze_conversation_flow(recent_messages, context)
        
        # Analyze addressing
        addressing_analysis = self._analyze_addressing(context, discord_context)
        
        # Build comprehensive bot context
        bot_context = {
            # Identity (from enthusiasm_flow.md)
            "botName": self.bot_name,
            "botUsername": str(context.bot.user) if context.bot.user else "unknown",
            "botPfp": str(context.bot.user.avatar.url) if context.bot.user and context.bot.user.avatar else "",
            "botPersonality": self.bot_personality,
            "botSkills": self.bot_skills,
            
            # Memory & History
            "chatHistory": chat_history,
            "botMemory": {},  # TODO: Expose from Honcho if needed
            "recentMessages": recent_messages,
            "lastMessage": {
                "author": str(context.author),
                "content": context.content,
                "timestamp": datetime.now().isoformat()
            },
            "lastUserMessage": {
                "author": str(context.author),
                "content": context.content
            },
            
            # Session & Environment  
            "sessionPrompt": os.getenv("SYSTEM_PROMPT", "You are a helpful AI assistant."),
            "sessionState": {
                "rateLimited": False,  # We already checked this
                "channelId": str(context.channel.id),
                "guildId": str(context.guild.id) if context.guild else None
            },
            "otherBotsInSession": [bot for bot in discord_context.get("entities", {}).get("symbients", []) if bot.get("id") != str(context.bot.user.id)],
            
            # Discord Context (our enhancement)
            "discord": discord_context,
            
            # Analysis (our enhancement)
            "whoIsAddressed": addressing_analysis.get("who_is_directly_addressed", "nobody"),
            "conversationFlow": conversation_analysis,
            "mentionedUsers": [str(user) for user in context.mentioned_users],
            "isDirectlyMentioned": context.is_mentioned
        }
        
        return bot_context
    
    async def _get_discord_context(self, context: MessageContext) -> Dict[str, Any]:
        """Get Discord context (server, channel, entities) - from DiscordContextProcessor logic"""
        
        # Server info
        server_info = {}
        if context.guild:
            server_info = {
                "name": context.guild.name,
                "description": context.guild.description or "",
                "member_count": context.guild.member_count,
                "id": str(context.guild.id)
            }
        else:
            server_info = {"name": "Direct Message", "description": "", "member_count": 2, "id": None}
        
        # Channel info
        channel_info = {
            "name": getattr(context.channel, 'name', 'dm'),
            "id": str(context.channel.id),
            "type": str(context.channel.type),
            "topic": getattr(context.channel, 'topic', None) or ""
        }
        
        # Entities (users and bots)
        entities = await self._get_entities(context)
        
        # Presence info
        presence_info = {}
        if context.guild:
            try:
                presence_info = {
                    "total_members": context.guild.member_count,
                    "total_online": sum(1 for m in context.guild.members if str(m.status) == 'online'),
                    "bot_count": sum(1 for m in context.guild.members if m.bot),
                    "human_count": sum(1 for m in context.guild.members if not m.bot)
                }
            except:
                presence_info = {"total_members": context.guild.member_count, "total_online": 1}
        else:
            presence_info = {"total_members": 2, "total_online": 1}
        
        return {
            "server": server_info,
            "channel": channel_info,
            "entities": entities,
            "presence": presence_info
        }
    
    async def _get_entities(self, context: MessageContext) -> Dict[str, List[Dict[str, Any]]]:
        """Get entities (users and bots) from channel"""
        entities = {"symbients": [], "humans": []}
        
        if not context.guild:
            return entities
        
        try:
            # Get channel members if available
            members = []
            if hasattr(context.channel, 'members'):
                members = list(context.channel.members)
            else:
                # Fallback to guild members (limited)
                members = list(context.guild.members)[:50]
            
            # Process each member
            for member in members:
                entity_info = {
                    "name": member.display_name or str(member),
                    "username": str(member),
                    "mention": member.mention,
                    "id": str(member.id),
                    "status": str(member.status),
                    "activity": str(member.activity.name) if member.activity else None
                }
                
                if member.bot:
                    entities["symbients"].append(entity_info)
                else:
                    # Only include online humans by default
                    if str(member.status) != 'offline' or member == context.author:
                        entities["humans"].append(entity_info)
            
            # Sort by status and name
            entities["humans"].sort(key=lambda x: (x["status"] == "online", x["name"]))
            entities["symbients"].sort(key=lambda x: (x["status"] == "online", x["name"]))
            
        except Exception as e:
            self.logger.warning(f"Could not get entities: {e}")
        
        return entities
    
    async def _get_recent_messages(self, context: MessageContext, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from channel"""
        try:
            messages = []
            async for message in context.channel.history(limit=limit):
                if message.id != context.message.id:  # Exclude current message
                    messages.append({
                        "author": str(message.author),
                        "content": message.content,
                        "is_bot": message.author.bot,
                        "timestamp": message.created_at.isoformat()
                    })
            
            # Reverse to get chronological order (oldest first)
            return list(reversed(messages))
            
        except Exception as e:
            self.logger.error(f"Error getting recent messages: {e}")
            return []
    
    async def _get_chat_history(self, context: MessageContext) -> List[Dict[str, Any]]:
        """Get chat history from Honcho if available"""
        if not self.honcho_client or not self.app:
            return []
        
        try:
            from .base_processor import get_honcho_user, get_honcho_session
            
            # Get user and session
            user = get_honcho_user(self.honcho_client, self.app.id, context.author)
            session, _ = get_honcho_session(self.honcho_client, self.app.id, user.id, str(context.channel.id))
            
            if session:
                # Get recent messages
                history_iter = self.honcho_client.apps.users.sessions.messages.list(
                    app_id=self.app.id, session_id=session.id, user_id=user.id, size=5
                )
                
                history = []
                for msg in history_iter:
                    history.append({
                        "content": msg.content,
                        "is_user": msg.is_user,
                        "timestamp": msg.created_at.isoformat() if hasattr(msg, 'created_at') else ""
                    })
                
                return history
                
        except Exception as e:
            self.logger.warning(f"Could not get chat history: {e}")
        
        return []
    
    def _analyze_conversation_flow(self, recent_messages: List[Dict[str, Any]], context: MessageContext) -> Dict[str, Any]:
        """Analyze conversation flow for turn-taking decisions"""
        if not recent_messages:
            return {"last_bot_message_idx": -1, "messages_since_last_bot": 0, "active_conversation": False, "last_bot_message_time": None, "time_since_last_bot": None}
        
        # Find last message from this bot
        last_bot_message_idx = -1
        last_bot_message_time = None
        for i, msg in enumerate(reversed(recent_messages)):
            if msg["author"] == str(context.bot.user):
                last_bot_message_idx = len(recent_messages) - 1 - i
                last_bot_message_time = msg.get("timestamp")
                break
        
        # Calculate time since last bot message
        time_since_last_bot = None
        if last_bot_message_time:
            try:
                from datetime import datetime
                # Try to parse ISO format timestamp
                if last_bot_message_time.endswith('Z'):
                    last_time = datetime.fromisoformat(last_bot_message_time[:-1])
                elif '+' in last_bot_message_time or last_bot_message_time.count(':') == 3:
                    # Has timezone info
                    last_time = datetime.fromisoformat(last_bot_message_time.replace('Z', '+00:00'))
                else:
                    last_time = datetime.fromisoformat(last_bot_message_time)
                
                # Calculate difference (assume UTC if no timezone)
                now = datetime.now(last_time.tzinfo) if last_time.tzinfo else datetime.now()
                time_since_last_bot = (now - last_time).total_seconds()
            except Exception as e:
                self.logger.warning(f"Could not parse timestamp {last_bot_message_time}: {e}")
        
        # Detect active conversation (simplified)
        recent_authors = [msg["author"] for msg in recent_messages[-3:]]
        unique_recent_authors = set(recent_authors)
        active_conversation = len(unique_recent_authors) <= 2 and len(recent_authors) >= 2
        
        return {
            "last_bot_message_idx": last_bot_message_idx,
            "messages_since_last_bot": len(recent_messages) - last_bot_message_idx - 1 if last_bot_message_idx >= 0 else len(recent_messages),
            "active_conversation": active_conversation,
            "recent_authors": recent_authors[-3:],
            "last_bot_message_time": last_bot_message_time,
            "time_since_last_bot": time_since_last_bot
        }
    
    def _analyze_addressing(self, context: MessageContext, discord_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze who is being addressed in the message"""
        content_lower = context.content.lower()
        bot_name_lower = self.bot_name.lower()
        
        # Check if bot is directly addressed
        who_is_directly_addressed = "nobody"
        if context.is_mentioned:
            # Check if the bot itself is mentioned by checking user IDs
            if any(user.id == context.bot.user.id for user in context.mentioned_users):
                who_is_directly_addressed = "me"
            else:
                who_is_directly_addressed = "someone_else"
        
        # Check for name variants without @mentions
        elif bot_name_lower in content_lower:
            who_is_directly_addressed = "me"
        
        # Check if someone else is addressed by name
        elif discord_context.get("entities", {}).get("humans", []):
            for human in discord_context["entities"]["humans"]:
                if human["name"].lower() in content_lower:
                    who_is_directly_addressed = "someone_else"
                    break
        
        return {
            "who_is_directly_addressed": who_is_directly_addressed,
            "is_response_to_me": who_is_directly_addressed == "me",
            "interrupting_likelihood": "high" if who_is_directly_addressed == "someone_else" else "low"
        }
    
    async def _check_other_bot_statuses(self, context: MessageContext, bot_context: Dict[str, Any]) -> Dict[str, str]:
        """Check status of other bots in server (simplified - use status from entities)"""
        bot_status_coordination = os.getenv("BOT_STATUS_COORDINATION", "false").lower() == "true"
        if not bot_status_coordination or not context.guild:
            return {}
        
        try:
            # Use existing status from Discord entities (already fetched)
            statuses = {}
            for symbiont in bot_context["discord"]["entities"]["symbients"]:
                if symbiont["id"] != str(context.bot.user.id):
                    statuses[symbiont["id"]] = symbiont["status"]
            
            # Log for debugging
            available_bots = [bot_id for bot_id, status in statuses.items() if status not in ['do_not_disturb', 'offline']]
            unavailable_bots = [bot_id for bot_id, status in statuses.items() if status in ['do_not_disturb', 'offline']]
            
            self.logger.info(f"🤖 Bot Status Check: {len(available_bots)} available, {len(unavailable_bots)} unavailable")
            
            return statuses
            
        except Exception as e:
            self.logger.warning(f"Error checking other bot statuses: {e}")
            return {}
    
    # Status management methods moved to top level bot_processors.py
    
    async def _call_unified_llm(self, bot_context: Dict[str, Any], context: MessageContext, other_bot_statuses: Dict[str, str] = None) -> str:
        """Make single LLM call with complete context for reasoning + scoring"""
        
        prompt = self._build_unified_prompt(bot_context, context, other_bot_statuses)
        
        # Log prompt for debugging (only last part to avoid spam)
        prompt_lines = prompt.split('\n')
        current_msg_idx = next((i for i, line in enumerate(prompt_lines) if "CURRENT MESSAGE:" in line), -1)
        if current_msg_idx >= 0 and len(prompt_lines) > current_msg_idx + 1:
            current_msg = prompt_lines[current_msg_idx + 1] if current_msg_idx + 1 < len(prompt_lines) else "N/A"
            self.logger.info(f"🔍 Current message being analyzed: {current_msg}")
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=150,  # Increased for reasoning + score + activities
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            raise ProcessorError("unified_enthusiasm", f"Error calling LLM: {e}", e)
    
    def _build_unified_prompt(self, bot_context: Dict[str, Any], context: MessageContext, other_bot_statuses: Dict[str, str] = None) -> str:
        """Build unified prompt with all bot context"""
        
        # Format recent messages (clean formatting to avoid LLM confusion)
        recent_messages_str = ""
        for msg in bot_context["recentMessages"][-5:]:  # Last 5 messages
            clean_content = self._clean_message_content(msg['content'])
            recent_messages_str += f"{msg['author']}: {clean_content}\n"
        
        # Format entities with status info
        symbients = bot_context["discord"]["entities"]["symbients"]
        humans = bot_context["discord"]["entities"]["humans"]
        
        # Include other bot statuses if available
        symbients_with_status = []
        if symbients:
            for bot in symbients:
                bot_id = bot['id']
                # Check if we have updated status info
                if other_bot_statuses and bot_id in other_bot_statuses:
                    actual_status = other_bot_statuses[bot_id]
                    if actual_status in ['do_not_disturb', 'offline']:
                        symbients_with_status.append(f"{bot['name']} (🔴 {actual_status})")
                    else:
                        symbients_with_status.append(f"{bot['name']} (🟢 {actual_status})")
                else:
                    symbients_with_status.append(f"{bot['name']} ({bot['status']})")
        elif other_bot_statuses is None:
            # Fallback if no other_bot_statuses provided
            symbients_with_status = [f"{bot['name']} ({bot['status']})" for bot in symbients] if symbients else []
        
        symbients_str = ", ".join(symbients_with_status) if symbients_with_status else "None"
        humans_str = ", ".join([f"{human['name']} ({human['status']})" for human in humans[:5]]) if humans else "None"
        
        # Format skills
        skills_str = ", ".join(bot_context["botSkills"]) if bot_context["botSkills"] else "General conversation"
        
        # Check for explicit boredom triggers in current message
        boredom_triggers = ["boring", "bored", "dull", "same thing", "repetitive", "stale"]
        current_content_lower = bot_context['lastMessage']['content'].lower()
        has_boredom_trigger = any(trigger in current_content_lower for trigger in boredom_triggers)
        
        prompt = f"""You are {bot_context['botName']} deciding whether to respond to the CURRENT MESSAGE below.

PERSONALITY: {bot_context['botPersonality']}
SKILLS: {skills_str}

CURRENT MESSAGE TO ANALYZE (80% weight):
{bot_context['lastMessage']['author']}: {bot_context['lastMessage']['content']}
{'[BOREDOM TRIGGER DETECTED]' if has_boredom_trigger else ''}

RECENT CONTEXT (20% weight - decreasing importance):
{recent_messages_str}

SERVER CONTEXT:
{bot_context['discord']['server']['name']} #{bot_context['discord']['channel']['name']} | Bots: {symbients_str} | Humans: {humans_str}

DECISION FACTORS:
• Direct mention: {bot_context['isDirectlyMentioned']}
• Who's addressed: {bot_context['whoIsAddressed']}
• My last response: {bot_context['conversationFlow']['messages_since_last_bot']} messages ago
• Recently active: {'YES' if bot_context['conversationFlow']['messages_since_last_bot'] <= 1 else 'NO'}

SCORING RULES (0-9):
Focus 80% on CURRENT MESSAGE content and relevance to my skills.

9: CURRENT MESSAGE directly @mentions me
7-8: CURRENT MESSAGE matches my skills AND I haven't responded recently (>2 messages ago)
4-6: CURRENT MESSAGE somewhat relevant to my skills
1-3: CURRENT MESSAGE low relevance OR I just responded recently or topic is boring
0: CURRENT MESSAGE mentions someone else specifically OR completely irrelevant

CRITICAL RULE: If I responded in last 1-2 messages → subtract 3-4 points from base score.

BOREDOM DETECTION (simple and direct):
1. If CURRENT MESSAGE contains "boring", "bored", "dull", "same thing", "repetitive" → TOPIC_CHANGE: YES
2. If [BOREDOM TRIGGER DETECTED] appears above → TOPIC_CHANGE: YES  
3. If last 3 recent messages all under 10 words → TOPIC_CHANGE: YES
4. Otherwise → TOPIC_CHANGE: NO

Analyze CURRENT MESSAGE first, then recent context for these specific triggers.

Respond exactly as:
REASONING: [Why the CURRENT MESSAGE does/doesn't warrant my response + any boredom detected]
SCORE: [0-9]
TOPIC_CHANGE: [YES/NO - if conversation is repetitive/boring and needs topic change]
<activities>
activity1, activity2, activity3, activity4
</activities>

Activities should be 4 comma-separated increasingly mundane-to-surreal things anyone could be doing right now (max 7 words each), unrelated to the message. If TOPIC_CHANGE=YES, make one activity especially conversation-worthy and novel."""

        
        return prompt
    
    def _clean_message_content(self, content: str) -> str:
        """Clean message content to avoid LLM parsing issues"""
        import re
        
        # Remove code blocks (triple backticks)
        content = re.sub(r'```[^`]*```', '[code block]', content, flags=re.DOTALL)
        
        # Remove inline code (single backticks)
        content = re.sub(r'`[^`]+`', '[code]', content)
        
        # Remove Discord mentions that could confuse LLM
        content = re.sub(r'<@!?\d+>', '[user mention]', content)
        content = re.sub(r'<#\d+>', '[channel mention]', content)
        content = re.sub(r'<@&\d+>', '[role mention]', content)
        
        # Remove excessive whitespace/newlines
        content = re.sub(r'\n+', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Trim and limit length for context
        content = content.strip()
        if len(content) > 200:
            content = content[:197] + "..."
            
        return content
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for reasoning, score, and activities"""
        try:
            # Log raw response for debugging
            self.logger.info(f"🔍 Raw LLM response: {repr(response)}")
            
            lines = response.strip().split('\n')
            
            reasoning = ""
            score = 5  # Default
            topic_change = False
            activities = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()
                elif line.startswith("SCORE:"):
                    score_text = line.replace("SCORE:", "").strip()
                    # Extract digit
                    import re
                    match = re.search(r'(\d)', score_text)
                    if match:
                        score = int(match.group(1))
                        score = max(0, min(9, score))  # Clamp to 0-9
                elif line.startswith("TOPIC_CHANGE:"):
                    topic_change_text = line.replace("TOPIC_CHANGE:", "").strip().upper()
                    topic_change = topic_change_text == "YES"
                elif line.startswith("ACTIVITIES:"):
                    activities_text = line.replace("ACTIVITIES:", "").strip()
                    if activities_text and activities_text not in ["{nothing}", "", "none", "None"]:
                        # Handle both comma-separated and bracket formats
                        if activities_text.startswith('[') and activities_text.endswith(']'):
                            # Remove brackets and split
                            activities_text = activities_text[1:-1]
                        activities = [act.strip().strip('"\'') for act in activities_text.split(',') if act.strip()]
                        # Filter out empty or placeholder activities
                        activities = [act for act in activities if act and act not in ["{nothing}", "nothing", "none", "None"]]
                    else:
                        activities = []
            
            # Parse XML activities format
            import re
            activities_match = re.search(r'<activities>(.*?)</activities>', response, re.DOTALL)
            if activities_match:
                activities_text = activities_match.group(1).strip()
                if activities_text:
                    activities = [act.strip().strip('"\'') for act in activities_text.split(',') if act.strip()]
                    # Filter out empty or placeholder activities
                    activities = [act for act in activities if act and act not in ["{nothing}", "nothing", "none", "None"]]
            
            
            # Log what we parsed
            self.logger.info(f"🔍 Parsed - reasoning: {repr(reasoning)}, score: {score}, topic_change: {topic_change}, activities: {activities}")
            
            return {
                "reasoning": reasoning,
                "score": score,
                "topic_change": topic_change,
                "activities": activities[:4] if activities else [],
                "raw_response": response
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {
                "reasoning": f"Parse error: {e}",
                "score": 5,
                "topic_change": False,
                "activities": [],
                "raw_response": response
            }
    
    async def _log_decision(self, context: MessageContext, bot_context: Dict[str, Any], 
                           llm_response: str, parsed_result: Dict[str, Any], should_respond: bool):
        """Log comprehensive decision information"""
        
        # Console logging (always)
        decision = "RESPOND" if should_respond else "SKIP"
        self.logger.info(f"🎯 ENTHUSIASM: {parsed_result['score']}/9 (need {self.threshold}) → {decision}")
        self.logger.info(f"💭 REASONING: {parsed_result['reasoning']}")
        
        # Log timing information for debugging
        msgs_since = bot_context['conversationFlow']['messages_since_last_bot']
        time_since = bot_context['conversationFlow']['time_since_last_bot']
        if time_since is not None:
            self.logger.info(f"⏰ LAST RESPONSE: {msgs_since} messages ago, {time_since:.1f}s ago")
        else:
            self.logger.info(f"⏰ LAST RESPONSE: {msgs_since} messages ago, no timestamp available")
        
        if parsed_result['activities']:
            activities_str = ", ".join(parsed_result['activities'])
            self.logger.info(f"🎲 ACTIVITIES: {activities_str}")
        else:
            self.logger.info("🎲 RANDOM ACTIVITIES: (none generated)")
            
        # Log topic change detection
        if parsed_result.get('topic_change', False):
            self.logger.info("🔄 TOPIC CHANGE: Conversation detected as repetitive/boring - suggesting new direction")
        
        # Structured logging (if debug enabled)
        if self.debug:
            try:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": f"{context.channel.id}_{context.author.id}_{int(datetime.now().timestamp())}",
                    "decision": decision,
                    "score": parsed_result['score'],
                    "threshold": self.threshold,
                    "reasoning": parsed_result['reasoning'],
                    "activities": parsed_result['activities'],
                    "message_context": {
                        "author": str(context.author),
                        "channel": str(context.channel),
                        "content": context.content[:200] + "..." if len(context.content) > 200 else context.content
                    },
                    "bot_context_summary": {
                        "name": bot_context['botName'],
                        "skills_count": len(bot_context['botSkills']),
                        "other_bots": len(bot_context['otherBotsInSession']),
                        "humans_present": len(bot_context['discord']['entities']['humans']),
                        "server": bot_context['discord']['server']['name'],
                        "channel": bot_context['discord']['channel']['name']
                    },
                    "llm_response": llm_response
                }
                
                self.logger.debug(f"📁 Structured log: {json.dumps(log_entry, ensure_ascii=False)}")
                
            except Exception as e:
                self.logger.error(f"Error creating structured log: {e}")
    
    def _format_verbose_prefix(self, parsed_result: Dict[str, Any]) -> str:
        """Format verbose reasoning for Discord display"""
        if not self.verbose_discord:
            return ""
        
        # Make the scoring clearer for users
        decision_text = "RESPOND" if parsed_result['score'] >= self.threshold else "SKIP"
        
        lines = [
            f"🤖 Response Decision: {parsed_result['score']}/9 (threshold: {self.threshold}) → {decision_text}",
            f"💭 Reasoning: {parsed_result['reasoning']}",
        ]
        
        # Add key influencing factors if bot_context is available
        if 'bot_context' in parsed_result:
            bot_context = parsed_result['bot_context']
            
            # Build key factors line
            factors = []
            
            # Check if bot was mentioned - use the proper Discord mention check from bot_context
            mentioned = bot_context.get('isDirectlyMentioned', False)
            
            factors.append(f"@mentioned: {'✅' if mentioned else '❌'}")
            
            # Recent activity check
            conv_flow = bot_context.get('conversationFlow', {})
            msgs_since = conv_flow.get('messages_since_last_bot', 999)
            time_since = conv_flow.get('time_since_last_bot')
            
            if time_since is not None:
                factors.append(f"last response: {msgs_since}msg/{time_since:.0f}s ago")
            else:
                factors.append(f"last response: {msgs_since}msg ago")
            
            # Skill matching (simplified)
            skills = bot_context.get('botSkills', [])
            message_content = parsed_result.get('message_content', '').lower()
            skill_match = any(skill.lower() in message_content for skill in skills[:3])  # Check first 3 skills
            factors.append(f"skill match: {'✅' if skill_match else '❌'}")
            
            # Other bots availability
            other_bots = bot_context.get('otherBotsInSession', [])
            if isinstance(other_bots, list):
                # otherBotsInSession is a list of bot entities
                available_bots = sum(1 for bot in other_bots if bot.get('status', 'unknown') not in ['do_not_disturb', 'offline'])
                total_bots = len(other_bots)
            else:
                # otherBotsInSession is a dict of {bot_id: status}
                available_bots = sum(1 for status in other_bots.values() if status not in ['do_not_disturb', 'offline'])
                total_bots = len(other_bots)
            
            if total_bots > 0:
                factors.append(f"other bots: {available_bots}/{total_bots} available")
            
            # Add factors line
            lines.append(f"🔍 Factors: {' • '.join(factors)}")
        
        # Add recent message logs if debug logging is enabled
        debug_logging = os.getenv("DEBUG_LOGGING", "false").lower() == "true"
        if debug_logging and 'bot_context' in parsed_result:
            lines.append("")
            lines.append("📝 Recent Messages:")
            recent_messages = parsed_result['bot_context'].get('recentMessages', [])
            for msg in recent_messages[-5:]:  # Last 5 messages only
                author = msg.get('author', 'Unknown')
                content = msg.get('content', '')
                # Clean content: remove line breaks, limit to 50 chars, and remove @mentions
                clean_content = content.replace('\n', ' ').replace('\r', ' ').strip()
                # Remove @mentions to avoid pinging users again
                import re
                clean_content = re.sub(r'@\w+', '@[user]', clean_content)
                if len(clean_content) > 50:
                    clean_content = clean_content[:47] + "..."
                lines.append(f"  {author}: {clean_content}")
                
        # Add activities if available
        if 'activities' in parsed_result and parsed_result['activities']:
            lines.append("")
            activities_str = ", ".join(parsed_result['activities'])
            lines.append(f"🎲 Random Activities: {activities_str}")
        elif 'activities' in parsed_result:
            lines.append("")
            lines.append("🎲 Random Activities: (none generated)")
        
        lines.append("")  # Empty line before actual response
        return "\n".join(lines)