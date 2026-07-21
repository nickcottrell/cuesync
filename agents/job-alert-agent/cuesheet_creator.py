"""
Cuesheet Creator

Creates cuesheets for dispatching proposals via CueSync
"""

from datetime import datetime
from typing import Dict


def create_proposal_cuesheet(job: Dict, proposal_result: Dict, score: int) -> Dict:
    """
    Create cuesheet with proposal for dispatch to CueSync

    Creates 2 cues:
    1. Email to you with proposal and job details
    2. Trello card with proposal, score, and tracking info

    Args:
        job: Job dictionary from parser
        proposal_result: Result from proposal_generator
        score: Opportunity score (1-10)

    Returns:
        Cuesheet dictionary ready for dispatch
    """

    platform = job.get('platform', 'unknown')
    job_id = job.get('job_id', 'unknown')
    title = job.get('title', 'Unknown Job')
    budget = job.get('budget', 0)
    url = job.get('url', '')

    proposal_text = proposal_result['proposal_text']
    job_type = proposal_result['job_type']
    vrgb_desc = proposal_result['vrgb_description']
    vrgb_used = proposal_result['vrgb_used']

    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    cuesheet_id = f"job-proposal-{platform}_{job_id}-{timestamp}"

    # Build email message
    email_subject = f"{'🎯' if score >= 8 else '⭐'} {platform.title()} Match ({score}/10): {title[:60]}"

    email_message = f"""New {platform.title()} opportunity scored {score}/10!

=== JOB DETAILS ===
Title: {title}
Budget: ${budget}
Platform: {platform.title()}
Score: {score}/10
URL: {url}

=== VRGB-GENERATED PROPOSAL ===
Tone: {vrgb_desc} ({job_type})

{proposal_text}

=== SCORING BREAKDOWN ===
Opportunity Score: {score}/10
- Budget: ${budget}
- Skills: {', '.join(job.get('skills', [])[:5])}
- Type: {job_type}

=== NEXT STEPS ===
1. Review proposal above
2. Check job details at: {url}
3. Customize if needed
4. Submit on {platform.title()}

This proposal was automatically generated using VRGB tone matching.
"""

    # Build Trello card description
    score_emoji = "🎯" if score >= 8 else "⭐" if score >= 7 else "👀"
    trello_title = f"{score_emoji} {score}/10 - {title[:50]}"

    trello_description = f"""**Opportunity Score: {score}/10**

**VRGB-Generated Proposal**
*Tone: {vrgb_desc}*
*Type: {job_type}*

---

{proposal_text}

---

**Job Details**
- Platform: {platform.title()}
- Budget: ${budget}
- Skills: {', '.join(job.get('skills', []))}
- Posted: {job.get('posted_at', 'Unknown')}
- URL: {url}

**Client Info**
{_format_client_info(job.get('client_info', {}))}

**VRGB Coordinates**
- Formality: `{vrgb_used.get('formality_level', 'N/A')}`
- Humor: `{vrgb_used.get('humor_intensity', 'N/A')}`
- Rationale: {vrgb_used.get('rationale', 'N/A')}
"""

    # Determine Trello list based on score
    if score >= 8:
        trello_list = "High-Priority Leads"
    elif score >= 7:
        trello_list = "Qualified Leads"
    else:
        trello_list = "Review Later"

    # Determine labels
    labels = [platform, f"score-{score}", job_type]
    if score >= 8:
        labels.append("high-priority")

    # Create cuesheet
    cuesheet = {
        "cuesheet_id": cuesheet_id,
        "title": f"{platform.title()} Opportunity: {title[:60]} (Score: {score}/10)",
        "description": f"Auto-generated proposal for {platform} job",
        "vrgb_metadata": {
            "note": f"Proposal generated with {job_type} tone",
            "opportunity_score": score,
            "generation_method": proposal_result.get('method', 'unknown')
        },
        "cues": [
            {
                "cue_id": f"proposal-email-{job_id}-{{timestamp}}",
                "vrgb": {
                    "formality_level": vrgb_used.get('formality_level'),
                    "humor_intensity": vrgb_used.get('humor_intensity')
                },
                "vrgb_source": vrgb_used.get('rationale', 'Auto-detected from job'),
                "tool": "email-me",
                "payload": {
                    "subject": email_subject,
                    "message": email_message,
                    "timestamp": "{iso8601_timestamp}"
                }
            },
            {
                "cue_id": f"proposal-trello-{job_id}-{{timestamp}}",
                "vrgb": {
                    "formality_level": vrgb_used.get('formality_level'),
                    "humor_intensity": vrgb_used.get('humor_intensity')
                },
                "vrgb_source": vrgb_used.get('rationale', 'Auto-detected from job'),
                "tool": "add-to-trello",
                "payload": {
                    "title": trello_title,
                    "description": trello_description,
                    "list": trello_list,
                    "labels": labels
                }
            }
        ]
    }

    return cuesheet


def _format_client_info(client_info: Dict) -> str:
    """Format client info for display"""
    if not client_info:
        return "No client info available"

    parts = []

    if 'company' in client_info:
        parts.append(f"- Company: {client_info['company']}")

    if 'location' in client_info:
        parts.append(f"- Location: {client_info['location']}")

    if 'payment_verified' in client_info:
        verified = "✅ Yes" if client_info['payment_verified'] else "❌ No"
        parts.append(f"- Payment Verified: {verified}")

    if 'jobs_posted' in client_info:
        parts.append(f"- Jobs Posted: {client_info['jobs_posted']}")

    if 'rating' in client_info:
        parts.append(f"- Rating: {client_info['rating']}/5")

    return '\n'.join(parts) if parts else "No client info available"


# TODO: Add more cue types
# def add_calendar_reminder(cuesheet: dict, deadline: str):
#     """Add calendar reminder for application deadline"""
#     pass
#
# def add_follow_up_cue(cuesheet: dict, follow_up_date: str):
#     """Schedule follow-up message if no response"""
#     pass
