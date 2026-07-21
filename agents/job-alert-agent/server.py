#!/usr/bin/env python3
"""
Job Alert Agent - Webhook Server

Receives job alert cues from CueSync, scores opportunities,
and generates VRGB-styled proposals for high-quality matches.

Usage:
    python3 server.py

    Runs on http://localhost:5001
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

# Add maestro to path for VRGB integration
MAESTRO_PATH = Path(__file__).parent.parent.parent.parent / "maestro"
sys.path.insert(0, str(MAESTRO_PATH / "gen"))

from parsers import detect_platform, parse_job_email
from opportunity_scorer import score_opportunity
from proposal_generator import generate_proposal_for_job
from cuesheet_creator import create_proposal_cuesheet
from dispatcher import dispatch_cuesheet


app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ready",
        "agent": "job-alert-agent",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/process-job-alert", methods=["POST"])
def process_job_alert():
    """
    Process incoming job alert from CueSync

    Expected payload from Zapier → CueSync:
    {
        "email_body": "...",
        "subject": "...",
        "from": "donotreply@upwork.com",
        "received_at": "2026-01-19T21:00:00Z",
        "platform": "upwork"  # Optional, will detect if missing
    }
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON payload"}), 400

        # Extract email data
        email_body = data.get("email_body", "")
        subject = data.get("subject", "")
        from_address = data.get("from", "")
        platform = data.get("platform")

        if not email_body or not subject:
            return jsonify({"error": "Missing email_body or subject"}), 400

        print(f"\n{'='*70}")
        print(f"PROCESSING JOB ALERT")
        print(f"{'='*70}")
        print(f"From: {from_address}")
        print(f"Subject: {subject}")
        print()

        # 1. Detect platform if not provided
        if not platform:
            platform = detect_platform(from_address, subject, email_body)
            print(f"✓ Detected platform: {platform}")

        # 2. Parse email to extract job details
        job = parse_job_email(email_body, subject, from_address, platform)

        if not job:
            print(f"✗ Could not parse job from email")
            return jsonify({
                "status": "skipped",
                "reason": "Could not parse job details"
            }), 200

        print(f"✓ Parsed job: {job.get('title', 'Unknown')[:50]}")
        print(f"  Platform: {platform}")
        print(f"  Budget: ${job.get('budget', 0)}")
        print()

        # 3. Score opportunity
        score = score_opportunity(job)
        job['opportunity_score'] = score

        print(f"✓ Opportunity Score: {score}/10")

        # Get minimum score threshold from env (default: 7)
        min_score = int(os.getenv("MIN_OPPORTUNITY_SCORE", "7"))

        if score < min_score:
            print(f"✗ Score {score} < threshold {min_score}")
            print(f"  Skipping proposal generation")
            print(f"{'='*70}\n")

            return jsonify({
                "status": "skipped",
                "reason": f"Score {score} below threshold {min_score}",
                "job_title": job.get('title'),
                "score": score
            }), 200

        print(f"✓ Score {score} >= threshold {min_score}")
        print(f"  Generating proposal...")
        print()

        # 4. Generate VRGB-styled proposal
        proposal_result = generate_proposal_for_job(job)

        print(f"✓ Proposal generated ({proposal_result['word_count']} words)")
        print(f"  VRGB: {proposal_result['vrgb_description']}")
        print(f"  Job Type: {proposal_result['job_type']}")
        print()

        # 5. Create cuesheet
        cuesheet = create_proposal_cuesheet(job, proposal_result, score)

        print(f"✓ Cuesheet created: {cuesheet['cuesheet_id']}")
        print(f"  Cues: {len(cuesheet['cues'])}")
        print()

        # 6. Dispatch to cue-dispatcher
        dispatch_result = dispatch_cuesheet(cuesheet)

        if dispatch_result['success']:
            print(f"✓ Dispatched to CueSync")
            print(f"  Proposal will arrive via email + Trello")
        else:
            print(f"✗ Dispatch failed: {dispatch_result['error']}")

        print(f"{'='*70}\n")

        return jsonify({
            "status": "success",
            "job_title": job.get('title'),
            "platform": platform,
            "score": score,
            "cuesheet_id": cuesheet['cuesheet_id'],
            "dispatched": dispatch_result['success']
        }), 200

    except Exception as e:
        print(f"✗ Error processing job alert: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/stats", methods=["GET"])
def stats():
    """
    TODO: Track statistics
    - Total jobs processed
    - Average opportunity score
    - Proposals generated
    - Success rate
    """
    return jsonify({
        "message": "Stats not yet implemented",
        "todo": "Add statistics tracking"
    }), 501


if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "5001"))

    print("=" * 70)
    print("JOB ALERT AGENT")
    print("=" * 70)
    print(f"Starting webhook server on http://localhost:{port}")
    print()
    print("Endpoints:")
    print(f"  GET  /health               - Health check")
    print(f"  POST /process-job-alert    - Process job alert from CueSync")
    print(f"  GET  /stats                - View statistics")
    print()
    print("Configuration:")
    print(f"  MIN_OPPORTUNITY_SCORE: {os.getenv('MIN_OPPORTUNITY_SCORE', '7')}")
    print(f"  MIN_BUDGET: {os.getenv('MIN_BUDGET', '50')}")
    print(f"  YOUR_SKILLS: {os.getenv('YOUR_SKILLS', '(not set)')}")
    print()
    print("Ready to receive job alerts from CueSync...")
    print("=" * 70)
    print()

    app.run(host="0.0.0.0", port=port, debug=True)
