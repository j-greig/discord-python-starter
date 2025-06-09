"""
Bot Status Coordination System

Provides functions to check Discord member status and implement
status-aware mention logic according to PRD_BOT_STATUS_COORDINATION.md
"""

import re
import logging
from typing import Dict, List, Tuple
import discord
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Status cache to reduce Discord API calls
_status_cache: Dict[str, Tuple[str, datetime]] = {}
_cache_duration_seconds = 30


async def check_bot_status(bot_id: str, guild: discord.Guild) -> str:
    """
    Check another bot's Discord status with caching
    Returns: 'online', 'idle', 'do_not_disturb', 'offline', 'unknown'
    """
    cache_key = f"{guild.id}_{bot_id}"
    current_time = datetime.now()
    
    # Check cache first
    if cache_key in _status_cache:
        cached_status, cache_time = _status_cache[cache_key]
        if current_time - cache_time < timedelta(seconds=_cache_duration_seconds):
            return cached_status
    
    try:
        member = guild.get_member(int(bot_id))
        if member and member.bot:
            status = str(member.status)
            # Cache the result
            _status_cache[cache_key] = (status, current_time)
            logger.debug(f"Bot status check: {member.display_name} ({bot_id}) is {status}")
            return status
        logger.debug(f"Bot status check: {bot_id} not found or not a bot")
        return 'unknown'
    except Exception as e:
        logger.warning(f"Failed to check bot status for {bot_id}: {e}")
        return 'unknown'


async def should_mention_entity(entity_mention: str, guild: discord.Guild, mention_dnd: bool = False, mention_offline: bool = False) -> bool:
    """
    Determine if entity should be mentioned based on status
    
    Args:
        entity_mention: Discord mention string like <@1234567890>
        guild: Discord guild object
        mention_dnd: Whether to mention do_not_disturb bots
        mention_offline: Whether to mention offline bots
    
    Returns:
        bool: True if entity should be mentioned
    """
    # Extract bot ID from mention format
    bot_id_match = re.search(r'<@!?(\d+)>', entity_mention)
    if not bot_id_match:
        return True  # Not a bot mention, allow it
    
    bot_id = bot_id_match.group(1)
    status = await check_bot_status(bot_id, guild)
    
    # Check against configuration
    if status == 'do_not_disturb' and not mention_dnd:
        return False
    if status == 'offline' and not mention_offline:
        return False
    
    return True


async def get_bot_statuses(guild: discord.Guild, bot_ids: List[str]) -> Dict[str, str]:
    """
    Get status for multiple bots efficiently
    
    Args:
        guild: Discord guild object
        bot_ids: List of bot IDs to check
    
    Returns:
        Dict mapping bot_id to status
    """
    statuses = {}
    for bot_id in bot_ids:
        statuses[bot_id] = await check_bot_status(bot_id, guild)
    return statuses


def extract_mentions_from_text(text: str) -> List[str]:
    """
    Extract all Discord mentions from text
    
    Args:
        text: Text to search for mentions
    
    Returns:
        List of mention strings like ['<@1234567890>', '<@9876543210>']
    """
    return re.findall(r'<@!?\d+>', text)


async def filter_mentions_by_status(text: str, guild: discord.Guild, mention_dnd: bool = False, mention_offline: bool = False) -> str:
    """
    Filter out mentions based on bot status
    
    Args:
        text: Text containing mentions
        guild: Discord guild object
        mention_dnd: Whether to keep do_not_disturb mentions
        mention_offline: Whether to keep offline mentions
    
    Returns:
        Text with unavailable bot mentions removed or converted to plain text
    """
    mentions = extract_mentions_from_text(text)
    filtered_text = text
    
    for mention in mentions:
        should_mention = await should_mention_entity(mention, guild, mention_dnd, mention_offline)
        
        if not should_mention:
            # Extract bot ID and get member info for name
            bot_id_match = re.search(r'<@!?(\d+)>', mention)
            if bot_id_match:
                bot_id = bot_id_match.group(1)
                try:
                    member = guild.get_member(int(bot_id))
                    if member:
                        # Replace mention with plain name
                        status = await check_bot_status(bot_id, guild)
                        filtered_text = filtered_text.replace(mention, member.display_name)
                        logger.info(f"Filtered mention {mention} -> {member.display_name} (status: {status})")
                    else:
                        # Remove mention entirely
                        filtered_text = filtered_text.replace(mention, "").strip()
                        logger.info(f"Removed unknown mention {mention}")
                except Exception as e:
                    logger.warning(f"Failed to process mention {mention}: {e}")
                    # Remove mention as fallback
                    filtered_text = filtered_text.replace(mention, "").strip()
    
    return filtered_text


async def build_status_context(guild: discord.Guild, known_bot_ids: List[str]) -> str:
    """
    Build context string about bot availability for system prompt
    
    Args:
        guild: Discord guild object
        known_bot_ids: List of known bot IDs to check
    
    Returns:
        Formatted status context string
    """
    if not known_bot_ids:
        return ""
    
    statuses = await get_bot_statuses(guild, known_bot_ids)
    context_lines = []
    
    context_lines.append("Current bot availability in this server:")
    
    for bot_id, status in statuses.items():
        try:
            member = guild.get_member(int(bot_id))
            if member:
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
            logger.warning(f"Failed to get member info for {bot_id}: {e}")
    
    context_lines.append("")
    context_lines.append("Only mention available bots (not those in do-not-disturb/offline). If you want to reference unavailable bots, mention them by name only (no @tag).")
    
    return "\n".join(context_lines)


def configure_from_env(env_config: dict) -> dict:
    """
    Configure bot status coordination from environment variables
    
    Args:
        env_config: Dictionary of environment variables
    
    Returns:
        Configuration dictionary for bot status coordination
    """
    return {
        'enabled': env_config.get('BOT_STATUS_COORDINATION', 'false').lower() == 'true',
        'cache_seconds': int(env_config.get('STATUS_CHECK_CACHE_SECONDS', '30')),
        'mention_dnd': env_config.get('MENTION_DO_NOT_DISTURB_BOTS', 'false').lower() == 'true',
        'mention_offline': env_config.get('MENTION_OFFLINE_BOTS', 'false').lower() == 'true',
        'known_bots': env_config.get('KNOWN_BOT_IDS', '').split(',') if env_config.get('KNOWN_BOT_IDS') else []
    }


# Clear cache periodically to prevent memory leaks
def clear_old_cache_entries():
    """Clear cache entries older than cache duration"""
    global _status_cache, _cache_duration_seconds
    
    current_time = datetime.now()
    expired_keys = []
    
    for cache_key, (_, cache_time) in _status_cache.items():
        if current_time - cache_time > timedelta(seconds=_cache_duration_seconds * 2):
            expired_keys.append(cache_key)
    
    for key in expired_keys:
        del _status_cache[key]
    
    if expired_keys:
        logger.debug(f"Cleared {len(expired_keys)} expired cache entries")


async def log_startup_user_status(bot):
    """
    Log all visible humans and bots with their current status on startup
    
    Args:
        bot: Discord bot instance
    """
    try:
        total_humans = 0
        total_bots = 0
        status_counts = {
            'online': {'humans': 0, 'bots': 0},
            'idle': {'humans': 0, 'bots': 0},
            'do_not_disturb': {'humans': 0, 'bots': 0},
            'offline': {'humans': 0, 'bots': 0}
        }
        
        logger.info("=== Startup User Status Survey ===")
        
        for guild in bot.guilds:
            logger.info(f"Guild: {guild.name} ({guild.id}) - {len(guild.members)} members")
            
            guild_humans = []
            guild_bots = []
            
            for member in guild.members:
                if member.bot:
                    guild_bots.append(member)
                    total_bots += 1
                    status = str(member.status)
                    if status in status_counts:
                        status_counts[status]['bots'] += 1
                else:
                    guild_humans.append(member)
                    total_humans += 1
                    status = str(member.status)
                    if status in status_counts:
                        status_counts[status]['humans'] += 1
            
            # Log bots in this guild
            if guild_bots:
                logger.info(f"  Bots ({len(guild_bots)}):")
                for bot_member in sorted(guild_bots, key=lambda m: m.display_name.lower()):
                    status = str(bot_member.status)
                    status_emoji = {
                        'online': '🟢',
                        'idle': '🟡', 
                        'do_not_disturb': '🔴',
                        'offline': '⚫'
                    }.get(status, '❓')
                    logger.info(f"    {status_emoji} {bot_member.display_name} ({bot_member.id}) - {status}")
            
            # Log humans in this guild (summary only to avoid spam)
            if guild_humans:
                human_status_summary = {}
                for human in guild_humans:
                    status = str(human.status)
                    human_status_summary[status] = human_status_summary.get(status, 0) + 1
                
                summary_parts = []
                for status, count in human_status_summary.items():
                    emoji = {
                        'online': '🟢',
                        'idle': '🟡', 
                        'do_not_disturb': '🔴',
                        'offline': '⚫'
                    }.get(status, '❓')
                    summary_parts.append(f"{emoji}{count}")
                
                logger.info(f"  Humans ({len(guild_humans)}): {' '.join(summary_parts)}")
        
        # Log overall summary
        logger.info("=== Summary ===")
        logger.info(f"Total humans: {total_humans}")
        logger.info(f"Total bots: {total_bots}")
        
        for status, counts in status_counts.items():
            if counts['humans'] > 0 or counts['bots'] > 0:
                emoji = {
                    'online': '🟢',
                    'idle': '🟡', 
                    'do_not_disturb': '🔴',
                    'offline': '⚫'
                }.get(status, '❓')
                logger.info(f"{emoji} {status}: {counts['humans']} humans, {counts['bots']} bots")
        
        logger.info("=== End Status Survey ===")
        
    except Exception as e:
        logger.error(f"Failed to log startup user status: {e}")