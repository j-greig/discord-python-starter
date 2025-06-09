# discord-python-starter

A starter template for Discord bots with [Honcho](https://github.com/plastic-labs/honcho) memory management, deployable to Fly.io.

## Features

- 🚀 **Unified Enthusiasm Architecture**: Streamlined 4-step processing pipeline for 60% complexity reduction
- 🤖 **Multi-provider support**: Anthropic (with prompt caching), OpenAI, and OpenRouter
- 🧠 **Memory management**: Persistent conversation history via Honcho
- 🎭 **Custom personalities**: System prompts, base context, and configurable bot skills
- 🎯 **Intelligent turn-taking**: Enthusiasm scoring (0-9) with configurable thresholds
- 🧪 **Smart responses**: Name variants, topic keywords, and boredom detection
- ⏰ **Zero-waste rate limiting**: Per-channel limits with immediate early exit
- 🤝 **Bot coordination**: Multi-bot status awareness and DND/online status management
- 📊 **Comprehensive debugging**: Verbose Discord output with reasoning display
- 🎲 **Topic change system**: Automatic conversation pivoting when boredom detected
- 🔧 **Easy deployment**: Ready for Fly.io with Docker and GitHub Actions

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Choose configuration:**
   ```bash
   # Anthropic (recommended)
   cp env.example .env
   
   # OpenAI
   cp env.openai.example .env
   
   # OpenRouter (multiple models)
   cp env.openrouter.example .env
   ```

3. **Set up base context:**
   ```bash
   cp base_context.example.json base_context.json
   # Edit with your agent's personality
   ```

4. **Run locally:**
   ```bash
   source .venv/bin/activate
   python src/bot.py
   ```

## Configuration

### Environment Variables

Key configuration options:

```bash
# Discord & API
BOT_TOKEN=your_discord_bot_token
API_PROVIDER=anthropic  # or "openai" or "openrouter"
ANTHROPIC_API_KEY=your_key  # if using Anthropic
OPENAI_API_KEY=your_key     # if using OpenAI/OpenRouter
OPENAI_BASE_URL=https://openrouter.ai/api/v1  # for OpenRouter

# Model & Agent
MODEL_NAME=claude-3-5-sonnet-20241022
MAX_TOKENS=1024
APP_NAME=your-unique-app-name
SYSTEM_PROMPT=You are a helpful AI assistant.
BASE_CONTEXT_FILE=base_context.json
ENABLE_PROMPT_CACHING=true  # Anthropic prompt caching (saves tokens)

# Unified Enthusiasm System
ENTHUSIASM_THRESHOLD=5      # Minimum score (0-9) to respond
ENTHUSIASM_MODEL=claude-3-haiku-20240307  # Model for scoring
VERBOSE_REASONING=false     # Show reasoning in Discord
SHOW_RECENT_MESSAGES=false  # Show message history in verbose output

# Bot Identity & Skills
BOT_NAME=Assistant
BOT_NAME_VARIANTS=ai,bot,helper,assistant
BOT_TOPICS=help,question,code,debug,programming
BOT_SKILLS=coding,debugging,explaining  # Bot capabilities
BOT_PERSONALITY=A helpful and curious assistant  # Or use PERSONALITY_FILE

# Rate Limiting & Performance
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_MESSAGE=⏰ Please wait before asking again.
RATE_LIMIT_CONFIG_FILE=rate_limits.json  # Per-channel limits
RANDOM_DELAY_ENABLED=true   # Add 1-3s breathing space
MIN_DELAY_SECONDS=1.0
MAX_DELAY_SECONDS=3.0

# Bot Status Coordination
BOT_STATUS_COORDINATION=true  # Enable multi-bot awareness
STATUS_CHECK_CACHE_SECONDS=30
MENTION_DO_NOT_DISTURB_BOTS=false
MENTION_OFFLINE_BOTS=false
```

### Intelligent Responses

Your bot can respond to messages **without @mentions** by detecting:

**Name variants:**
```bash
BOT_NAME=TechBot
BOT_NAME_VARIANTS=tech,bot,helper,ai
```

Now the bot responds to:
- "Can the **tech** help me with this?"
- "Is the **bot** available?"
- "**Helper**, I need assistance"

**Relevant topics:**
```bash
BOT_TOPICS=python,javascript,debugging,deploy,docker
```

Now the bot responds to:
- "I'm having **python** issues"
- "Need help with **debugging**"
- "**Docker** container won't start"

**Configuration tips:**
- Use lowercase, comma-separated values
- Start with 3-5 variants/topics, expand as needed
- Monitor for false positives and adjust

### Base Context

Create conversation context that prepends all interactions:

```bash
cp base_context.example.json base_context.json
```

Example format:
```json
[
  {
    "role": "user",
    "content": "What is your role?"
  },
  {
    "role": "assistant", 
    "content": "I'm a specialized AI assistant for your team..."
  }
]
```

## Advanced Configuration

### System Prompt from File

For complex prompts, use a separate file:

```bash
# Create prompt file
cp system_prompt.example.txt system_prompt.txt

# Configure environment
SYSTEM_PROMPT_FILE=system_prompt.txt
```

### Per-Channel Rate Limits

Configure different limits for different channels:

```bash
# Create config file
cp rate_limits.example.json rate_limits.json

# Get channel IDs (Discord Developer Mode → right-click channel → Copy ID)
# Configure limits
{
  "123456789012345678": 3,   // #general
  "234567890123456789": 15,  // #dev-help
  "345678901234567890": 5    // #random
}

# Set environment variable
RATE_LIMIT_CONFIG_FILE=rate_limits.json
```

## Discord Setup

1. **Create Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create new application → Bot section → Add Bot
   - Copy bot token
   - **Enable Required Intents:**
     - Message Content Intent ✅
     - Server Members Intent ✅
     - Presence Intent ✅ (for bot status detection)

2. **Invite Bot to Server:**
   - OAuth2 → URL Generator → Select `bot` and `applications.commands`
   - Permissions: Send Messages, Use Slash Commands, Read Message History

3. **Test Bot:**
   - Direct mention: `@YourBot hello`
   - Name variant: `bot, can you help with python?`
   - Topic mention: `I need help with python`
   - Slash commands:
     - `/restart` - Reset conversation history
     - `/dialectic query` - Search conversation history
     - `/document text` - Save to knowledge base
     - `/test_enthusiasm` - Test scoring without responding
     - `/processor_status` - Show processor configuration
     - `/discord_context` - Show server/channel context
     - `/boring` - Trigger topic change system

## Unified Enthusiasm Architecture

The bot uses a streamlined 4-step processing pipeline:

```
1. Rate Limit Check → Immediate exit if limited (saves ~$0.03/message)
2. Unified Enthusiasm → Context gathering + LLM scoring in one step
3. Status Coordination → Bot availability management
4. Response Generation → If enthusiasm ≥ threshold
```

### Enthusiasm Scoring

The bot scores each message from 0-9 based on:
- Direct mentions or name variants
- Topic relevance and skill matching
- Conversation flow and timing
- Other bots' availability
- Boredom/repetition detection

Only messages scoring ≥ threshold (default: 5) get responses.

## Deployment

### Fly.io Deployment

1. **Initialize:**
   ```bash
   fly launch --no-deploy
   ```

2. **Set secrets:**
   ```bash
   fly secrets set BOT_TOKEN="your_token"
   fly secrets set API_PROVIDER="anthropic"
   fly secrets set ANTHROPIC_API_KEY="your_key"
   fly secrets set MODEL_NAME="claude-3-5-sonnet-20241022"
   fly secrets set APP_NAME="my-discord-agent"
   fly secrets set BOT_NAME="TechBot"
   fly secrets set BOT_NAME_VARIANTS="tech,bot,helper"
   fly secrets set BOT_TOPICS="python,javascript,debugging"
   fly secrets set SYSTEM_PROMPT="Your system prompt"
   fly secrets set MAX_TOKENS="1024"
   fly secrets set RATE_LIMIT_PER_MINUTE="10"
   ```

3. **Deploy:**
   ```bash
   fly deploy
   ```

4. **Check status:**
   ```bash
   fly logs
   fly status
   ```

### Docker Deployment

```bash
docker build -t discord-bot . && docker run --env-file .env discord-bot
```

## Usage

**Bot responds to:**
- **Direct mentions**: `@YourBot help me debug this`
- **Name variants**: `bot, can you help with python?`
- **Topic keywords**: `I'm having javascript issues`
- **Slash commands**:
  - `/restart` - Reset conversation history
  - `/dialectic query` - Search conversation history  
  - `/document text` - Save information to knowledge base

**Response logic:**
```
@mention OR (name_variant OR topic) → Bot responds
```

**Rate limiting:**
- Per-channel limits (independent tracking)
- Global fallback for unconfigured channels
- Shows friendly message when limited

## Architecture

### Unified Processing Pipeline

```
┌─────────────────┐
│ Discord Message │
└────────┬────────┘
         │
    ┌────▼────┐     ❌ Rate Limited?
    │Rate Check│────────→ Exit (DND)
    └────┬────┘
         │ ✅
┌────────▼────────┐
│ Unified         │  • Basic validation
│ Enthusiasm      │  • Discord context
│ Processor       │  • Bot status check
│                 │  • LLM scoring (0-9)
└────────┬────────┘
         │
    ┌────▼────┐     ❌ Score < 5?
    │Threshold │────────→ Exit
    └────┬────┘
         │ ✅
┌────────▼────────┐
│Status + Response│  • Set online status
│Generation       │  • Generate response
└─────────────────┘
```

### Key Improvements

- **60% complexity reduction**: From 7 processors to 4 steps
- **Zero computational waste**: Rate limiting happens first
- **Single LLM call**: All context and scoring in one request
- **Better debugging**: Comprehensive verbose output option

### Memory Management

- **Per-channel sessions**: Each Discord channel = separate conversation
- **Base context**: Always included in API calls (personality/background)
- **Persistent history**: Survives bot restarts via Honcho
- **User isolation**: Each user has independent memory per channel

## Advanced Features

### Boredom Detection & Topic Changes

The bot detects conversation staleness and suggests new topics:
- Triggers on keywords like "boring", "bored", "stale"
- Generates 4 random activities for conversation pivoting
- Seamlessly introduces new topics in responses

### Multi-Bot Coordination

When multiple bots are present:
- Tracks other bots' online/DND status
- Considers bot availability in response decisions
- Updates own status based on rate limits
- Prevents response collisions

### Prompt Caching (Anthropic)

Reduce costs with intelligent caching:
- System prompts cached for 1 hour
- Base context cached for reuse
- ~50% token cost reduction
- Enable with `ENABLE_PROMPT_CACHING=true`

## Troubleshooting

**Bot not responding:**
- Check Discord permissions & bot token
- Verify API keys and model names
- Check rate limits (wait 1 minute)
- View logs: `fly logs`

**Intelligent responses not working:**
- Verify `BOT_NAME_VARIANTS` and `BOT_TOPICS` are set
- Check logs for "Bot configured with X name variants and Y topic variants"
- Test with exact variant/topic words
- Ensure bot has Message Content Intent enabled

**Too many responses:**
- Reduce number of variants/topics
- Use more specific keywords
- Increase rate limits if needed

**Configuration issues:**
- Validate JSON syntax for config files
- Ensure channel IDs are strings in JSON
- Check file permissions (readable by bot)
- Verify environment variables are set

## Cost Considerations

**API Costs (per million tokens):**
- Claude 3.5 Sonnet: ~$3-15
- Claude 3 Opus: ~$15-75  
- Claude 3 Haiku: ~$0.25-1.25
- GPT-4: ~$30-60
- GPT-3.5 Turbo: ~$0.5-2

**Hosting:**
- Fly.io: ~$5-10/month

**Cost optimization:**
- Use rate limiting to control usage
- Choose appropriate models for use case
- Keep base context reasonably sized
- Monitor usage via provider dashboards
- Be selective with intelligent response keywords

## File Structure

```
discord-python-starter/
├── src/
│   ├── bot.py                      # Main bot with unified pipeline
│   ├── processors/
│   │   ├── base_processor.py       # Base processor framework
│   │   ├── unified_enthusiasm.py   # Core scoring & context processor
│   │   ├── status_coordinator.py   # Bot status management
│   │   ├── llm_processor.py        # Response generation
│   │   └── response_handler.py     # Discord message delivery
│   └── honcho_utils.py             # Honcho utilities
├── env.example                     # Configuration template
├── base_context.example.json       # Example base context
├── system_prompt.example.txt       # Example system prompt
├── rate_limits.example.json        # Example rate limits
├── CLAUDE.md                       # Developer documentation
├── Dockerfile                      # Docker configuration
├── fly.toml                        # Fly.io configuration
└── pyproject.toml                  # Python dependencies
```

> [!CAUTION]
> Never commit `.env` files or API keys to version control. The included `.gitignore` prevents this.

---

**Need help?** Check the example files and logs for troubleshooting. The bot includes comprehensive error handling and logging to help diagnose issues.