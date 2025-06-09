"""
Status Coordinator Processor - Manages bot status based on availability.

Features:
- Sets bot status to "do not disturb" when rate limited
- Sets bot status to "online" when available  
- Other bots can check this status to avoid mentioning busy bots
- Caches status checks to reduce API calls
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import discord
from .base_processor import BaseProcessor, MessageContext, ProcessorError


class StatusCoordinatorProcessor(BaseProcessor):
    """
    Processor that coordinates bot status based on availability.
    
    Sets Discord status to indicate when bot is rate limited or busy.
    Provides utilities for other bots to check status before mentioning.
    """
    
    def __init__(self):
        super().__init__("status_coordinator")
        
        # Configuration
        self.enabled = os.getenv("BOT_STATUS_COORDINATION", "true").lower() == "true"
        self.cache_seconds = int(os.getenv("STATUS_CHECK_CACHE_SECONDS", "30"))
        self.mention_dnd = os.getenv("MENTION_DO_NOT_DISTURB_BOTS", "false").lower() == "true"
        self.mention_offline = os.getenv("MENTION_OFFLINE_BOTS", "false").lower() == "true"
        
        # Status cache to reduce Discord API calls
        self._status_cache: Dict[str, Tuple[str, datetime]] = {}
        
        # Track our own rate limit status
        self._is_rate_limited = False
        self._last_status_change = None
        self._bot = None  # Will be set when first message processes
        
        self.logger.info(f"Status coordinator initialized (enabled: {self.enabled})")
        if self.enabled:
            self.logger.info(f"Cache duration: {self.cache_seconds}s")
            self.logger.info(f"Mention DND bots: {self.mention_dnd}")
            self.logger.info(f"Mention offline bots: {self.mention_offline}")
            self.logger.info("╰( ͡° ͜ʖ ͡° )つ Status coordinator using robust per-message checking!")
    
    async def process(self, context: MessageContext) -> bool:
        """
        Update bot status based on current availability.
        
        Returns:
            True if processing should continue, False if rate limited
        """
        if not self.enabled:
            return True
        
        try:
            # Store bot reference
            if self._bot is None:
                self._bot = context.bot
            
            # Check if we're currently rate limited
            rate_limited = context.get_data("rate_limited", False)
            
            # ROBUST CHECK: Always verify status should match reality
            should_be_rate_limited = rate_limited
            
            # If we think we're rate limited but enough time has passed, we should be online
            if self._is_rate_limited and self._last_status_change:
                time_since_change = datetime.now() - self._last_status_change
                if time_since_change.total_seconds() > 65:  # 65 second buffer
                    self.logger.info(f"🔄 /ᐠ｡ꞈ｡ᐟ\ Auto-recovery: stuck in DND for {time_since_change.total_seconds():.1f}s, forcing online!")
                    should_be_rate_limited = False
            
            self.logger.info(f"🔍 Status check: current_rate_limited={rate_limited}, should_be={should_be_rate_limited}, bot_state={self._is_rate_limited}")
            
            # Update status if it should change
            if should_be_rate_limited != self._is_rate_limited:
                self.logger.info(f"Status change needed: {self._is_rate_limited} → {should_be_rate_limited}")
                await self._update_bot_status(context.bot, should_be_rate_limited)
                self._is_rate_limited = should_be_rate_limited
                self._last_status_change = datetime.now()
            
            # Store status info in context for other processors
            context.set_data("bot_status", {
                "is_rate_limited": self._is_rate_limited,
                "last_status_change": self._last_status_change,
                "current_status": "do_not_disturb" if self._is_rate_limited else "online"
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in status coordinator: {e}")
            return True  # Don't block processing on status errors
    
    async def _update_bot_status(self, bot: discord.Bot, rate_limited: bool):
        """Update the bot's Discord status"""
        try:
            if rate_limited:
                # Check if bot already has a custom rate limit status - don't override it
                try:
                    current_activity = bot.guilds[0].me.activity if bot.guilds else None
                    if (current_activity and 
                        current_activity.type == discord.ActivityType.custom and 
                        "Rate limited until" in current_activity.name):
                        self.logger.info(f"🔴 Status already set with custom timestamp: {current_activity.name}")
                        return  # Don't override the precise timestamp
                except Exception as e:
                    self.logger.debug(f"Could not check current activity: {e}")
                
                # Calculate rate limit expiry time from global timestamps
                activity_name = "Rate limited - please wait"
                
                # Try to get precise expiry time from global rate limiting data
                try:
                    # Import at function level to avoid circular imports
                    import time
                    from datetime import datetime, timezone
                    
                    # Access global rate timestamps (this is a bit hacky but works)
                    import sys
                    bot_module = sys.modules.get('__main__')
                    if hasattr(bot_module, '_rate_timestamps'):
                        rate_timestamps = bot_module._rate_timestamps
                        rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
                        
                        # Find any channel that's currently rate limited
                        current_time = time.time()
                        for channel_id, timestamps in rate_timestamps.items():
                            recent_timestamps = [t for t in timestamps if current_time - t <= 60]
                            if len(recent_timestamps) >= rate_limit_per_minute:
                                # Calculate when the oldest timestamp expires
                                oldest_timestamp = min(recent_timestamps)
                                expire_time = oldest_timestamp + 60
                                expire_datetime = datetime.fromtimestamp(expire_time, tz=timezone.utc)
                                expire_str = expire_datetime.strftime("%H:%M:%S")
                                activity_name = f"Rate limited until {expire_str}"
                                break
                                
                except Exception as e:
                    self.logger.debug(f"Could not calculate precise expiry time: {e}")
                
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=activity_name.replace("Rate limited", "cooldown")
                )
                self.logger.info(f"🔴 CHANGING STATUS → DO NOT DISTURB with custom presence: {activity_name}")
                await bot.change_presence(
                    status=discord.Status.do_not_disturb,
                    activity=activity
                )
                self.logger.info("✅ Status change completed")
            else:
                # Set back to online with normal activity
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name="for messages"
                )
                self.logger.info("🟢 CHANGING STATUS → ONLINE (available)")
                await bot.change_presence(
                    status=discord.Status.online,
                    activity=activity
                )
                self.logger.info("✅ Status change completed")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to update bot status: {e}")
    
    async def check_bot_status(self, bot_id: str, guild: discord.Guild) -> str:
        """
        Check another bot's Discord status with caching.
        
        Returns: 'online', 'idle', 'do_not_disturb', 'offline', 'unknown'
        """
        cache_key = f"{guild.id}_{bot_id}"
        current_time = datetime.now()
        
        # Check cache first
        if cache_key in self._status_cache:
            cached_status, cache_time = self._status_cache[cache_key]
            if current_time - cache_time < timedelta(seconds=self.cache_seconds):
                return cached_status
        
        try:
            member = guild.get_member(int(bot_id))
            if member and member.bot:
                status = str(member.status)
                # Cache the result
                self._status_cache[cache_key] = (status, current_time)
                self.logger.debug(f"Bot status check: {member.display_name} ({bot_id}) is {status}")
                return status
            self.logger.debug(f"Bot status check: {bot_id} not found or not a bot")
            return 'unknown'
        except Exception as e:
            self.logger.warning(f"Failed to check bot status for {bot_id}: {e}")
            return 'unknown'
    
    async def should_mention_bot(self, bot_mention: str, guild: discord.Guild) -> bool:
        """
        Determine if bot should be mentioned based on status.
        
        Args:
            bot_mention: Discord mention string like <@1234567890>
            guild: Discord guild object
        
        Returns:
            bool: True if bot should be mentioned
        """
        if not self.enabled:
            return True
        
        # Extract bot ID from mention format
        bot_id_match = re.search(r'<@!?(\d+)>', bot_mention)
        if not bot_id_match:
            return True  # Not a bot mention, allow it
        
        bot_id = bot_id_match.group(1)
        status = await self.check_bot_status(bot_id, guild)
        
        # Check against configuration
        if status == 'do_not_disturb' and not self.mention_dnd:
            self.logger.debug(f"Skipping mention of DND bot {bot_id}")
            return False
        if status == 'offline' and not self.mention_offline:
            self.logger.debug(f"Skipping mention of offline bot {bot_id}")
            return False
        
        return True
    
    async def get_available_bots(self, guild: discord.Guild, bot_ids: List[str]) -> List[str]:
        """
        Filter list of bot IDs to only include available ones.
        
        Args:
            guild: Discord guild object
            bot_ids: List of bot IDs to check
        
        Returns:
            List of available bot IDs
        """
        if not self.enabled:
            return bot_ids
        
        available_bots = []
        for bot_id in bot_ids:
            status = await self.check_bot_status(bot_id, guild)
            
            # Include if available
            if status in ['online', 'idle']:
                available_bots.append(bot_id)
            elif status == 'do_not_disturb' and self.mention_dnd:
                available_bots.append(bot_id)
            elif status == 'offline' and self.mention_offline:
                available_bots.append(bot_id)
        
        return available_bots
    
    async def build_status_context(self, guild: discord.Guild, known_bot_ids: List[str]) -> str:
        """
        Build context string about bot availability for system prompt.
        
        Args:
            guild: Discord guild object
            known_bot_ids: List of known bot IDs to check
        
        Returns:
            Formatted status context string
        """
        if not self.enabled or not known_bot_ids:
            return ""
        
        context_lines = ["Current bot availability:"]
        
        for bot_id in known_bot_ids:
            try:
                member = guild.get_member(int(bot_id))
                if member and member.bot:
                    status = await self.check_bot_status(bot_id, guild)
                    name = member.display_name
                    emoji = {
                        'online': '🟢',
                        'idle': '🟡', 
                        'do_not_disturb': '🔴',
                        'offline': '⚫',
                        'unknown': '❓'
                    }.get(status, '❓')
                    
                    context_lines.append(f"- {name}: {emoji} {status}")
            except Exception as e:
                self.logger.warning(f"Failed to get member info for {bot_id}: {e}")
        
        context_lines.append("")
        context_lines.append("Only mention available bots (🟢🟡). If referencing busy/offline bots, use names without @tags.")
        
        return "\n".join(context_lines)
    
    def clear_old_cache_entries(self):
        """Clear cache entries older than cache duration"""
        current_time = datetime.now()
        expired_keys = []
        
        for cache_key, (_, cache_time) in self._status_cache.items():
            if current_time - cache_time > timedelta(seconds=self.cache_seconds * 2):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self._status_cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleared {len(expired_keys)} expired cache entries")
    
    async def on_startup(self, bot: discord.Bot):
        """Log startup status survey of all visible bots and humans"""
        if not self.enabled:
            return
            
        try:
            self.logger.info("🔍 === Bot Status Survey ===")
            
            for guild in bot.guilds:
                bots = [m for m in guild.members if m.bot]
                humans = [m for m in guild.members if not m.bot]
                
                self.logger.info(f"📍 {guild.name}: {len(bots)} bots, {len(humans)} humans")
                
                # Log bot statuses
                if bots:
                    for bot_member in sorted(bots, key=lambda m: m.display_name.lower()):
                        status = str(bot_member.status)
                        emoji = {
                            'online': '🟢',
                            'idle': '🟡', 
                            'do_not_disturb': '🔴',
                            'offline': '⚫'
                        }.get(status, '❓')
                        self.logger.info(f"  🤖 {emoji} {bot_member.display_name} - {status}")
            
            self.logger.info("🔍 === End Status Survey ===")
            
        except Exception as e:
            self.logger.error(f"Failed to log startup status survey: {e}")