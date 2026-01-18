# Cuesync - Maestro Deployment Node

**Dumb executor that runs Maestro cuesheets on schedule.**

---

## What This Is

A minimal deployment wrapper for [Maestro](https://github.com/nickcottrell/maestro):

- **Flat file schedule** (`config.yaml`) - Edit to change what runs when
- **Auto-sync** - Pulls maestro updates every 30 minutes (adjustable)
- **Cron-based** - Simple, reliable scheduling
- **Dumb executor** - No logic, just pull and run

---

## Architecture

```
cuesync/
├── config.yaml        # Schedule configuration (EDIT THIS)
├── hooks              # Simple management commands
├── setup.sh           # One-time server setup
├── sync.sh            # Auto-pull and update cron
├── .env.example       # Secrets template
├── logs/              # Execution logs
│   └── archive/       # Archived logs (7+ days)
└── maestro/           # Git submodule → dev repo
    └── (pulled automatically)
```

---

## Quick Setup

### 1. Deploy to Server ($5/month AWS Lightsail)

```bash
# SSH to server
ssh ubuntu@your-server

# Clone cuesync repo
git clone --recursive https://github.com/3dmath/cuesync.git
cd cuesync

# Run one-time setup
chmod +x setup.sh sync.sh
./setup.sh
```

### 2. Configure Secrets

Edit `.env` with your API credentials:

```bash
nano .env
```

Fill in:
- Upwork API keys
- Zapier webhook URLs
- Preferences

### 3. Done

Server is now:
- ✅ Auto-syncing maestro code every 30 minutes (adjustable in config.yaml)
- ✅ Running cuesheets on schedule (from `config.yaml`)
- ✅ Logging to `logs/`

---

## Change Schedule

Edit `config.yaml`:

```yaml
cuesheets:
  - name: morning-workflow
    schedule: "0 8 * * *"  # Changed to 8am
    enabled: true
```

Commit and push:

```bash
git add config.yaml
git commit -m "Change morning-workflow to 8am"
git push
```

**Server auto-pulls and regenerates cron within 30 minutes** (adjustable in config.yaml).

---

## Change Cuesheets

Work in the [maestro repo](https://github.com/nickcottrell/maestro):

```bash
# On your laptop
cd ~/repos/maestro
# Make changes with Claude Code
git push
```

**Server auto-pulls within 30 minutes** (adjustable in config.yaml).

---

## Manual Operations

```bash
# SSH to server
ssh ubuntu@your-server
cd cuesync

# Force sync now
./sync.sh

# Check what's scheduled next
./hooks list-next

# View recent log for a cuesheet
./hooks view-log morning-workflow

# Archive old logs (7+ days)
./hooks archive-logs

# Check overall status
./hooks status

# Check cron jobs
crontab -l

# Test cuesheet manually
cd maestro
./hooks run morning-workflow --dry-run
```

---

## Files

### `config.yaml` - The Schedule

Flat file that controls everything:

- Sync interval (how often to pull updates)
- Cuesheet schedules (what runs when)
- Enable/disable cuesheets

**Edit this file to change timing.**

### `setup.sh` - One-Time Setup

Run once on fresh server:

- Installs dependencies
- Clones maestro submodule
- Sets up Python environment
- Configures secrets
- Generates initial cron

### `sync.sh` - Auto-Pull Script

Runs every 30 minutes (via cron, adjustable in config.yaml):

- Pulls latest cuesync config
- Pulls latest maestro code
- Regenerates cron from `config.yaml`

**You rarely need to run this manually.**

### `hooks` - Management Commands

Simple commands for deployment node:

- `./hooks list-next` - Show next scheduled executions
- `./hooks view-log <name>` - View recent log for a cuesheet
- `./hooks archive-logs` - Archive logs older than 7 days
- `./hooks status` - Show overall deployment status

**Dumb and simple. No magic.**

### `.env` - Secrets

API keys and credentials:

- Upwork API keys
- Zapier webhooks
- Preferences

**Gitignored. Never commit.**

---

## Log Management

**Execution Logs:**
- All cuesheet executions log to `logs/<cuesheet-name>.log`
- Sync operations log to `logs/sync.log`
- Logs grow indefinitely until archived

**Archive Strategy:**
- Run `./hooks archive-logs` to archive logs older than 7 days
- Archives saved to `logs/archive/logs-<timestamp>.tar.gz`
- Original logs deleted after archiving
- Recommend running archive weekly or monthly

**View Logs:**
```bash
./hooks view-log morning-workflow  # Last 50 lines
./hooks status                      # Overall status + recent files
tail -f logs/morning-workflow.log  # Live tail
```

---

## Infrastructure

**Recommended: AWS Lightsail $5/month**

- Ubuntu 22.04 LTS
- 512 MB RAM
- 20 GB SSD
- Static IP

**Setup:**

1. Create Lightsail instance
2. SSH to server
3. Clone cuesync repo
4. Run `./setup.sh`

**That's it.**

---

## Why This is Minimal

- **4 core files** (config.yaml, hooks, setup.sh, sync.sh)
- **1 server** ($5/month)
- **Flat file schedule** (no complex config)
- **Git pull** (no deployment pipeline)
- **Cron** (no Lambda, no EventBridge)
- **Simple hooks** (4 commands, no magic)
- **Dumb logging** (append to files, archive when old)

---

## Workflow Summary

### Development (Maestro Repo)

```bash
# Work here with Claude Code
cd maestro
# Edit cuesheets, filters, templates
git push
# Server pulls within 30 min (or next sync interval)
```

### Schedule Changes (Cuesync Repo)

```bash
# Edit timing
nano config.yaml
git push
# Server regenerates cron within 30 min (or next sync interval)
```

### Deployment (Server)

```bash
# Runs automatically via cron
# No manual intervention needed
# Just monitor logs
```

---

## Related Repositories

- **Maestro**: https://github.com/nickcottrell/maestro (development repo)
- **Cuesync**: https://github.com/3dmath/cuesync (this repo - deployment)

---

## Status

**Production ready for:**
- ✅ Scheduled cuesheet execution
- ✅ Auto-sync from dev repo
- ✅ Flat file schedule management

**Future enhancements:**
- Email notifications on failure
- Health check endpoint
- Multiple maestro branches (staging/prod)

---

**Cuesync is intentionally dumb. No logic. Just pull and run.**

**Last Updated**: 2026-01-18