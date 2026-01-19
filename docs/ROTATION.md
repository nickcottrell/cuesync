# CueSync Rotation Strategy - Three Layers

CueSync supports **three independent layers of rotation** for different security scenarios and operational needs.

---

## Overview

```
┌────────────────────────────────────────────────────────────┐
│ Layer 3: Complete Teardown (teardown.sh)                   │
│ Destroys: Instance + Static IP + Everything                │
│ Use when: Shutting down or moving regions                  │
└────────────────────────────────────────────────────────────┘
                            │
    ┌───────────────────────┴───────────────────────┐
    │ Layer 2: Instance Rotation (rotate-instance.sh)│
    │ Destroys: Lightsail instance (fresh Ubuntu)    │
    │ Keeps: Static IP (no dispatcher updates)       │
    │ Use when: Instance compromised                 │
    └───────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │ Layer 1: Key Rotation (rotate.sh)     │
        │ Rotates: Keys + config only            │
        │ Keeps: Instance + IP                   │
        │ Use when: Routine rotation             │
        └───────────────────────────────────────┘
```

---

## Layer 1: Key Rotation (Fast, 30 seconds)

**Script:** `./rotate.sh`

**What it does:**
- Generates new upstream key
- Updates `config.yaml` with new key hash
- Redeploys to existing instance
- Saves new credentials to `.rotation-info`

**What stays the same:**
- Lightsail instance (same VM)
- Static IP address (no dispatcher updates)
- SSH keys and system configuration

**When to use:**
- Routine rotation (every 30 days)
- Key suspected leaked (but instance secure)
- Proactive security hygiene
- Before expiration date

**How to run:**
```bash
# Default: 30 days
./rotate.sh

# Custom expiration (1 year)
EXPIRES_DAYS=365 ./rotate.sh

# Then update dispatchers:
cd /path/to/maestro/.cue-dispatcher
cat > .env <<EOF
CUESYNC_URL=http://3.138.41.20:8080
UPSTREAM_KEY=<from-.rotation-info>
EOF
```

**Pros:**
- ✅ Fast (30 seconds)
- ✅ No IP changes
- ✅ Minimal disruption

**Cons:**
- ⚠️ Doesn't help if instance itself is compromised

---

## Layer 2: Instance Rotation (Deep Clean, 5 minutes)

**Script:** `./rotate-instance.sh`

**What it does:**
- Detaches static IP from old instance
- **Destroys entire Lightsail instance**
- Creates brand new Ubuntu instance
- Reattaches same static IP
- Opens firewall ports
- Deploys CueSync with new keys

**What stays the same:**
- Static IP address (no dispatcher updates needed!)
- Static IP name (`cuesync-static-ip`)

**What's destroyed:**
- Entire VM (fresh Ubuntu install)
- All system logs
- SSH host keys
- Any potential backdoors/rootkits
- Old CueSync database

**When to use:**
- Instance suspected compromised
- Deep clean needed
- Unusual system behavior detected
- Failed security audit
- Every 3-6 months as best practice

**How to run:**
```bash
# Default: 30 days
./rotate-instance.sh

# Custom expiration (6 months)
EXPIRES_DAYS=180 ./rotate-instance.sh

# Then update dispatchers (same IP, new key):
cd /path/to/maestro/.cue-dispatcher
cat > .env <<EOF
CUESYNC_URL=http://3.138.41.20:8080  # Same IP!
UPSTREAM_KEY=<from-.rotation-info>
EOF
```

**Pros:**
- ✅ Truly disposable (fresh VM)
- ✅ No IP changes (static IP preserved)
- ✅ Removes any system-level compromise
- ✅ Clean slate

**Cons:**
- ⚠️ Takes ~5 minutes (creating new instance)
- ⚠️ Requires AWS credentials configured

---

## Layer 3: Complete Teardown (Nuclear Option)

**Script:** `./teardown.sh`

**What it does:**
- Detaches static IP
- **Destroys instance**
- **Releases static IP** (gone forever)
- Optionally cleans up local files

**What's destroyed:**
- Everything
- Instance
- Static IP
- All infrastructure

**When to use:**
- Shutting down CueSync permanently
- Moving to different AWS region
- Moving to different cloud provider
- Project decommissioning

**How to run:**
```bash
./teardown.sh
# Type 'destroy' to confirm

# Optional: Clean up local files too
```

**After teardown:**
To redeploy from scratch:
```bash
# 1. Allocate new static IP
aws lightsail allocate-static-ip --static-ip-name cuesync-static-ip-v2

# 2. Create new instance
aws lightsail create-instances \
  --instance-names cuesync-node-v2 \
  --availability-zone us-east-2a \
  --blueprint-id ubuntu_22_04 \
  --bundle-id nano_3_0

# 3. Attach IP and deploy
aws lightsail attach-static-ip --static-ip-name cuesync-static-ip-v2 --instance-name cuesync-node-v2
./deploy.sh
```

---

## Architecture: Static IP Benefits

### Why Static IP Matters

```
┌─────────────────────────────────────────┐
│ Static IP: 3.138.41.20 (PERMANENT)      │  ← Never changes
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Lightsail Instance (DISPOSABLE)         │  ← Can be destroyed/recreated
│ - cuesync-node                          │
│ - Fresh Ubuntu every rotation           │
│ - System logs reset                     │
└─────────────────────────────────────────┘
```

**Benefits:**
1. **No dispatcher updates** - IP stays constant across instance rotations
2. **True disposability** - Nuke VM anytime, IP persists
3. **Clean boundary** - Permanent (IP) vs Disposable (VM)
4. **DNS friendly** - Can point domain to static IP once

---

## Expiration Configuration

All rotation scripts support custom expiration via `EXPIRES_DAYS`:

```bash
# 10 days
EXPIRES_DAYS=10 ./rotate.sh

# 30 days (default)
./rotate.sh

# 90 days (quarterly)
EXPIRES_DAYS=90 ./rotate.sh

# 1 year
EXPIRES_DAYS=365 ./rotate.sh

# 5 years (set and forget)
EXPIRES_DAYS=1825 ./rotate-instance.sh
```

**Recommendation:**
- Development: 10-30 days
- Production: 90-180 days
- Long-term stable: 365+ days

CueSync will **auto-reject** all new cues after expiration (HTTP 410 Gone).

---

## Decision Matrix

| Scenario | Script to Use | Why |
|----------|---------------|-----|
| Routine rotation | `rotate.sh` | Fast, minimal disruption |
| Key suspected leaked | `rotate.sh` | New key, same instance |
| Before expiration | `rotate.sh` | Extend lifetime |
| Unusual activity detected | `rotate-instance.sh` | Fresh VM, deep clean |
| Instance suspected compromised | `rotate-instance.sh` | Nuclear option for VM |
| Failed security scan | `rotate-instance.sh` | Clean slate |
| Quarterly best practice | `rotate-instance.sh` | Proactive security |
| Shutting down project | `teardown.sh` | Complete cleanup |
| Moving AWS regions | `teardown.sh` | Start fresh elsewhere |

---

## Current Configuration

**Static IP:** `3.138.41.20`
**Static IP Name:** `cuesync-static-ip`
**Instance Name:** `cuesync-node`
**Region:** `us-east-2`
**Blueprint:** `ubuntu_22_04`
**Bundle:** `nano_3_0` (512MB RAM, 1 vCPU)

---

## Best Practices

1. **Proactive rotation schedule:**
   - Layer 1 (key): Every 30 days
   - Layer 2 (instance): Every 90-180 days
   - Layer 3 (teardown): Only when decommissioning

2. **After rotation:**
   - Update all dispatchers immediately
   - Test with `dispatch.sh examples/test.json`
   - Monitor health endpoint for 24h

3. **Monitor for compromise:**
   - Run `./check-health.sh` hourly (cron)
   - Alert on unusual patterns
   - Layer 2 rotation if suspicious

4. **Document rotations:**
   - Keep `.rotation-info` files temporarily
   - Log rotation dates
   - Track which repos need dispatcher updates

5. **Static IP maintenance:**
   - Keep attached to an instance (free)
   - Detached static IPs cost $0.005/hr (~$3.60/month)
   - Never release unless doing Layer 3 teardown

---

## Emergency Procedures

### If CueSync is compromised:

1. **Immediate:** Stop accepting new cues
   ```bash
   ssh cuesync-node 'sudo systemctl stop cuesync'
   ```

2. **Assess:** Layer 1 or Layer 2 needed?
   - Key leaked? → Layer 1 (`rotate.sh`)
   - Instance compromised? → Layer 2 (`rotate-instance.sh`)

3. **Execute rotation**
   ```bash
   ./rotate-instance.sh  # Most common emergency response
   ```

4. **Update dispatchers** within 5 minutes

5. **Monitor** for 24-48 hours after rotation

---

## Files

```
cuesync/
├── rotate.sh                    # Layer 1: Key rotation
├── rotate-instance.sh           # Layer 2: Instance rotation
├── teardown.sh                  # Layer 3: Complete destruction
├── check-health.sh              # Compromise detection
├── deploy.sh                    # Initial deployment
└── .rotation-info               # Generated credentials (gitignored)
```

---

## Summary

**Three layers give you flexibility:**
- **Layer 1** = Fast, routine maintenance
- **Layer 2** = Deep clean, truly disposable
- **Layer 3** = Nuclear option, complete teardown

**Static IP = Clean boundary:**
- Permanent: IP address
- Disposable: Everything else

**Expiration = Forced rotation:**
- Can be set for days, months, or years
- Auto-rejects after expiration
- No forgotten relays

**You control the rotation strategy based on your security posture.**
