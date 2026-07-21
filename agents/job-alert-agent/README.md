# Job Alert Agent

**Automated job opportunity scoring and VRGB-styled proposal generation**

## Overview

This agent receives job alert emails via CueSync, scores opportunities, and automatically generates VRGB-styled proposals for high-quality matches.

## Architecture

```
Zapier: New Gmail with label "job-alert"
  ↓
POST to CueSync: /cue
  tool: "process-job-alert"
  payload: {
    email_body: "...",
    subject: "...",
    from: "donotreply@upwork.com",
    platform: "upwork"
  }
  ↓
CueSync dispatches to: http://localhost:5001/process-job-alert
  ↓
Job Alert Agent:
  1. Parse email → extract job details
  2. Score opportunity (1-10 based on budget, skills, client quality)
  3. If score >= threshold (default: 7):
     - Detect VRGB coordinates (enterprise/startup/urgent/creative)
     - Generate VRGB-styled proposal
     - Create proposal cuesheet
     - POST to cue-dispatcher (authenticated)
  ↓
Cue Dispatcher → CueSync
  ↓
CueSync dispatches proposal:
  - tool: "email-me" → Send proposal to your inbox
  - tool: "add-to-trello" → Create card with score/details
```

## Components

### `server.py`
Flask/FastAPI webhook listener that receives `process-job-alert` cues from CueSync.

### `parsers/`
Email parsers for each platform:
- `upwork_parser.py` - Parse Upwork job alerts
- `indeed_parser.py` - Parse Indeed job alerts
- `linkedin_parser.py` - Parse LinkedIn job alerts

Each parser extracts:
- Job title
- Budget/salary
- Description
- Required skills
- Client/company info
- Application deadline
- Job URL

### `opportunity_scorer.py`
Scores jobs 1-10 based on:
- **Budget** (0-3 pts): Higher budget = better
- **Skills Match** (0-3 pts): Match your expertise
- **Client Quality** (0-2 pts): Payment verified, history
- **Urgency** (0-1 pt): Time-sensitive jobs
- **Competition** (0-1 pt): Fewer applicants

### `proposal_generator.py`
Uses maestro's VRGB system:
- Imports from `../../maestro/gen/ops/detect_job_vrgb.py`
- Imports from `../../maestro/gen/ops/generate_proposal_vrgb.py`
- Generates tone-appropriate proposals

### `cuesheet_creator.py`
Creates cuesheets with:
- Email summary with opportunity score
- Trello card with proposal + job details

### `dispatcher.py`
POSTs cuesheets to cue-dispatcher with proper authentication:
- Signs payloads with upstream key
- Sends to dispatcher endpoint
- Dispatcher validates and forwards to CueSync

## Configuration

### Environment Variables
```bash
# CueSync/Dispatcher
DISPATCHER_URL=http://localhost:8080/dispatch
UPSTREAM_KEY=your-secret-key

# Scoring Thresholds
MIN_OPPORTUNITY_SCORE=7  # Only generate proposals for 7+ scores
MIN_BUDGET=50            # Minimum job budget

# Your Skills (for matching)
YOUR_SKILLS=react,javascript,python,node,typescript,api
```

### Zapier Setup

**Trigger:** Gmail - New Labeled Email
- Label: `job-alert`
- Trigger on: New emails only

**Action:** Webhooks - POST
- URL: `http://your-cuesync-ip:8080/cue`
- Method: POST
- Headers:
  - `Content-Type: application/json`
  - `X-CueSync-Signature: {{signature}}`
  - `X-CueSync-Key: {{upstream_key}}`
- Body:
```json
{
  "cue_id": "job-alert-{{timestamp}}",
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

**Signature Calculation:**
Use Zapier Code step to generate HMAC-SHA256 signature:
```javascript
const crypto = require('crypto');
const payload = JSON.stringify(inputData);
const signature = crypto.createHmac('sha256', 'your-upstream-key')
  .update(payload)
  .digest('hex');
output = {signature};
```

## Usage

### Running the Agent

```bash
# Start the job alert agent
cd agents/job-alert-agent
python3 server.py

# Agent runs on http://localhost:5001
```

### CueSync Configuration

Add to `cuesync/config.yaml`:
```yaml
tools:
  email-me: "https://hook.us1.make.com/..."
  add-to-trello: "https://hook.us1.make.com/..."
  process-job-alert: "http://localhost:5001/process-job-alert"
```

### Testing

```bash
# Test with sample Upwork email
curl -X POST http://localhost:5001/process-job-alert \
  -H "Content-Type: application/json" \
  -H "X-CueSync-Tool: process-job-alert" \
  -d '{
    "email_body": "Fix React Component Bug...",
    "subject": "New Job Match: React Developer",
    "from": "donotreply@upwork.com",
    "platform": "upwork"
  }'
```

## Flow Example

### 1. Upwork Email Arrives
```
From: donotreply@upwork.com
Subject: New Job Match: Fix React Component Rendering Bug

Fix React Component Rendering Bug
Budget: $150
Posted: 2 hours ago

We need someone to fix a React component that's not rendering...
Skills: React, JavaScript, Debugging
```

### 2. Zapier Triggers
- Detects email with label "job-alert"
- POSTs to CueSync with signed payload

### 3. Agent Processes
```python
Job parsed:
  title: "Fix React Component Rendering Bug"
  budget: 150
  skills: ["React", "JavaScript", "Debugging"]

Opportunity Score: 8/10
  Budget: 2 pts ($150)
  Skills: 3 pts (all match)
  Client: 2 pts (verified, 10+ jobs)
  Urgency: 1 pt ("2 hours ago")

✅ Score >= 7 → Generate proposal

VRGB detected: Standard (Professional/Balanced)
  formality_level: #8B8B8B
  humor_intensity: #8B8B8B

Proposal generated (183 words)
```

### 4. Cuesheet Created
```json
{
  "cuesheet_id": "job-proposal-upwork_1234567-20260119",
  "title": "Upwork Opportunity: Fix React Component (Score: 8/10)",
  "cues": [
    {
      "cue_id": "proposal-email-{timestamp}",
      "tool": "email-me",
      "payload": {
        "subject": "🎯 High-Quality Match (8/10): Fix React Component - $150",
        "message": "[VRGB-Generated Proposal]\n\n..."
      }
    },
    {
      "cue_id": "proposal-trello-{timestamp}",
      "tool": "add-to-trello",
      "payload": {
        "title": "⭐ 8/10 - Fix React Component ($150)",
        "description": "**Proposal**\n...\n\n**Job Details**\n...",
        "list": "High-Priority Leads",
        "labels": ["upwork", "high-score", "standard"]
      }
    }
  ]
}
```

### 5. You Receive
- Email with proposal in your inbox
- Trello card in "High-Priority Leads" list
- Review and submit (or ignore)

## Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Design Zapier integration flow
- [x] Stub out agent architecture
- [ ] Implement email parsers
- [ ] Implement opportunity scorer
- [ ] Integrate maestro VRGB system

### Phase 2: Platform Support
- [ ] Upwork parser (priority)
- [ ] Indeed parser
- [ ] LinkedIn parser

### Phase 3: Intelligence
- [ ] Machine learning on proposal success rate
- [ ] A/B testing VRGB coordinates
- [ ] Client quality prediction
- [ ] Optimal response timing

### Phase 4: Automation
- [ ] Auto-submit proposals (with approval threshold)
- [ ] Follow-up message generation
- [ ] Interview scheduling

## Files

```
agents/job-alert-agent/
├── README.md                    # This file
├── server.py                    # Flask webhook listener
├── requirements.txt             # Python dependencies
├── config.yaml                  # Agent configuration
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py           # Base parser class
│   ├── upwork_parser.py         # Upwork email parser
│   ├── indeed_parser.py         # Indeed email parser
│   └── linkedin_parser.py       # LinkedIn email parser
├── opportunity_scorer.py        # Job scoring logic
├── proposal_generator.py        # VRGB proposal generation
├── cuesheet_creator.py          # Create proposal cuesheets
└── dispatcher.py                # POST to cue-dispatcher

Integration with maestro:
../../../maestro/gen/ops/detect_job_vrgb.py
../../../maestro/gen/ops/generate_proposal_vrgb.py
../../../maestro/gen/llm_client.py
```

## Notes

- Agent runs independently from CueSync (different port)
- Uses maestro's VRGB system (shared codebase)
- Fully stateless (no database, logs only)
- Zapier handles email detection and delivery
- CueSync handles webhook dispatch
- All version controlled and reproducible

**Status:** Stubbed, ready for implementation
**Created:** 2026-01-19
