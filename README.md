# CueSync - Minimal, Secure Cue Relay

**Simple, dumb job queue that relays authenticated payloads to Zapier webhooks.**

---

## What CueSync Is

CueSync is a **minimal relay** with one job:

1. Accept authenticated CUESHEET payloads from upstream (Cue Dispatcher)
2. Store them in SQLite
3. Execute each one ONCE by sending its payload to its specified webhook
4. Mark as executed (never runs again)
5. Expire after configured lifetime

**CueSync does NOT:**
- Make decisions about what to execute
- Understand what the payload means
- Schedule cuesheets (that's Cue Dispatcher's job)
- Execute complex operations (that's Zapier's job)

**CueSync is intentionally dumb. It only validates, stores, and relays.**

---

## Quick Start with Hooks

CueSync provides a unified `hooks` script for all operations:

```bash
# Check server health
./hooks health

# View statistics
./hooks stats

# View logs
./hooks logs 100

# Rotate keys (30 days)
./hooks rotate 30

# Rotate entire instance (fresh VM, 90 days)
./hooks rotate-instance 90

# Send test cue
./hooks test

# Generate new key
./hooks keygen

# SSH to instance
./hooks ssh

# Help
./hooks help
```

All commands are logged to `logs/hooks.log` for audit trail.

---

## Costs & Billing (AWS Lightsail)

**TL;DR: ~$3.50/month flat, no matter how many times you rotate.**

### Current Setup
```
Instance:  nano_3_0 (512MB RAM, 2 vCPU, 20GB SSD)
Cost:      $3.50/month ($0.00486/hour)
Static IP: FREE (when attached to instance)
Total:     ~$3.50/month
```

### How Billing Works

**Hourly prorated** - You pay for runtime hours, NOT per instance creation:
```
Month with 1 instance running:  720 hours × $0.00486 = $3.50
Month with 10 rotations:        720 hours × $0.00486 = $3.50
```

**No fees for:**
- ✅ Creating instances
- ✅ Destroying instances
- ✅ Rotating (any number of times)
- ✅ Static IP (when attached)

**Costs money:**
- ⚠️ Instance running time (~$0.005/hour)
- ⚠️ Static IP detached (~$3.60/month) - **keep attached!**

### Cost Examples

**Scenario 1: Run for 30 days**
```
1 instance × 720 hours = $3.50/month
```

**Scenario 2: Rotate weekly (4 instances)**
```
Instance 1: 168 hours = $0.82
Instance 2: 168 hours = $0.82
Instance 3: 168 hours = $0.82
Instance 4: 216 hours = $1.05
Total: $3.51/month (same!)
```

**Scenario 3: Rotate daily (30 instances)**
```
30 instances × 24 hours each = $3.50/month (still the same!)
```

**Scenario 4: Run for 10 days, teardown, restart later**
```
First 10 days:  240 hours = $1.17
Teardown (stopped, $0 cost)
Last 10 days:   240 hours = $1.17
Total: $2.34/month (saved $1.16)
```

### Rotation Impact on Costs

**Key Rotation (`./hooks rotate`):**
- Same instance, new keys
- Cost: $0 change
- Downtime: ~10 seconds

**Instance Rotation (`./hooks rotate-instance`):**
- New VM, fresh Ubuntu
- Cost: $0 change (billed hourly)
- Downtime: ~5 minutes

**Complete Teardown (`./hooks teardown`):**
- Destroys everything
- Cost: Stops billing ($3.50/month saved)

### Cost Tracking

**Check current charges:**
```bash
# AWS Console
https://lightsail.aws.amazon.com/ → Account → Billing

# Or via CLI
aws lightsail get-instances --query 'instances[*].[name,bundleId,state.name]'
```

**Set billing alert:**
1. AWS Console → Billing Dashboard
2. Create alarm: Alert if charges > $5/month
3. Get email if costs spike

### Cost Optimization

**✅ Do this:**
- Keep static IP attached (free)
- Use nano_3_0 bundle (cheapest)
- Teardown unused relays
- Rotate as needed (no extra cost)

**❌ Don't do this:**
- Leave static IP detached ($3.60/month waste)
- Forget orphaned instances
- Use larger bundles unless needed

**Check for orphans:**
```bash
# List all instances
aws lightsail get-instances --query 'instances[*].[name,state.name]' --output table

# List all static IPs
aws lightsail get-static-ips --query 'staticIps[*].[name,isAttached]' --output table

# Clean up detached IPs
aws lightsail release-static-ip --static-ip-name <name>
```

### Bundle Sizes (If You Need More Power)

| Bundle | RAM | vCPU | Storage | Price/Month |
|--------|-----|------|---------|-------------|
| nano_3_0 | 512MB | 2 | 20GB | **$3.50** (current) |
| micro_3_0 | 1GB | 2 | 40GB | $5.00 |
| small_3_0 | 2GB | 2 | 60GB | $10.00 |

**Recommendation:** nano_3_0 is sufficient for most use cases.

### Multi-Project Costs

**Option A: One CueSync per project**
```
3 projects × $3.50 = $10.50/month
+ Better isolation
+ Independent expirations
+ Separate security
```

**Option B: Shared CueSync**
```
1 shared instance = $3.50/month
+ Lower cost
- Shared expiration
- All tools in one config
```

### Bottom Line

**You can rotate instances as many times as you want - it's always ~$3.50/month.**

The disposable design costs nothing extra. Rotate daily, weekly, or monthly - same price.

---

## Architecture

```
Cue Dispatcher (upstream, another repo)
    ↓
[creates cuesheet with webhook URL + payload]
    ↓
[signs with secret key]
    ↓
CueSync (this repo)
    ↓
[validates signature]
    ↓
[stores in SQLite]
    ↓
[worker thread executes ONCE]
    ↓
[POSTs payload to webhook URL]
    ↓
[marks as executed]
    ↓
Zapier Webhook (receives payload, does actual work)
```

**Key Points:**
- Each cuesheet specifies its own `webhook_url` (typically a Zapier webhook)
- Each cuesheet contains a `payload` (dumb data to relay)
- CueSync executes each cuesheet exactly ONCE
- After execution, cuesheet is marked as completed (never runs again)

---

## Cuesheet Structure

```json
{
  "cuesheet_id": "morning-workflow-001",
  "webhook_url": "https://hooks.zapier.com/hooks/catch/12345/abcdef",
  "payload": {
    "workflow": "morning-check",
    "data": "whatever zapier needs"
  },
  "metadata": {
    "created_at": "2026-01-19T00:00:00Z",
    "source": "cue-dispatcher"
  }
}
```

**Required Fields:**
- `cuesheet_id` - Unique identifier (prevents duplicates)
- `webhook_url` - Where to send the payload
- `payload` - What to send (arbitrary JSON)

**Optional:**
- `metadata` - Additional context (not sent to webhook)

---

## Security Model

### Dual-Key Handshake

1. **Cue Dispatcher** signs cuesheet with secret key
2. **CueSync** validates signature before accepting
3. **Zapier webhook** receives unsigned payload (Zapier handles its own auth)

### Expiration First

- CueSync refuses execution past `expires_at` timestamp
- No silent continuation
- No auto-renew without explicit action

### Disposable by Design

If CueSync is suspected compromised:
1. Destroy the server
2. Spin up a new CueSync with new key
3. Update Cue Dispatcher with new key

**No data loss. Cuesheets are one-time use.**

---

## Configuration

CueSync is defined by **one config file**: `config.yaml`

### Setup Configuration

**First time setup:**
```bash
# 1. Copy example template
cp config.yaml.example config.yaml

# 2. Generate key and hash
./hooks keygen
# Copy the hash into config.yaml

# 3. Edit config.yaml with your webhooks
vim config.yaml
```

**Config structure:**
```yaml
cuesync_id: cuesync-prod-001  # Unique identifier
expires_at: "2026-02-19T00:00:00Z"  # Hard expiration

# Authentication (SHA-256 hash of upstream signing key)
auth:
  upstream_key_hash: "your-key-hash-here"

# Tool Mapping (tool name → webhook URL)
tools:
  tool1: https://hooks.zapier.com/hooks/catch/YOUR_WEBHOOK_1
  tool2: https://hooks.zapier.com/hooks/catch/YOUR_WEBHOOK_2
  tool3: https://hooks.zapier.com/hooks/catch/YOUR_WEBHOOK_3

# Storage
db_path: "cuesync.db"

# Execution
worker_interval_seconds: 60  # check for pending cues every 60s
max_retry_attempts: 3  # retry failed webhooks up to 3 times

# Optional
renewal_window_seconds: 86400
```

**Security:**
- ✅ `config.yaml` - gitignored (contains webhook URLs)
- ✅ `config.yaml.example` - committed (template)
- ⚠️ Never commit `config.yaml` with real webhooks

---

## Quick Start

### 1. Generate Upstream Key

```bash
# Generate random key
UPSTREAM_KEY=$(openssl rand -hex 32)
echo "Save this key: $UPSTREAM_KEY"

# Generate hash for config
./generate_key_hash.py "$UPSTREAM_KEY"
```

Copy the hash into `config.yaml` under `auth.upstream_key_hash`.

### 2. Start Relay

```bash
# Install dependencies
pip install -r requirements.txt

# Start relay
./relay.py
```

Relay runs on `http://localhost:8080` by default.

### 3. Send Test Cuesheet

```bash
# Edit test-cuesheet.json and add your Zapier webhook URL
nano test-cuesheet.json

# Send signed cuesheet
./send_cuesheet.py test-cuesheet.json "$UPSTREAM_KEY"
```

Expected output:
```json
{
  "status": "accepted",
  "cuesheet_id": "test-morning-workflow-001"
}
```

### 4. Check Status

```bash
# Health check (includes stats)
curl http://localhost:8080/health

# Execution stats
curl http://localhost:8080/stats
```

### 5. Watch Execution

The worker thread checks for pending cuesheets every 10 seconds.

You'll see output like:
```
[2026-01-19T12:00:00Z] Processing 1 pending cuesheets...
  [test-morning-workflow-001] SUCCESS → https://hooks.zapier.com/...
```

Check your Zapier webhook - the payload should have arrived!

---

## API Reference

### `POST /cuesheet`

Accept a signed cuesheet for execution.

**Headers:**
- `Content-Type: application/json`
- `X-CueSync-Signature: <hmac-sha256-signature>`
- `X-CueSync-Key: <upstream-signing-key>`

**Request Body:**
```json
{
  "cuesheet_id": "unique-id-001",
  "webhook_url": "https://hooks.zapier.com/...",
  "payload": { "any": "data" },
  "metadata": { "optional": "context" }
}
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "cuesheet_id": "unique-id-001"
}
```

**Error Responses:**
- `401` - Missing authentication headers
- `403` - Invalid signature or key
- `409` - Cuesheet ID already exists
- `410` - CueSync has expired

### `GET /health`

Health check with execution statistics.

**Response (200 OK):**
```json
{
  "status": "ready",
  "cuesync_id": "cuesync-001",
  "expires_at": "2026-02-19T00:00:00Z",
  "can_renew": false,
  "stats": {
    "pending": 5,
    "executed": 142,
    "failed": 3,
    "total": 150
  }
}
```

### `GET /stats`

Execution statistics only.

**Response (200 OK):**
```json
{
  "pending": 5,
  "executed": 142,
  "failed": 3,
  "total": 150
}
```

---

## How Cue Dispatcher Sends Cuesheets

From upstream (Cue Dispatcher), sign and send cuesheets:

```python
import json
import hmac
import hashlib
import urllib.request

def send_cuesheet(cuesheet, upstream_key, cuesync_url):
    payload = json.dumps(cuesheet).encode("utf-8")
    signature = hmac.new(
        upstream_key.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    req = urllib.request.Request(
        f"{cuesync_url}/cuesheet",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-CueSync-Signature": signature,
            "X-CueSync-Key": upstream_key,
        }
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

# Example cuesheet
cuesheet = {
    "cuesheet_id": "morning-workflow-20260119",
    "webhook_url": "https://hooks.zapier.com/hooks/catch/12345/abcdef",
    "payload": {
        "action": "run_workflow",
        "workflow_id": "morning-check",
        "params": {"priority": "high"}
    }
}

result = send_cuesheet(
    cuesheet,
    "your-upstream-key",
    "http://cuesync.example.com:8080"
)
```

---

## Execution Flow

### 1. Receive Cuesheet

Cue Dispatcher sends signed cuesheet → CueSync validates and stores.

### 2. Worker Thread

Background thread runs every `worker_interval_seconds` (10s default):
- Fetches pending cuesheets from SQLite
- Executes each one by POSTing payload to webhook_url
- Marks as `executed` or `failed`

### 3. Retry Logic

If webhook fails:
- Retry up to `max_retry_attempts` (3 default)
- Exponential backoff between retries
- After max retries, mark as `failed`

### 4. One-Time Execution

Each cuesheet executes exactly ONCE:
- Duplicate `cuesheet_id` rejected (409 Conflict)
- After execution, status = `executed` (never runs again)

---

## Files

```
cuesync/
├── hooks                     # Unified command interface (all operations)
├── relay.py                  # Main relay implementation (~480 lines)
├── config.yaml.example      # Configuration template (copy to config.yaml)
├── requirements.txt          # Python dependencies (PyYAML only)
├── README.md                 # This file
│
├── scripts/                  # All operational scripts
│   ├── deploy.sh             # Initial deployment to Lightsail
│   ├── rotate.sh             # Layer 1: Key rotation (~30s)
│   ├── rotate-instance.sh    # Layer 2: Full instance rotation (~5min)
│   ├── teardown.sh           # Layer 3: Complete destruction
│   ├── check-health.sh       # Compromise detection monitoring
│   └── generate_key_hash.py  # Utility to generate key hashes
│
├── docs/                     # Documentation
│   ├── HOOKS.md              # Hooks command reference
│   └── ROTATION.md           # Three-layer rotation strategy
│
├── logs/                     # Command logs (gitignored)
│   └── hooks.log             # Audit trail of all operations
│
└── archive/                  # Non-essential files (gitignored)
```

**Generated/secret files (gitignored):**
- `config.yaml` - Your actual config (copy from config.yaml.example)
- `cuesync.db` - SQLite database (stores cues with execution status)
- `.rotation-info` - Temporary credentials after rotation
- `config.yaml.backup.*` - Config backups from rotation

---

## Design Principles

### Simple

- Single Python file (~480 lines)
- SQLite for persistence (no external database)
- Standard library only (except PyYAML)

### Secure

- Dual-key handshake validation
- No plaintext keys stored (only SHA-256 hash)
- Expiration enforced at multiple layers
- Each cuesheet validated before storage

### Dumb

- No scheduling logic (Cue Dispatcher handles that)
- No workflow logic (Zapier handles that)
- Just validates, stores, and relays

### Disposable

- Cheap to destroy and recreate
- No cascading failures if destroyed
- One-time cuesheets (no state to preserve)

**A senior security engineer should be able to say:**
**"This is simple enough that it's secure on principle."**

---

## Deployment

See `deploy.sh` for production deployment to a server with systemd.

```bash
# Set deployment configuration
export SERVER_HOST="your-server.example.com"
export SERVER_USER="ubuntu"
export CUESYNC_PORT="8080"

# Deploy
./deploy.sh
```

---

## Relationship to Other Systems

**Cue Dispatcher** = Scheduling + Orchestration (creates cuesheets, decides when to send)
**CueSync** = Secure Relay (validates, stores, executes once)
**Zapier** = Execution (receives payload, does actual work)

CueSync sits in the middle, ensuring only authenticated cuesheets reach Zapier.

---

## Troubleshooting

### Cuesheet Rejected (403)

- Verify upstream key matches hash in `config.yaml`
- Check signature generation (HMAC-SHA256)
- Ensure payload hasn't been modified between signing and sending

### Cuesheet Already Exists (409)

- `cuesheet_id` must be unique
- Check if cuesheet was already sent
- Use timestamped IDs to avoid conflicts

### Webhook Failed

- Check webhook URL is reachable
- Verify webhook accepts JSON POST
- Check Zapier webhook logs
- CueSync will retry up to `max_retry_attempts`

### Worker Not Processing

- Check relay logs for errors
- Verify `worker_interval_seconds` in config
- Check database for pending cuesheets: `sqlite3 cuesync.db "SELECT * FROM cuesheets WHERE status='pending'"`

---

## Compromise Detection and Rotation

**CueSync is disposable by design.** If compromised, destroy and recreate rather than repair.

### Detecting Compromise

Run health checks regularly to detect suspicious activity:

```bash
./check-health.sh
```

The health check monitors:
1. **Unusual volume** - Spike in cues received
2. **High failure rate** - Many failed cues could indicate attack attempts
3. **Spam patterns** - Same source sending excessive cues
4. **Unknown tools** - Cues referencing non-existent tools
5. **Expiration status** - Days until automatic expiration
6. **Recent errors** - Last 5 failures for pattern analysis

**Warning signs:**
- More than 100 cues in one hour
- More than 10 failures in one hour
- Single source sending 20+ cues
- Failed cues with "not found" errors (tool enumeration attempts)
- Less than 7 days until expiration

### Rotating CueSync

If compromise suspected or expiration approaching:

```bash
./rotate.sh
```

This script:
1. Generates new upstream key (64-char hex)
2. Calculates new SHA-256 hash
3. Sets new expiration (30 days from now)
4. Backs up old config
5. Updates `config.yaml` with new credentials
6. Deploys to server via `deploy.sh`
7. Saves new credentials to `.rotation-info` (gitignored)

**After rotation, update all dispatchers:**

```bash
# In each repo using CueSync (e.g., maestro/.cue-dispatcher)
cd /path/to/maestro/.cue-dispatcher
cat > .env <<EOF
CUESYNC_URL=http://your-server.example.com:8080
UPSTREAM_KEY=<new-key-from-rotation-info>
EOF
```

**Environment variables for rotation:**
- `EXPIRES_DAYS` - Days until expiration (default: 30)
- `SERVER_HOST` - Server hostname
- `SERVER_USER` - SSH user
- `REMOTE_DIR` - CueSync installation path

### Rotation Schedule

**Recommended rotation frequency:**
- Normal: Every 30 days (before expiration)
- Suspicious activity detected: Immediately
- After any security incident: Immediately

**Automation:**
```bash
# Run health check hourly
0 * * * * /opt/cuesync/check-health.sh >> /var/log/cuesync-health.log

# Alert if health check fails
0 * * * * /opt/cuesync/check-health.sh || echo "CueSync health check failed" | mail -s "CueSync Alert" admin@example.com
```

### What to Monitor

**Database queries:**
```bash
# Check for unusual patterns
sqlite3 cuesync.db "SELECT tool, COUNT(*) FROM cues GROUP BY tool;"
sqlite3 cuesync.db "SELECT status, COUNT(*) FROM cues GROUP BY status;"
sqlite3 cuesync.db "SELECT * FROM cues WHERE received_at > datetime('now', '-1 hour');"
```

**Server logs:**
```bash
# Check access logs for unusual IPs or patterns
ssh user@server 'journalctl -u cuesync -n 100'
```

**Webhook responses:**
Monitor your Zapier or webhook endpoints for:
- Unexpected payloads
- High volume of requests
- Failed authentications

---

## Status

**Production ready for:**
- ✅ Authenticated cuesheet relay
- ✅ Dual-key signature validation
- ✅ One-time execution with retry logic
- ✅ SQLite persistence with execution tracking
- ✅ Expiration enforcement
- ✅ Disposable deployment model

**CueSync is intentionally boring.**
**If it grows more complex, it is wrong.**

---

**Last Updated**: 2026-01-19
