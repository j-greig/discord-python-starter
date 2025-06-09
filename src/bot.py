"""
Discord Bot with Unified Enthusiasm Architecture
Streamlined bot implementation with optimized rate limiting and intelligent response detection.
"""

import logging
import os
import time
import discord
from datetime import datetime
from dotenv import load_dotenv
from honcho import Honcho

# Import processors
from processors.base_processor import ProcessorPipeline, MessageContext, get_honcho_user
from processors.unified_enthusiasm import UnifiedEnthusiasmProcessor
from processors.status_coordinator import StatusCoordinatorProcessor
from processors.llm_processor import LLMProcessor
from processors.response_handler import ResponseHandlerProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.ERROR)

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_NAME = os.getenv("APP_NAME")

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)

# Honcho setup
honcho_client = Honcho()
app = honcho_client.apps.get_or_create(name=APP_NAME)
logger.info(f"Honcho app acquired with id {app.id}")

# Initialize processor pipeline
pipeline = ProcessorPipeline()

# Initialize processors (simplified pipeline)
unified_enthusiasm = UnifiedEnthusiasmProcessor(honcho_client, app)
status_coordinator = StatusCoordinatorProcessor()
llm_processor = LLMProcessor(honcho_client, app)
response_handler = ResponseHandlerProcessor(honcho_client, app)

# Add to pipeline (minimal pipeline - most logic in unified processor)
pipeline.add_processor(unified_enthusiasm)

logger.info("Processor pipeline initialized")


@bot.event
async def on_ready():
    print(f"🤖 Bot logged in as {bot.user}")
    print(f"📊 Pipeline has {len(pipeline.processors)} active processors")
    
    # Run startup status survey
    await status_coordinator.on_startup(bot)
    
    # Start background status monitor
    bot.loop.create_task(background_status_monitor())
    
    print("⚡ Waiting for messages...")

async def background_status_monitor():
    """Background task to reset DND status when rate limits expire"""
    import asyncio
    
    try:
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            # Skip if status coordination disabled
            bot_status_coordination = os.getenv("BOT_STATUS_COORDINATION", "false").lower() == "true"
            if not bot_status_coordination:
                continue
                
            current_time = time.time()
            rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
            
            # Thread-safe copy of channel list to avoid race conditions
            channel_ids = list(_rate_timestamps.keys())
            any_currently_rate_limited = False
            
            # Check if ANY channel is currently rate limited
            for channel_id in channel_ids:
                if channel_id not in _rate_timestamps:
                    continue  # Channel removed while we were iterating
                    
                timestamps = _rate_timestamps[channel_id]
                
                # Count recent timestamps (thread-safe read)
                recent_count = sum(1 for t in timestamps if current_time - t <= 60)
                
                if recent_count >= rate_limit_per_minute:
                    any_currently_rate_limited = True
                    break
            
            # Only set online if NO channels are rate limited
            if not any_currently_rate_limited:
                try:
                    current_status = bot.guilds[0].me.status if bot.guilds else None
                    if current_status == discord.Status.do_not_disturb:
                        logger.info("🟢 Background monitor: No active rate limits, setting online")
                        await bot.change_presence(status=discord.Status.online)
                except Exception as e:
                    logger.warning(f"Background status check failed: {e}")
            
            # Cleanup empty channel entries to prevent memory growth
            empty_channels = [cid for cid, ts in _rate_timestamps.items() 
                            if not ts or all(current_time - t > 120 for t in ts)]
            for cid in empty_channels:
                _rate_timestamps.pop(cid, None)
                
            if empty_channels:
                logger.debug(f"🧹 Cleaned {len(empty_channels)} empty channel entries")
                
    except asyncio.CancelledError:
        logger.info("Background status monitor cancelled")
    except Exception as e:
        logger.error(f"Background status monitor fatal error: {e}")
        # Exit gracefully instead of infinite error loop


# Global rate limiting state
_rate_timestamps = {}  # channel_id -> list of timestamps

async def _is_rate_limited_quick(context: MessageContext) -> bool:
    """Quick rate limit check without creating processor"""
    rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    channel_id = context.channel.id
    current_time = time.time()
    
    # Get or create timestamp list for this channel
    if channel_id not in _rate_timestamps:
        _rate_timestamps[channel_id] = []
    
    timestamps = _rate_timestamps[channel_id]
    
    # Remove timestamps older than 1 minute
    old_count = len(timestamps)
    timestamps[:] = [t for t in timestamps if current_time - t <= 60]
    new_count = len(timestamps)
    
    # Check if rate limited
    rate_limited = new_count >= rate_limit_per_minute
    
    # If not rate limited and we had old timestamps (rate limit expired), set back to online
    if not rate_limited and old_count > new_count and old_count >= rate_limit_per_minute:
        logger.info(f"🟢 Rate limit expired - setting status back to online")
        await _set_online_status_quick(context)
    
    # Debug logging
    logger.info(f"🔍 Quick rate check: {new_count}/{rate_limit_per_minute} in last 60s, rate_limited={rate_limited}")
    if old_count != new_count:
        logger.info(f"🔍 Cleaned {old_count - new_count} old timestamps")
    
    return rate_limited

async def _set_dnd_status_quick(context: MessageContext) -> None:
    """Quick DND status setting without creating processor"""
    bot_status_coordination = os.getenv("BOT_STATUS_COORDINATION", "false").lower() == "true"
    if not bot_status_coordination:
        return
    
    try:
        # Calculate when rate limit will expire
        rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
        channel_id = context.channel.id
        
        if channel_id in _rate_timestamps and _rate_timestamps[channel_id]:
            # Find the oldest timestamp that will expire last
            current_time = time.time()
            oldest_timestamp = min(_rate_timestamps[channel_id])
            expire_time = oldest_timestamp + 60  # Rate limit window is 60 seconds
            
            # Format the expiry time
            from datetime import datetime, timezone
            expire_datetime = datetime.fromtimestamp(expire_time, tz=timezone.utc)
            expire_str = expire_datetime.strftime("%H:%M:%S")
            
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"cooldown until {expire_str}"
            )
        else:
            # Fallback if no timestamps
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="rate limit cooldown"
            )
        
        await bot.change_presence(status=discord.Status.do_not_disturb, activity=activity)
        logger.info(f"🔴 Set bot status to DND (rate limited - quick) - {activity.name}")
    except Exception as e:
        logger.warning(f"Error setting DND status: {e}")

async def _set_online_status_quick(context: MessageContext) -> None:
    """Quick online status setting when rate limit expires"""
    bot_status_coordination = os.getenv("BOT_STATUS_COORDINATION", "false").lower() == "true"
    if not bot_status_coordination:
        return
    
    try:
        await bot.change_presence(status=discord.Status.online)
        logger.info("🟢 Set bot status to ONLINE (rate limit expired)")
    except Exception as e:
        logger.warning(f"Error setting online status: {e}")

def _record_response_quick(channel_id: int):
    """Record response timestamp for rate limiting"""
    if channel_id not in _rate_timestamps:
        _rate_timestamps[channel_id] = []
    
    timestamp = time.time()
    _rate_timestamps[channel_id].append(timestamp)
    logger.info(f"📝 Recorded response timestamp for rate limiting: {len(_rate_timestamps[channel_id])} total")

def _record_response_with_timestamp(channel_id: int, timestamp: float):
    """Record specific timestamp for rate limiting (race condition prevention)"""
    if channel_id not in _rate_timestamps:
        _rate_timestamps[channel_id] = []
    
    _rate_timestamps[channel_id].append(timestamp)
    logger.info(f"📝 Committed response timestamp for rate limiting: {len(_rate_timestamps[channel_id])} total")


@bot.event
async def on_message(message):
    """
    Process messages using the unified enthusiasm processor pipeline.
    Simplified: UnifiedEnthusiasm → StatusCoordinator → LLM → ResponseHandler
    """
    try:
        # Create message context
        context = MessageContext(message, bot)
        
        logger.debug(f"📝 Processing message from {context.author} in #{context.channel.name}")
        
        # Step 0: Quick rate limit check FIRST (before any processing)
        if await _is_rate_limited_quick(context):
            logger.info("🛑 Rate limited - skipping all processing")
            await _set_dnd_status_quick(context)
            # Skip status coordinator to preserve custom timestamp
            return
        
        # Step 1: Pre-record response timestamp to prevent race conditions
        # (We'll only keep this if we actually decide to respond)
        temp_timestamp = time.time()
        
        # Step 2: Unified enthusiasm processing (validation, context, scoring)
        results = await pipeline.process(context)
        
        # Check if we should skip (unified processor handles early exits)
        unified_result = results.get("unified_enthusiasm", {})
        if unified_result.get("should_skip", False):
            skip_reason = unified_result.get("reason", "unknown")
            logger.debug(f"⏭️ Skipping message: {skip_reason}")
            # Don't record timestamp if we're not responding
            return
        
        # Step 3: Commit the response timestamp NOW (before any delays)
        _record_response_with_timestamp(context.channel.id, temp_timestamp)
        
        # Step 4: Update status (we're available to respond)
        await status_coordinator.process(context)
        
        # Step 4: Generate response
        enthusiasm_score = unified_result.get("enthusiasm_score", 0)
        topic_change = unified_result.get("topic_change", False)
        activities = unified_result.get("activities", [])
        verbose_prefix = unified_result.get("verbose_prefix", "")
        
        logger.info(f"🚀 Generating response (enthusiasm: {enthusiasm_score})")
        
        # Add topic change context to message context for LLM
        if topic_change and activities:
            context.set_data("topic_change_requested", True)
            context.set_data("topic_change_activity", activities[0])  # Use first activity as conversation starter
        
        async with message.channel.typing():
            response = await llm_processor.process(context)
            
        # Step 5: Add verbose prefix if enabled
        if verbose_prefix:
            response = verbose_prefix + response
        
        # Step 6: Send response
        await response_handler.process(context, response)
        
        logger.info("✅ Message processing complete")
        
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        # Log only - no Discord message sent


@bot.slash_command(
    name="test_enthusiasm",
    description="Test enthusiasm scoring for the last message without responding"
)
async def test_enthusiasm(ctx):
    """Test command to see enthusiasm scores without generating responses"""
    await ctx.defer()
    
    try:
        # Get the last message (excluding the slash command)
        last_message = None
        async for msg in ctx.channel.history(limit=10):
            if msg.id != ctx.interaction.id and not msg.content.startswith('/'):
                last_message = msg
                break
        
        if not last_message:
            await ctx.followup.send("❌ No recent message found to test")
            return
        
        # Build context and test unified enthusiasm processing
        context = MessageContext(last_message, bot)
        
        # Run unified enthusiasm processing
        result = await unified_enthusiasm.process(context)
        
        # Extract results
        should_skip = result.get("should_skip", False)
        skip_reason = result.get("reason", "none")
        enthusiasm_score = result.get("enthusiasm_score", 0)
        
        # Get debug info from unified result
        reasoning = result.get("reasoning", "No reasoning available")
        threshold = int(os.getenv("ENTHUSIASM_THRESHOLD", "5"))
        
        # Format response  
        would_respond = not should_skip and enthusiasm_score >= threshold
        
        response = f"""**🧪 Enthusiasm Test Results**
        
**Message**: `{last_message.content[:100]}...` (from {last_message.author.mention})

**Basic Filtering**: {'❌ Skip' if should_skip else '✅ Process'} ({skip_reason})
**Enthusiasm Score**: {enthusiasm_score}/9 (threshold: {threshold})
**Final Decision**: {'✅ RESPOND' if would_respond else '❌ NO RESPONSE'}

**Raw Analysis**: 
```{reasoning}```
"""
        
        await ctx.followup.send(response)
        
    except Exception as e:
        logger.error(f"Error in test_enthusiasm: {e}")
        await ctx.followup.send(f"❌ Error testing enthusiasm: {str(e)}")


@bot.slash_command(
    name="processor_status", 
    description="Show status of all processors"
)
async def processor_status(ctx):
    """Show which processors are enabled and their configuration"""
    await ctx.defer()
    
    try:
        status_lines = ["**🔧 Processor Status**\n"]
        
        # Check each processor (simplified pipeline)
        processors_to_check = [
            ("Unified Enthusiasm", unified_enthusiasm),
            ("Status Coordinator", status_coordinator),
            ("LLM Processor", llm_processor),
            ("Response Handler", response_handler),
        ]
        
        for name, processor in processors_to_check:
            enabled = "✅ Enabled" if processor.is_enabled() else "❌ Disabled"
            status_lines.append(f"**{name}**: {enabled}")
        
        # Add configuration info
        status_lines.append(f"\n**Configuration:**")
        status_lines.append(f"• Enthusiasm Threshold: {os.getenv('ENTHUSIASM_THRESHOLD', '5')}")
        status_lines.append(f"• Enthusiasm Model: {os.getenv('ENTHUSIASM_MODEL', 'claude-3-haiku-20240307')}")
        status_lines.append(f"• Rate Limit: {os.getenv('RATE_LIMIT_PER_MINUTE', '1')}/minute")
        status_lines.append(f"• API Provider: {os.getenv('API_PROVIDER', 'anthropic')}")
        
        await ctx.followup.send("\n".join(status_lines))
        
    except Exception as e:
        logger.error(f"Error in processor_status: {e}")
        await ctx.followup.send(f"❌ Error getting processor status: {str(e)}")


@bot.slash_command(
    name="boring",
    description="Trigger topic change by simulating a boring conversation complaint"
)
async def boring_command(ctx):
    """Test command to trigger topic change behavior"""
    await ctx.defer()
    
    try:
        # Create a fake message with boredom trigger
        class FakeMessage:
            def __init__(self):
                self.author = ctx.author
                self.content = "this conversation is boring"
                self.id = 999999999
                self.channel = ctx.channel
                self.guild = ctx.guild
                self.mentions = []
                self.mention_everyone = False
                self.created_at = datetime.now()
        
        fake_message = FakeMessage()
        test_context = MessageContext(fake_message, bot)
        
        # Run unified enthusiasm processing
        result = await unified_enthusiasm.process(test_context)
        
        # Check if topic change was triggered
        topic_change = result.get("topic_change", False)
        activities = result.get("activities", [])
        reasoning = result.get("reasoning", "No reasoning")
        
        if topic_change and activities:
            response = f"""🎲 **Topic Change Triggered!**
            
**Boredom Detection**: ✅ Working
**Random Activity**: {activities[0]}
**All Activities**: {', '.join(activities)}

**LLM Reasoning**: 
```{reasoning}```

The bot would now pivot the conversation using "{activities[0]}" as a conversation starter."""
        else:
            response = f"""❌ **Topic Change Not Triggered**
            
**Boredom Detection**: Failed to detect "boring" trigger
**Activities Generated**: {len(activities)} activities
**Reasoning**: {reasoning}

Debug: topic_change={topic_change}, activities={activities}"""
        
        await ctx.followup.send(response)
        
    except Exception as e:
        logger.error(f"Error in boring command: {e}")
        await ctx.followup.send(f"❌ Error testing boredom detection: {str(e)}")


@bot.slash_command(
    name="discord_context",
    description="Show current Discord context (server, channel, entities)"  
)
async def discord_context_command(ctx):
    """Display the Discord context that the bot sees"""
    await ctx.defer()
    
    try:
        # Build dummy context to extract Discord info  
        message = ctx.interaction
        dummy_context = MessageContext(message, bot)
        
        # Extract Discord context using unified processor
        discord_info = await unified_enthusiasm._get_discord_context(dummy_context)
        
        # Format response
        response = ["**📍 Discord Context Information**\n"]
        
        # Server info
        server = discord_info['server']
        response.append(f"**Server**: {server['name']}")
        if server['description']:
            response.append(f"**Description**: {server['description']}")
        response.append(f"**Members**: {discord_info['presence']['total_online']}/{server['member_count']} online\n")
        
        # Channel info
        channel = discord_info['channel']
        response.append(f"**Channel**: #{channel['name']}")
        if channel['topic']:
            response.append(f"**Topic**: {channel['topic']}\n")
        
        # Entities
        entities = discord_info['entities']
        response.append(f"**🤖 Symbients ({len(entities['symbients'])}):**")
        for bot_entity in entities['symbients'][:5]:  # Limit to 5
            response.append(f"• {bot_entity['name']} ({bot_entity['status']}) - `{bot_entity['mention']}`")
        
        response.append(f"\n**👥 Humans ({len(entities['humans'])}):**")  
        for human in entities['humans'][:10]:  # Limit to 10
            roles = human.get('roles', [])
            role_str = f" [{', '.join(roles[:2])}]" if roles else ""
            response.append(f"• {human['name']} ({human['status']}){role_str} - `{human['mention']}`")
        
        await ctx.followup.send("\n".join(response))
        
    except Exception as e:
        logger.error(f"Error in discord_context command: {e}")
        await ctx.followup.send(f"❌ Error getting Discord context: {str(e)}")


# Keep existing slash commands from original bot.py
@bot.slash_command(
    name="force_online",
    description="Force bot status back to online (emergency fix for stuck DND mode)"
)
async def force_online(ctx):
    """Emergency command to force bot status back to online"""
    await ctx.defer()
    try:
        # Show current state first
        current_state = f"DND={status_coordinator._is_rate_limited}"
        if status_coordinator._last_status_change:
            time_since = datetime.now() - status_coordinator._last_status_change
            current_state += f", stuck for {time_since.total_seconds():.1f}s"
        
        # Force back to online
        await status_coordinator._update_bot_status(bot, False)
        status_coordinator._is_rate_limited = False
        status_coordinator._last_status_change = datetime.now()
        
        await ctx.followup.send(f"/ᐠ｡ꞈ｡ᐟ\ forced online! was: {current_state} - using robust per-message recovery now!")
    except Exception as e:
        await ctx.followup.send(f"❌ /ᐠ｡×｡ᐟ\ failed: {e}")


@bot.slash_command(
    name="restart",
    description="Reset all of your messaging history with Honcho in this channel.",
)
async def restart(ctx):
    logger.info(f"Restarting conversation for {ctx.author.name}")
    async with ctx.typing():
        # Use the same logic as original bot
        user = get_honcho_user(honcho_client, app.id, ctx.author)
        
        from honcho_utils import get_session
        location_id = str(ctx.channel_id)
        session, _ = get_session(
            honcho_client, app.id, user.id, {location_id: True}, create=True
        )

        if session:
            honcho_client.apps.users.sessions.delete(
                app_id=app.id, user_id=user.id, session_id=session.id
            )

    await ctx.respond("The conversation has been restarted.")


if __name__ == "__main__":
    bot.run(BOT_TOKEN)