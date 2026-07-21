# Job Alert Agent - Quick Start Guide

Get your automated job proposal system running in 5 steps.

## Prerequisites

- Python 3.9+
- CueSync relay running
- Maestro repo (for VRGB system)
- Zapier account (free tier works)

## Step 1: Install Dependencies

```bash
cd agents/job-alert-agent
pip3 install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example config
cp config.yaml.example config.yaml

# Set environment variables
export DISPATCHER_URL="http://localhost:8080/dispatch"
export MIN_OPPORTUNITY_SCORE=7
export MIN_BUDGET=50
export YOUR_SKILLS="react,javascript,python,node,typescript"
```

## Step 3: Start the Agent

```bash
python3 server.py

# You should see:
# ======================================================================
# JOB ALERT AGENT
# ======================================================================
# Starting webhook server on http://localhost:5001
# ...
# Ready to receive job alerts from CueSync...
```

## Step 4: Add Tool to CueSync Config

Edit `cuesync/config.yaml`:

```yaml
tools:
  email-me: "https://hook.us1.make.com/..."
  add-to-trello: "https://hook.us1.make.com/..."
  process-job-alert: "http://localhost:5001/process-job-alert"  # ADD THIS
```

Restart CueSync:
```bash
cd ../../  # Back to cuesync root
./hooks restart
```

## Step 5: Set Up Zapier

### Create Zap

1. **Trigger:** Gmail - New Labeled Email
   - Label: `job-alert`
   - Trigger on: New emails only

2. **Action:** Webhooks - Custom Request
   - Method: POST
   - URL: `http://YOUR_CUESYNC_IP:8080/cue`
   - Headers:
     ```
     Content-Type: application/json
     X-CueSync-Signature: (see below)
     X-CueSync-Key: (your upstream key)
     ```
   - Body:
     ```json
     {
       "cue_id": "job-alert-{{zap_meta_utc_iso}}",
       "tool": "process-job-alert",
       "payload": {
         "email_body": "{{body_plain}}",
         "subject": "{{subject}}",
         "from": "{{from_email}}",
         "received_at": "{{date_received}}",
         "platform": "upwork"
       }
     }
     ```

3. **Signature Calculation** (Add Code step before webhook):
   ```javascript
   const crypto = require('crypto');
   const upstream_key = 'YOUR_UPSTREAM_KEY';

   const payload = JSON.stringify({
     "cue_id": `job-alert-${inputData.timestamp}`,
     "tool": "process-job-alert",
     "payload": {
       "email_body": inputData.body_plain,
       "subject": inputData.subject,
       "from": inputData.from_email,
       "received_at": inputData.date_received,
       "platform": "upwork"
     }
   });

   const signature = crypto.createHmac('sha256', upstream_key)
     .update(payload)
     .digest('hex');

   output = {signature: signature};
   ```

4. **Test Zap** - Send test email with label "job-alert"

## Step 6: Label Job Alerts in Gmail

### Option A: Manual Labels
Go to Gmail and create label "job-alert", then apply to Upwork/Indeed/LinkedIn emails

### Option B: Gmail Filters (Automated)
Create filters that auto-apply the label:

**Upwork:**
- From: `donotreply@upwork.com`
- Subject contains: `New Job Match`
- Apply label: `job-alert`

**Indeed:**
- From: `noreply@indeed.com`
- Subject contains: `jobs`
- Apply label: `job-alert`

**LinkedIn:**
- From: `jobs-noreply@linkedin.com`
- Subject contains: `New jobs`
- Apply label: `job-alert`

## Testing

### Test with Sample Email

```bash
curl -X POST http://localhost:5001/process-job-alert \
  -H "Content-Type: application/json" \
  -d '{
    "email_body": "Fix React Component Rendering Bug\nBudget: $150\nSkills: React, JavaScript",
    "subject": "New Job Match: Fix React Component",
    "from": "donotreply@upwork.com",
    "platform": "upwork"
  }'
```

Expected output:
```
======================================================================
PROCESSING JOB ALERT
======================================================================
From: donotreply@upwork.com
Subject: New Job Match: Fix React Component

✓ Detected platform: upwork
✓ Parsed job: Fix React Component Rendering Bug
  Platform: upwork
  Budget: $150

✓ Opportunity Score: 8/10
✓ Score 8 >= threshold 7
  Generating proposal...

✓ Proposal generated (183 words)
  VRGB: Professional + Balanced
  Job Type: standard

✓ Cuesheet created: job-proposal-upwork_abc123-20260119
  Cues: 2

✓ Dispatched to CueSync
  Proposal will arrive via email + Trello
======================================================================
```

### Check Your Email & Trello
- Within 60 seconds, you should receive:
  - Email with VRGB-styled proposal
  - Trello card with job details + proposal

## Troubleshooting

### Agent not starting?
```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check dependencies
pip3 install -r requirements.txt

# Check port availability
lsof -i :5001
```

### CueSync not dispatching?
```bash
# Check CueSync health
curl http://localhost:8080/health

# Check tool is registered
curl http://localhost:8080/health | jq '.tools'
# Should include "process-job-alert"
```

### Zapier not triggering?
- Check label is exactly "job-alert" (case-sensitive)
- Verify Gmail trigger is set to "New labeled emails"
- Check Zap history for errors
- Test with manual "Send Test" in Zapier

### No proposals generating?
- Check opportunity score: `curl http://localhost:5001/stats`
- Lower MIN_OPPORTUNITY_SCORE: `export MIN_OPPORTUNITY_SCORE=5`
- Check email parsing: Look for "✗ Could not parse job" in logs

## What Happens When It Works

```
1. Job alert email arrives in Gmail
   ↓
2. Gmail applies label "job-alert"
   ↓
3. Zapier detects labeled email (within ~1 min)
   ↓
4. Zapier POSTs to CueSync with signed payload
   ↓
5. CueSync validates and dispatches to job-alert-agent
   ↓
6. Agent:
   - Parses email
   - Scores opportunity (1-10)
   - If score >= 7:
     - Detects VRGB coordinates
     - Generates proposal
     - Creates cuesheet
     - Dispatches back to CueSync
   ↓
7. CueSync dispatches proposal:
   - Email arrives in your inbox
   - Trello card created
   ↓
8. You review, customize if needed, and submit!
```

## Next Steps

- [ ] Test with real Upwork email
- [ ] Tune scoring thresholds
- [ ] Customize proposal templates
- [ ] Add Indeed support
- [ ] Add LinkedIn support
- [ ] Track proposal success rates
- [ ] Optimize VRGB coordinates based on results

## Support

See full documentation in `README.md`
