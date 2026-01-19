# CueSync Hooks - Command Reference

The `hooks` script provides a unified interface for all CueSync operations with automatic logging.

---

## Quick Reference

```bash
./hooks <command> [options]
```

All commands are logged to `logs/hooks.log` for audit trail.

---

## Commands

### Deployment

**`./hooks deploy`**
Deploy CueSync to Lightsail instance
- Copies files to server
- Installs dependencies
- Creates systemd service
- Starts relay

**`./hooks status`**
Check systemd service status
- Shows if relay is running
- Recent log entries
- Service health

### Monitoring

**`./hooks health`**
Check health endpoint
- Server status (ready/expired)
- Expiration date
- Available tools
- Execution stats

**`./hooks stats`**
Show execution statistics
- Total cues processed
- Executed count
- Failed count
- Pending count

**`./hooks logs [lines]`**
View server logs
- Default: 50 lines
- Example: `./hooks logs 100`

**`./hooks watch-logs`**
Watch logs in real-time
- Live tail of systemd logs
- Ctrl+C to exit

**`./hooks check-health`**
Run health check script
- Unusual volume detection
- High failure rate alerts
- Spam pattern detection
- Unknown tool references
- Expiration warnings

**`./hooks db-stats`**
Query database statistics
- Cue counts by status
- Direct SQLite query

### Rotation

**`./hooks rotate [days]`**
Key rotation (Layer 1)
- Default: 30 days
- Generates new key
- Updates config
- Redeploys to same instance
- Fast (~30 seconds)

Example:
```bash
./hooks rotate 90    # 90-day expiration
./hooks rotate 365   # 1-year expiration
```

**`./hooks rotate-instance [days]`**
Instance rotation (Layer 2)
- Default: 30 days
- Destroys old instance
- Creates fresh Ubuntu VM
- Keeps same static IP
- Deep clean (~5 minutes)

Example:
```bash
./hooks rotate-instance 180   # 6-month expiration
```

**`./hooks teardown`**
Complete destruction (Layer 3)
- Destroys instance
- Releases static IP
- Complete cleanup
- Requires typing 'destroy' to confirm

### Utilities

**`./hooks test`**
Send test cue
- Uses dispatcher from maestro repo
- Sends test.json
- Verifies end-to-end flow

**`./hooks ssh`**
SSH into CueSync instance
- Opens interactive shell
- Useful for debugging

**`./hooks keygen`**
Generate new key and hash
- Creates random 64-char key
- Calculates SHA-256 hash
- Shows config.yaml format

**`./hooks ip`**
Show static IP information
- IP address
- Attachment status
- AWS resource details

**`./hooks help`**
Show help message
- All available commands
- Usage examples

---

## Logging

All hook commands are logged to `logs/hooks.log`:

```
[2026-01-19T21:18:38Z] health | status=checking
[2026-01-19T21:18:38Z] health | status=healthy
[2026-01-19T21:18:41Z] stats | status=fetching
[2026-01-19T21:18:41Z] stats | status=success
[2026-01-19T21:18:50Z] keygen | status=started
[2026-01-19T21:18:50Z] keygen | status=success
```

**Log format:**
```
[timestamp] command | status=<status>
```

**View logs:**
```bash
cat logs/hooks.log
tail -f logs/hooks.log  # Live tail
```

---

## Environment Variables

Override defaults with environment variables:

**`STATIC_IP`**
Static IP address
- Default: `3.138.41.20`
- Example: `STATIC_IP=1.2.3.4 ./hooks health`

**`INSTANCE_NAME`**
Lightsail instance name
- Default: `cuesync-node`
- Example: `INSTANCE_NAME=cuesync-prod ./hooks ssh`

**`EXPIRES_DAYS`**
Days until expiration
- Default: `30`
- Example: `EXPIRES_DAYS=365 ./hooks rotate`

---

## Common Workflows

### Daily Health Check
```bash
./hooks health
./hooks stats
./hooks check-health
```

### Monthly Key Rotation
```bash
./hooks rotate 30
# Update dispatchers with new key from .rotation-info
```

### Quarterly Instance Refresh
```bash
./hooks rotate-instance 90
# Fresh VM every 90 days
```

### Debugging
```bash
./hooks logs 200          # View recent logs
./hooks watch-logs        # Live tail
./hooks ssh               # Interactive shell
./hooks db-stats          # Database query
```

### End-to-End Test
```bash
./hooks test              # Send test cue
sleep 65                  # Wait for worker cycle (60s)
./hooks stats             # Verify execution
```

---

## Integration with CI/CD

Hooks can be used in automation:

```bash
#!/bin/bash
# Weekly rotation job

./hooks rotate 30
if [ $? -eq 0 ]; then
    echo "Rotation successful"
    # Update dispatcher configs
    ./update-dispatchers.sh
else
    echo "Rotation failed"
    exit 1
fi
```

---

## Security

**Logged operations:**
- All hook commands logged with timestamp
- Audit trail for compliance
- Debug failed operations

**Not logged:**
- Key values (only "started/success")
- Payload contents
- Sensitive config data

**Log file location:**
- `logs/hooks.log`
- Gitignored by default
- Backed up separately if needed

---

## Examples

**Check if server is healthy:**
```bash
$ ./hooks health
Checking health endpoint...
{
    "status": "ready",
    "cuesync_id": "cuesync-prod-001",
    "expires_at": "2026-01-29T20:43:28+00:00"
}
```

**Rotate with 1-year expiration:**
```bash
$ ./hooks rotate 365
Rotating keys (Layer 1)...
[1/7] Generating new upstream key...
[2/7] Generating key hash...
[3/7] Setting expiration...
  Expires: 2027-01-19T21:30:00Z
...
✅ Key rotation complete
```

**View recent activity:**
```bash
$ ./hooks logs 20
Jan 19 21:18:38 python3[12817]: [2026-01-19T21:18:38] "GET /health HTTP/1.1" 200 -
Jan 19 21:18:41 python3[12817]: [2026-01-19T21:18:41] "GET /stats HTTP/1.1" 200 -
```

**Generate new key:**
```bash
$ ./hooks keygen
Generating new key and hash...

Upstream Key: c91c146cd831f748ca10bb3aad026ccaa7cf5fc93ab1488f09904a167f3cd893
SHA-256 Hash: a50432425ecce83f7fd06ea8f11946e29d5d386f3515bbbf039b716d59d66cf8

Add to config.yaml:
  upstream_key_hash: "a50432425ecce83f7fd06ea8f11946e29d5d386f3515bbbf039b716d59d66cf8"
```

---

## Troubleshooting

**Command fails with "No such file or directory":**
- Ensure you're in the cuesync directory
- Run: `chmod +x hooks`

**SSH connection fails:**
- Check SSH config: `cat ~/.ssh/config | grep cuesync`
- Verify key permissions: `ls -la ~/.ssh/cuesync-key.pem`
- Should be: `-rw------- (600)`

**Health check returns unhealthy:**
- Check if relay is running: `./hooks status`
- View recent logs: `./hooks logs 50`
- SSH and debug: `./hooks ssh`

**Rotation fails:**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify static IP exists: `./hooks ip`
- Check instance status: `aws lightsail get-instance --instance-name cuesync-node`

---

## See Also

- `README.md` - Full CueSync documentation
- `ROTATION.md` - Three-layer rotation strategy
- `logs/hooks.log` - Command audit trail
