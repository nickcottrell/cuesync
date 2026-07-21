"""
Email Parsers for Job Platforms

Detects platform and parses job alert emails from:
- Upwork
- Indeed
- LinkedIn
"""

from .upwork_parser import parse_upwork_email
from .indeed_parser import parse_indeed_email
from .linkedin_parser import parse_linkedin_email


def detect_platform(from_address: str, subject: str, body: str) -> str:
    """
    Detect job platform from email metadata

    Args:
        from_address: Email sender
        subject: Email subject line
        body: Email body text

    Returns:
        Platform name: "upwork", "indeed", "linkedin", or "unknown"
    """

    from_lower = from_address.lower()
    subject_lower = subject.lower()

    # Upwork
    if "upwork.com" in from_lower or "upwork" in subject_lower:
        return "upwork"

    # Indeed
    if "indeed.com" in from_lower or "indeed" in subject_lower:
        return "indeed"

    # LinkedIn
    if "linkedin.com" in from_lower or "linkedin" in subject_lower:
        return "linkedin"

    return "unknown"


def parse_job_email(body: str, subject: str, from_address: str, platform: str) -> dict:
    """
    Parse job email based on platform

    Args:
        body: Email body text
        subject: Email subject
        from_address: Sender email
        platform: Platform name (upwork/indeed/linkedin)

    Returns:
        Job dictionary with standardized fields:
        {
            "job_id": str,
            "title": str,
            "budget": int,
            "description": str,
            "skills": list[str],
            "url": str,
            "posted_at": str (ISO8601),
            "deadline": str (ISO8601) | None,
            "platform": str,
            "client_info": dict,
            "raw_email": str
        }

        Returns None if parsing fails
    """

    if platform == "upwork":
        return parse_upwork_email(body, subject)

    elif platform == "indeed":
        return parse_indeed_email(body, subject)

    elif platform == "linkedin":
        return parse_linkedin_email(body, subject)

    else:
        # Unknown platform - return basic info
        return {
            "job_id": f"unknown-{hash(body)}"[:16],
            "title": subject,
            "budget": 0,
            "description": body[:500],
            "skills": [],
            "url": "",
            "posted_at": "",
            "deadline": None,
            "platform": "unknown",
            "client_info": {},
            "raw_email": body
        }
