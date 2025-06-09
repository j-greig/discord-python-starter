# Claude Code Deployment Notes

## Quick Deploy to Ploi Server

When working on this Discord bot, use these commands to deploy updates:

### On Ploi Server (ssh ploi@139.59.160.27)

```bash
cd ~/containers/discord_bot_scramble
sudo chown -R ploi:ploi .
git pull origin master
docker-compose down && docker-compose up -d --build
```

### Environment Setup

- Server repo points to: `https://github.com/j-greig/discord-python-scramble`
- Container directory: `~/containers/discord_bot_scramble`
- Environment file: `.env` (contains BOT_TOKEN, BOT_PROMPT, etc.)
- Key files: `prompt.md`, `examples.scramble.json`

### Development Workflow

1. Edit code locally in `/Users/james/Repos/discord-python-starter`
2. Push changes to private repo: `https://github.com/j-greig/discord-python-scramble`
3. SSH to server and run deploy commands above
4. Check Discord to verify bot is online

### Container Info

- Container name: `discord_bot_scramble`
- Runs: `python -u src/bot.py`
- Uses docker-compose.yml for configuration