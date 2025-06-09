## Discord Bot Docker Deployment Guide

### Pre-deployment Checklist

- [ ] Ensure VPS has Docker installed
- [ ] Configure firewall to allow Discord bot traffic
- [ ] Have all required API keys ready

### Required Files

1. Application Files:
   - [ ] src/ directory
   - [ ] prompt.md
   - [ ] examples.json/examples.scramble.json
   - [ ] pyproject.toml
   - [ ] uv.lock
   - [ ] Dockerfile
   - [ ] .dockerignore

2. Environment Setup:
   - [ ] Create production .env file with all required variables
   - [ ] Ensure all API keys are valid
   - [ ] Set DEBUG_LOGGING=false for production

### Deployment Steps

1. **Server Setup**
   ```bash
   # Update system
   apt update && apt upgrade -y
   
   # Install Docker if not already installed
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

2. **Application Deployment**
   ```bash
   # Create deployment directory
   mkdir -p /opt/discord-bot
   cd /opt/discord-bot
   
   # Copy all required files to the server
   # (Use scp, git clone, or your preferred method)
   
   # Create production .env file
   cp .env.template .env
   nano .env  # Edit with production values
   
   # Build Docker image
   docker build -t discord-bot .
   
   # Run container
   docker run -d \
     --name discord-bot \
     --restart unless-stopped \
     --env-file .env \
     discord-bot
   ```

3. **Verification**
   ```bash
   # Check container logs
   docker logs discord-bot
   
   # Monitor container status
   docker ps
   ```

### Maintenance Commands

```bash
# Stop bot
docker stop discord-bot

# Start bot
docker start discord-bot

# View logs
docker logs -f discord-bot

# Rebuild and restart (after updates)
docker build -t discord-bot .
docker stop discord-bot
docker rm discord-bot
docker run -d --name discord-bot --restart unless-stopped --env-file .env discord-bot
```

### Troubleshooting

1. Check container logs:
   ```bash
   docker logs discord-bot
   ```

2. Check container status:
   ```bash
   docker ps -a | grep discord-bot
   ```

3. Common issues:
   - Invalid environment variables
   - Discord bot token issues
   - Network connectivity problems
   - API rate limiting

### Monitoring

- [ ] Set up Docker container monitoring
- [ ] Configure log rotation
- [ ] Set up alerts for container down events 