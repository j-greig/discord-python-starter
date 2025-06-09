# discord-python-starter

A starter template for making discord bots with
[Honcho](https//github.com/plastic-labs/honcho) that are deployed to fly.io

The main logic for the discord bot is in the `bot.py` file. It contains 2
functions.

- `on_message` — the event that is run when a message is sent to the server
  the bot is in
- `restart` — A discord slash command called restart. It is used to close the
  `session` and create a new one

The template uses [openrouter](https://openrouter.ai) for LLM inferences and
supports all the LLMs on there

## Getting Started

First, install the dependencies for the project.

```bash
uv sync
```

From here you can edit the `bot.py` file to add whatever logic you want for the
3 methods described above. Additional functionality can be added to the bot.
Refer to the [py-cord documentation](https://pycord.dev)

### Environment Variables

The repo contains a `.env.template` file that shows all the default environment
variables used by the discord bot. Make a copy of this template and fill out the
`.env` with your own values.

```bash
cp .env.template .env
```

#### Bot Prompt

The bot supports two ways of defeining custom prompts via the `BOT_PROMPT` environment variable:

- **File-based**: Set `BOT_PROMPT=prompt.md` to load character definitions from `prompt.md`
- **Inline**: Set `BOT_PROMPT="Your custom prompt text"` for simple prompts

> [!CAUTION]
> Make sure you do not push your `.env` file to GitHub or any other version
> control. These should remain secret. By default the included `.gitignore` file
> should prevent this.


### Run locally

```bash
source .venv/bin/activate
python src/bot.py
```

### Docker

The project offers [Docker](https://www.docker.com/) for packaging the bot code
and providing a single executable to start the bot. The below commands will
build the docker image and then run the bot using a local `.env` file.

```bash
docker build -t discord-bot . && docker run --env-file .env discord-bot
```

For development, add `--rm` to automatically clean up the container when it stops:

```bash
docker build -t discord-bot . && docker run --rm --env-file .env discord-bot
```

## Deployment

### Fly.io (Default)

The project contains a generic `fly.toml` that will run a single process for the
discord bot.

To launch the bot for the first time, run `fly launch`.
Use `cat .env | fly secrets import` to add the environment variables to fly.

**By default, `fly.toml` will automatically stop the machine if inactive. This
doesn't work well with a discord bot, so remove that line and change `min_machines_running` to `1`.**

After launching, use `fly deploy` to update your deployment.

### Ploi/Docker Compose

#### Complete Ploi Setup Guide

**1. Create Discord Application**
- Go to Discord Developer Portal and create new application
- Create bot and copy the BOT_TOKEN
- Invite bot to your Discord server with appropriate permissions

**2. Set up Ploi Docker Application**
- In Ploi dashboard: Servers → Your Server → Docker → Applications
- Click "Create application" 
- Enter application name (e.g., `discord_bot_wibwob`)
- Save (this creates the container directory structure)

**3. Set up SSH access from server to GitHub**
- SSH to your server: `ssh ploi@your-server-ip`
- Generate SSH key: `ssh-keygen -t ed25519 -C "ploi@server"`
- Add public key to GitHub: `cat ~/.ssh/id_ed25519.pub`
- Copy output and add to GitHub → Settings → SSH keys

**4. Clone repository**
```bash
cd ~/containers/your_app_name
sudo chown -R ploi:ploi .
git clone git@github.com:your-username/your-repo.git .
```

**5. Set up environment file**
```bash
nano .env
```
Add your bot configuration:
```
BOT_TOKEN=your-unique-bot-token-here
BOT_PROMPT=prompt.md
BOT_NAME=YourBotName
# ... other variables
```

**6. Deploy the bot**
```bash
docker-compose up -d --build
```

**7. Verify deployment**
- Check Ploi → Docker → Status tab for running containers
- Verify bot is online in Discord
- Check logs if needed: `docker-compose logs -f`

#### Quick Deploy Commands

After initial setup, use these commands for updates:
```bash
cd ~/containers/your_app_name
sudo chown -R ploi:ploi .
git pull origin master
docker-compose down && docker-compose up -d --build
```

#### Important Notes
- Each bot needs its own Discord application and BOT_TOKEN
- Don't use `sudo` with git commands (breaks SSH key access)
- Use SSH clone URLs (`git@github.com:...`) not HTTPS
- Ensure docker-compose.yml has correct environment variables
